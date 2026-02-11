# 🎬 Video Summarizer

多平台视频内容总结工具 - 支持 **YouTube**、**B站**、**抖音**、**西瓜视频**、**微博**、**Twitter/X**、**Instagram**

## ✨ 特性

- 🎯 **多平台支持** - YouTube（字幕）、B站（弹幕+字幕）、抖音、西瓜、微博、Twitter、Instagram
- 📝 **多种分析模式** - 简要、详细、时间戳、情感、趋势
- 🔧 **自定义 Prompt** - 完全自定义分析角度
- ⚙️ **灵活配置** - 配置文件、环境变量、命令行参数
- 💾 **弹幕清洗** - 自动过滤无意义内容
- 📊 **B站字幕** - 支持 CC 字幕/自动字幕

## 🚀 快速开始

### 安装

```bash
cd /home/jetson/.openclaw/workspace/skills/youtube-summarizer
pip install -r requirements.txt
```

### 配置 API

```bash
# 方式一：配置文件 config.json
{
    "api_key": "your-api-key",
    "api_url": "https://api.minimaxi.com/v1/chat/completions",
    "model": "MiniMax-M2.1"
}

# 方式二：命令行参数
python video_summarizer.py "URL" --api-key "key" --api-url "url"
```

### 使用

```bash
# YouTube 简要总结
python video_summarizer.py "https://youtube.com/watch?v=xxx"

# B站 详细分析（自动清洗弹幕 + 字幕）
python video_summarizer.py "https://bilibili.com/video/BVxxx" -f detailed

# 情感分析
python video_summarizer.py "URL" -f sentiment

# 自定义 prompt
python video_summarizer.py "URL" -p "请从商业角度分析这个视频"
```

## 📖 Prompt 类型

| 类型 | 说明 |
|------|------|
| `brief` | 简要总结（默认） |
| `detailed` | 详细分析 |
| `timestamp` | 时间戳要点 |
| `sentiment` | 情感分析 |
| `trend` | 趋势分析 |

### 自定义 Prompt

```bash
python video_summarizer.py "URL" \
  -p "请从以下角度分析：1. 目标受众是谁？2. 核心卖点是什么？3. 制作水平如何？"
```

可用的模板变量：

```
{platform}   - 平台名称
{title}      - 视频标题
{author}     - 作者/UP主
{desc}       - 描述/简介
{duration}   - 时长（秒）
{views}      - 播放量
{likes}      - 点赞数
{subtitle}   - 字幕内容（YouTube）
{danmaku}    - 弹幕内容（B站）
{max_length} - 最大长度
```

## 🔧 CLI 参数

```
位置参数:
  url                  视频链接

可选参数:
  -f, --format         总结格式 (brief/detailed/timestamp/sentiment/trend)
  -p, --prompt         自定义 prompt 模板
  -m, --max-length     最大长度 (默认 500)
  --api-key            API Key
  --api-url            API URL
  --model              模型名称
  --no-save            不保存到文件
  --no-clean           不清洗弹幕（B站）
  --no-subtitle        强制使用弹幕（B站）
  --list-prompts       列出所有 prompt 类型
```

## 🌐 支持的平台

| 平台 | 内容类型 | 备注 |
|------|----------|------|
| YouTube | 字幕 | 自动获取字幕 |
| Bilibili | 弹幕 + 字幕 | 弹幕清洗 + CC字幕 |
| 抖音 | 描述 | 需登录获取更多 |
| 西瓜视频 | 描述 | 需登录获取更多 |
| 微博 | 文本 | 需登录获取更多 |
| Twitter/X | 文本 | 需登录获取更多 |
| Instagram | 文本 | 需登录获取更多 |

## 📁 文件结构

```
youtube-summarizer/
├── video_summarizer.py       # 主程序（多平台统一）
├── youtube_summarizer.py    # YouTube 专用版
├── bilibili_summarizer.py   # B站 专用版
├── config.example           # 配置示例
├── README.md                # 说明文档
└── requirements.txt        # 依赖
```

## 🏗️ 架构

```
视频 URL
    │
    ├─→ YouTube ─→ 字幕提取 ─→ LLM 分析 ─→ Markdown
    │
    ├─→ Bilibili ─→ 弹幕清洗 ─→ 字幕提取 ─→ LLM 分析 ─→ Markdown
    │
    ├─→ 抖音/西瓜 ─→ 描述提取 ─→ LLM 分析 ─→ Markdown
    │
    └─→ 微博/Twitter/Instagram ─→ 文本提取 ─→ LLM 分析 ─→ Markdown
```

## 📦 依赖

- `youtube-transcript-api`
- `requests`

## 🔗 GitHub

🔗 **https://github.com/Tuzfucius/youtube-transcript-summarizer**

---

*Built with ❤️ by OpenClaw*
