#!/usr/bin/env python3
"""
本地Python WebSocket服务器，替代Firebase实现心算双人对战游戏
使用WebSocket进行实时通信，内存存储游戏数据
"""

import asyncio
import websockets
import json
import logging
import time
from typing import Dict, List, Optional, Set
import random
import string
from dataclasses import dataclass, asdict
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.DEBUG)
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

    def generate_room_id(self, length=6):
        """生成房间ID"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

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
        """重新开始游戏"""
        room_id = self.player_rooms.get(player_id)
        if not room_id or room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        room.state = 'waiting'
        room.problems = []
        room.start_ts = None
        room.finished_at = None
        
        # 重置所有玩家统计
        for player in self.room_players[room_id].values():
            player.correct = 0
            player.wrong = 0
            player.attempted = 0
        
        await self.broadcast_room_update(room_id)
        logger.info(f"房间 {room_id} 游戏重置")
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
        print(f"收到消息: {message_data}")  # 临时调试
        player_id = self.ws_to_player.get(websocket)
        if not player_id:
            logger.warning(f"收到未注册客户端的消息: {message_data}")
            return
        
        try:
            message = json.loads(message_data)
            msg_type = message.get('type')
            print(f"玩家 {player_id} 发送消息: {msg_type}")  # 临时调试
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
        print(f"新客户端连接: {path}")  # 临时调试
        try:
            # 等待客户端发送player_id
            message = await websocket.recv()
            print(f"收到注册消息: {message}")  # 临时调试
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
            print(f"开始监听玩家 {player_id} 的消息")  # 临时调试
            async for message in websocket:
                print(f"收到玩家 {player_id} 的原始消息: {message}")  # 临时调试
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

async def main():
    """启动服务器"""
    server = GameServer()
    
    # 启动心跳检查器
    asyncio.create_task(server.start_heartbeat_checker())
    
    # 启动WebSocket服务器
    host = "localhost"
    port = 8765
    
    logger.info(f"游戏服务器启动在 ws://{host}:{port}")
    
    async with websockets.serve(server.handle_client, host, port):
        await asyncio.Future()  # 保持服务器运行

if __name__ == "__main__":
    asyncio.run(main())