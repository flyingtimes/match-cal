#!/usr/bin/env python3
"""
基于HTTP的心算对战游戏服务器
不使用WebSocket，采用HTTP轮询方式实现实时功能
"""

import asyncio
import json
import logging
import time
import os
import mimetypes
import argparse
import socket
from typing import Dict, List, Optional, Set
import random
import string
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from aiohttp import web, WSMsgType
import aiohttp_cors

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 游戏常量
DURATION = 60  # 游戏时长（秒）
PROBLEM_COUNT = 200  # 题目池大小
PLAYER_TIMEOUT = 15  # 玩家超时时间（秒）
POLL_INTERVAL = 2  # 轮询间隔（秒）

@dataclass
class Problem:
    """题目数据结构"""
    a: int
    b: int
    op: str
    answer: int

@dataclass
class Player:
    """玩家数据结构"""
    id: str
    name: str
    last_seen: float
    correct: int = 0
    wrong: int = 0
    attempted: int = 0
    online: bool = True

@dataclass
class Room:
    """房间数据结构"""
    id: str
    state: str  # 'waiting', 'running', 'finished'
    created_at: float
    duration: int = DURATION
    problem_count: int = PROBLEM_COUNT
    problems: List[Problem] = None
    start_ts: Optional[float] = None
    finished_at: Optional[float] = None

class HTTPGameServer:
    """HTTP游戏服务器主类"""
    
    def __init__(self):
        # 房间数据
        self.rooms: Dict[str, Room] = {}
        # 房间内玩家列表
        self.room_players: Dict[str, Dict[str, Player]] = {}
        # 玩家到房间的映射
        self.player_rooms: Dict[str, str] = {}

    def generate_room_id(self, length=3):
        """生成房间ID"""
        return ''.join(random.choices(string.digits, k=length))

    def generate_player_name(self, player_id):
        """生成玩家名称"""
        return f"P{player_id}"

    def generate_problems(self, count):
        """生成题目列表"""
        problems = []
        for _ in range(count):
            op = '+' if random.random() < 0.5 else '-'
            a = random.randint(10, 99)
            b = random.randint(10, 99)
            if op == '-' and a < b:
                a, b = b, a
            answer = a + b if op == '+' else a - b
            problems.append(Problem(a=a, b=b, op=op, answer=answer))
        return problems

    def register_player(self, player_id):
        """注册玩家（如果房间不存在会自动创建）"""
        logger.info(f"玩家注册: {player_id}")
        return True

    def create_room(self, player_id):
        """创建房间"""
        room_id = self.generate_room_id()
        room = Room(
            id=room_id,
            state='waiting',
            created_at=time.time()
        )
        self.rooms[room_id] = room
        self.room_players[room_id] = {}
        
        # 将创建者加入房间
        player = Player(
            id=player_id,
            name=self.generate_player_name(player_id),
            last_seen=time.time()
        )
        
        self.room_players[room_id][player_id] = player
        self.player_rooms[player_id] = room_id
        
        logger.info(f"玩家 {player_id} 创建房间 {room_id}")
        return room_id

    def join_room(self, player_id, room_id):
        """加入房间"""
        if room_id not in self.rooms:
            logger.warning(f"房间 {room_id} 不存在")
            return False
        
        if room_id not in self.room_players:
            self.room_players[room_id] = {}
        
        # 如果玩家已经在其他房间，先离开
        old_room_id = self.player_rooms.get(player_id)
        if old_room_id and old_room_id in self.room_players:
            self.room_players[old_room_id].pop(player_id, None)
        
        player = Player(
            id=player_id,
            name=self.generate_player_name(player_id),
            last_seen=time.time()
        )
        
        self.room_players[room_id][player_id] = player
        self.player_rooms[player_id] = room_id
        
        logger.info(f"玩家 {player_id} 加入房间 {room_id}")
        return True

    def leave_room(self, player_id):
        """离开房间"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players:
            self.room_players[room_id].pop(player_id, None)
            self.player_rooms.pop(player_id, None)
            logger.info(f"玩家 {player_id} 离开房间 {room_id}")

    def start_game(self, player_id):
        """开始游戏"""
        room_id = self.player_rooms.get(player_id)
        logger.info(f"玩家 {player_id} 请求开始游戏，房间ID: {room_id}")
        
        if not room_id or room_id not in self.rooms:
            logger.warning(f"房间不存在或玩家不在房间中: room_id={room_id}, player_id={player_id}")
            return False
        
        room = self.rooms[room_id]
        logger.info(f"房间当前状态: {room.state}")
        
        if room.state != 'waiting':
            logger.warning(f"房间状态不是waiting: {room.state}")
            return False
        
        # 检查是否有足够的在线玩家
        online_players = [p for p in self.room_players[room_id].values() if p.online]
        logger.info(f"在线玩家数量: {len(online_players)}, 需要至少2个")
        
        if len(online_players) < 2:
            logger.warning(f"在线玩家不足: {len(online_players)} < 2")
            return False
        
        # 生成题目
        problems = self.generate_problems(PROBLEM_COUNT)
        
        # 更新房间状态
        room.state = 'running'
        room.start_ts = time.time()
        room.problems = [asdict(p) for p in problems]
        
        # 重置所有玩家统计
        for player in self.room_players[room_id].values():
            player.correct = 0
            player.wrong = 0
            player.attempted = 0
            player.last_seen = time.time()
        
        # 设置游戏结束定时器
        asyncio.create_task(self.schedule_game_end(room_id))
        
        logger.info(f"房间 {room_id} 游戏开始")
        return True

    async def schedule_game_end(self, room_id):
        """定时结束游戏"""
        await asyncio.sleep(DURATION)
        if room_id in self.rooms and self.rooms[room_id].state == 'running':
            await self.finish_game(room_id)

    async def finish_game(self, room_id):
        """结束游戏"""
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        room.state = 'finished'
        room.finished_at = time.time()
        
        logger.info(f"房间 {room_id} 游戏结束")

    def update_player_stats(self, player_id, correct, wrong, attempted):
        """更新玩家统计"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players and player_id in self.room_players[room_id]:
            player = self.room_players[room_id][player_id]
            player.correct = correct
            player.wrong = wrong
            player.attempted = attempted
            player.last_seen = time.time()

    def update_player_name(self, player_id, new_name):
        """更新玩家名称"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players and player_id in self.room_players[room_id]:
            old_name = self.room_players[room_id][player_id].name
            self.room_players[room_id][player_id].name = new_name
            self.room_players[room_id][player_id].last_seen = time.time()
            logger.info(f"玩家 {player_id} 更改名称: {old_name} -> {new_name}")
            return True
        else:
            logger.warning(f"无法更新玩家 {player_id} 的名称: 房间不存在或玩家不在房间中")
            return False

    def restart_game(self, player_id):
        """重新开始游戏（保持房间号）"""
        room_id = self.player_rooms.get(player_id)
        if not room_id or room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        # 保持房间状态为waiting，但不清除房间ID
        room.state = 'waiting'
        room.problems = []
        room.start_ts = None
        room.finished_at = None
        
        # 重置所有玩家统计
        for player in self.room_players[room_id].values():
            player.correct = 0
            player.wrong = 0
            player.attempted = 0
            player.last_seen = time.time()
        
        logger.info(f"房间 {room_id} 游戏重置（保持房间号）")
        return True

    def get_room_status(self, room_id):
        """获取房间状态"""
        if room_id not in self.rooms or room_id not in self.room_players:
            return None
        
        room = self.rooms[room_id]
        players = self.room_players[room_id]
        
        # 检查不活跃玩家
        current_time = time.time()
        for player_id, player in players.items():
            if player.online and current_time - player.last_seen > PLAYER_TIMEOUT:
                player.online = False
                player.last_seen = 0
                logger.info(f"玩家 {player_id} 超时离线")
        
        return {
            'room': asdict(room),
            'players': [asdict(p) for p in players.values()]
        }

    def ping_player(self, player_id):
        """玩家心跳"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players and player_id in self.room_players[room_id]:
            self.room_players[room_id][player_id].last_seen = time.time()
            return True
        return False

# 创建全局服务器实例
game_server = HTTPGameServer()

async def handle_register(request):
    """处理玩家注册"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        success = game_server.register_player(player_id)
        
        if success:
            return web.json_response({
                'success': True,
                'player_id': player_id,
                'message': '注册成功'
            })
        else:
            return web.json_response({'success': False, 'error': '注册失败'}, status=500)
            
    except Exception as e:
        logger.error(f"注册处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_create_room(request):
    """处理创建房间"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        room_id = game_server.create_room(player_id)
        
        return web.json_response({
            'success': True,
            'room_id': room_id,
            'message': f'房间 {room_id} 创建成功'
        })
        
    except Exception as e:
        logger.error(f"创建房间处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_join_room(request):
    """处理加入房间"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        room_id = data.get('room_id')
        
        if not player_id or not room_id:
            return web.json_response({'success': False, 'error': '缺少必要参数'}, status=400)
        
        success = game_server.join_room(player_id, room_id)
        
        return web.json_response({
            'success': success,
            'room_id': room_id if success else None,
            'message': '加入房间成功' if success else '加入房间失败'
        })
        
    except Exception as e:
        logger.error(f"加入房间处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_start_game(request):
    """处理开始游戏"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        success = game_server.start_game(player_id)
        
        return web.json_response({
            'success': success,
            'message': '游戏开始成功' if success else '游戏开始失败'
        })
        
    except Exception as e:
        logger.error(f"开始游戏处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_update_stats(request):
    """处理更新统计"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        correct = data.get('correct', 0)
        wrong = data.get('wrong', 0)
        attempted = data.get('attempted', 0)
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        game_server.update_player_stats(player_id, correct, wrong, attempted)
        
        return web.json_response({
            'success': True,
            'message': '统计更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新统计处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_update_name(request):
    """处理更新名称"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        new_name = data.get('name', '').strip()
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        if not new_name or len(new_name) > 12:
            return web.json_response({'success': False, 'error': '名称无效或过长'}, status=400)
        
        success = game_server.update_player_name(player_id, new_name)
        
        return web.json_response({
            'success': success,
            'message': '名称更新成功' if success else '名称更新失败'
        })
        
    except Exception as e:
        logger.error(f"更新名称处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_restart_game(request):
    """处理重新开始游戏"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        success = game_server.restart_game(player_id)
        
        return web.json_response({
            'success': success,
            'message': '游戏重置成功' if success else '游戏重置失败'
        })
        
    except Exception as e:
        logger.error(f"重新开始游戏处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_get_room_status(request):
    """处理获取房间状态"""
    try:
        room_id = request.match_info.get('room_id')
        
        if not room_id:
            return web.json_response({'success': False, 'error': '缺少room_id'}, status=400)
        
        status = game_server.get_room_status(room_id)
        
        if status:
            return web.json_response({
                'success': True,
                'data': status
            })
        else:
            return web.json_response({'success': False, 'error': '房间不存在'}, status=404)
        
    except Exception as e:
        logger.error(f"获取房间状态处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

async def handle_ping(request):
    """处理心跳"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        
        if not player_id:
            return web.json_response({'success': False, 'error': '缺少player_id'}, status=400)
        
        success = game_server.ping_player(player_id)
        
        return web.json_response({
            'success': success,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"心跳处理错误: {e}")
        return web.json_response({'success': False, 'error': str(e)}, status=500)

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='心算对战游戏HTTP服务器')
    parser.add_argument('--host', default=os.getenv('GAME_HOST', '0.0.0.0'), 
                       help='服务器侦听地址 (默认: 0.0.0.0，允许局域网访问)')
    parser.add_argument('--port', type=int, default=int(os.getenv('HTTP_PORT', '8000')), 
                       help='HTTP服务器端口 (默认: 8000)')
    return parser.parse_args()

async def main():
    """启动HTTP服务器"""
    # 解析命令行参数
    args = parse_args()
    
    # 创建应用
    app = web.Application()
    
    # 配置CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # 添加路由
    routes = [
        web.post('/api/register', handle_register),
        web.post('/api/create_room', handle_create_room),
        web.post('/api/join_room', handle_join_room),
        web.post('/api/start_game', handle_start_game),
        web.post('/api/update_stats', handle_update_stats),
        web.post('/api/update_name', handle_update_name),
        web.post('/api/restart_game', handle_restart_game),
        web.get('/api/room/{room_id}', handle_get_room_status),
        web.post('/api/ping', handle_ping),
    ]
    
    for route in routes:
        resource = app.router.add_route(route.method, route.path, route.handler)
        cors.add(resource)
    
    # 静态文件服务
    app.router.add_static('/', path='.', name='static')
    
    # 服务器配置
    host = args.host
    port = args.port
    
    # 获取本机IP用于显示
    local_ip = get_local_ip()
    
    logger.info("启动HTTP游戏服务器...")
    logger.info(f"服务器配置:")
    logger.info(f"  侦听地址: {host}")
    logger.info(f"  HTTP端口: {port}")
    logger.info(f"  轮询间隔: {POLL_INTERVAL}秒")
    
    # 启动服务器
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info("服务器启动完成！")
    logger.info(f"访问地址:")
    logger.info(f"  本地访问: http://localhost:{port}")
    if host == "0.0.0.0" and local_ip != "127.0.0.1":
        logger.info(f"  局域网访问: http://{local_ip}:{port}")
    
    # 保持服务器运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("服务器停止运行")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务器停止运行")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")