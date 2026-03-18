# `src/` 目录说明

`src/` 是项目的核心代码目录。外部调用应尽量通过 `src` 包暴露的接口进入，而不是直接依赖内部实现细节。

## 核心职责

`src/` 负责三件事：

1. 解析运行时配置
2. 提取并标准化平台文本内容
3. 调用 LLM 生成总结结果

## 文件说明

| 文件 | 作用 |
|---|---|
| `__init__.py` | 统一导出稳定 API |
| `config.py` | 统一解析 `config.json`、环境变量和显式参数 |
| `core.py` | 主编排层，负责提取、Prompt、LLM、结果封装 |
| `extractors.py` | 平台提取兼容入口 |
| `prompts.py` | Prompt 模板与渲染 |
| `utils.py` | 日志、重试、错误处理、计时器 |
| `advanced.py` | 批处理、历史记录、对比等扩展能力 |

## 与其他目录的关系

- `src/` 不负责 CLI 参数解析
- `src/` 不负责 Web UI 视图渲染
- `src/` 不负责落盘导出格式
- 这些工作分别交给根目录下的入口脚本处理

## 推荐调用方式

```python
from src import summarize

result = summarize("https://www.youtube.com/watch?v=xxx", format="brief")
print(result["summary"])
```

## 结果约定

`summarize()` 返回结构化字典，核心字段包括：

- `platform`
- `video_info`
- `summary`
- `format`
- `timestamp`
- `error`

`error` 只在以下情况出现：

- 视频 ID 或 BV 号无法解析
- 没有提取到可总结内容
- LLM 请求失败
