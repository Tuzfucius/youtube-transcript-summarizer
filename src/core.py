#!/usr/bin/env python3
"""
核心总结器
VideoSummarizer 类及 summarize()、detect() 便捷函数
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests

from .extractors import (
    BilibiliExtractor,
    DanmakuCleaner,
    GenericExtractor,
    YouTubeExtractor,
    detect_platform,
    list_platforms,
)
from .prompts import DEFAULT_PROMPTS
from .utils import Timer, handle_errors, logger


# ============== 主总结器 ==============
class VideoSummarizer:
    """多平台视频内容总结器"""

    def __init__(self, config: Dict = None):
        cfg = config or {}
        self.api_key = (
            cfg.get("api_key")
            or os.getenv("MINIMAX_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.api_url = (
            cfg.get("api_url")
            or os.getenv("VIDEO_SUMMARIZER_API_URL")
            or "https://api.minimaxi.com/v1/chat/completions"
        )
        self.model = (
            cfg.get("model")
            or os.getenv("VIDEO_SUMMARIZER_MODEL")
            or "MiniMax-M2.1"
        )
        self.prompts = DEFAULT_PROMPTS.copy()

    # ------------------------------------------------------------------
    # 内容提取
    # ------------------------------------------------------------------
    def _extract(self, url: str, use_sub: bool, clean: bool) -> Dict:
        """根据平台分发到对应提取器，返回统一格式的 info dict"""
        platform = detect_platform(url)
        logger.info(f"提取 {platform} 视频: {url[:60]}...")

        if platform == "youtube":
            vid = YouTubeExtractor.extract_video_id(url)
            if not vid:
                return {"platform": platform, "error": "无法解析视频 ID", "content": ""}
            tr = YouTubeExtractor.get_transcript(vid)
            content = tr["text"] if tr else ""
            return {
                "platform":     platform,
                "id":           vid,
                "url":          url,
                "title":        "",
                "owner":        "",
                "desc":         "",
                "views":        0,
                "likes":        0,
                "content":      content,
                "content_type": "字幕",
            }

        elif platform == "bilibili":
            bvid = BilibiliExtractor.extract_bvid(url)
            if not bvid:
                return {"platform": platform, "error": "无法解析 BV 号", "content": ""}

            info = BilibiliExtractor.get_video_info(bvid) or {}
            content = ""

            if use_sub:
                sub = BilibiliExtractor.get_subtitles(
                    info.get("bvid", bvid), info.get("cid", 0)
                )
                if sub.get("has_subtitle"):
                    content = sub.get("text", "")

            if not content:
                danmaku = BilibiliExtractor.get_danmaku(info.get("cid", 0))
                if clean:
                    danmaku, _ = DanmakuCleaner.clean(danmaku)
                content = " ".join(d["text"] for d in danmaku[:500])

            return {
                "platform":     platform,
                "id":           info.get("bvid", bvid),
                "url":          url,
                "title":        info.get("title", ""),
                "owner":        info.get("owner", ""),
                "desc":         info.get("desc", ""),
                "views":        info.get("stat", {}).get("view", 0),
                "likes":        info.get("stat", {}).get("like", 0),
                "content":      content,
                "content_type": "字幕" if use_sub and content else "弹幕",
            }

        else:
            info = GenericExtractor.get_info(url, platform)
            return {
                "platform":     platform,
                "id":           url,
                "url":          url,
                "title":        info.get("title", ""),
                "owner":        "",
                "desc":         "",
                "views":        0,
                "likes":        0,
                "content":      "",
                "content_type": "描述",
            }

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------
    def _call_llm(self, prompt: str) -> str:
        """向 LLM API 发起请求，返回回复文本"""
        if not self.api_key:
            return "⚠️ 未配置 API Key，请在 config.json 中设置 api_key"

        try:
            r = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.5,
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"❌ API 错误: {e}"

    # ------------------------------------------------------------------
    # 主处理入口
    # ------------------------------------------------------------------
    @handle_errors(default_return={"error": "处理失败"})
    def process(
        self,
        url: str,
        format: str = "brief",
        prompt: str = None,
        max_len: int = 500,
        clean: bool = True,
        use_sub: bool = True,
    ) -> Dict:
        """
        提取视频内容并调用 LLM 生成总结。

        Args:
            url:     视频链接
            format:  prompt 模板名称（brief/detailed/timestamp/sentiment/trend）
            prompt:  自定义 prompt（优先级高于 format）
            max_len: 总结最大字数（注入 prompt 模板）
            clean:   是否清洗弹幕
            use_sub: 是否优先使用字幕（Bilibili）

        Returns:
            结构化结果 dict
        """
        with Timer(f"提取 {url[:40]}"):
            info = self._extract(url, use_sub, clean)
            if "error" in info and not info.get("content"):
                return {**info, "summary": info.get("error", "")}

        content_truncated = info.get("content", "")[:3000]
        # 防止 prompt 模板被 content 中的 {} 破坏
        safe_content = content_truncated.replace("{", "{{").replace("}", "}}")

        prompt_template = prompt or self.prompts.get(format, self.prompts["brief"])
        try:
            prompt_text = prompt_template.format(
                title=info.get("title", ""),
                author=info.get("owner", ""),
                desc=info.get("desc", ""),
                views=info.get("views", 0),
                likes=info.get("likes", 0),
                content=safe_content,
                max_length=max_len,
            )
        except KeyError:
            prompt_text = prompt_template  # 自定义 prompt 可能不含模板变量

        with Timer("LLM 分析"):
            summary = self._call_llm(prompt_text)

        logger.success("处理完成")
        return {
            "platform": info.get("platform", "unknown"),
            "video_info": {
                "id":           info.get("id"),
                "url":          url,
                "title":        info.get("title"),
                "owner":        info.get("owner"),
                "content_type": info.get("content_type"),
            },
            "summary":   summary,
            "format":    format,
            "timestamp": datetime.now().isoformat(),
        }


# ============== 便捷函数 ==============
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
) -> Dict:
    """
    一行代码总结视频。

    Args:
        url:          视频链接
        format:       输出格式（brief/detailed/timestamp/sentiment/trend）
        prompt:       自定义 prompt
        max_length:   总结最大字数
        api_key:      LLM API Key（优先于环境变量）
        api_url:      LLM API 地址
        model:        LLM 模型名
        use_subtitle: 是否优先使用字幕（Bilibili）
        clean_danmaku: 是否清洗弹幕

    Returns:
        {'platform', 'video_info', 'summary', 'format', 'timestamp'}
    """
    s = VideoSummarizer({"api_key": api_key, "api_url": api_url, "model": model})
    return s.process(url, format, prompt, max_length, clean_danmaku, use_subtitle)


def detect(url: str) -> str:
    """检测 URL 所属平台"""
    return detect_platform(url)


def clean_danmaku_text(text: str) -> str:
    """清洗单条弹幕文本"""
    dm = [{"text": text}]
    cleaned, _ = DanmakuCleaner.clean(dm)
    return " ".join(d["text"] for d in cleaned)


# ============== LLM 工具定义（供 MCP/Claude Code 使用） ==============
def get_tool_definition() -> Dict:
    return {
        "name": "summarize_video",
        "description": "Summarize video content from any platform (YouTube, Bilibili, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url":        {"type": "string", "description": "Video URL (required)"},
                "format":     {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                "prompt":     {"type": "string", "description": "Custom prompt"},
                "max_length": {"type": "integer"},
                "api_key":    {"type": "string"},
                "api_url":    {"type": "string"},
                "model":      {"type": "string"},
            },
            "required": ["url"],
        },
    }


def get_all_tools() -> List[Dict]:
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
    "summarize", "detect", "clean_danmaku_text",
    "get_tool_definition", "get_all_tools",
    "DEFAULT_PROMPTS",
    "detect_platform", "list_platforms",
]
