#!/usr/bin/env python3
"""
测试网络配置脚本
验证服务器的host配置是否正确工作
"""

import subprocess
import sys
import time
import requests
import socket

def test_server_startup():
    """测试服务器启动和局域网配置"""
    print("🧪 测试服务器网络配置...")
    print("=" * 50)
    
    # 测试默认配置（允许局域网访问）
    print("1️⃣ 测试默认配置（允许局域网访问）:")
    print("   启动命令: python3 combined_server.py --host 0.0.0.0")
    
    try:
        # 启动服务器进程
        process = subprocess.Popen([
            sys.executable, "combined_server.py", 
            "--host", "0.0.0.0",
            "--http-port", "8001"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务器启动
        time.sleep(2)
        
        # 检查服务器是否正在运行
        if process.poll() is None:
            print("   ✅ 服务器启动成功")
            
            # 测试本地访问
            try:
                response = requests.get("http://localhost:8001", timeout=5)
                if response.status_code == 200:
                    print("   ✅ 本地访问正常")
                else:
                    print(f"   ❌ 本地访问失败，状态码: {response.status_code}")
            except Exception as e:
                print(f"   ❌ 本地访问测试失败: {e}")
            
            # 获取本机IP
            local_ip = socket.gethostbyname(socket.gethostname())
            print(f"   🌐 本机IP地址: {local_ip}")
            print(f"   🌍 局域网访问地址: http://{local_ip}:8001")
            
            # 停止服务器
            process.terminate()
            process.wait()
            print("   ✅ 服务器已停止")
            
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ 服务器启动失败:")
            print(f"      错误信息: {stderr.decode()}")
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    print()
    
    # 测试仅本地访问配置
    print("2️⃣ 测试仅本地访问配置:")
    print("   启动命令: python3 combined_server.py --host localhost")
    
    try:
        # 启动服务器进程
        process = subprocess.Popen([
            sys.executable, "combined_server.py", 
            "--host", "localhost",
            "--http-port", "8002"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务器启动
        time.sleep(2)
        
        # 检查服务器是否正在运行
        if process.poll() is None:
            print("   ✅ 服务器启动成功")
            print("   🔒 仅本地访问模式")
            
            # 测试本地访问
            try:
                response = requests.get("http://localhost:8002", timeout=5)
                if response.status_code == 200:
                    print("   ✅ 本地访问正常")
                else:
                    print(f"   ❌ 本地访问失败，状态码: {response.status_code}")
            except Exception as e:
                print(f"   ❌ 本地访问测试失败: {e}")
            
            # 停止服务器
            process.terminate()
            process.wait()
            print("   ✅ 服务器已停止")
            
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ 服务器启动失败:")
            print(f"      错误信息: {stderr.decode()}")
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    print()
    print("=" * 50)
    print("🎉 网络配置测试完成！")
    print()
    print("📝 使用说明:")
    print("  • 默认配置允许局域网访问: python3 run_server.py")
    print("  • 仅本地访问: python3 run_server.py --local-only")
    print("  • 自定义host: python3 run_server.py --host 192.168.1.100")
    print("  • 自定义端口: python3 run_server.py --http-port 9000")

if __name__ == "__main__":
    test_server_startup()