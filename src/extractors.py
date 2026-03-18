#!/usr/bin/env python3
"""
平台内容提取器
包含 YouTube、Bilibili、通用提取器和弹幕清洗器
"""

import gzip
import re
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Dict, List, Optional, Tuple

import requests

from .utils import handle_errors, logger, retry

# ============== Bilibili 公共请求头 ==============
BILIBILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}


# ============== 平台检测 ==============
_PLATFORMS: Dict[str, List[str]] = {
    "youtube":      ["youtube.com", "youtu.be"],
    "bilibili":     ["bilibili.com", "b站"],
    "douyin":       ["tiktok.com", "douyin"],
    "kuaishou":     ["kuaishou.com", "快手"],
    "xigua":        ["ixigua.com", "西瓜视频"],
    "twitch":       ["twitch.tv"],
    "vimeo":        ["vimeo.com"],
    "weibo":        ["weibo.com"],
    "twitter":      ["twitter.com", "x.com"],
    "instagram":    ["instagram.com"],
    "xiaohongshu":  ["xiaohongshu.com", "小红书"],
    "zhihu":        ["zhihu.com"],
    "telegram":     ["t.me"],
    "reddit":       ["reddit.com"],
    "medium":       ["medium.com"],
    "quora":        ["quora.com"],
    "pinterest":    ["pinterest.com"],
    "netease":      ["music.163.com"],
    "qqmusic":      ["y.qq.com"],
    "soundcloud":   ["soundcloud.com"],
    "taobao":       ["taobao.com"],
    "tmall":        ["tmall.com"],
    "jd":           ["jd.com"],
    "dewu":         ["dewu.com"],
    "zhuanzhuan":   ["zhuanzhuan.com"],
    "xianyu":       ["xianyu.com"],
    "amazon":       ["amazon."],
    "ebay":         ["ebay.com"],
    "etsy":         ["etsy.com"],
    "shopify":      ["shopify"],
    "meituan":      ["meituan.com"],
    "eleme":        ["ele.me"],
    "ctrip":        ["ctrip.com"],
    "mafengwo":     ["mafengwo.cn"],
    "airbnb":       ["airbnb.com"],
    "codeforces":   ["codeforces.com"],
    "leetcode":     ["leetcode.com"],
    "douban":       ["douban.com"],
    "tieba":        ["tieba.baidu.com"],
    "lofter":       ["lofter.com"],
    "douyu":        ["douyu.com"],
    "huya":         ["huya.com"],
    "yy":           ["yy.com"],
    "snapchat":     ["snapchat.com"],
}


def detect_platform(url: str) -> str:
    """根据 URL 检测所属平台，未匹配返回 'unknown'"""
    url_lower = url.lower()
    for platform, keywords in _PLATFORMS.items():
        if any(k in url_lower for k in keywords):
            return platform
    return "unknown"


def list_platforms() -> List[str]:
    """返回所有支持的平台名称"""
    return list(_PLATFORMS.keys())


# ============== 弹幕清洗器 ==============
class DanmakuCleaner:
    """B 站弹幕清洗，过滤无意义内容"""

    REMOVE_PATTERNS = [
        r"^[\d\.\,\-\+\=\s]+$",  # 纯数字/符号
        r"^.{1,2}$",              # 过短
        r"^[\w\s]{1,5}$",         # 过短英文
    ]
    KEEP_PATTERNS = [
        r"[\u4e00-\u9fff]{2,}",   # 至少两个汉字
        r"[，。！？]{2,}",         # 中文标点
        r"笑|哭|泪|牛逼|顶|赞|帅|美|可爱|哈哈",
    ]

    @classmethod
    @handle_errors(default_return=([], {"total": 0, "kept": 0}))
    def clean(
        cls,
        danmaku: List[Dict],
        min_len: int = 2,
        max_len: int = 50,
        spam_threshold: int = 3,
    ) -> Tuple[List[Dict], Dict]:
        """
        清洗弹幕列表。

        Args:
            danmaku: [{'time': float, 'text': str}, ...]
            min_len: 最短文字长度
            max_len: 最长文字长度
            spam_threshold: 同文本出现次数超过此值视为刷屏

        Returns:
            (cleaned_list, stats_dict)
        """
        stats = {"total": len(danmaku), "kept": 0, "removed": 0}

        # 统计高频文本（仅对较长文本计入刷屏）
        counter = Counter(
            d["text"] for d in danmaku if len(d.get("text", "")) > 5
        )
        spam_texts = {t for t, c in counter.items() if c > spam_threshold}

        cleaned: List[Dict] = []
        for d in danmaku:
            text = d.get("text", "").strip()
            if len(text) < min_len or len(text) > max_len or text in spam_texts:
                stats["removed"] += 1
                continue
            is_junk = any(re.search(p, text) for p in cls.REMOVE_PATTERNS)
            is_kept = any(re.search(p, text) for p in cls.KEEP_PATTERNS)
            if is_junk and not is_kept:
                stats["removed"] += 1
                continue
            cleaned.append(d)
            stats["kept"] += 1

        logger.info(
            f"弹幕清洗: {stats['total']} → {stats['kept']} "
            f"(保留率: {stats['kept'] / max(1, stats['total']) * 100:.1f}%)"
        )
        return cleaned, stats


# ============== YouTube 提取器 ==============
class YouTubeExtractor:
    """从 YouTube 提取字幕内容"""

    @staticmethod
    @handle_errors(default_return=None)
    def extract_video_id(url: str) -> Optional[str]:
        """解析视频 ID（11 位字符）"""
        m = (
            re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
            or re.search(r"youtu\.be\/([0-9A-Za-z_-]{11})", url)
        )
        return m.group(1) if m else None

    @staticmethod
    @handle_errors(default_return=None)
    @retry(max_attempts=3, delay=2.0)
    def get_transcript(video_id: str, langs: List[str] = None) -> Optional[Dict]:
        """
        获取字幕文本。

        Args:
            video_id: YouTube 视频 ID
            langs: 优先语言列表，默认 ['zh-Hans', 'en']

        Returns:
            {'text': str, 'language': str} 或 None
        """
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        for lang in langs or ["zh-Hans", "en"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                fetched = transcript.fetch()
                # 兼容新版 API（>= 0.6）：fetched 是可迭代的 snippet 对象
                if hasattr(fetched, "__iter__"):
                    try:
                        text = " ".join(
                            snippet.text
                            for snippet in fetched
                            if hasattr(snippet, "text")
                        )
                    except Exception:
                        text = str(fetched)
                else:
                    text = str(fetched)

                if text.strip():
                    return {"text": text, "language": lang}
            except Exception:
                continue

        logger.warning(f"YouTube 视频 {video_id} 无可用字幕")
        return None


# ============== Bilibili 提取器 ==============
class BilibiliExtractor:
    """从 Bilibili 提取字幕或弹幕内容"""

    @staticmethod
    @handle_errors(default_return=None)
    def extract_bvid(url: str) -> Optional[str]:
        """解析 BV 号"""
        m = re.search(r"BV[A-Za-z0-9]{10}", url)
        return m.group(0) if m else None

    @staticmethod
    @handle_errors(default_return=None)
    @retry(max_attempts=3, delay=1.0)
    def get_video_info(bvid: str) -> Optional[Dict]:
        """获取视频基本信息（标题、作者、cid 等）"""
        r = requests.get(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers=BILIBILI_HEADERS,
            timeout=10,
        )
        d = r.json()
        if d.get("code") != 0:
            raise ValueError(d.get("message", "API 错误"))
        info = d["data"]
        return {
            "bvid":     info["bvid"],
            "title":    info["title"],
            "owner":    info["owner"]["name"],
            "cid":      info["cid"],
            "duration": info["duration"],
            "stat":     info["stat"],
            "desc":     info.get("desc", ""),
        }

    @staticmethod
    @handle_errors(default_return={"has_subtitle": False, "text": ""})
    @retry(max_attempts=2, delay=1.0)
    def get_subtitles(bvid: str, cid: int) -> Dict:
        """
        获取 CC 字幕并拼接为纯文本。

        Returns:
            {'has_subtitle': bool, 'text': str}
        """
        r = requests.get(
            f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}",
            headers=BILIBILI_HEADERS,
            timeout=10,
        )
        d = r.json()
        if d.get("code") != 0:
            return {"has_subtitle": False, "text": ""}

        subtitles = d.get("data", {}).get("subtitle", {}).get("subtitles", [])
        if not subtitles:
            return {"has_subtitle": False, "text": ""}

        # 下载第一条字幕 JSON
        sub_url = subtitles[0].get("subtitle_url", "")
        if not sub_url.startswith("http"):
            sub_url = "https:" + sub_url

        sub_r = requests.get(sub_url, headers=BILIBILI_HEADERS, timeout=10)
        sub_data = sub_r.json()

        # 字幕格式：{"body": [{"content": "...", "from": ..., "to": ...}, ...]}
        body = sub_data.get("body", [])
        text = " ".join(
            item.get("content", "") for item in body if isinstance(item, dict)
        )
        return {"has_subtitle": bool(text), "text": text}

    @staticmethod
    @handle_errors(default_return=[])
    @retry(max_attempts=3, delay=1.0)
    def get_danmaku(cid: int) -> List[Dict]:
        """获取弹幕列表（XML 格式解析）"""
        r = requests.get(
            f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}",
            headers=BILIBILI_HEADERS,
            timeout=10,
        )
        # 尝试解压 gzip
        try:
            content = gzip.decompress(r.content)
        except Exception:
            content = r.content

        result: List[Dict] = []
        try:
            root = ET.fromstring(content)
            for elem in root.findall(".//d"):
                p_str = elem.get("p", "")
                if not p_str:
                    continue
                parts = p_str.split(",")
                try:
                    result.append({
                        "time": float(parts[0]),
                        "text": elem.text or "",
                    })
                except (ValueError, IndexError):
                    result.append({"time": 0.0, "text": elem.text or ""})
        except ET.ParseError as e:
            # XML 损坏时，提取所有文本节点
            logger.warning(f"弹幕 XML 解析异常，降级处理: {e}")
            try:
                text_str = content.decode("utf-8", errors="ignore")
                texts = re.findall(r">([^<]+)<", text_str)
                result = [
                    {"time": 0.0, "text": t.strip()}
                    for t in texts
                    if t.strip()
                ][:500]
            except Exception:
                pass

        return result


# ============== 通用提取器（其他平台回退） ==============
class GenericExtractor:
    """对未深度支持的平台，仅返回基础信息占位"""

    @staticmethod
    @handle_errors(default_return={})
    def get_info(url: str, platform: str = None) -> Dict:
        p = platform or detect_platform(url)
        return {
            "id":       url,
            "url":      url,
            "title":    f"{p} 内容",
            "platform": p,
            "content":  "",
            "content_type": "描述",
        }


__all__ = [
    "detect_platform", "list_platforms",
    "DanmakuCleaner",
    "YouTubeExtractor",
    "BilibiliExtractor",
    "GenericExtractor",
    "BILIBILI_HEADERS",
]
