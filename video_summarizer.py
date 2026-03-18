#!/usr/bin/env python3
"""
兼容层 - 从 src 重导出所有公共 API
保持向后兼容，旧代码无需修改 import 路径
"""
from src import *  # noqa: F401, F403
from src import (  # noqa: F401
    DEFAULT_PROMPTS,
    Timer,
    VideoSummarizer,
    BilibiliExtractor,
    DanmakuCleaner,
    GenericExtractor,
    YouTubeExtractor,
    clean_danmaku_text,
    detect,
    detect_platform,
    get_all_tools,
    get_tool_definition,
    handle_errors,
    list_platforms,
    logger,
    retry,
    setup_logger,
    summarize,
    __version__,
)
