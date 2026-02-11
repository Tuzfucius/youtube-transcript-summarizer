# 🎬 Video Summarizer

**支持 45+ 平台的多平台内容总结工具**

> Python API | CLI | MCP Server | Claude Code | OpenCode

## ✨ 特性

- 🎯 **45+ 平台支持** - 视频、社交、音乐、电商、编程社区
- 📝 **5 种分析模式** - 简要、详细、时间戳、情感、趋势
- 🔧 **多种接入方式** - Python、CLI、MCP Server
- 💾 **弹幕清洗** - 自动过滤无意义内容
- 🤖 **大模型友好** - Claude Code、OpenCode 原生接入

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

### CLI

```bash
# 基本使用
python -m video_summarizer --url "https://youtube.com/watch?v=xxx"

# 详细总结
python video_summarizer.py -u "URL" -f detailed

# 自定义 prompt
python video_summarizer.py "URL" -p "从商业角度分析"
```

### MCP Server

```bash
# Stdio 模式（Claude Code）
python mcp_server.py --mcp-stdio

# HTTP 模式
python mcp_server.py --mcp-http --port 8080
```

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

## 📋 输出格式

| 格式 | 说明 |
|------|------|
| `brief` | 简要总结（默认） |
| `detailed` | 详细分析 |
| `timestamp` | 带时间戳 |
| `sentiment` | 情感分析 |
| `trend` | 趋势分析 |

## 🔧 配置

### 环境变量
```bash
export MINIMAX_API_KEY="your-api-key"
export VIDEO_SUMMARIZER_API_URL="https://api.minimaxi.com/v1/chat/completions"
export VIDEO_SUMMARIZER_MODEL="MiniMax-M2.1"
```

### 配置文件
```json
{
    "api_key": "your-api-key",
    "api_url": "https://api.minimaxi.com/v1/chat/completions",
    "model": "MiniMax-M2.1"
}
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
├── mcp_server.py         # MCP Server
├── mcp_config.json       # MCP 配置
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
