#!/usr/bin/env python3
"""
测试用户名称修改功能
"""

import asyncio
import websockets
import json
import time

async def test_name_change():
    """测试名称修改功能"""
    uri = "ws://localhost:8765"
    
    # 创建两个测试玩家
    player1_id = "test_player_1"
    player2_id = "test_player_2"
    
    try:
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
            await asyncio.sleep(1)
            
            # 监听房间更新
            print("监听房间更新和名称修改...")
            
            async def listen_messages(ws, player_name):
                try:
                    async for message in ws:
                        data = json.loads(message)
                        if data.get('type') == 'room_update':
                            players = data.get('players', [])
                            for p in players:
                                if p['id'] != player_name:
                                    print(f"{player_name} 收到房间更新: 玩家 {p['name']} (ID: {p['id']}) 在线: {p['online']}")
                        elif data.get('type') == 'name_updated':
                            print(f"{player_name} 收到名称更新通知: {data}")
                except websockets.exceptions.ConnectionClosed:
                    print(f"{player_name} 连接关闭")
            
            # 启动监听任务
            task1 = asyncio.create_task(listen_messages(ws1, "玩家1"))
            task2 = asyncio.create_task(listen_messages(ws2, "玩家2"))
            
            # 等待初始房间同步
            await asyncio.sleep(1)
            
            # 玩家1修改名称
            print("玩家1修改名称为 'Alice'...")
            await ws1.send(json.dumps({
                'type': 'update_player_name',
                'name': 'Alice'
            }))
            
            # 等待名称更新传播
            await asyncio.sleep(2)
            
            # 玩家2修改名称
            print("玩家2修改名称为 'Bob'...")
            await ws2.send(json.dumps({
                'type': 'update_player_name',
                'name': 'Bob'
            }))
            
            # 等待名称更新传播
            await asyncio.sleep(2)
            
            # 取消监听任务
            task1.cancel()
            task2.cancel()
            
            print("✅ 名称修改测试完成")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("请确保服务器正在运行在 ws://localhost:8765")

if __name__ == "__main__":
    try:
        asyncio.run(test_name_change())
    except KeyboardInterrupt:
        print("测试被中断")
    except Exception as e:
        print(f"测试出错: {e}")