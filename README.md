# Video Summarizer

这是一个围绕“视频文本提取 + LLM 总结”构建的 Python 项目。当前版本以 YouTube 和 Bilibili 为主要可用平台，重点保证真实提取链路、配置安全和入口层可维护性。

## 项目定位

项目当前的稳定能力是：

- 从 YouTube 提取官方字幕、自动字幕，必要时回退到 `youtube-transcript-api`
- 从 Bilibili 提取字幕，失败时回退到弹幕
- 对提取后的文本调用 LLM 做结构化总结
- 提供 CLI、Python API、Web UI、MCP Server、字幕导出等入口

项目不再沿用早期“支持 45+ 平台”的描述。是否可用，以仓库中真实实现和实际联调结果为准。

## 架构概览

核心链路如下：

```text
入口层
CLI / Web UI / MCP / 导出脚本 / Python API
    ->
核心编排层
src/core.py
    ->
提取兼容层
src/extractors.py
    ->
服务层
src/services/youtube.py / bilibili.py / captions.py
    ->
LLM API 或导出文件
```

更详细的设计说明见 [docs/README.md](/E:/Project/youtube-transcript-summarizer/docs/README.md)。

## 环境准备

推荐在 Windows 11 上用 conda 管理环境：

```bash
conda create -n youtube-summarizer python=3.11
conda activate youtube-summarizer
pip install -r requirements.txt
```

按需安装可选依赖：

```bash
pip install gradio
pip install faster-whisper
```

说明：

- `requirements.txt` 已包含基础运行所需的 `requests`、`yt-dlp`、`youtube-transcript-api`
- `gradio` 用于 Web UI
- `faster-whisper` 用于后续无字幕视频的语音转写能力

## 配置说明

### 配置文件原则

用户的 API Key 应保存在本机 `config.json` 中，不能上传到仓库。

仓库中只保留：

- [`config.example.json`](/E:/Project/youtube-transcript-summarizer/config.example.json)：可提交的模板

本机私有文件：

- `config.json`：真实密钥和本地参数

`config.json` 已被 `.gitignore` 忽略。

### 创建配置文件

Windows 下可以执行：

```bash
copy config.example.json config.json
```

然后编辑本地 `config.json`。

### 字段说明

推荐配置示例：

```json
{
  "api_key": "your-api-key-here",
  "api_url": "https://api.minimaxi.com/v1/chat/completions",
  "model": "MiniMax-M2.1",
  "format": "brief",
  "use_subtitle": true,
  "clean_danmaku": true,
  "cache_enabled": true,
  "log_level": "INFO"
}
```

字段含义：

- `api_key`：LLM API Key，必填，建议只保存在本机 `config.json`
- `api_url`：LLM 接口地址。默认是 OpenAI 兼容的 `/v1/chat/completions`
- `model`：模型名称
- `format`：默认总结格式，可选 `brief`、`detailed`、`timestamp`、`sentiment`、`trend`
- `use_subtitle`：对支持的平台优先尝试字幕轨
- `clean_danmaku`：是否对 Bilibili 弹幕做清洗
- `cache_enabled`：当前作为保留字段，后续可用于缓存扩展
- `log_level`：日志级别，例如 `INFO`、`DEBUG`、`WARNING`

### 配置来源优先级

运行时配置按以下顺序覆盖：

1. 显式函数参数或命令行参数
2. 环境变量
3. `config.json`
4. 内置默认值

### 支持的环境变量

可替代 `config.json` 的环境变量包括：

- `VIDEO_SUMMARIZER_API_KEY`
- `MINIMAX_API_KEY`
- `OPENAI_API_KEY`
- `VIDEO_SUMMARIZER_API_URL`
- `VIDEO_SUMMARIZER_MODEL`
- `VIDEO_SUMMARIZER_FORMAT`
- `VIDEO_SUMMARIZER_USE_SUBTITLE`
- `VIDEO_SUMMARIZER_CLEAN_DANMAKU`
- `VIDEO_SUMMARIZER_CACHE_ENABLED`
- `VIDEO_SUMMARIZER_LOG_LEVEL`

### 常见配置场景

#### 场景 1：默认使用本地配置

```bash
python cli.py url "https://www.youtube.com/watch?v=xxx"
```

#### 场景 2：命令行临时覆盖模型

```bash
python cli.py url "https://www.youtube.com/watch?v=xxx" --model gpt-4o-mini
```

#### 场景 3：命令行临时覆盖 API 地址

```bash
python cli.py url "https://www.youtube.com/watch?v=xxx" --api-url https://api.openai.com/v1/chat/completions
```

#### 场景 4：只导出字幕，不调用 LLM

```bash
python export_subtitle.py "https://www.youtube.com/watch?v=xxx" -f txt
```

## 使用方式

### Python API

```python
from src import summarize

result = summarize(
    "https://www.youtube.com/watch?v=xxx",
    format="brief"
)
print(result["summary"])
```

### CLI

```bash
python cli.py url "https://www.youtube.com/watch?v=xxx" -f brief
python cli.py batch urls.txt -f detailed
python cli.py compare "URL1" "URL2"
python cli.py config --set model=gpt-4o-mini
python cli.py providers
```

### 导出字幕或弹幕

```bash
python export_subtitle.py "https://www.youtube.com/watch?v=xxx" -f txt
python export_subtitle.py "https://www.bilibili.com/video/BVxxx" -f json
```

### Web UI

```bash
python web_ui.py --port 7860
```

### MCP Server

```bash
python mcp_server.py --mcp-stdio
python mcp_server.py --mcp-http --port 8080
```

如果未安装 `mcp` 相关依赖，脚本会给出明确提示，而不是在导入阶段直接崩溃。

## 返回结构

`summarize()` 返回结构化字典，常见字段如下：

```python
{
    "platform": "youtube",
    "video_info": {
        "id": "...",
        "url": "https://...",
        "title": "...",
        "owner": "...",
        "content_type": "字幕",
        "source_type": "subtitle",
        "language": "en",
        "content_length": 2094
    },
    "summary": "...",
    "format": "brief",
    "timestamp": "2026-03-18T09:23:53",
    "error": None
}
```

当内容为空、平台解析失败或 LLM 调用失败时，`error` 会包含结构化错误信息。

## 测试

运行：

```bash
pytest
```

当前测试重点覆盖：

- 入口层调用
- 配置读写与敏感信息遮蔽
- 无网络模拟链路
- 导出逻辑

真实线上视频验证不放入默认测试，而是作为手动联调流程执行。

## 目录说明

- [`docs/README.md`](/E:/Project/youtube-transcript-summarizer/docs/README.md)：项目架构说明
- [`src/README.md`](/E:/Project/youtube-transcript-summarizer/src/README.md)：核心模块说明
- [`src/services/README.md`](/E:/Project/youtube-transcript-summarizer/src/services/README.md)：提取服务层说明
- [`tests/README.md`](/E:/Project/youtube-transcript-summarizer/tests/README.md)：测试说明
- [`logs/README.md`](/E:/Project/youtube-transcript-summarizer/logs/README.md)：日志目录说明
