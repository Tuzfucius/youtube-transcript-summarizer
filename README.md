# Video Summarizer

一个以视频内容提取和文本总结为主的 Python 项目。当前仓库的重点是把视频字幕、自动字幕或弹幕整理成可读文本，再交给 LLM 做总结。

## 当前能力

- 支持 YouTube 和 Bilibili 的内容提取
- 支持基于 `src.core.summarize()` 的文本总结
- 支持 CLI、Web UI、导出字幕/弹幕
- 支持本地 `config.json` 读取，但不会把密钥写进日志
- 支持历史记录、对比和批量处理等入口命令

## 说明

仓库里原先的“45+ 平台”描述过于夸大。实际可用性取决于每个平台的提取实现和外部接口状态，当前文档不再做超出实现能力的承诺。

`config.json` 是本机私有配置文件，里面可以放 API Key，但它不应该上传到仓库。仓库只保留 `config.example.json` 作为模板，`.gitignore` 也已经忽略了 `config.json`。

## 环境

推荐在 Windows 11 上使用 conda 创建虚拟环境：

```bash
conda create -n youtube-summarizer python=3.11
conda activate youtube-summarizer
pip install -r requirements.txt
```

如果需要 Web UI 或字幕转写，再按需安装额外依赖：

```bash
pip install gradio
pip install yt-dlp
pip install faster-whisper
```

## 配置

复制示例配置并在本地修改：

```bash
copy config.example.json config.json
```

`config.json` 建议至少包含以下字段：

```json
{
  "api_key": "your-api-key-here",
  "api_url": "https://api.minimaxi.com/v1/chat/completions",
  "model": "MiniMax-M2.1",
  "format": "brief",
  "use_subtitle": true,
  "clean_danmaku": true
}
```

## 使用

### CLI

```bash
python cli.py url "https://www.youtube.com/watch?v=xxx" -f brief
python cli.py batch urls.txt -f detailed
python cli.py compare "URL1" "URL2"
python cli.py config --set api_key=your-key
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

### Python API

```python
from src import summarize

result = summarize(
    "https://www.youtube.com/watch?v=xxx",
    format="brief",
    api_key="your-key",
)
print(result["summary"])
```

## 测试

```bash
pytest
```

测试默认不依赖线上接口，重点覆盖入口层、文本导出和无网络链路的模拟总结。

## 目录说明

- `src/`：核心提取、清洗、总结逻辑
- `tests/`：测试用例与测试说明
- `cli.py`：命令行入口
- `web_ui.py`：Web UI 入口
- `export_subtitle.py`：字幕/弹幕导出入口

