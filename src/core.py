#!/usr/bin/env python3
"""
核心总结层。
负责配置装配、内容提取结果规范化、Prompt 组装、LLM 调用和结果输出。
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List, Mapping, Optional

import requests

from .config import AppConfig, resolve_runtime_config
from .extractors import (
    BilibiliExtractor,
    DanmakuCleaner,
    GenericExtractor,
    YouTubeExtractor,
    detect_platform,
    list_platforms,
)
from .prompts import DEFAULT_PROMPTS, render_prompt
from .utils import Timer, logger

DEFAULT_CONTENT_LIMIT = 3000
DEFAULT_MAX_TOKENS = 2000
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TIMEOUT = 60


def _now_iso() -> str:
    return datetime.now().isoformat()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
    return str(value).strip()


def _segments_to_text(segments: Any) -> str:
    if not isinstance(segments, list):
        return ""

    texts: List[str] = []
    for segment in segments:
        if isinstance(segment, dict):
            candidate = (
                segment.get("content")
                or segment.get("text")
                or segment.get("snippet")
                or segment.get("line")
            )
            text = _normalize_text(candidate)
            if text:
                texts.append(text)
        elif isinstance(segment, (list, tuple)) and segment:
            text = _normalize_text(segment[-1])
            if text:
                texts.append(text)
        else:
            text = _normalize_text(segment)
            if text:
                texts.append(text)

    return "\n".join(texts).strip()


def _normalize_source_payload(raw: Any, default_source_type: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "content": "",
        "segments": [],
        "language": "",
        "warnings": [],
        "source_type": default_source_type,
        "content_type": default_source_type,
    }

    if raw is None:
        return payload

    if isinstance(raw, str):
        payload["content"] = raw.strip()
        return payload

    if isinstance(raw, tuple):
        if raw:
            payload["content"] = _normalize_text(raw[0])
        if len(raw) > 1 and isinstance(raw[1], dict):
            payload.update(_normalize_source_payload(raw[1], default_source_type))
        return payload

    if isinstance(raw, dict):
        payload["title"] = _normalize_text(raw.get("title"))
        payload["owner"] = _normalize_text(raw.get("owner") or raw.get("author"))
        payload["desc"] = _normalize_text(raw.get("desc") or raw.get("description"))
        payload["language"] = _normalize_text(raw.get("language"))
        payload["source_type"] = _normalize_text(
            raw.get("source_type") or raw.get("type") or default_source_type
        ) or default_source_type
        payload["content_type"] = _normalize_text(
            raw.get("content_type") or raw.get("source_type") or default_source_type
        ) or default_source_type
        payload["warnings"] = raw.get("warnings", []) if isinstance(raw.get("warnings"), list) else []
        payload["segments"] = raw.get("segments") if isinstance(raw.get("segments"), list) else []

        content = (
            raw.get("content")
            or raw.get("text")
            or raw.get("summary")
            or raw.get("transcript")
            or raw.get("body")
        )
        if isinstance(content, list):
            payload["content"] = _segments_to_text(content)
        else:
            payload["content"] = _normalize_text(content)

        if not payload["content"] and payload["segments"]:
            payload["content"] = _segments_to_text(payload["segments"])
        return payload

    payload["content"] = _normalize_text(raw)
    return payload


def _trim_content(content: str, limit: int = DEFAULT_CONTENT_LIMIT) -> str:
    text = _normalize_text(content)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _strip_reasoning_content(text: str) -> str:
    """移除部分推理模型返回的 think 标签内容。"""
    value = _normalize_text(text)
    if not value:
        return ""
    value = re.sub(r"<think>.*?</think>", "", value, flags=re.IGNORECASE | re.DOTALL)
    return value.strip()


def _structure_error(code: str, message: str, **details: Any) -> Dict[str, Any]:
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return error


def _extract_error_message(error: Any) -> str:
    if isinstance(error, dict):
        return _normalize_text(error.get("message") or error.get("error") or error.get("detail"))
    return _normalize_text(error)


class VideoSummarizer:
    """多平台视频内容总结器。"""

    def __init__(
        self,
        config: Optional[Mapping[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> None:
        self.config: AppConfig = resolve_runtime_config(config, config_path=config_path)
        self.api_key = self.config.api_key
        self.api_url = self.config.api_url
        self.model = self.config.model
        self.prompts = DEFAULT_PROMPTS.copy()

    def _extract(self, url: str, use_sub: bool, clean: bool) -> Dict[str, Any]:
        """按平台提取内容，并规范化为统一结构。"""
        platform = detect_platform(url)
        logger.info(f"提取 {platform} 内容: {url[:60]}...")

        if platform == "youtube":
            video_id = YouTubeExtractor.extract_video_id(url)
            if not video_id:
                return {
                    "platform": platform,
                    "id": "",
                    "url": url,
                    "title": "",
                    "owner": "",
                    "desc": "",
                    "views": 0,
                    "likes": 0,
                    "content": "",
                    "segments": [],
                    "source_type": "subtitle",
                    "content_type": "字幕",
                    "error": _structure_error("INVALID_VIDEO_ID", "无法解析 YouTube 视频 ID"),
                }

            transcript = YouTubeExtractor.get_transcript(video_id)
            transcript_payload = _normalize_source_payload(transcript, "subtitle")
            content = transcript_payload["content"]

            return {
                "platform": platform,
                "id": video_id,
                "url": url,
                "title": transcript_payload.get("title", ""),
                "owner": transcript_payload.get("owner", ""),
                "desc": transcript_payload.get("desc", ""),
                "views": 0,
                "likes": 0,
                "content": content,
                "segments": transcript_payload["segments"],
                "language": transcript_payload["language"],
                "warnings": transcript_payload["warnings"],
                "source_type": transcript_payload["source_type"] or "subtitle",
                "content_type": "字幕",
            }

        if platform == "bilibili":
            bvid = BilibiliExtractor.extract_bvid(url)
            if not bvid:
                return {
                    "platform": platform,
                    "id": "",
                    "url": url,
                    "title": "",
                    "owner": "",
                    "desc": "",
                    "views": 0,
                    "likes": 0,
                    "content": "",
                    "segments": [],
                    "source_type": "subtitle",
                    "content_type": "字幕",
                    "error": _structure_error("INVALID_BVID", "无法解析 BV 号"),
                }

            info = BilibiliExtractor.get_video_info(bvid) or {}
            content = ""
            content_type = "弹幕"
            source_type = "danmaku"
            language = ""
            warnings: List[str] = []

            if use_sub:
                subtitle_payload = _normalize_source_payload(
                    BilibiliExtractor.get_subtitles(
                        info.get("bvid", bvid), info.get("cid", 0)
                    ),
                    "subtitle",
                )
                if subtitle_payload["content"]:
                    content = subtitle_payload["content"]
                    content_type = "字幕"
                    source_type = subtitle_payload["source_type"] or "subtitle"
                    language = subtitle_payload["language"]
                    warnings.extend(subtitle_payload["warnings"])

            if not content:
                danmaku = BilibiliExtractor.get_danmaku(info.get("cid", 0))
                if clean:
                    danmaku, stats = DanmakuCleaner.clean(danmaku)
                    warnings.append(
                        f"弹幕清洗: {stats.get('kept', 0)}/{stats.get('total', 0)}"
                    )
                content = " ".join(
                    _normalize_text(item.get("text"))
                    for item in danmaku[:500]
                    if _normalize_text(item.get("text"))
                )

            return {
                "platform": platform,
                "id": info.get("bvid", bvid),
                "url": url,
                "title": info.get("title", ""),
                "owner": info.get("owner", ""),
                "desc": info.get("desc", ""),
                "views": info.get("stat", {}).get("view", 0),
                "likes": info.get("stat", {}).get("like", 0),
                "content": content,
                "segments": [],
                "language": language,
                "warnings": warnings,
                "source_type": source_type,
                "content_type": content_type if content else "弹幕",
            }

        info = GenericExtractor.get_info(url, platform)
        return {
            "platform": platform,
            "id": url,
            "url": url,
            "title": info.get("title", ""),
            "owner": "",
            "desc": "",
            "views": 0,
            "likes": 0,
            "content": "",
            "segments": [],
            "language": "",
            "warnings": [],
            "source_type": "description",
            "content_type": "描述",
        }

    def _build_prompt(
        self,
        info: Mapping[str, Any],
        format_name: str,
        prompt: Optional[str],
        max_len: int,
    ) -> str:
        content = _trim_content(info.get("content", ""))
        template = prompt or self.prompts.get(format_name, self.prompts["brief"])
        return render_prompt(
            template=template,
            title=info.get("title", ""),
            author=info.get("owner", ""),
            desc=info.get("desc", ""),
            views=info.get("views", 0),
            likes=info.get("likes", 0),
            content=content,
            max_length=max_len,
        )

    def _build_llm_request(self, prompt_text: str) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any]

        if "anthropic.com" in self.api_url or self.api_url.rstrip("/").endswith("/v1/messages"):
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
            payload = {
                "model": self.model,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt_text}],
            }
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt_text}],
                "max_tokens": DEFAULT_MAX_TOKENS,
                "temperature": DEFAULT_TEMPERATURE,
            }

        return {"headers": headers, "payload": payload}

    def _parse_llm_response(self, response: requests.Response) -> str:
        data = response.json()

        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                first_choice = choices[0] or {}
                message = first_choice.get("message") or {}
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, list):
                        texts = [
                            item.get("text", "")
                            for item in content
                            if isinstance(item, dict)
                        ]
                        text = "\n".join(t for t in texts if t).strip()
                        if text:
                            return _strip_reasoning_content(text)
                    text = _normalize_text(content)
                    if text:
                        return _strip_reasoning_content(text)
                text = _normalize_text(first_choice.get("text"))
                if text:
                    return _strip_reasoning_content(text)

            output_text = _normalize_text(data.get("output_text"))
            if output_text:
                return _strip_reasoning_content(output_text)

            content = data.get("content")
            if isinstance(content, list):
                texts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                ]
                text = "\n".join(t for t in texts if t).strip()
                if text:
                    return _strip_reasoning_content(text)

            text = _normalize_text(data.get("message"))
            if text:
                return _strip_reasoning_content(text)

        return _strip_reasoning_content(response.text)

    def _call_llm(self, prompt_text: str) -> Dict[str, Any]:
        """调用 LLM API，并返回结构化结果。"""
        if not self.api_key:
            message = "未配置 API Key，请在 config.json 或环境变量中设置 api_key"
            return {"ok": False, "summary": message, "error": _structure_error("MISSING_API_KEY", message)}

        request_spec = self._build_llm_request(prompt_text)
        try:
            response = requests.post(
                self.api_url,
                headers=request_spec["headers"],
                json=request_spec["payload"],
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return {"ok": True, "summary": self._parse_llm_response(response), "error": None}
        except Exception as exc:
            logger.error(f"LLM 调用失败: {exc}")
            message = f"API 错误: {exc}"
            return {"ok": False, "summary": message, "error": _structure_error("LLM_REQUEST_FAILED", message)}

    def _build_result(
        self,
        info: Mapping[str, Any],
        summary: str,
        format_name: str,
        error: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        video_info = {
            "id": info.get("id"),
            "url": info.get("url"),
            "title": info.get("title", ""),
            "owner": info.get("owner", ""),
            "content_type": info.get("content_type", "未知"),
            "source_type": info.get("source_type", "unknown"),
            "language": info.get("language", ""),
            "content_length": len(_normalize_text(info.get("content", ""))),
        }

        result = {
            "platform": info.get("platform", "unknown"),
            "video_info": video_info,
            "summary": summary,
            "format": format_name,
            "timestamp": _now_iso(),
        }
        if error:
            result["error"] = dict(error)
        return result

    def _empty_content_result(
        self,
        info: Mapping[str, Any],
        format_name: str,
        reason: str,
    ) -> Dict[str, Any]:
        message = reason or "未提取到可用于总结的内容"
        error = _structure_error(
            "EMPTY_CONTENT",
            message,
            platform=info.get("platform", "unknown"),
            source_type=info.get("source_type", ""),
        )
        return self._build_result(info, message, format_name, error=error)

    def process(
        self,
        url: str,
        format: str = "brief",
        prompt: str = None,
        max_len: int = 500,
        clean: bool = True,
        use_sub: bool = True,
    ) -> Dict[str, Any]:
        """
        提取视频内容并调用 LLM 生成总结。
        """
        with Timer(f"提取 {url[:40]}"):
            info = self._extract(url, use_sub, clean)

        error = info.get("error")
        content = _normalize_text(info.get("content", ""))
        if error and not content:
            logger.warning(_extract_error_message(error) or "内容提取失败")
            return self._empty_content_result(
                info,
                format,
                _extract_error_message(error) or "内容提取失败",
            )

        if not content:
            logger.warning("未提取到可用于总结的内容")
            return self._empty_content_result(info, format, "未提取到可用于总结的内容")

        prompt_text = self._build_prompt(info, format, prompt, max_len)

        with Timer("LLM 分析"):
            llm_result = self._call_llm(prompt_text)

        summary = llm_result["summary"]
        if not llm_result["ok"]:
            return self._build_result(info, summary, format, error=llm_result["error"])

        logger.success("处理完成")
        return self._build_result(info, summary, format)


def summarize(
    url: str,
    format: str = "brief",
    prompt: str = None,
    max_length: int = 500,
    api_key: str = None,
    api_url: str = None,
    model: str = None,
    use_subtitle: bool = True,
    clean_danmaku: bool = True,
) -> Dict[str, Any]:
    """
    一行调用总结视频。
    """
    config = {
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
    }
    summarizer = VideoSummarizer(config)
    return summarizer.process(
        url=url,
        format=format,
        prompt=prompt,
        max_len=max_length,
        clean=clean_danmaku,
        use_sub=use_subtitle,
    )


def detect(url: str) -> str:
    """检测 URL 所属平台。"""
    return detect_platform(url)


def clean_danmaku_text(text: str) -> str:
    """清洗单条弹幕文本。"""
    cleaned, _ = DanmakuCleaner.clean([{"text": text}])
    return " ".join(item["text"] for item in cleaned)


def get_tool_definition() -> Dict[str, Any]:
    return {
        "name": "summarize_video",
        "description": "Summarize video content from any platform (YouTube, Bilibili, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Video URL (required)"},
                "format": {
                    "type": "string",
                    "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"],
                },
                "prompt": {"type": "string", "description": "Custom prompt"},
                "max_length": {"type": "integer"},
                "api_key": {"type": "string"},
                "api_url": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["url"],
        },
    }


def get_all_tools() -> List[Dict[str, Any]]:
    return [
        get_tool_definition(),
        {
            "name": "detect_platform",
            "description": "Detect the platform of a given URL",
            "inputSchema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
        {
            "name": "list_platforms",
            "description": "List all supported platforms",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


__all__ = [
    "VideoSummarizer",
    "summarize",
    "detect",
    "clean_danmaku_text",
    "get_tool_definition",
    "get_all_tools",
    "DEFAULT_PROMPTS",
    "detect_platform",
    "list_platforms",
]
