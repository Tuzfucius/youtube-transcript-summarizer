#!/usr/bin/env python3
"""
Prompt 模板与渲染工具。
"""

from __future__ import annotations

from typing import Dict, Optional

DEFAULT_PROMPTS: Dict[str, str] = {
    "brief": """\
请基于以下视频内容生成简洁总结。

标题：{title}
作者：{author}
描述：{desc}
内容：{content}

要求：
1. 使用中文输出。
2. 先给出 1 段摘要。
3. 再给出 3 到 5 个关键要点。
4. 总字数尽量控制在 {max_length} 字以内。

输出格式：
## 摘要
## 关键要点
- 要点 1
- 要点 2
""",
    "detailed": """\
请基于以下视频内容进行结构化分析。

标题：{title}
作者：{author}
描述：{desc}
播放量：{views:,}
点赞数：{likes:,}
内容：{content}

请按以下结构输出：
1. 视频主旨
2. 主要内容
3. 观众反馈或互动特征
4. 值得关注的细节
5. 可复用的观点或结论

要求：
使用中文，条理清晰，避免空话。
""",
    "timestamp": """\
请从以下内容中提取带时间顺序的信息。

标题：{title}
内容：{content}

请按以下结构输出：
## 一句话总结
## 时间线要点
- [时间] [事件或观点]
## 核心结论
""",
    "sentiment": """\
请分析以下内容的情绪倾向与互动氛围。

标题：{title}
内容：{content}

请按以下结构输出：
1. 整体情绪倾向
2. 主要情绪来源
3. 互动热度判断
4. 简短结论
""",
    "trend": """\
请分析以下内容是否具有传播趋势或话题价值。

标题：{title}
播放量：{views:,}
内容：{content}

请按以下结构输出：
1. 内容类型
2. 热点原因
3. 趋势判断
4. 后续观察建议
""",
}


def list_prompt_formats() -> list[str]:
    return list(DEFAULT_PROMPTS.keys())


def render_prompt(
    format_name: Optional[str] = None,
    *,
    template: Optional[str] = None,
    title: str = "",
    author: str = "",
    desc: str = "",
    views: int = 0,
    likes: int = 0,
    content: str = "",
    max_length: int = 500,
) -> str:
    source = template or DEFAULT_PROMPTS.get(format_name or "brief", DEFAULT_PROMPTS["brief"])
    rendered = source

    replacements = {
        "title": title or "",
        "author": author or "",
        "desc": desc or "",
        "content": content or "",
        "max_length": str(max_length or 500),
    }

    for placeholder in ("{views:,}", "{views}"):
        rendered = rendered.replace(placeholder, f"{views or 0:,}")
    for placeholder in ("{likes:,}", "{likes}"):
        rendered = rendered.replace(placeholder, f"{likes or 0:,}")

    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{key}}}", value)

    return rendered


__all__ = ["DEFAULT_PROMPTS", "list_prompt_formats", "render_prompt"]
