# 架构说明

本文档描述当前项目的实际架构、调用链路和扩展边界，便于后续继续维护或重构。

## 1. 项目目标

项目的核心目标不是“抓取任意平台的一切内容”，而是围绕以下主链路稳定工作：

1. 从视频页面提取可总结文本
2. 对文本做清洗、规整和统一建模
3. 调用 LLM 生成结构化总结
4. 通过 CLI、Web UI、MCP Server、导出脚本等入口对外提供能力

当前稳定支持的平台重点是：

- YouTube
- Bilibili

其中：

- YouTube 优先使用 `yt-dlp` 获取官方字幕，再回退到自动字幕，最后回退到 `youtube-transcript-api`
- Bilibili 优先尝试字幕轨，失败后回退到弹幕

## 2. 分层结构

### 2.1 入口层

入口层只负责参数、展示和文件输出，不承载核心业务逻辑：

- `cli.py`
- `web_ui.py`
- `mcp_server.py`
- `export_subtitle.py`

这一层的原则是：

- 不重复实现平台提取逻辑
- 不直接拼装复杂 Prompt
- 不持有密钥状态
- 只做输入转换、调用核心接口和展示结果

### 2.2 核心编排层

`src/core.py` 是主业务编排层，负责：

- 解析运行时配置
- 调用平台提取器
- 统一提取结果结构
- 组装 Prompt
- 调用 LLM
- 输出结构化结果

核心返回结构的稳定字段包括：

- `platform`
- `video_info`
- `summary`
- `format`
- `timestamp`
- `error`

### 2.3 配置层

`src/config.py` 负责统一配置来源：

1. `config.example.json` 提供参考模板
2. `config.json` 作为本机私有配置
3. 环境变量作为覆盖项
4. 显式函数参数优先级最高

设计原则：

- API Key 只保存在本机
- 日志和文档中不打印完整密钥
- 所有入口都复用同一套配置解析逻辑

### 2.4 提取兼容层

`src/extractors.py` 是兼容入口层，对上层暴露统一接口，对下层转发到 `src/services/`。

这样做的原因是：

- 便于保留旧接口
- 便于逐步重构底层提取逻辑
- 避免 CLI / Web UI / 核心流程直接依赖底层实现细节

### 2.5 服务层

`src/services/` 存放具体提取与清洗逻辑：

- `youtube.py`：YouTube 字幕提取与回退策略
- `bilibili.py`：Bilibili 视频信息、字幕、弹幕抓取
- `captions.py`：VTT / SRT / JSON3 解析与字幕清洗

服务层输出统一的内容载荷，常见字段包括：

- `title`
- `owner`
- `desc`
- `content`
- `segments`
- `source_type`
- `content_type`
- `language`
- `warnings`

## 3. 典型调用链路

### 3.1 总结链路

```text
CLI / Web UI / MCP / Python API
    -> src.core.VideoSummarizer.process()
    -> src.extractors.*
    -> src.services.*
    -> src.prompts.render_prompt()
    -> LLM API
    -> 结构化结果
```

### 3.2 导出链路

```text
export_subtitle.py
    -> src.extractors.*
    -> src.services.*
    -> 纯文本或 JSON 文件
```

## 4. 错误处理原则

项目当前采用“结构化错误优先”的方式：

- 平台解析失败时返回明确错误码
- 提取到空内容时返回 `EMPTY_CONTENT`
- 不在空内容情况下继续请求 LLM
- 将网络抖动、字幕缺失、自动字幕不可用等情况体现在 `warnings` 或错误信息中

## 5. 安全与本地文件原则

- `config.json` 不提交到仓库
- `history.db` 属于本地产物，不作为代码资产
- `logs/` 下日志属于运行时产物
- 示例配置只放在 `config.example.json`

## 6. 后续扩展建议

如果后续要扩展平台或重构功能，建议遵守以下顺序：

1. 先在 `src/services/` 实现真实提取能力
2. 再在 `src/extractors.py` 暴露兼容接口
3. 最后接入 `src/core.py`
4. 再补入口层和测试

这样可以避免入口层和底层逻辑反复耦合。
