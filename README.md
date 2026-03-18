# 🎬 Video Summarizer

**支持 45+ 平台的多平台视频内容总结工具**

> Python API | CLI | MCP Server | Claude Code | Web UI

---

## ✨ 特性

- 🎯 **45+ 平台支持** - YouTube、Bilibili、抖音、Twitter 等
- 📝 **5 种分析模式** - 简要、详细、时间戳、情感、趋势
- 🔧 **多种接入方式** - Python API、CLI、MCP Server、Claude Code
- 💾 **弹幕清洗** - 自动过滤无意义弹幕
- 🚀 **异步并发** - 多视频同时处理
- 📊 **历史记录** - SQLite 存储与统计
- 🔍 **视频对比** - 多视频对比分析
- 🌐 **多 API 支持** - MiniMax、OpenAI、DeepSeek、Anthropic
- 💰 **成本追踪** - Token 统计、成本计算
- 🎤 **Whisper 支持** - 语音转文字（可选）
- 🎨 **Web UI** - Gradio 浏览器界面（可选）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制配置示例并填写你的 API Key：

```bash
cp config.example.json config.json
# 然后编辑 config.json，填写 api_key
```

或使用 CLI 命令设置：

```bash
python cli.py config --set api_key=your-api-key-here
```

### 3. 开始使用

```python
from src import summarize

result = summarize("https://www.youtube.com/watch?v=xxx", format="brief")
print(result["summary"])
```

---

## 📁 目录结构

```
youtube-transcript-summarizer/
├── src/                      # 核心源码
│   ├── __init__.py          # 统一公共 API 导出
│   ├── utils.py             # 日志、重试、计时器等工具
│   ├── prompts.py           # LLM Prompt 模板管理
│   ├── extractors.py        # YouTube/Bilibili 内容提取器
│   ├── core.py              # VideoSummarizer 类及便捷函数
│   ├── advanced.py          # 异步并发、历史记录、多 LLM 工厂
│   └── README.md
│
├── tests/                   # 测试用例
│   ├── test_stability.py    # 基础稳定性测试（无需 API Key）
│   └── README.md
│
├── cli.py                   # 命令行工具（入口）
├── mcp_server.py            # MCP Server（入口）
├── web_ui.py                # Gradio Web UI（入口，可选）
├── export_subtitle.py       # 字幕/弹幕导出工具（入口）
├── claude_code.py           # Claude Code 集成
│
├── video_summarizer.py      # 兼容层（向后兼容旧 import）
├── __init__.py              # 兼容层（向后兼容旧 import）
│
├── config.json              # 用户配置（需自行创建）
├── config.example.json      # 配置示例
├── requirements.txt         # 基础依赖
├── requirements-light.txt   # 轻量化依赖
├── requirements-full.txt    # 完整依赖
└── README.md
```

---

## ⚙️ 配置说明

### config.json 字段详解

```json
{
  "api_key":       "your-api-key-here",
  "api_url":       "https://api.minimaxi.com/v1/chat/completions",
  "model":         "MiniMax-M2.1",
  "format":        "brief",
  "use_subtitle":  true,
  "clean_danmaku": true,
  "cache_enabled": true,
  "log_level":     "INFO"
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | string | — | **必填**，LLM API Key |
| `api_url` | string | MiniMax 地址 | LLM 接口地址，切换提供商时修改 |
| `model` | string | `MiniMax-M2.1` | 使用的模型名称 |
| `format` | string | `brief` | 默认输出格式 |
| `use_subtitle` | boolean | `true` | Bilibili 是否优先使用 CC 字幕（否则用弹幕）|
| `clean_danmaku` | boolean | `true` | 是否清洗弹幕（过滤无意义内容）|
| `cache_enabled` | boolean | `true` | 是否启用缓存 |
| `log_level` | string | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR）|

### 各 LLM 提供商配置

#### MiniMax（默认）
```json
{
  "api_key": "your-minimax-key",
  "api_url": "https://api.minimaxi.com/v1/chat/completions",
  "model":   "MiniMax-M2.1"
}
```

#### OpenAI / OpenAI 兼容接口
```json
{
  "api_key": "sk-xxx",
  "api_url": "https://api.openai.com/v1/chat/completions",
  "model":   "gpt-4o"
}
```

#### DeepSeek
```json
{
  "api_key": "your-deepseek-key",
  "api_url": "https://api.deepseek.com/v1/chat/completions",
  "model":   "deepseek-chat"
}
```

#### Anthropic（Claude）
```json
{
  "api_key": "sk-ant-xxx",
  "api_url": "https://api.anthropic.com/v1/messages",
  "model":   "claude-3-5-sonnet-20241022"
}
```

### 环境变量（替代 config.json）

```bash
export MINIMAX_API_KEY="your-api-key"
# 或
export OPENAI_API_KEY="your-api-key"

export VIDEO_SUMMARIZER_API_URL="https://api.minimaxi.com/v1/chat/completions"
export VIDEO_SUMMARIZER_MODEL="MiniMax-M2.1"
```

---

## 📖 使用方式

### Python API

```python
from src import summarize, detect

# 总结视频
result = summarize(
    "https://www.youtube.com/watch?v=xxx",
    format="brief",         # 输出格式
    api_key="your-key",     # 可选，优先于 config.json
)
print(result["summary"])

# 自定义 Prompt
result = summarize(
    url="https://bilibili.com/video/BVxxx",
    prompt="请从以下角度分析：1. 核心观点 2. 目标受众 3. 制作水平"
)

# 检测平台
print(detect("https://twitter.com/xxx"))  # → twitter
```

### CLI

```bash
# 总结单个视频
python cli.py url "https://youtube.com/watch?v=xxx" -f brief

# 指定 LLM 提供商
python cli.py url "URL" --provider openai --api-key sk-xxx

# 保存到文件
python cli.py url "URL" -f detailed -o result.md

# 批量处理
python cli.py batch urls.txt -f brief -o results.json

# 异步并发批量
python cli.py batch urls.txt --async -c 5

# 对比多个视频
python cli.py compare "URL1" "URL2" "URL3"

# 历史记录
python cli.py history
python cli.py history --search AI

# 统计
python cli.py stats

# 查看 LLM 提供商
python cli.py providers

# 管理配置
python cli.py config
python cli.py config --set api_key=xxx
python cli.py config --get api_key
```

### MCP Server

```bash
# Stdio 模式（Claude Code 推荐）
python mcp_server.py --mcp-stdio

# HTTP 模式
python mcp_server.py --mcp-http --port 8080

# 直接 CLI 调用
python mcp_server.py --url "URL" --format brief
```

### 仅导出字幕

```bash
# 导出为 TXT
python export_subtitle.py "URL" -f txt

# 导出为 JSON
python export_subtitle.py "URL" -f json -o output.json

# 批量导出
python export_subtitle.py --batch urls.txt -d ./subtitles
```

---

## 📋 输出格式

| 格式 | 说明 |
|------|------|
| `brief` | 简要总结（默认），含摘要和关键要点 |
| `detailed` | 详细分析，含内容、风格、受众、热门原因 |
| `timestamp` | 带时间戳的要点提取 |
| `sentiment` | 情感分析（适合弹幕） |
| `trend` | 趋势分析 |

---

## 📊 返回结构

```python
{
    "platform": "youtube",
    "video_info": {
        "id":           "视频ID",
        "url":          "https://...",
        "title":        "视频标题",
        "owner":        "作者",
        "content_type": "字幕"  # 或 "弹幕"
    },
    "summary":   "总结内容...",
    "format":    "brief",
    "timestamp": "2026-03-18T08:00:00"
}
```

---

## 🌐 支持平台

| 分类 | 平台 |
|------|------|
| 视频 | YouTube · Bilibili · 抖音 · 快手 · 西瓜视频 · Twitch · Vimeo |
| 社交 | Twitter/X · Weibo · Instagram · 小红书 · 知乎 · Reddit · Medium |
| 音乐 | 网易云音乐 · QQ音乐 · SoundCloud |
| 电商 | 淘宝 · 天猫 · 京东 · 亚马逊 · eBay · Etsy |
| 直播 | 斗鱼 · 虎牙 · YY |
| 其他 | Codeforces · LeetCode · 豆瓣 · 贴吧 |

完整列表：`python cli.py providers` 或 `from src import list_platforms; print(list_platforms())`

---

## 🚀 高级功能

### 异步并发

```python
from src.advanced import AsyncSummarizer
import asyncio

async def main():
    s = AsyncSummarizer(max_concurrent=5, api_key="xxx")
    results = await s.summarize_batch(
        urls=["URL1", "URL2", "URL3"],
        format="brief"
    )

asyncio.run(main())
```

### 历史记录

```python
from src.advanced import HistoryStore

store = HistoryStore()
store.add(url, title, platform, summary, format, tags=["AI"])
results = store.search("AI")
stats = store.get_stats()
```

### 多 LLM 工厂

```python
from src.advanced import LLMFactories, quick_summarize

# 查看支持的提供商
print(LLMFactories.list_providers())  # ['minimax', 'openai', 'deepseek', 'anthropic']

# 指定提供商总结
result = quick_summarize("URL", provider="openai", api_key="sk-xxx")
```

---

## 🎤 Whisper 转录（可选）

```bash
pip install faster-whisper yt-dlp

python whisper_transcribe.py "audio.wav" --model small
```

| 模型 | 大小 | 推荐场景 |
|------|------|----------|
| tiny | 39M | 快速测试 |
| small | 244M | **日常推荐** |
| medium | 769M | 高精度 |
| large-v3 | 1.5G | 最高精度 |

---

## 🎨 Web UI（可选）

```bash
pip install gradio
python web_ui.py --port 7860
# 访问 http://localhost:7860
```

---

## 📦 安装方式

```bash
# 基础安装（推荐）
pip install -r requirements.txt

# 完整安装（包括可选功能说明）
pip install -r requirements-full.txt

# 可选：Whisper 转录
pip install faster-whisper yt-dlp
```

---

## 🔗 相关链接

- GitHub: <https://github.com/Tuzfucius/youtube-transcript-summarizer>

---

## 更新日志

### v3.9.0 (2026-03-18)

- 🏗️ **目录重构** - 核心代码迁移至 `src/`，职责分明
- 🐛 **修复** `mcp_server.py` 参数名错误（`prompt_type` → `format`）
- 🐛 **修复** `mcp_server.py` 引用不存在的 `PLATFORMS` 属性
- 🐛 **修复** `BilibiliExtractor` 字幕内容提取逻辑（补全字幕下载和文本解析）
- 🐛 **修复** `YouTubeExtractor` 兼容新版 `youtube_transcript_api`（>= 0.6）
- 🐛 **修复** `cli.py` 参数名错误（`clean_danmaku_flag` → `clean_danmaku`）
- 🐛 **修复** `export_subtitle.py` 错误的 `from __init__ import`
- ✨ **新增** `tests/` 测试目录，稳定性测试更完善

### v3.8.5 (2026-02-11)

- ✨ Claude Code Skill 集成
- ✨ 自然语言触发
- ✨ 成本追踪、Whisper 支持
