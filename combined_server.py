#!/usr/bin/env python3
"""
合并的服务器：同时提供HTTP文件服务和WebSocket游戏服务
使用单一进程和端口，简化部署和使用
"""

import asyncio
import websockets
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
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import websockets.server
from websockets.server import WebSocketServerProtocol

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 游戏常量
DURATION = 60  # 游戏时长（秒）
PROBLEM_COUNT = 200  # 题目池大小
HEARTBEAT_INTERVAL = 4  # 心跳间隔（秒）
PLAYER_TIMEOUT = 12  # 玩家超时时间（秒）

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

class GameServer:
    """游戏服务器主类"""
    
    def __init__(self):
        # 存储所有连接的客户端
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        # 房间数据
        self.rooms: Dict[str, Room] = {}
        # 房间内玩家列表
        self.room_players: Dict[str, Dict[str, Player]] = {}
        # 玩家到房间的映射
        self.player_rooms: Dict[str, str] = {}
        # WebSocket连接到玩家ID的映射
        self.ws_to_player: Dict[websockets.WebSocketServerProtocol, str] = {}

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

    async def register_client(self, websocket, player_id):
        """注册新客户端"""
        self.clients[player_id] = websocket
        self.ws_to_player[websocket] = player_id
        logger.info(f"客户端注册成功: {player_id}")

    async def unregister_client(self, websocket):
        """注销客户端"""
        player_id = self.ws_to_player.get(websocket)
        if player_id:
            # 设置玩家离线
            room_id = self.player_rooms.get(player_id)
            if room_id and room_id in self.room_players:
                if player_id in self.room_players[room_id]:
                    self.room_players[room_id][player_id].online = False
                    self.room_players[room_id][player_id].last_seen = 0
                    await self.broadcast_room_update(room_id)
            
            # 清理连接
            self.clients.pop(player_id, None)
            self.ws_to_player.pop(websocket, None)
            self.player_rooms.pop(player_id, None)
            logger.info(f"客户端注销: {player_id}")

    async def create_room(self, player_id):
        """创建房间"""
        room_id = self.generate_room_id()
        room = Room(
            id=room_id,
            state='waiting',
            created_at=time.time()
        )
        self.rooms[room_id] = room
        self.room_players[room_id] = {}
        
        # 将创建者加入房间（不立即广播，等房间创建完成后再广播）
        if room_id not in self.room_players:
            self.room_players[room_id] = {}
        
        player = Player(
            id=player_id,
            name=self.generate_player_name(player_id),
            last_seen=time.time()
        )
        
        self.room_players[room_id][player_id] = player
        self.player_rooms[player_id] = room_id
        
        logger.info(f"玩家 {player_id} 加入房间 {room_id}")
        return room_id

    async def join_room(self, player_id, room_id):
        """加入房间"""
        if room_id not in self.rooms:
            return False
        
        if room_id not in self.room_players:
            self.room_players[room_id] = {}
        
        player = Player(
            id=player_id,
            name=self.generate_player_name(player_id),
            last_seen=time.time()
        )
        
        self.room_players[room_id][player_id] = player
        self.player_rooms[player_id] = room_id
        
        await self.broadcast_room_update(room_id)
        logger.info(f"玩家 {player_id} 加入房间 {room_id}")
        return True

    async def leave_room(self, player_id):
        """离开房间"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players:
            self.room_players[room_id].pop(player_id, None)
            self.player_rooms.pop(player_id, None)
            await self.broadcast_room_update(room_id)
            logger.info(f"玩家 {player_id} 离开房间 {room_id}")

    async def start_game(self, player_id):
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
        logger.info(f"玩家详情: {[{p.name: p.online} for p in self.room_players[room_id].values()]}")
        
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
        
        await self.broadcast_room_update(room_id)
        
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
        
        await self.broadcast_room_update(room_id)
        logger.info(f"房间 {room_id} 游戏结束")

    async def update_player_stats(self, player_id, correct, wrong, attempted):
        """更新玩家统计"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players and player_id in self.room_players[room_id]:
            player = self.room_players[room_id][player_id]
            player.correct = correct
            player.wrong = wrong
            player.attempted = attempted
            player.last_seen = time.time()
            await self.broadcast_room_update(room_id)

    async def update_player_name(self, player_id, new_name):
        """更新玩家名称"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players and player_id in self.room_players[room_id]:
            old_name = self.room_players[room_id][player_id].name
            self.room_players[room_id][player_id].name = new_name
            self.room_players[room_id][player_id].last_seen = time.time()
            logger.info(f"玩家 {player_id} 更改名称: {old_name} -> {new_name}")
            logger.info(f"开始广播房间 {room_id} 的名称更新")
            await self.broadcast_room_update(room_id)
            logger.info(f"房间 {room_id} 名称更新广播完成")
        else:
            logger.warning(f"无法更新玩家 {player_id} 的名称: 房间不存在或玩家不在房间中")

    async def restart_game(self, player_id):
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
        # 注意：房间ID保持不变，这样玩家可以继续使用相同的房间号
        
        # 重置所有玩家统计
        for player in self.room_players[room_id].values():
            player.correct = 0
            player.wrong = 0
            player.attempted = 0
            player.last_seen = time.time()  # 更新最后活跃时间
        
        await self.broadcast_room_update(room_id)
        logger.info(f"房间 {room_id} 游戏重置（保持房间号）")
        return True

    async def broadcast_room_update(self, room_id):
        """广播房间更新"""
        if room_id not in self.rooms or room_id not in self.room_players:
            logger.warning(f"广播房间更新失败: 房间 {room_id} 不存在")
            return
        
        room = self.rooms[room_id]
        players = self.room_players[room_id]
        
        logger.info(f"广播房间更新 {room_id}: 状态={room.state}, 玩家数={len(players)}")
        
        # 构建消息
        message = {
            'type': 'room_update',
            'room': asdict(room),
            'players': [asdict(p) for p in players.values()]
        }
        
        # 发送给房间内所有在线玩家
        sent_count = 0
        for player_id, player in players.items():
            if player.online and player_id in self.clients:
                try:
                    await self.clients[player_id].send(json.dumps(message))
                    sent_count += 1
                    logger.debug(f"发送房间更新给玩家 {player_id}")
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"向玩家 {player_id} 发送消息失败，连接已关闭")
                except Exception as e:
                    logger.error(f"向玩家 {player_id} 发送消息时出错: {e}")
        
        logger.info(f"房间更新广播完成，发送给 {sent_count} 个玩家")

    async def heartbeat(self, player_id):
        """处理心跳"""
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.room_players and player_id in self.room_players[room_id]:
            self.room_players[room_id][player_id].last_seen = time.time()

    async def check_inactive_players(self):
        """检查不活跃玩家"""
        current_time = time.time()
        for room_id, players in self.room_players.items():
            for player_id, player in players.items():
                if player.online and current_time - player.last_seen > PLAYER_TIMEOUT:
                    player.online = False
                    player.last_seen = 0
                    logger.info(f"玩家 {player_id} 超时离线")
                    await self.broadcast_room_update(room_id)

    async def handle_message(self, websocket, message_data):
        """处理客户端消息"""
        player_id = self.ws_to_player.get(websocket)
        if not player_id:
            logger.warning(f"收到未注册客户端的消息: {message_data}")
            return
        
        try:
            message = json.loads(message_data)
            msg_type = message.get('type')
            logger.debug(f"收到玩家 {player_id} 的消息类型: {msg_type}")
            logger.debug(f"消息内容: {message}")
            
            if msg_type == 'create_room':
                room_id = await self.create_room(player_id)
                # 先发送房间创建响应
                await websocket.send(json.dumps({
                    'type': 'room_created',
                    'room_id': room_id
                }))
                # 然后立即广播房间更新
                await self.broadcast_room_update(room_id)
            
            elif msg_type == 'join_room':
                room_id = message.get('room_id')
                success = await self.join_room(player_id, room_id)
                await websocket.send(json.dumps({
                    'type': 'join_result',
                    'success': success,
                    'room_id': room_id if success else None
                }))
            
            elif msg_type == 'start_game':
                success = await self.start_game(player_id)
                await websocket.send(json.dumps({
                    'type': 'start_result',
                    'success': success
                }))
            
            elif msg_type == 'update_stats':
                correct = message.get('correct', 0)
                wrong = message.get('wrong', 0)
                attempted = message.get('attempted', 0)
                await self.update_player_stats(player_id, correct, wrong, attempted)
            
            elif msg_type == 'update_player_name':
                logger.info(f"收到玩家 {player_id} 的名称更新请求")
                new_name = message.get('name', '').strip()
                logger.info(f"新名称: '{new_name}' (长度: {len(new_name)})")
                if new_name and len(new_name) <= 12:
                    await self.update_player_name(player_id, new_name)
                else:
                    logger.warning(f"无效的用户名称: '{new_name}' (长度: {len(new_name)})")
            
            elif msg_type == 'restart_game':
                success = await self.restart_game(player_id)
                await websocket.send(json.dumps({
                    'type': 'restart_result',
                    'success': success
                }))
            
            elif msg_type == 'heartbeat':
                await self.heartbeat(player_id)
            
        except json.JSONDecodeError:
            logger.error(f"无法解析消息: {message_data}")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        player_id = None
        logger.info(f"新客户端连接: {path}")
        try:
            # 等待客户端发送player_id
            message = await websocket.recv()
            data = json.loads(message)
            if data.get('type') == 'register':
                player_id = data.get('player_id')
                if not player_id:
                    await websocket.close()
                    return
                
                await self.register_client(websocket, player_id)
                
                # 发送注册成功消息
                await websocket.send(json.dumps({
                    'type': 'registered',
                    'player_id': player_id
                }))
                
                # 如果URL中有房间参数，自动加入
                if path.startswith('/room/'):
                    room_id = path.split('/')[-1]
                    await self.join_room(player_id, room_id)
            
            # 持续处理消息
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端连接关闭: {player_id}")
        except Exception as e:
            logger.error(f"处理客户端连接时出错: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start_heartbeat_checker(self):
        """启动心跳检查器"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await self.check_inactive_players()

class HTTPHandler:
    """HTTP请求处理器"""
    
    def __init__(self, document_root='.'):
        self.document_root = document_root
    
    def get_mime_type(self, filepath):
        """获取文件的MIME类型"""
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            if filepath.endswith('.js'):
                return 'application/javascript'
            elif filepath.endswith('.css'):
                return 'text/css'
            else:
                return 'text/html'
        return mime_type
    
    async def handle_request(self, reader, writer):
        """处理HTTP请求"""
        try:
            # 读取请求行
            request_line = await reader.readline()
            request_line = request_line.decode('utf-8').strip()
            
            if not request_line:
                writer.close()
                return
            
            # 解析请求
            method, path, version = request_line.split(' ')
            
            # 读取头部
            headers = {}
            while True:
                header_line = await reader.readline()
                header_line = header_line.decode('utf-8').strip()
                if not header_line:
                    break
                if ':' in header_line:
                    key, value = header_line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # 构建文件路径
            if path == '/':
                filepath = os.path.join(self.document_root, 'index.html')
            else:
                filepath = os.path.join(self.document_root, path.lstrip('/'))
            
            # 安全检查
            filepath = os.path.abspath(filepath)
            if not filepath.startswith(os.path.abspath(self.document_root)):
                # 403 Forbidden
                response = "HTTP/1.1 403 Forbidden\r\n\r\n"
                writer.write(response.encode())
                writer.close()
                return
            
            # 检查文件是否存在
            if os.path.exists(filepath) and os.path.isfile(filepath):
                # 读取文件内容
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                # 构建响应
                mime_type = self.get_mime_type(filepath)
                response = f"HTTP/1.1 200 OK\r\nContent-Type: {mime_type}\r\nContent-Length: {len(content)}\r\n\r\n"
                writer.write(response.encode())
                writer.write(content)
            else:
                # 404 Not Found
                html_content = b"""
<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
<h1>404 Not Found</h1>
<p>The requested URL was not found on this server.</p>
</body>
</html>
"""
                response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(html_content)}\r\n\r\n"
                writer.write(response.encode())
                writer.write(html_content)
            
            writer.close()
            
        except Exception as e:
            logger.error(f"处理HTTP请求时出错: {e}")
            writer.close()

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个UDP socket连接到外网地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='心算对战游戏服务器')
    parser.add_argument('--host', default=os.getenv('GAME_HOST', '0.0.0.0'), 
                       help='服务器侦听地址 (默认: 0.0.0.0，允许局域网访问)')
    parser.add_argument('--http-port', type=int, default=int(os.getenv('HTTP_PORT', '8000')), 
                       help='HTTP服务器端口 (默认: 8000)')
    parser.add_argument('--ws-port', type=int, default=int(os.getenv('WS_PORT', '8765')), 
                       help='WebSocket服务器端口 (默认: 8765)')
    return parser.parse_args()

async def main():
    """启动合并服务器"""
    # 解析命令行参数
    args = parse_args()
    
    # 创建游戏服务器
    game_server = GameServer()
    
    # 启动心跳检查器
    asyncio.create_task(game_server.start_heartbeat_checker())
    
    # 启动HTTP服务器
    http_handler = HTTPHandler()
    
    # 服务器配置
    host = args.host
    http_port = args.http_port
    ws_port = args.ws_port
    
    # 获取本机IP用于显示
    local_ip = get_local_ip()
    
    logger.info("启动合并服务器...")
    logger.info(f"服务器配置:")
    logger.info(f"  侦听地址: {host}")
    logger.info(f"  HTTP端口: {http_port}")
    logger.info(f"  WebSocket端口: {ws_port}")
    
    # 启动HTTP服务器
    http_server = await asyncio.start_server(
        http_handler.handle_request,
        host,
        http_port
    )
    
    # 启动WebSocket服务器
    async with websockets.serve(game_server.handle_client, host, ws_port):
        logger.info("服务器启动完成！")
        logger.info(f"访问地址:")
        logger.info(f"  本地访问: http://localhost:{http_port}")
        if host == "0.0.0.0" and local_ip != "127.0.0.1":
            logger.info(f"  局域网访问: http://{local_ip}:{http_port}")
            logger.info(f"  WebSocket: ws://{local_ip}:{ws_port}")
        await asyncio.Future()  # 保持服务器运行

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务器停止运行")
    except Exception as e:
        logger.error(f"服务器运行出错: {e}")