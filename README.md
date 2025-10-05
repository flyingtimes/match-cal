# 两位数心算游戏

一个纯前端实现的两位数心算对战游戏，支持单人练习和好友对战模式。

## 功能特性

- 🎮 单人练习模式 - 随时随地训练心算能力
- 👥 好友对战模式 - 与朋友一起挑战
- 🧮 数学心算挑战 - 两位数加减法练习
- 📊 实时比分统计 - 详细的成绩分析
- 💻 响应式Web界面 - 支持手机、平板、电脑
- 🔊 音效反馈 - 答对/答错的即时反馈
- 🎨 精美的视觉效果 - 五彩纸屑庆祝动画
- ⏱️ 计时挑战 - 60秒限时答题

## 技术栈

- **前端**: HTML5 + CSS3 + JavaScript (ES6+)
- **样式**: CSS Grid + Flexbox + CSS动画
- **音效**: Web Audio API
- **部署**: Vercel 静态网站托管
- **包管理**: npm/uv

## 在线访问

游戏已部署在 Vercel，可以直接在线访问：
🎮 **在线演示**: https://match-cal.vercel.app

## 本地运行

### 方法1: 使用 Python HTTP 服务器

```bash
# 克隆项目
git clone <repository-url>
cd match-cal

# 启动本地服务器
python -m http.server 8000

# 或者使用项目脚本
npm run dev
```

### 方法2: 使用 Node.js (需要安装 http-server)

```bash
# 安装 http-server
npm install -g http-server

# 启动服务器
http-server -p 8000
```

访问 `http://localhost:8000` 即可开始游戏。

## 部署到 Vercel

### 自动部署（推荐）

1. 将项目推送到 GitHub
2. 在 Vercel 中导入项目
3. Vercel 会自动识别并部署静态网站

### 手动部署

```bash
# 安装 Vercel CLI
npm install -g vercel

# 登录 Vercel
vercel login

# 部署项目
npm run deploy
```

## 游戏模式

### 单人练习模式
- 点击"单人练习"按钮
- 点击"开始练习"开始游戏
- 60秒内完成尽可能多的题目
- 游戏结束后显示详细成绩

### 好友对战模式
- 点击"好友对战"按钮
- 创建房间或加入现有房间
- 分享房间号给好友
- 双方准备后开始对战
- 游戏结束后比较成绩

## 游戏规则

1. **题目类型**: 两位数加减法 (例如: 45 + 67 = ?, 89 - 23 = ?)
2. **时间限制**: 60秒
3. **计分方式**: 
   - 答对加分，答错不扣分
   - 正确率 = 答对题数 / 总答题数 × 100%
4. **操作方式**: 
   - 输入答案后按 Enter 或点击"提交"
   - 可以点击"跳过"跳过当前题目（计为答错）

## 项目结构

```
match-cal/
├── index.html          # 游戏主页面
├── package.json        # 项目配置和脚本
├── pyproject.toml      # Python项目配置（用于开发）
├── vercel.json         # Vercel部署配置
├── .gitignore          # Git忽略文件
├── README.md           # 项目说明
└── CLAUDE.md           # 开发说明
```

## 开发命令

```bash
# 本地开发
npm run dev

# 构建项目（静态文件无需构建）
npm run build

# 预览部署
npm run preview

# 部署到 Vercel
npm run deploy
```

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 特色功能

### 🎨 视觉设计
- 现代化的深色主题设计
- 流畅的CSS动画效果
- 响应式布局适配各种设备
- 五彩纸屑庆祝动画

### 🎵 音效系统
- Web Audio API生成的音效
- 答对/答错的即时音效反馈
- 无需外部音频文件

### 📱 移动端优化
- 触摸友好的界面设计
- 数字键盘优化
- 全屏体验支持

### ⚡ 性能优化
- 纯前端实现，加载速度快
- 无服务器依赖，可离线使用
- 高效的Canvas动画渲染

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License