#!/usr/bin/env python3
"""
专门测试用户名称修改通知功能
"""

import asyncio
import websockets
import json
import time

async def test_name_notification():
    """测试名称修改通知功能"""
    uri = "ws://localhost:8765"
    
    # 创建两个测试玩家
    player1_id = "test_player_alice"
    player2_id = "test_player_bob"
    
    try:
        # 连接两个玩家
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
            
            # 等待加入完成并接收房间更新
            print("等待房间状态同步...")
            await asyncio.sleep(1)
            
            # 设置消息监听
            messages_received = {"player1": [], "player2": []}
            
            async def listen_player1():
                try:
                    while True:
                        message = await ws1.recv()
                        data = json.loads(message)
                        messages_received["player1"].append(data)
                        print(f"玩家1收到消息: {data}")
                        
                        # 检查是否收到房间更新（包含名称变更）
                        if data.get('type') == 'room_update':
                            players = data.get('players', [])
                            for p in players:
                                if p['id'] != player1_id:
                                    print(f"玩家1看到对手: {p['name']} (ID: {p['id']})")
                except websockets.exceptions.ConnectionClosed:
                    print("玩家1连接关闭")
            
            async def listen_player2():
                try:
                    while True:
                        message = await ws2.recv()
                        data = json.loads(message)
                        messages_received["player2"].append(data)
                        print(f"玩家2收到消息: {data}")
                        
                        # 检查是否收到房间更新（包含名称变更）
                        if data.get('type') == 'room_update':
                            players = data.get('players', [])
                            for p in players:
                                if p['id'] != player2_id:
                                    print(f"玩家2看到对手: {p['name']} (ID: {p['id']})")
                except websockets.exceptions.ConnectionClosed:
                    print("玩家2连接关闭")
            
            # 启动监听任务
            task1 = asyncio.create_task(listen_player1())
            task2 = asyncio.create_task(listen_player2())
            
            # 等待初始房间同步
            await asyncio.sleep(2)
            
            print("\n=== 开始测试名称修改通知 ===")
            
            # 测试1: 玩家1修改名称
            print("测试1: 玩家1修改名称为 'Alice'...")
            await ws1.send(json.dumps({
                'type': 'update_player_name',
                'name': 'Alice'
            }))
            
            # 等待通知传播
            await asyncio.sleep(3)
            
            # 检查玩家2是否收到了玩家1的名称更新
            player1_updates = [msg for msg in messages_received["player2"] 
                              if msg.get('type') == 'room_update']
            if player1_updates:
                print("✅ 玩家2收到了房间更新（可能包含名称变更）")
                # 检查最新的房间状态
                latest_update = player1_updates[-1]
                players = latest_update.get('players', [])
                alice_found = any(p.get('name') == 'Alice' and p.get('id') == player1_id 
                                for p in players)
                if alice_found:
                    print("✅ 玩家2成功看到玩家1的新名称 'Alice'")
                else:
                    print("❌ 玩家2没有看到玩家1的新名称")
            else:
                print("❌ 玩家2没有收到任何房间更新")
            
            # 测试2: 玩家2修改名称
            print("\n测试2: 玩家2修改名称为 'Bob'...")
            await ws2.send(json.dumps({
                'type': 'update_player_name',
                'name': 'Bob'
            }))
            
            # 等待通知传播
            await asyncio.sleep(3)
            
            # 检查玩家1是否收到了玩家2的名称更新
            player2_updates = [msg for msg in messages_received["player1"] 
                              if msg.get('type') == 'room_update']
            if player2_updates:
                print("✅ 玩家1收到了房间更新（可能包含名称变更）")
                # 检查最新的房间状态
                latest_update = player2_updates[-1]
                players = latest_update.get('players', [])
                bob_found = any(p.get('name') == 'Bob' and p.get('id') == player2_id 
                              for p in players)
                if bob_found:
                    print("✅ 玩家1成功看到玩家2的新名称 'Bob'")
                else:
                    print("❌ 玩家1没有看到玩家2的新名称")
            else:
                print("❌ 玩家1没有收到任何房间更新")
            
            # 取消监听任务
            task1.cancel()
            task2.cancel()
            
            print("\n=== 测试完成 ===")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_name_notification())
    except KeyboardInterrupt:
        print("测试被中断")
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()