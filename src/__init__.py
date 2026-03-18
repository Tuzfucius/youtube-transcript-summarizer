#!/usr/bin/env python3
"""
src 包公共 API 导出
所有外部代码应通过此文件 import，而非直接引用子模块
"""

from .core import (
    VideoSummarizer,
    clean_danmaku_text,
    detect,
    detect_platform,
    get_all_tools,
    get_tool_definition,
    list_platforms,
    summarize,
)
from .extractors import (
    BilibiliExtractor,
    DanmakuCleaner,
    GenericExtractor,
    YouTubeExtractor,
)
from .prompts import DEFAULT_PROMPTS
from .utils import Timer, handle_errors, logger, retry, setup_logger

__version__ = "3.9.0"

__all__ = [
    # 核心函数
    "summarize", "detect", "detect_platform", "list_platforms",
    "clean_danmaku_text",
    # 类
    "VideoSummarizer",
    "YouTubeExtractor", "BilibiliExtractor",
    "DanmakuCleaner", "GenericExtractor",
    # 工具定义
    "get_tool_definition", "get_all_tools",
    # 工具函数
    "logger", "setup_logger", "Timer", "retry", "handle_errors",
    # 常量
    "DEFAULT_PROMPTS",
    "__version__",
]
