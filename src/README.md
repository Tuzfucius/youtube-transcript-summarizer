# `src/` 模块说明

`src/` 目录保存项目的核心能力，外部入口建议统一通过 `src` 包导入，不要直接依赖内部实现文件。

## 目录职责

| 文件 | 作用 |
|---|---|
| `__init__.py` | 统一对外导出 API，减少外部代码对内部结构的耦合 |
| `config.py` | 读取本地 `config.json`、环境变量和显式参数，并生成运行时配置 |
| `core.py` | 核心总结流程：内容提取结果规范化、Prompt 组装、LLM 调用、结果封装 |
| `extractors.py` | 平台内容提取器，负责字幕、弹幕或通用内容抓取 |
| `prompts.py` | Prompt 模板和渲染工具 |
| `utils.py` | 日志、重试、错误处理、计时器等公共工具 |
| `advanced.py` | 异步批处理、历史记录和其他扩展能力 |

## 配置原则

`config.json` 只允许保存在本地，不应提交到仓库。用户的 `api_key` 应优先通过本地配置或环境变量读取，日志中不得打印完整密钥。

## 主要调用方式

```python
from src import summarize

result = summarize("https://www.youtube.com/watch?v=xxx", format="brief")
print(result["summary"])
```

## 结果约定

`summarize()` 返回结构化字典，常见字段包括：

- `platform`
- `video_info`
- `summary`
- `format`
- `timestamp`
- `error`，仅在异常或空内容时出现

