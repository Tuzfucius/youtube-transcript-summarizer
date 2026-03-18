#!/usr/bin/env python3
"""
提取服务层。

这里放置字幕解析、YouTube 回退抓取、Bilibili 内容抓取等内部实现，
由 `src.extractors` 作为兼容入口向外暴露。
"""

from .bilibili import (
    BILIBILI_HEADERS,
    extract_bvid,
    get_bilibili_danmaku,
    get_bilibili_subtitles,
    get_bilibili_video_info,
)
from .captions import (
    build_content_payload,
    clean_caption_segments,
    clean_text,
    parse_json3_subtitles,
    parse_srt_subtitles,
    parse_subtitle_file,
    parse_vtt_subtitles,
    segments_to_text,
)
from .youtube import fetch_youtube_transcript, normalize_youtube_url, select_best_subtitle_language

__all__ = [
    "BILIBILI_HEADERS",
    "extract_bvid",
    "get_bilibili_danmaku",
    "get_bilibili_subtitles",
    "get_bilibili_video_info",
    "build_content_payload",
    "clean_caption_segments",
    "clean_text",
    "parse_json3_subtitles",
    "parse_srt_subtitles",
    "parse_subtitle_file",
    "parse_vtt_subtitles",
    "segments_to_text",
    "fetch_youtube_transcript",
    "normalize_youtube_url",
    "select_best_subtitle_language",
]
