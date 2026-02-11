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
- 🚀 **异步并发** - 多视频同时处理
- 📊 **历史记录** - SQLite 存储与统计
- 🔍 **视频对比** - 多视频对比分析
- 🌐 **多 API 支持** - MiniMax、OpenAI、DeepSeek、Anthropic

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

# 批量处理（同步）
python cli.py batch urls.txt -o results.json

# 批量处理（异步并发）
python cli.py batch urls.txt --async -c 5

# 对比多个视频
python cli.py compare "URL1" "URL2" "URL3" -o comparison.json

# 查看历史记录
python cli.py history

# 搜索历史
python cli.py history --search AI

# 查看统计
python cli.py stats

# LLM 提供商
python cli.py providers
python cli.py url "URL" --provider openai

# 配置管理
python cli.py config --set api_key=xxx
python cli.py config --get api_key
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

## 🚀 高级功能

### 异步并发处理
```python
from advanced import AsyncSummarizer

async def main():
    async_s = AsyncSummarizer(max_concurrent=5)
    results = await async_s.summarize_batch(
        urls=["URL1", "URL2", "URL3"],
        format="brief"
    )

asyncio.run(main())
```

### 多 LLM 提供商
```python
from advanced import LLMFactories, quick_summarize

# 查看支持的提供商
print(LLMFactories.list_providers())
# ['minimax', 'openai', 'deepseek', 'anthropic']

# 使用 OpenAI
result = quick_summarize("URL", provider="openai", api_key="xxx")
```

### 历史记录管理
```python
from advanced import HistoryStore

store = HistoryStore()

# 添加到历史
store.add(url, title, platform, summary, format, tags=["AI", "技术"])

# 搜索
results = store.search("AI")

# 统计
stats = store.get_stats()
print(f"总记录: {stats['total']}")

# 获取所有
all_history = store.get_all(limit=100)
```

### 视频对比
```python
from advanced import VideoComparator

comparator = VideoComparator()
report = comparator.compare(["URL1", "URL2", "URL3"], format="brief")

print(report['comparison']['platforms'])  # 平台分布
```

## 🔗 GitHub

🔗 **https://github.com/Tuzfucius/youtube-transcript-summarizer**

---

*Built with ❤️ by OpenClaw*

## 更新日志

### v3.8.3 (2026-02-11) - 本次更新

- ✨ **异步并发** - AsyncSummarizer 支持多视频并发处理
- ✨ **多 API 支持** - MiniMax、OpenAI、DeepSeek、Anthropic
- ✨ **历史记录** - SQLite 存储、搜索、统计
- ✨ **视频对比** - 多视频对比分析报告
- ✨ **CLI 增强** - 对比、历史、统计命令

### v3.8.2 (2026-02-11)

- ✨ CLI 增强 - 全新命令行工具
- ✨ 批量处理 - 支持文件批量输入
- ✨ 配置文件 - 集中管理 API key 和参数
- ✨ 缓存管理 - 查看和清除缓存
- ✨ 多种输出 - 支持 JSON 和 Markdown 文件输出
- ✨ 配置命令 - CLI 内置配置管理

### v3.8.1 (2026-02-11)

- ✅ 稳定性增强
- ✅ 日志系统
- ✅ 重试机制
- ✅ 错误处理
