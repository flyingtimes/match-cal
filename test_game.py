#!/usr/bin/env python3
"""
测试游戏功能的简单脚本
"""

import asyncio
import websockets
import json
import time

async def test_game():
    """测试游戏功能"""
    uri = "ws://localhost:8765"
    
    # 创建两个测试玩家
    player1_id = "test_player_1"
    player2_id = "test_player_2"
    
    async with websockets.connect(uri) as ws1, websockets.connect(uri) as ws2:
        print("✅ 两个WebSocket连接建立成功")
        
        # 注册玩家1
        await ws1.send(json.dumps({
            'type': 'register',
            'player_id': player1_id
        }))
        response1 = await ws1.recv()
        print(f"玩家1注册响应: {json.loads(response1)}")
        
        # 注册玩家2
        await ws2.send(json.dumps({
            'type': 'register',
            'player_id': player2_id
        }))
        response2 = await ws2.recv()
        print(f"玩家2注册响应: {json.loads(response2)}")
        
        # 玩家1创建房间
        await ws1.send(json.dumps({
            'type': 'create_room'
        }))
        response = await ws1.recv()
        room_data = json.loads(response)
        room_id = room_data.get('room_id')
        print(f"房间创建成功: {room_id}")
        
        # 等待房间创建完成
        await asyncio.sleep(0.5)
        
        # 玩家2加入房间
        await ws2.send(json.dumps({
            'type': 'join_room',
            'room_id': room_id
        }))
        response = await ws2.recv()
        join_data = json.loads(response)
        print(f"玩家2加入房间响应: {join_data}")
        
        # 等待加入完成
        await asyncio.sleep(0.5)
        
        # 等待一下让房间状态同步
        await asyncio.sleep(1)
        
        # 玩家1开始游戏
        await ws1.send(json.dumps({
            'type': 'start_game'
        }))
        response = await ws1.recv()
        print(f"开始游戏响应: {json.loads(response)}")
        
        # 监听房间更新
        print("监听房间更新...")
        for i in range(3):
            try:
                response1 = await asyncio.wait_for(ws1.recv(), timeout=2)
                data1 = json.loads(response1)
                if data1.get('type') == 'room_update':
                    print(f"玩家1收到房间更新: 游戏状态={data1['room']['state']}")
                
                response2 = await asyncio.wait_for(ws2.recv(), timeout=2)
                data2 = json.loads(response2)
                if data2.get('type') == 'room_update':
                    print(f"玩家2收到房间更新: 游戏状态={data2['room']['state']}")
            except asyncio.TimeoutError:
                break
        
        print("✅ 游戏功能测试完成")

if __name__ == "__main__":
    try:
        asyncio.run(test_game())
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("请确保服务器正在运行在 ws://localhost:8765")