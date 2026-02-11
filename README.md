# 📹 YouTube Transcript Summarizer

基于字幕的 YouTube 视频总结工具。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/jetson/.openclaw/workspace/skills/youtube-summarizer
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp config.example .env
# 编辑 .env 填入你的 API Key
```

### 3. 运行

```bash
# 基本使用
python youtube_summarizer.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 详细格式
python youtube_summarizer.py "https://www.youtube.com/watch?v=VIDEO_ID" -f detailed

# 带时间戳
python youtube_summarizer.py "https://www.youtube.com/watch?v=VIDEO_ID" -f timestamp
```

## 📖 使用示例

```bash
# 简要总结
python youtube_summarizer.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 详细总结
python youtube_summarizer.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --format detailed --max-length 800

# 时间戳版本
python youtube_summarizer.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --format timestamp
```

## 🔧 CLI 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | YouTube 视频链接 | 必需 |
| `-f, --format` | 输出格式 | brief |
| `-m, --max-length` | 最大长度 | 500 |
| `-p, --provider` | LLM 提供商 | deepseek |
| `-k, --api-key` | API Key | 从环境变量读取 |
| `--save/--no-save` | 是否保存文件 | True |

## 📝 输出格式

### brief (简要)
```markdown
## 摘要
[简短总结]

## 关键要点
- 要点 1
- 要点 2
- 要点 3
```

### detailed (详细)
```markdown
## 完整摘要
[详细总结]

## 关键要点
1. 要点 1
2. 要点 2
3. 要点 3
...

## 结论
[结论或建议]
```

### timestamp (时间戳)
```markdown
## 摘要
[一句话总结]

## 时间戳要点
- [03:12] 相关话题
- [08:45] 重要信息
...

## 核心要点
- 要点 1
- 要点 2
- 要点 3
```

## 🏗️ 架构设计

```
YouTube URL
    │
    ▼
┌─────────────────────┐
│  Extract Video ID    │
│  (正则表达式)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Get Transcript      │
│  youtube-transcript │
│  -api              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Split Text         │
│  (避免超上下文)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  LLM Summarize      │
│  DeepSeek / OpenAI  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Format Output      │
│  Markdown 保存      │
└─────────────────────┘
```

## ⚠️ 注意事项

1. **字幕可用性**: 部分视频没有字幕
2. **语言**: 默认优先英文，然后中文
3. **长度**: 长视频处理时间较长
4. **API 成本**: 考虑使用 DeepSeek（性价比高）

## 📦 依赖

- `youtube-transcript-api`
- `openai`
- `requests`
- `python-dotenv`

## 🔗 参考项目

- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- [summarize_anything](https://github.com/rodion-m/summarize_anything)
- [yt-transcript-summarizer](https://github.com/fschuhi/yt-transcript-summarizer)

---

*Built with ❤️ by OpenClaw Agent System*
