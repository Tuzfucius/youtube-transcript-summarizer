#!/usr/bin/env python3
"""
src 包统一导出。
外部入口尽量只从这里导入，避免直接依赖内部实现细节。
"""

from .config import (
    AppConfig,
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_PATH,
    load_config,
    load_env_config,
    mask_secret,
    redact_config,
    resolve_runtime_config,
)
from .core import (
    DEFAULT_PROMPTS,
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
from .prompts import list_prompt_formats, render_prompt
from .utils import Timer, handle_errors, logger, retry, setup_logger

__version__ = "3.10.0"

__all__ = [
    "summarize",
    "detect",
    "detect_platform",
    "list_platforms",
    "clean_danmaku_text",
    "VideoSummarizer",
    "YouTubeExtractor",
    "BilibiliExtractor",
    "DanmakuCleaner",
    "GenericExtractor",
    "get_tool_definition",
    "get_all_tools",
    "logger",
    "setup_logger",
    "Timer",
    "retry",
    "handle_errors",
    "DEFAULT_PROMPTS",
    "list_prompt_formats",
    "render_prompt",
    "AppConfig",
    "DEFAULT_CONFIG",
    "DEFAULT_CONFIG_PATH",
    "load_config",
    "load_env_config",
    "resolve_runtime_config",
    "mask_secret",
    "redact_config",
    "__version__",
]
