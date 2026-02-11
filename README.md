# 🎬 Video Summarizer

**支持 45+ 平台的多平台内容总结工具**

> Python API | CLI | MCP Server | Claude Code | OpenCode

## ✨ 特性

- 🎯 **45+ 平台支持** - 视频、社交、音乐、电商、编程社区
- 📝 **5 种分析模式** - 简要、详细、时间戳、情感、趋势
- 🔧 **多种接入方式** - Python、CLI、MCP Server
- 💾 **弹幕清洗** - 自动过滤无意义内容
- 🤖 **大模型友好** - Claude Code、OpenCode 原生接入
- ⚡ **CLI 增强** - 批量处理、配置文件、缓存管理

## 🚀 快速开始

### Python API（推荐）

```python
from video_summarizer import summarize

# 一行代码总结视频
result = summarize("https://youtube.com/watch?v=xxx", format="brief")
print(result["summary"])
```

### Claude Code / OpenCode

```python
from video_summarizer import get_all_tools, summarize

# 获取工具定义
tools = get_all_tools()

# 直接调用
result = summarize("https://bilibili.com/video/BVxxx", format="detailed")
```

### CLI（新增 v3.8.2）

```bash
# 单视频总结
python cli.py url "https://youtube.com/watch?v=xxx" -f brief

# 保存到文件
python cli.py url "https://bilibili.com/video/BVxxx" -f detailed -o result.md

# 批量处理
python cli.py batch urls.txt -o results.json

# 查看支持平台
python cli.py platforms

# 配置管理
python cli.py config --set api_key=xxx

# 缓存管理
python cli.py cache --list
python cli.py cache --clear
```

### MCP Server

```bash
# Stdio 模式（Claude Code）
python mcp_server.py --mcp-stdio

# HTTP 模式
python mcp_server.py --mcp-http --port 8080
```

### CLI 参数说明

| 参数 | 说明 |
|------|------|
| `url` | 视频 URL |
| `batch` | 批量处理文件 |
| `-f, --format` | 输出格式 (brief/detailed/timestamp/sentiment/trend) |
| `-o, --output` | 输出文件 (JSON/Markdown) |
| `--api-key` | API Key |
| `--api-url` | API URL |
| `--model` | 模型名称 |
| `--no-subtitle` | 不使用字幕 |
| `--no-clean` | 不清洗弹幕 |
| `-q, --quiet` | 安静模式 |

## 🌐 支持的平台

### 视频 (7)
YouTube · Bilibili · 抖音 · 快手 · 西瓜视频 · Twitch · Vimeo

### 社交 (15)
微博 · Twitter/X · Instagram · 小红书 · 知乎 · Telegram · Snapchat · Pinterest · Reddit · Medium · Quora · B站专栏 · 豆瓣 · 贴吧 · Lofter

### 音乐 (4)
网易云音乐 · QQ音乐 · SoundCloud · Podcast

### 电商 (13)
淘宝 · 天猫 · 京东 · 得物 · 转转 · 闲鱼 · 亚马逊 · eBay · Etsy · Shopify · 美团 · 饿了么

### 旅游 (5)
携程 · 马蜂窝 · Airbnb

### 直播 (3)
斗鱼 · 虎牙 · YY

### 编程 (2)
Codeforces · LeetCode

### ACG (3)
半次元

## 📖 使用示例

### YouTube 字幕总结
```python
from video_summarizer import summarize

result = summarize(
    "https://www.youtube.com/watch?v=xxx",
    format="detailed"
)
print(result["summary"])
```

### B站弹幕分析
```python
result = summarize(
    "https://www.bilibili.com/video/BVxxx",
    format="sentiment",  # 情感分析
    clean_danmaku=True   # 自动清洗弹幕
)
print(result["summary"])
```

### 自定义 Prompt
```python
result = summarize(
    url="https://youtube.com/watch?v=xxx",
    prompt="请从以下角度分析：1. 目标受众是谁？2. 核心卖点？3. 制作水平？"
)
```

### CLI 批量处理

创建 `urls.txt`:
```
https://youtube.com/watch?v=video1
https://bilibili.com/video/BVvideo2
https://youtube.com/watch?v=video3
```

运行:
```bash
python cli.py batch urls.txt -f brief -o results.json
```

## 📋 输出格式

| 格式 | 说明 |
|------|------|
| `brief` | 简要总结（默认） |
| `detailed` | 详细分析 |
| `timestamp` | 带时间戳 |
| `sentiment` | 情感分析 |
| `trend` | 趋势分析 |

## 🔧 配置

### 配置文件 (新增 v3.8.2)

创建 `config.json`:
```json
{
    "api_key": "your-api-key",
    "api_url": "https://api.minimaxi.com/v1/chat/completions",
    "model": "MiniMax-M2.1",
    "format": "brief",
    "use_subtitle": true,
    "clean_danmaku": true
}
```

### 环境变量
```bash
export MINIMAX_API_KEY="your-api-key"
export VIDEO_SUMMARIZER_API_URL="https://api.minimaxi.com/v1/chat/completions"
export VIDEO_SUMMARIZER_MODEL="MiniMax-M2.1"
```

### CLI 配置管理
```bash
# 查看配置
python cli.py config

# 设置配置
python cli.py config --set api_key=xxx
python cli.py config --set model=MiniMax-M2.1

# 获取配置
python cli.py config --get api_key
```

## 📦 安装

```bash
pip install -r requirements.txt
```

## 📁 文件结构

```
youtube-summarizer/
├── __init__.py           # Python API
├── video_summarizer.py   # 核心模块
├── cli.py                # CLI 工具 (新增)
├── mcp_server.py         # MCP Server
├── mcp_config.json       # MCP 配置
├── config.example.json   # 配置示例 (新增)
├── package.json          # 包配置
├── SKILL.md              # Skill 文档
├── README.md             # 本文档
└── requirements.txt      # 依赖
```

## 🤖 大模型接入

### Claude Code
```json
{
  "tools": [
    {
      "name": "summarize_video",
      "description": "Summarize video content",
      "inputSchema": {
        "type": "object",
        "properties": {
          "url": {"type": "string"},
          "format": {"type": "string", "enum": ["brief", "detailed", "timestamp"]}
        }
      }
    }
  ]
}
```

### OpenCode
```python
from video_summarizer import summarize

# OpenCode 工具调用
result = summarize(url="https://youtube.com/watch?v=xxx")
```

## 📊 返回值

```python
{
    "platform": "youtube",
    "video_info": {
        "id": "xxx",
        "url": "https://youtube.com/watch?v=xxx",
        "title": "标题",
        "author": "作者",
        "views": 10000,
        "likes": 500
    },
    "summary": "总结内容...",
    "format": "brief",
    "timestamp": "2026-02-11T15:00:00"
}
```

## 🔗 GitHub

🔗 **https://github.com/Tuzfucius/youtube-transcript-summarizer**

---

*Built with ❤️ by OpenClaw*

## 更新日志

### v3.8.2 (2026-02-11) - 本次更新

- ✨ **CLI 增强** - 全新命令行工具
- ✨ **批量处理** - 支持文件批量输入
- ✨ **配置文件** - 集中管理 API key 和参数
- ✨ **缓存管理** - 查看和清除缓存
- ✨ **多种输出** - 支持 JSON 和 Markdown 文件输出
- ✨ **配置命令** - CLI 内置配置管理

### v3.8.1 (2026-02-11)

- ✅ 稳定性增强
- ✅ 日志系统
- ✅ 重试机制
- ✅ 错误处理
