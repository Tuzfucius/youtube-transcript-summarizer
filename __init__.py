#!/usr/bin/env python3
"""
Video Summarizer - 支持 Claude Code、OpenCode 等大模型框架

Quick Start:
    from video_summarizer import summarize
    
    result = summarize("https://youtube.com/watch?v=xxx", format="brief")
    print(result["summary"])
"""

import os
import sys
from typing import Dict, Optional

# 导入核心类
from video_summarizer import (
    VideoSummarizer,
    detect_platform,
    YouTubeExtractor,
    BilibiliExtractor,
    DanmakuCleaner
)


# ============== 便捷函数 ==============
def summarize(url: str, 
              format: str = "brief",
              prompt: str = None,
              max_length: int = 500,
              api_key: str = None,
              api_url: str = None,
              model: str = None,
              clean_danmaku: bool = True,
              use_subtitle: bool = True) -> Dict:
    """
    快速总结视频内容
    
    Args:
        url: 视频链接
        format: 总结格式 (brief/detailed/timestamp/sentiment/trend)
        prompt: 自定义 prompt
        max_length: 最大长度
        api_key: API Key
        api_url: API URL
        model: 模型名称
        clean_danmaku: 是否清洗弹幕
        use_subtitle: 是否优先使用字幕
        
    Returns:
        {
            "platform": str,
            "video_info": {...},
            "summary": str,
            "format": str,
            "timestamp": str
        }
    """
    config = {}
    if api_key:
        config["api_key"] = api_key
    if api_url:
        config["api_url"] = api_url
    if model:
        config["model"] = model
    
    s = VideoSummarizer(config)
    return s.process(
        url=url,
        prompt_type=format,
        custom_prompt=prompt,
        max_length=max_length,
        clean_danmaku=clean_danmaku,
        use_subtitle=use_subtitle
    )


def extract(url: str,
            clean_danmaku: bool = True,
            use_subtitle: bool = True) -> Dict:
    """
    提取视频内容（不总结）
    
    Returns:
        {
            "platform": str,
            "info": {...},
            "content": str,
            "content_type": str,
            "language": str
        }
    """
    s = VideoSummarizer()
    return s.extract_content(
        url=url,
        clean_danmaku=clean_danmaku,
        use_subtitle=use_subtitle
    )


def clean_danmaku_text(text: str) -> str:
    """清洗弹幕文本"""
    from video_summarizer import DanmakuCleaner
    
    danmaku = [{"text": text}]
    cleaned, _ = DanmakuCleaner.clean(danmaku)
    return " ".join([d["text"] for d in cleaned])


def detect(url: str) -> str:
    """检测视频平台"""
    return detect_platform(url)


# ============== Claude Code / OpenCode 工具格式 ==============
def get_tool_definition() -> Dict:
    """
    获取 Claude Code / OpenCode 工具定义
    
    Usage:
        tools = [get_tool_definition()]
        for tool in tools:
            # 注册工具
    """
    return {
        "name": "summarize_video",
        "description": "Summarize video content from any platform (YouTube, Bilibili, Douyin, Twitter, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Video URL to summarize (required)"
                },
                "format": {
                    "type": "string",
                    "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"],
                    "default": "brief",
                    "description": "Summary format"
                },
                "prompt": {
                    "type": "string",
                    "description": "Custom prompt for analysis"
                },
                "max_length": {
                    "type": "integer",
                    "default": 500,
                    "description": "Maximum summary length"
                },
                "api_key": {
                    "type": "string",
                    "description": "API key for LLM service"
                },
                "api_url": {
                    "type": "string",
                    "description": "LLM API URL (default: MiniMax)"
                },
                "model": {
                    "type": "string",
                    "description": "LLM model name (default: MiniMax-M2.1)"
                }
            },
            "required": ["url"]
        }
    }


def get_all_tools() -> list:
    """获取所有工具定义"""
    return [
        {
            "name": "summarize_video",
            "description": "Summarize video content from any platform",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Video URL"},
                    "format": {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                    "prompt": {"type": "string", "description": "Custom prompt"},
                    "max_length": {"type": "integer"},
                    "api_key": {"type": "string"},
                    "api_url": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "extract_video",
            "description": "Extract content from video without summarization",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Video URL"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "detect_platform",
            "description": "Detect platform of a URL",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to detect"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "list_platforms",
            "description": "List all supported platforms",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]


# ============== 导出 ==============
__all__ = [
    "summarize",
    "extract",
    "clean_danmaku_text",
    "detect",
    "VideoSummarizer",
    "detect_platform",
    "YouTubeExtractor",
    "BilibiliExtractor",
    "DanmakuCleaner",
    "get_tool_definition",
    "get_all_tools"
]

__version__ = "3.8.0"
