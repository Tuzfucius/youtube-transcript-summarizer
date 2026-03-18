#!/usr/bin/env python3
"""
字幕与文本清洗工具。

职责：
- 解析 VTT / SRT / JSON3 字幕文件
- 清洗字幕分段
- 生成统一内容返回结构
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


_TIME_RE = re.compile(
    r"^(?:(\d{1,2}):)?(\d{2}):(\d{2})([.,]\d{3})?$"
)
_CUE_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}(?:[.,]\d{3})?)\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}(?:[.,]\d{3})?)"
)


def _timestamp_to_seconds(value: str) -> float:
    value = value.strip().replace(",", ".")
    match = _TIME_RE.match(value)
    if not match:
        return 0.0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    milliseconds = match.group(4)
    fraction = float(f"0{milliseconds}") if milliseconds else 0.0
    return hours * 3600 + minutes * 60 + seconds + fraction


def clean_text(text: str) -> str:
    """对单段字幕做基础清洗。"""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\u200b", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?，。！？；：])", r"\1", text)
    text = re.sub(r"([,.;:!?，。！？；：])([^\s])", r"\1 \2", text)
    return text.strip()


def clean_caption_segments(segments: Sequence[Dict]) -> List[Dict]:
    """清洗字幕分段并去掉空白与明显重复内容。"""
    cleaned: List[Dict] = []
    last_text = ""
    for segment in segments or []:
        text = clean_text(str(segment.get("text", "")))
        if not text:
            continue

        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", 0.0) or 0.0)
        if cleaned and text == last_text:
            continue

        cleaned.append({"start": start, "end": end, "text": text})
        last_text = text
    return cleaned


def segments_to_text(segments: Sequence[Dict]) -> str:
    """把字幕分段转成可供总结模型使用的纯文本。"""
    cleaned = clean_caption_segments(segments)
    return " ".join(segment["text"] for segment in cleaned).strip()


def parse_vtt_subtitles(text: str) -> List[Dict]:
    """解析 WebVTT 字幕。"""
    segments: List[Dict] = []
    current: List[str] = []
    start = 0.0
    end = 0.0

    for raw_line in text.splitlines():
        line = raw_line.strip("\ufeff").strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE"):
            if current:
                segments.append({"start": start, "end": end, "text": clean_text(" ".join(current))})
                current = []
            continue

        cue_match = _CUE_RE.search(line)
        if cue_match:
            if current:
                segments.append({"start": start, "end": end, "text": clean_text(" ".join(current))})
            start = _timestamp_to_seconds(cue_match.group("start"))
            end = _timestamp_to_seconds(cue_match.group("end"))
            current = []
            continue

        if re.fullmatch(r"\d+", line):
            continue

        current.append(line)

    if current:
        segments.append({"start": start, "end": end, "text": clean_text(" ".join(current))})

    return clean_caption_segments(segments)


def parse_srt_subtitles(text: str) -> List[Dict]:
    """解析 SRT 字幕。"""
    segments: List[Dict] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        time_line_index = 0
        if re.fullmatch(r"\d+", lines[0]):
            time_line_index = 1
        if time_line_index >= len(lines):
            continue
        cue_match = _CUE_RE.search(lines[time_line_index])
        if not cue_match:
            continue
        body = " ".join(lines[time_line_index + 1 :])
        segments.append(
            {
                "start": _timestamp_to_seconds(cue_match.group("start")),
                "end": _timestamp_to_seconds(cue_match.group("end")),
                "text": clean_text(body),
            }
        )
    return clean_caption_segments(segments)


def parse_json3_subtitles(text: str) -> List[Dict]:
    """解析 YouTube JSON3 字幕。"""
    payload = json.loads(text)
    events = payload.get("events", [])
    segments: List[Dict] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        body = event.get("segs") or []
        raw_text = "".join(seg.get("utf8", "") for seg in body if isinstance(seg, dict))
        text_value = clean_text(raw_text)
        if not text_value:
            continue

        start = float(event.get("tStartMs", 0) or 0) / 1000.0
        duration = float(event.get("dDurationMs", 0) or 0) / 1000.0
        segments.append(
            {
                "start": start,
                "end": start + duration,
                "text": text_value,
            }
        )

    return clean_caption_segments(segments)


def parse_subtitle_file(path: Path) -> List[Dict]:
    """根据文件后缀解析字幕文件。"""
    suffix = path.suffix.lower()
    content = path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".vtt":
        return parse_vtt_subtitles(content)
    if suffix == ".srt":
        return parse_srt_subtitles(content)
    if suffix in {".json3", ".json"}:
        try:
            return parse_json3_subtitles(content)
        except Exception:
            return []
    return []


def build_content_payload(
    *,
    platform: str,
    item_id: str,
    url: str,
    title: str = "",
    owner: str = "",
    desc: str = "",
    language: str = "",
    source_type: str = "",
    content_type: str = "字幕",
    segments: Optional[Sequence[Dict]] = None,
    warnings: Optional[Sequence[str]] = None,
    metadata: Optional[Dict] = None,
    error: str = "",
) -> Dict:
    """构造统一返回结构。"""
    normalized_segments = clean_caption_segments(list(segments or []))
    text = segments_to_text(normalized_segments)
    payload = {
        "platform": platform,
        "id": item_id,
        "url": url,
        "title": title,
        "owner": owner,
        "desc": desc,
        "language": language,
        "source_type": source_type,
        "content_type": content_type,
        "segments": normalized_segments,
        "content": text,
        "text": text,
        "has_subtitle": bool(text),
        "warnings": list(warnings or []),
        "metadata": dict(metadata or {}),
        "error": error,
    }
    return payload

