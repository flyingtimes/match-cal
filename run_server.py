#!/usr/bin/env python3
"""
简单的启动脚本，用于启动合并服务器
支持局域网访问配置
"""

import subprocess
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='启动心算对战游戏服务器')
    parser.add_argument('--host', default='0.0.0.0', 
                       help='服务器侦听地址 (默认: 0.0.0.0，允许局域网访问)')
    parser.add_argument('--http-port', type=int, default=8000, 
                       help='HTTP服务器端口 (默认: 8000)')
    parser.add_argument('--ws-port', type=int, default=8765, 
                       help='WebSocket服务器端口 (默认: 8765)')
    parser.add_argument('--local-only', action='store_true',
                       help='仅本地访问 (等同于 --host localhost)')
    
    args = parser.parse_args()
    
    # 如果指定了 --local-only，则使用 localhost
    if args.local_only:
        args.host = 'localhost'
    
    print("🎮 启动心算对战游戏服务器...")
    print("=" * 50)
    
    # 检查是否存在合并服务器文件
    if not os.path.exists("combined_server.py"):
        print("❌ 错误：找不到 combined_server.py 文件")
        sys.exit(1)
    
    print("🚀 服务器配置:")
    print(f"📍 侦听地址: {args.host}")
    print(f"📡 HTTP端口: {args.http_port}")
    print(f"🔗 WebSocket端口: {args.ws_port}")
    
    if args.host == "localhost":
        print("🌐 游戏地址: http://localhost:{}".format(args.http_port))
        print("🔒 仅本地访问模式")
    else:
        print("🌐 本地访问: http://localhost:{}".format(args.http_port))
        print("🌍 局域网访问: http://[本机IP]:{}".format(args.http_port))
        print("📱 支持局域网设备访问")
    
    print("=" * 50)
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        # 构建命令参数
        cmd = [
            sys.executable, "combined_server.py",
            "--host", str(args.host),
            "--http-port", str(args.http_port),
            "--ws-port", str(args.ws_port)
        ]
        
        # 启动合并服务器
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n✋ 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()