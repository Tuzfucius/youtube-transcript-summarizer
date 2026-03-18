#!/usr/bin/env python3
"""
平台内容提取兼容层。

对外保持 `src.extractors` 的旧入口不变，内部转接到 `src.services`。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from .services import (
    BILIBILI_HEADERS,
    build_content_payload,
    clean_caption_segments,
    clean_text,
    extract_bvid as service_extract_bvid,
    fetch_youtube_transcript,
    get_bilibili_danmaku,
    get_bilibili_subtitles,
    get_bilibili_video_info,
)
from .utils import handle_errors, logger


_PLATFORMS: Dict[str, List[str]] = {
    "youtube": ["youtube.com", "youtu.be", "youtube-nocookie.com"],
    "bilibili": ["bilibili.com", "b23.tv", "b站"],
    "douyin": ["tiktok.com", "douyin"],
    "kuaishou": ["kuaishou.com", "快手"],
    "xigua": ["ixigua.com", "西瓜视频"],
    "twitch": ["twitch.tv"],
    "vimeo": ["vimeo.com"],
    "weibo": ["weibo.com"],
    "twitter": ["twitter.com", "x.com"],
    "instagram": ["instagram.com"],
    "xiaohongshu": ["xiaohongshu.com", "小红书"],
    "zhihu": ["zhihu.com"],
    "telegram": ["t.me"],
    "reddit": ["reddit.com"],
    "medium": ["medium.com"],
    "quora": ["quora.com"],
    "pinterest": ["pinterest.com"],
    "netease": ["music.163.com"],
    "qqmusic": ["y.qq.com"],
    "soundcloud": ["soundcloud.com"],
    "taobao": ["taobao.com"],
    "tmall": ["tmall.com"],
    "jd": ["jd.com"],
    "dewu": ["dewu.com"],
    "zhuanzhuan": ["zhuanzhuan.com"],
    "xianyu": ["xianyu.com"],
    "amazon": ["amazon."],
    "ebay": ["ebay.com"],
    "etsy": ["etsy.com"],
    "shopify": ["shopify"],
    "meituan": ["meituan.com"],
    "eleme": ["ele.me"],
    "ctrip": ["ctrip.com"],
    "mafengwo": ["mafengwo.cn"],
    "airbnb": ["airbnb.com"],
    "codeforces": ["codeforces.com"],
    "leetcode": ["leetcode.com"],
    "douban": ["douban.com"],
    "tieba": ["tieba.baidu.com"],
    "lofter": ["lofter.com"],
    "douyu": ["douyu.com"],
    "huya": ["huya.com"],
    "yy": ["yy.com"],
    "snapchat": ["snapchat.com"],
}


def detect_platform(url: str) -> str:
    """根据 URL 检测所属平台。"""
    url_lower = (url or "").lower()
    for platform, keywords in _PLATFORMS.items():
        if any(keyword in url_lower for keyword in keywords):
            return platform
    return "unknown"


def list_platforms() -> List[str]:
    """返回支持的平台列表。"""
    return list(_PLATFORMS.keys())


class DanmakuCleaner:
    """B 站弹幕清洗器。"""

    REMOVE_PATTERNS = [
        r"^[\d\.\,\-\+\=\s]+$",
        r"^.{1,2}$",
        r"^[\w\s]{1,5}$",
    ]
    KEEP_PATTERNS = [
        r"[\u4e00-\u9fff]{2,}",
        r"[，。！？；：]{2,}",
        r"哈哈|笑死|牛|绝了|可以|不错|好家伙",
    ]

    @classmethod
    @handle_errors(default_return=([], {"total": 0, "kept": 0, "removed": 0}))
    def clean(
        cls,
        danmaku: List[Dict],
        min_len: int = 2,
        max_len: int = 50,
        spam_threshold: int = 3,
    ) -> Tuple[List[Dict], Dict]:
        """清洗弹幕列表。"""
        stats = {"total": len(danmaku), "kept": 0, "removed": 0}
        counter = Counter(
            item.get("text", "").strip() for item in danmaku if len(item.get("text", "").strip()) > 5
        )
        spam_texts = {text for text, count in counter.items() if count > spam_threshold}

        cleaned: List[Dict] = []
        for item in danmaku:
            text = clean_text(str(item.get("text", "")))
            if len(text) < min_len or len(text) > max_len or text in spam_texts:
                stats["removed"] += 1
                continue

            is_junk = any(re.search(pattern, text) for pattern in cls.REMOVE_PATTERNS)
            is_kept = any(re.search(pattern, text) for pattern in cls.KEEP_PATTERNS)
            if is_junk and not is_kept:
                stats["removed"] += 1
                continue

            cleaned.append({"time": float(item.get("time", 0.0) or 0.0), "text": text})
            stats["kept"] += 1

        logger.info(
            "弹幕清洗: %s -> %s (保留率 %.1f%%)",
            stats["total"],
            stats["kept"],
            stats["kept"] / max(1, stats["total"]) * 100,
        )
        return cleaned, stats


class YouTubeExtractor:
    """YouTube 字幕提取器。"""

    @staticmethod
    @handle_errors(default_return=None)
    def extract_video_id(url: str) -> Optional[str]:
        """解析 YouTube 视频 ID。"""
        value = url or ""
        patterns = [
            r"(?:v=|\/shorts\/|\/embed\/)([0-9A-Za-z_-]{11})",
            r"youtu\.be\/([0-9A-Za-z_-]{11})",
            r"youtube\.com\/watch\?v=([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(1)
        if re.fullmatch(r"[0-9A-Za-z_-]{11}", value.strip()):
            return value.strip()
        return None

    @staticmethod
    @handle_errors(default_return=None)
    def get_transcript(video_id: str, langs: List[str] = None) -> Optional[Dict]:
        """
        获取字幕文本。

        优先使用 yt-dlp，再回退到 youtube-transcript-api。
        """
        result = fetch_youtube_transcript(video_id, preferred_languages=langs)
        if not result:
            return None
        return result


class BilibiliExtractor:
    """Bilibili 字幕和弹幕提取器。"""

    @staticmethod
    @handle_errors(default_return=None)
    def extract_bvid(url: str) -> Optional[str]:
        return service_extract_bvid(url)

    @staticmethod
    @handle_errors(default_return=None)
    def get_video_info(bvid: str) -> Optional[Dict]:
        return get_bilibili_video_info(bvid)

    @staticmethod
    @handle_errors(default_return={"has_subtitle": False, "text": "", "segments": []})
    def get_subtitles(bvid: str, cid: int) -> Dict:
        payload = get_bilibili_subtitles(bvid, cid)
        return {
            "has_subtitle": bool(payload.get("content")),
            "text": payload.get("content", ""),
            "segments": payload.get("segments", []),
            "language": payload.get("language", ""),
            "source_type": payload.get("source_type", ""),
            "content_type": payload.get("content_type", "字幕"),
            "payload": payload,
        }

    @staticmethod
    @handle_errors(default_return=[])
    def get_danmaku(cid: int) -> List[Dict]:
        return get_bilibili_danmaku(cid)


class GenericExtractor:
    """兜底提取器。"""

    @staticmethod
    @handle_errors(default_return={})
    def get_info(url: str, platform: str = None) -> Dict:
        p = platform or detect_platform(url)
        return build_content_payload(
            platform=p,
            item_id=url,
            url=url,
            title=f"{p} 内容",
            source_type="generic",
            content_type="描述",
            segments=[],
        )


__all__ = [
    "detect_platform",
    "list_platforms",
    "DanmakuCleaner",
    "YouTubeExtractor",
    "BilibiliExtractor",
    "GenericExtractor",
    "BILIBILI_HEADERS",
]
