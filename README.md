# 心算对战游戏

一个基于HTTP和WebSocket的双人心算对战游戏，使用Python开发。

## 功能特性

- 🎮 双人实时对战
- 🧮 数学心算挑战
- 📊 实时比分统计
- 💻 响应式Web界面
- 🌐 局域网多人游戏支持
- ⚡ WebSocket实时通信
- 🔊 音效反馈

## 技术栈

- **后端**: Python + WebSockets
- **前端**: HTML5 + CSS3 + JavaScript
- **包管理**: uv
- **通信协议**: WebSocket

## 环境要求

- Python 3.8+
- uv (Python包管理器)

## 安装和运行

### 1. 克隆项目

```bash
git clone <repository-url>
cd match-cal
```

### 2. 使用uv安装依赖

```bash
uv sync
```

### 3. 启动服务器

#### 默认配置启动（推荐）
```bash
uv run http_server.py
```

#### 自定义配置启动
```bash
uv run http_server.py --host 0.0.0.0 --http-port 8000 --ws-port 8765
```

#### 仅本地访问
```bash
uv run http_server.py --local-only
```

### 4. 访问游戏

打开浏览器访问：`http://localhost:8000`

如果是局域网配置，其他设备可通过 `http://<你的IP地址>:8000` 访问。

## 命令行参数

- `--host`: 服务器侦听地址（默认：0.0.0.0）
- `--http-port`: HTTP服务器端口（默认：8000）
- `--ws-port`: WebSocket服务器端口（默认：8765）
- `--local-only`: 仅本地访问（等同于--host localhost）

## 配置文件

项目使用`.env`文件管理环境变量和API密钥，请确保在项目根目录创建`.env`文件。

## 项目结构

```
match-cal/
├── pyproject.toml          # 项目配置和依赖
├── http_server.py          # HTTP和WebSocket服务器
├── index.html              # 游戏主页面
├── ring.flac               # 音效文件
├── README_HTTP.md          # HTTP服务器详细说明
└── CLAUDE.md               # 项目开发说明
```

## 游戏规则

1. 两名玩家同时开始游戏
2. 在60秒内完成尽可能多的数学计算题
3. 题目包括加减乘除运算
4. 正确答案加分，错误答案不扣分
5. 时间结束后显示最终得分和胜者

## 故障排除

1. **端口被占用**: 更改端口号或关闭占用端口的程序
2. **局域网访问失败**: 检查防火墙设置和网络配置
3. **WebSocket连接失败**: 确认端口配置正确且未被阻止

## 许可证

MIT License