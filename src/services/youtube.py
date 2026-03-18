#!/usr/bin/env python3
"""
YouTube 提取服务。

策略顺序：
1. yt-dlp 官方字幕
2. yt-dlp 自动字幕
3. youtube-transcript-api 兜底
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .captions import build_content_payload, parse_subtitle_file


DEFAULT_PREFERRED_LANGS = [
    "zh-Hans",
    "zh-CN",
    "zh",
    "zh-Hant",
    "zh-TW",
    "en",
    "en-US",
    "en-GB",
    "ja",
    "ko",
]


def normalize_youtube_url(url_or_id: str) -> str:
    """把视频 ID 或 URL 归一化为 YouTube URL。"""
    value = (url_or_id or "").strip()
    if not value:
        return value
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"https://www.youtube.com/watch?v={value}"


def select_best_subtitle_language(
    available_languages: Iterable[str],
    preferred_languages: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """按偏好顺序挑选字幕语言。"""
    available = [lang for lang in available_languages if lang]
    if not available:
        return None

    available_set = set(available)
    for language in preferred_languages or DEFAULT_PREFERRED_LANGS:
        if language in available_set:
            return language

    return sorted(available)[0]


def _load_ytdlp():
    try:
        import yt_dlp

        return yt_dlp
    except Exception:
        return None


def _extract_video_info(yt_dlp_module, url: str) -> Dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }
    with yt_dlp_module.YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _download_subtitles(yt_dlp_module, url: str, output_dir: Path, language: str, auto: bool) -> None:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "writesubtitles": not auto,
        "writeautomaticsub": auto,
        "subtitleslangs": [language],
        "subtitlesformat": "best",
        "outtmpl": str(output_dir / "%(id)s.%(language)s.%(ext)s"),
    }
    with yt_dlp_module.YoutubeDL(options) as ydl:
        ydl.download([url])


def _find_subtitle_files(output_dir: Path) -> List[Path]:
    candidates: List[Path] = []
    for suffix in ("*.vtt", "*.srt", "*.json3", "*.json"):
        candidates.extend(output_dir.glob(suffix))
    return sorted({path.resolve() for path in candidates})


def _parse_subtitle_download(output_dir: Path) -> Tuple[List[Dict], str]:
    for path in _find_subtitle_files(output_dir):
        segments = parse_subtitle_file(path)
        if segments:
            return segments, path.suffix.lower().lstrip(".")
    return [], ""


def _clear_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_file():
            try:
                child.unlink()
            except Exception:
                continue


def _extract_with_ytdlp(url: str, preferred_languages: Optional[Sequence[str]] = None) -> Optional[Dict]:
    yt_dlp_module = _load_ytdlp()
    if yt_dlp_module is None:
        return None

    try:
        preferred_languages = list(preferred_languages or DEFAULT_PREFERRED_LANGS)
        with tempfile.TemporaryDirectory(prefix="youtube_subtitles_") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            info = _extract_video_info(yt_dlp_module, url)
            video_id = str(info.get("id") or "")
            title = str(info.get("title") or "")
            owner = str(info.get("uploader") or info.get("channel") or "")
            desc = str(info.get("description") or "")

            subtitles = info.get("subtitles") or {}
            auto_subtitles = info.get("automatic_captions") or {}

            manual_lang = select_best_subtitle_language(subtitles.keys(), preferred_languages)
            auto_lang = select_best_subtitle_language(auto_subtitles.keys(), preferred_languages)

            warnings: List[str] = []
            metadata = {
                "extractor": info.get("extractor"),
                "webpage_url": info.get("webpage_url"),
                "duration": info.get("duration"),
            }

            attempts: List[Tuple[str, Optional[str], bool]] = [
                ("subtitle", manual_lang, False),
                ("auto_subtitle", auto_lang, True),
            ]

            for source_type, language, auto in attempts:
                if not language:
                    continue
                try:
                    _clear_directory(temp_dir)
                    _download_subtitles(yt_dlp_module, url, temp_dir, language, auto)
                except Exception as exc:
                    warnings.append(f"{source_type}:{language}:{exc}")
                    continue

                segments, ext = _parse_subtitle_download(temp_dir)
                if not segments:
                    warnings.append(f"{source_type}:{language}:empty")
                    continue

                return build_content_payload(
                    platform="youtube",
                    item_id=video_id or url,
                    url=url,
                    title=title,
                    owner=owner,
                    desc=desc,
                    language=language,
                    source_type=source_type,
                    content_type="字幕",
                    segments=segments,
                    warnings=warnings,
                    metadata={**metadata, "subtitle_format": ext},
                )

            return {
                "platform": "youtube",
                "id": video_id or url,
                "url": url,
                "title": title,
                "owner": owner,
                "desc": desc,
                "language": "",
                "source_type": "",
                "content_type": "字幕",
                "segments": [],
                "content": "",
                "text": "",
                "has_subtitle": False,
                "warnings": warnings,
                "metadata": metadata,
                "error": "yt-dlp 未找到可用字幕或自动字幕",
            }
    except Exception:
        return None


def _extract_with_transcript_api(video_id_or_url: str, preferred_languages: Optional[Sequence[str]] = None) -> Optional[Dict]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception:
        return None

    import re

    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([0-9A-Za-z_-]{11})", video_id_or_url or "")
    video_id = match.group(1) if match else (video_id_or_url.strip() if video_id_or_url else "")
    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)
    except Exception:
        return None

    for language in preferred_languages or DEFAULT_PREFERRED_LANGS:
        try:
            transcript = transcript_list.find_transcript([language])
            fetched = transcript.fetch()
            segments: List[Dict] = []
            for snippet in fetched:
                text = getattr(snippet, "text", "")
                start = float(getattr(snippet, "start", 0.0) or 0.0)
                duration = float(getattr(snippet, "duration", 0.0) or 0.0)
                if text:
                    segments.append({"start": start, "end": start + duration, "text": text})

            if segments:
                return build_content_payload(
                    platform="youtube",
                    item_id=video_id,
                    url=normalize_youtube_url(video_id_or_url),
                    title="",
                    owner="",
                    desc="",
                    language=language,
                    source_type="transcript_api",
                    content_type="字幕",
                    segments=segments,
                    warnings=["yt-dlp unavailable or failed"],
                    metadata={"provider": "youtube_transcript_api"},
                )
        except Exception:
            continue

    return None


def fetch_youtube_transcript(video_id_or_url: str, preferred_languages: Optional[Sequence[str]] = None) -> Optional[Dict]:
    """按优先级提取 YouTube 字幕。"""
    url = normalize_youtube_url(video_id_or_url)
    result = _extract_with_ytdlp(url, preferred_languages=preferred_languages)
    if result and result.get("content"):
        return result

    transcript_api_result = _extract_with_transcript_api(video_id_or_url, preferred_languages=preferred_languages)
    if transcript_api_result and transcript_api_result.get("content"):
        return transcript_api_result

    return result or transcript_api_result
