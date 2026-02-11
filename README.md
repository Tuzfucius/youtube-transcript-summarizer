# 🎬 Video Summarizer

**支持 45+ 平台的多平台内容总结工具**

> Python API | CLI | MCP Server | Claude Code | OpenCode

## ✨ 特性

- 🎯 **45+ 平台支持** - 视频、社交、音乐、电商、编程社区
- 📝 **5 种分析模式** - 简要、详细、时间戳、情感、趋势
- 🔧 **多种接入方式** - Python、CLI、MCP Server、Claude Code
- 💾 **弹幕清洗** - 自动过滤无意义内容
- 🤖 **大模型友好** - Claude Code、OpenCode 原生接入
- ⚡ **CLI 增强** - 批量处理、配置文件、缓存管理
- 🚀 **异步并发** - 多视频同时处理
- 📊 **历史记录** - SQLite 存储与统计
- 🔍 **视频对比** - 多视频对比分析
- 🌐 **多 API 支持** - MiniMax、OpenAI、DeepSeek、Anthropic
- 💰 **成本追踪** - Token 统计、成本计算
- 🎤 **Whisper 支持** - 语音转文字（无字幕时）

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
# 轻量化安装（推荐快速体验）
pip install -r requirements-light.txt

# 全部安装（完整功能）
pip install -r requirements-full.txt

# 可选：Whisper 支持
pip install faster-whisper yt-dlp
```

## 📁 文件结构

```
youtube-summarizer/
├── __init__.py           # Python API
├── video_summarizer.py   # 核心模块
├── cli.py                # CLI 工具 (full)
├── advanced.py           # 高级功能 (full)
├── mcp_server.py         # MCP Server (full)
├── claude_code.py        # Claude Code 集成 (full)
├── deploy.py             # 部署管理 (new!)
│
├── requirements-light.txt # 轻量化依赖
├── requirements-full.txt  # 全部依赖
│
├── config.example.json   # 配置示例
├── SKILL.md              # Skill 文档
└── README.md             # 本文档
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

### Claude Code Skill 集成
```python
from claude_code import (
    parse_natural_language,
    claude_code_tool_definitions,
    CostTracker
)

# 自然语言解析
result = parse_natural_language("Summarize this video: https://youtube.com/watch?v=xxx")
if result:
    print(f"命令: {result['command']}, URL: {result['url']}")

# Claude Code 工具定义
tools = claude_code_tool_definitions()

# 成本追踪
tracker = CostTracker()
cost = tracker.track(model="gpt-4", prompt_tokens=1000, completion_tokens=500)
print(f"本次成本: ${cost:.4f}")
```

### 自然语言命令
支持自然语言触发：
```bash
# 这些命令都会被识别
summarize this video: https://youtube.com/watch?v=xxx
总结这个视频：https://bilibili.com/video/BVxxx
What's in this video? https://twitter.com/xxx
```

### 成本追踪
```python
from claude_code import CostTracker

tracker = CostTracker()

# 记录每次 API 调用
tracker.track("gpt-4", prompt_tokens=1000, completion_tokens=500)
tracker.track("MiniMax-M2.1", prompt_tokens=500, completion_tokens=300)

# 获取统计
summary = tracker.get_summary()
print(f"总请求: {summary['total_requests']}")
print(f"总成本: ${summary['total_cost']:.4f}")

# 导出报告
tracker.export_json("cost_report.json")
```

### LLM 定价参考

| 模型 | 输入价格 | 输出价格 |
|------|---------|---------|
| MiniMax-M2.1 | $0.001/1K | $0.001/1K |
| GPT-4 | $0.03/1K | $0.06/1K |
| GPT-3.5-Turbo | $0.0005/1K | $0.0015/1K |
| DeepSeek-Chat | $0.00014/1K | $0.00028/1K |
| Claude-3-Opus | $0.015/1K | $0.075/1K |

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

## 📦 部署方式

### 部署模式对比

| | 轻量化部署 | 全部部署 |
|---|---|---|
| **大小** | ~500KB | ~2MB |
| **依赖** | 2 个 | 2 个 (+ 可选) |
| **文件** | 2 个 | 6 个 |
| **核心功能** | ✅ 总结/提取/清洗 | ✅ 全部功能 |
| **CLI 工具** | ❌ | ✅ |
| **异步并发** | ❌ | ✅ |
| **历史记录** | ❌ | ✅ |
| **视频对比** | ❌ | ✅ |
| **MCP Server** | ❌ | ✅ |
| **Claude Code** | ❌ | ✅ |
| **字幕导出** | ❌ | ✅ |

### 新功能：仅导出字幕

```bash
# 导出字幕为 TXT
python export_subtitle.py "URL" -f txt

# 导出为 JSON
python export_subtitle.py "URL" -f json -o output.json

# 批量导出
python export_subtitle.py --batch urls.txt -d ./subtitles
```

### 安装方式

#### 轻量化部署（推荐快速体验）

```bash
# 安装依赖
pip install -r requirements-light.txt

# 使用
python -c "from video_summarizer import summarize; print(summarize('URL'))"
```

#### 全部部署（完整功能）

```bash
# 安装依赖
pip install -r requirements-full.txt

# 可选：安装 Whisper（语音转文字）
pip install faster-whisper yt-dlp

# 运行部署向导
python deploy.py --quick
```

### 部署管理命令

```bash
# 查看模式对比
python deploy.py --show

# 快速开始
python deploy.py --quick

# 检查安装状态
python deploy.py --check --mode full

# 生成安装脚本
python deploy.py --install light   # 轻量化
python deploy.py --install full   # 全部
```

### 部署脚本

运行后会生成对应脚本：
- `install_light.sh` - 轻量化安装脚本
- `install_full.sh` - 全部安装脚本

```bash
# 使用安装脚本
bash install_light.sh
# 或
bash install_full.sh
```

## 更新日志

### v3.8.5 (2026-02-11) - 部署模式

**参考项目**：
- [TubeWhale](https://github.com/yaninsanity/TubeWhale) - 多 Agent 架构、SQLite 持久化、Token 统计
- [video-summarizer](https://github.com/liang121/video-summarizer) - Claude Code Skill、自动依赖安装、并行 Whisper
- [AI-Video-Summarizer](https://github.com/siddharthsky/AI-Video-Summarizer) - 多 LLM 支持、Streamlit UI

**本次更新**：
- ✨ **Claude Code Skill 集成** - Skill Manifest 和工具定义
- ✨ **自然语言触发** - 智能识别用户意图
- ✨ **依赖自动检查** - 检查并提示安装缺失依赖
- ✨ **成本追踪** - Token 统计、成本计算
- ✨ **配置文件模板** - 完整配置示例
- ✨ **Whisper 支持** - 语音转文字（可选功能）
- ✨ **CLI 增强** - config、cost 命令

### v3.8.3 (2026-02-11)

- ✨ 异步并发 - AsyncSummarizer 支持多视频并发处理
- ✨ 多 API 支持 - OpenAI、DeepSeek、Anthropic
- ✨ 历史记录 - SQLite 存储、搜索、统计
- ✨ 视频对比 - 多视频对比分析报告
- ✨ CLI 增强 - 对比、历史、统计命令

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
