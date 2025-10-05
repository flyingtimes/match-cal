#!/usr/bin/env python3
"""
测试HTTP游戏服务器的API功能
"""

import asyncio
import aiohttp
import json
import time

async def test_api():
    """测试API功能"""
    base_url = "http://localhost:8000"
    player_id = "test123"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 开始测试HTTP游戏服务器API...")
        print("=" * 50)
        
        try:
            # 1. 测试注册玩家
            print("1. 测试玩家注册...")
            async with session.post(f"{base_url}/api/register", 
                                   json={"player_id": player_id}) as resp:
                result = await resp.json()
                print(f"   注册结果: {result}")
                assert result['success'], "玩家注册失败"
            
            # 2. 测试创建房间
            print("\n2. 测试创建房间...")
            async with session.post(f"{base_url}/api/create_room", 
                                   json={"player_id": player_id}) as resp:
                result = await resp.json()
                print(f"   创建房间结果: {result}")
                assert result['success'], "创建房间失败"
                room_id = result['room_id']
                print(f"   房间ID: {room_id}")
            
            # 3. 测试获取房间状态
            print(f"\n3. 测试获取房间状态...")
            async with session.get(f"{base_url}/api/room/{room_id}") as resp:
                result = await resp.json()
                print(f"   房间状态: {result}")
                assert result['success'], "获取房间状态失败"
                assert result['data']['room']['id'] == room_id, "房间ID不匹配"
            
            # 4. 测试心跳
            print(f"\n4. 测试心跳...")
            async with session.post(f"{base_url}/api/ping", 
                                   json={"player_id": player_id}) as resp:
                result = await resp.json()
                print(f"   心跳结果: {result}")
                assert result['success'], "心跳失败"
            
            # 5. 测试更新名称
            print(f"\n5. 测试更新名称...")
            new_name = "测试玩家"
            async with session.post(f"{base_url}/api/update_name", 
                                   json={"player_id": player_id, "name": new_name}) as resp:
                result = await resp.json()
                print(f"   更新名称结果: {result}")
                assert result['success'], "更新名称失败"
            
            # 6. 模拟第二个玩家加入
            print(f"\n6. 测试第二个玩家加入...")
            player2_id = "test456"
            async with session.post(f"{base_url}/api/register", 
                                   json={"player_id": player2_id}) as resp:
                result = await resp.json()
                assert result['success'], "第二个玩家注册失败"
            
            async with session.post(f"{base_url}/api/join_room", 
                                   json={"player_id": player2_id, "room_id": room_id}) as resp:
                result = await resp.json()
                print(f"   第二个玩家加入结果: {result}")
                assert result['success'], "第二个玩家加入失败"
            
            # 7. 检查房间状态（应该有两个玩家）
            print(f"\n7. 检查房间状态...")
            async with session.get(f"{base_url}/api/room/{room_id}") as resp:
                result = await resp.json()
                players = result['data']['players']
                print(f"   房间内玩家数量: {len(players)}")
                assert len(players) == 2, "房间内玩家数量不正确"
                
                # 检查玩家名称是否正确更新
                player1 = next(p for p in players if p['id'] == player_id)
                assert player1['name'] == new_name, "玩家名称未正确更新"
                print(f"   玩家1名称: {player1['name']}")
                print(f"   玩家2名称: {players[0]['name'] if players[0]['id'] != player_id else players[1]['name']}")
            
            # 8. 测试开始游戏
            print(f"\n8. 测试开始游戏...")
            async with session.post(f"{base_url}/api/start_game", 
                                   json={"player_id": player_id}) as resp:
                result = await resp.json()
                print(f"   开始游戏结果: {result}")
                assert result['success'], "开始游戏失败"
            
            # 9. 检查游戏状态
            print(f"\n9. 检查游戏状态...")
            await asyncio.sleep(1)  # 等待一秒让服务器处理
            async with session.get(f"{base_url}/api/room/{room_id}") as resp:
                result = await resp.json()
                room = result['data']['room']
                print(f"   游戏状态: {room['state']}")
                assert room['state'] == 'running', "游戏状态不正确"
                assert len(room['problems']) > 0, "题目未生成"
                print(f"   题目数量: {len(room['problems'])}")
            
            # 10. 测试更新统计
            print(f"\n10. 测试更新统计...")
            async with session.post(f"{base_url}/api/update_stats", 
                                   json={"player_id": player_id, "correct": 5, "wrong": 2, "attempted": 7}) as resp:
                result = await resp.json()
                print(f"    更新统计结果: {result}")
                assert result['success'], "更新统计失败"
            
            print("\n" + "=" * 50)
            print("✅ 所有API测试通过！HTTP服务器工作正常。")
            
        except aiohttp.ClientError as e:
            print(f"❌ 网络连接错误: {e}")
            print("请确保HTTP服务器正在运行在 http://localhost:8000")
        except AssertionError as e:
            print(f"❌ 测试失败: {e}")
        except Exception as e:
            print(f"❌ 测试出错: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())