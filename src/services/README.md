# services 目录说明

这里存放提取链路的内部实现，不直接作为业务入口给外部调用。

## 文件职责

- `captions.py`：字幕文件解析、字幕清洗、统一返回结构构造。
- `youtube.py`：YouTube 内容提取，优先 `yt-dlp` 官方字幕，再回退到自动字幕和 `youtube-transcript-api`。
- `bilibili.py`：Bilibili 视频信息、字幕、弹幕抓取。

## 设计原则

- 外部调用继续通过 `src.extractors` 进入，避免影响现有 `core.py`、CLI、Web UI。
- 所有提取结果尽量标准化为同一结构，至少包含 `text`、`content`、`segments`、`source_type`、`language`。
- API key、Cookie、账号凭据不在这里处理。
