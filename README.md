# 🎬 Video Summarizer

**支持 40+ 平台的多平台内容总结工具**

## ✨ 特性

- 🎯 **40+ 平台支持** - 视频、社交、音乐、电商、编程社区
- 📝 **多种分析模式** - 简要、详细、时间戳、情感、趋势
- 🔧 **自定义 Prompt** - 完全自定义分析角度
- 💾 **弹幕清洗** - 自动过滤无意义内容
- ⚙️ **灵活配置** - 配置文件、环境变量、命令行参数

## 🌐 支持的平台

### 视频平台 (7)
YouTube · Bilibili · 抖音 · 快手 · 西瓜视频 · Twitch · Vimeo

### 社交媒体 (11)
微博 · Twitter/X · Instagram · 小红书 · 知乎 · Telegram · Snapchat · Pinterest · Reddit · Medium · Quora

### 音乐/音频 (4)
网易云音乐 · QQ音乐 · SoundCloud · Podcast

### 电商平台 (13)
淘宝 · 天猫 · 京东 · 得物 · 转转 · 闲鱼 · 亚马逊 · eBay · Etsy · Shopify · 美团 · 饿了么

### 旅游/本地生活 (5)
携程 · 马蜂窝 · Airbnb

### 编程社区 (2)
Codeforces · LeetCode

## 🚀 快速开始

```bash
pip install -r requirements.txt

# 使用
python video_summarizer.py "https://youtube.com/watch?v=xxx" -f detailed
python video_summarizer.py "https://bilibili.com/video/BVxxx" --no-clean
python video_summarizer.py "https://twitter.com/xxx/status/xxx" -f sentiment
```

## 📖 CLI 参数

```bash
-f, --format     总结格式 (brief/detailed/timestamp/sentiment/trend)
-p, --prompt     自定义 prompt 模板
--no-clean       不清洗弹幕
--no-subtitle    强制使用弹幕
--list-prompts   列出所有 prompt 类型
```

## 📦 依赖

- `youtube-transcript-api`
- `requests`

## 🔗 GitHub

🔗 **https://github.com/Tuzfucius/youtube-transcript-summarizer**

---

*Built with ❤️ by OpenClaw*
