# `src/services/` 目录说明

这个目录存放平台提取与字幕清洗的底层实现，不直接作为外部业务入口。

## 文件职责

- `captions.py`：解析 `vtt`、`srt`、`json3`，清洗字幕片段并生成统一内容载荷
- `youtube.py`：YouTube 字幕提取，优先 `yt-dlp`，失败后回退到 `youtube-transcript-api`
- `bilibili.py`：Bilibili 视频信息、字幕和弹幕抓取

## 设计原则

- 上层统一通过 `src.extractors` 调用，避免入口层直接依赖底层文件
- 尽量把所有提取结果收敛为同一种结构
- 服务层只负责提取与标准化，不负责 LLM 配置和总结逻辑

## 标准化字段

服务层返回值尽量包含以下字段：

- `title`
- `owner`
- `desc`
- `content`
- `segments`
- `source_type`
- `content_type`
- `language`
- `warnings`

## 当前重点平台

- YouTube
- Bilibili

其他平台如果要支持，建议在这一层新增独立服务文件，再由 `src.extractors` 提供兼容入口。
