#!/usr/bin/env python3
"""
启动HTTP心算对战游戏服务器
使用HTTP轮询替代WebSocket
"""

import subprocess
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='启动HTTP心算对战游戏服务器')
    parser.add_argument('--host', default='0.0.0.0', 
                       help='服务器侦听地址 (默认: 0.0.0.0，允许局域网访问)')
    parser.add_argument('--port', type=int, default=8000, 
                       help='HTTP服务器端口 (默认: 8000)')
    parser.add_argument('--local-only', action='store_true',
                       help='仅本地访问 (等同于 --host localhost)')
    
    args = parser.parse_args()
    
    # 如果指定了 --local-only，则使用 localhost
    if args.local_only:
        args.host = 'localhost'
    
    print("🎮 启动HTTP心算对战游戏服务器...")
    print("=" * 50)
    
    # 检查是否存在HTTP服务器文件
    if not os.path.exists("http_server.py"):
        print("❌ 错误：找不到 http_server.py 文件")
        sys.exit(1)
    
    print("🚀 服务器配置:")
    print(f"📍 侦听地址: {args.host}")
    print(f"📡 HTTP端口: {args.port}")
    print(f"🔄 使用HTTP轮询替代WebSocket")
    
    if args.host == "localhost":
        print("🌐 游戏地址: http://localhost:{}".format(args.port))
        print("🔒 仅本地访问模式")
    else:
        print("🌐 本地访问: http://localhost:{}".format(args.port))
        print("🌍 局域网访问: http://[本机IP]:{}".format(args.port))
        print("📱 支持局域网设备访问")
    
    print("📝 前端页面: http://localhost:{}/index_http.html".format(args.port))
    print("=" * 50)
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        # 构建命令参数
        cmd = [
            sys.executable, "http_server.py",
            "--host", str(args.host),
            "--port", str(args.port)
        ]
        
        # 启动HTTP服务器
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n✋ 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()