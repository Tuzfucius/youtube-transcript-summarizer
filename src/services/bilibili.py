#!/usr/bin/env python3
"""
Bilibili 提取服务。
"""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import requests

from .captions import build_content_payload, clean_caption_segments, segments_to_text


BILIBILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com/",
}


def extract_bvid(url: str) -> Optional[str]:
    """解析 Bilibili BV 号。"""
    match = re.search(r"BV[0-9A-Za-z]{10}", url or "")
    return match.group(0) if match else None


def get_bilibili_video_info(bvid: str) -> Optional[Dict]:
    """获取 Bilibili 视频基础信息。"""
    response = requests.get(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
        headers=BILIBILI_HEADERS,
        timeout=10,
    )
    data = response.json()
    if data.get("code") != 0:
        raise ValueError(data.get("message", "Bilibili API 错误"))

    info = data["data"]
    return {
        "bvid": info["bvid"],
        "title": info["title"],
        "owner": info["owner"]["name"],
        "cid": info["cid"],
        "duration": info["duration"],
        "stat": info["stat"],
        "desc": info.get("desc", ""),
    }


def _choose_subtitle_track(subtitles: List[Dict]) -> Optional[Dict]:
    if not subtitles:
        return None

    preferred = ("zh-Hans", "zh-CN", "zh", "zh-Hant", "zh-TW", "en")
    for language in preferred:
        for item in subtitles:
            if language.lower() in str(item.get("lan", "")).lower():
                return item
    return subtitles[0]


def get_bilibili_subtitles(bvid: str, cid: int) -> Dict:
    """获取 Bilibili 字幕并归一化。"""
    response = requests.get(
        f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}",
        headers=BILIBILI_HEADERS,
        timeout=10,
    )
    data = response.json()
    if data.get("code") != 0:
        return build_content_payload(
            platform="bilibili",
            item_id=bvid,
            url=f"https://www.bilibili.com/video/{bvid}",
            source_type="subtitle",
            content_type="字幕",
            segments=[],
            error=data.get("message", "Bilibili 字幕接口错误"),
        )

    subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
    track = _choose_subtitle_track(subtitles)
    if not track:
        return build_content_payload(
            platform="bilibili",
            item_id=bvid,
            url=f"https://www.bilibili.com/video/{bvid}",
            source_type="subtitle",
            content_type="字幕",
            segments=[],
            error="未找到可用字幕",
        )

    subtitle_url = track.get("subtitle_url", "")
    if subtitle_url and not subtitle_url.startswith("http"):
        subtitle_url = "https:" + subtitle_url

    subtitle_response = requests.get(subtitle_url, headers=BILIBILI_HEADERS, timeout=10)
    subtitle_data = subtitle_response.json()
    body = subtitle_data.get("body", [])

    segments = []
    for item in body:
        if not isinstance(item, dict):
            continue
        text = str(item.get("content", "")).strip()
        if not text:
            continue
        segments.append(
            {
                "start": float(item.get("from", 0.0) or 0.0),
                "end": float(item.get("to", 0.0) or 0.0),
                "text": text,
            }
        )

    return build_content_payload(
        platform="bilibili",
        item_id=bvid,
        url=f"https://www.bilibili.com/video/{bvid}",
        title="",
        owner="",
        desc="",
        language=str(track.get("lan", "")),
        source_type="subtitle",
        content_type="字幕",
        segments=segments,
        metadata={"subtitle_url": subtitle_url, "raw_track": track},
    )


def get_bilibili_danmaku(cid: int) -> List[Dict]:
    """获取 Bilibili 弹幕列表。"""
    response = requests.get(
        f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}",
        headers=BILIBILI_HEADERS,
        timeout=10,
    )
    try:
        content = gzip.decompress(response.content)
    except Exception:
        content = response.content

    result: List[Dict] = []
    try:
        root = ET.fromstring(content)
        for elem in root.findall(".//d"):
            text = (elem.text or "").strip()
            if not text:
                continue
            p_value = elem.get("p", "")
            parts = p_value.split(",")
            try:
                result.append({"time": float(parts[0]), "text": text})
            except Exception:
                result.append({"time": 0.0, "text": text})
    except ET.ParseError:
        text_str = content.decode("utf-8", errors="ignore")
        texts = re.findall(r">([^<]+)<", text_str)
        result = [{"time": 0.0, "text": text.strip()} for text in texts if text.strip()][:500]

    return clean_caption_segments(result)

