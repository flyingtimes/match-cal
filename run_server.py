#!/usr/bin/env python3
"""
简单的启动脚本，用于启动合并服务器
"""

import subprocess
import sys
import os

def main():
    print("🎮 启动心算对战游戏服务器...")
    print("=" * 50)
    
    # 检查是否存在合并服务器文件
    if not os.path.exists("combined_server.py"):
        print("❌ 错误：找不到 combined_server.py 文件")
        sys.exit(1)
    
    print("🚀 启动服务器...")
    print("📡 HTTP服务器: http://localhost:8000")
    print("🔗 WebSocket服务器: ws://localhost:8765")
    print("🌐 游戏地址: http://localhost:8000")
    print("=" * 50)
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        # 启动合并服务器
        subprocess.run([sys.executable, "combined_server.py"], check=True)
    except KeyboardInterrupt:
        print("\n✋ 服务器已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()