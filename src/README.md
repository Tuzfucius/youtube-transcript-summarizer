# src/ 模块说明

本目录包含 Video Summarizer 的所有核心源码，入口脚本（`cli.py`、`mcp_server.py` 等）在项目根目录。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 统一导出公共 API |
| `utils.py` | 公共工具：日志、重试装饰器、错误处理、计时器 |
| `prompts.py` | 所有 LLM Prompt 模板集中管理 |
| `extractors.py` | 各平台内容提取器（YouTube、Bilibili、通用），弹幕清洗器 |
| `core.py` | `VideoSummarizer` 类、`summarize()` / `detect()` 便捷函数 |
| `advanced.py` | 异步批量处理、历史记录（SQLite）、多 LLM 工厂、视频对比 |

## Import 示例

```python
# 推荐：从 src 导入
from src import summarize, detect

# 或直接使用根目录兼容层
from video_summarizer import summarize
```
