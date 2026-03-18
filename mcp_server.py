#!/usr/bin/env python3
"""
Video Summarizer MCP Server
支持 Claude Code、OpenCode 等大模型框架接入

用法:
    python mcp_server.py --mcp-stdio       # Stdio 模式（Claude Code 推荐）
    python mcp_server.py --mcp-http --port 8080  # HTTP 模式
    python mcp_server.py --url "URL"       # 直接 CLI 调用
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.core import VideoSummarizer, detect_platform, list_platforms, DEFAULT_PROMPTS


class VideoSummarizerMCPServer:
    """Video Summarizer MCP Server"""

    def __init__(self):
        self.server = Server("video-summarizer")
        self.setup_handlers()

    def setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="summarize_video",
                    description="Summarize video content from any platform (YouTube, Bilibili, Twitter, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url":           {"type": "string",  "description": "Video URL to summarize"},
                            "format":        {"type": "string",  "enum": list(DEFAULT_PROMPTS.keys()), "default": "brief"},
                            "prompt":        {"type": "string",  "description": "Custom prompt for analysis"},
                            "max_length":    {"type": "integer", "default": 500},
                            "api_key":       {"type": "string",  "description": "LLM API Key"},
                            "api_url":       {"type": "string",  "description": "LLM API URL"},
                            "model":         {"type": "string",  "description": "LLM model name"},
                            "clean_danmaku": {"type": "boolean", "default": True},
                            "use_subtitle":  {"type": "boolean", "default": True},
                        },
                        "required": ["url"],
                    },
                ),
                Tool(
                    name="detect_platform",
                    description="Detect the platform of a URL",
                    inputSchema={
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                ),
                Tool(
                    name="list_platforms",
                    description="List all supported platforms",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="get_summary_formats",
                    description="List all available summary formats",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            try:
                if name == "summarize_video":
                    result = await self._summarize_video(arguments)
                    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

                elif name == "detect_platform":
                    platform = detect_platform(arguments.get("url", ""))
                    return [TextContent(type="text", text=json.dumps({"platform": platform}, ensure_ascii=False))]

                elif name == "list_platforms":
                    platforms = list_platforms()
                    return [TextContent(type="text", text=json.dumps({"platforms": platforms, "count": len(platforms)}, ensure_ascii=False))]

                elif name == "get_summary_formats":
                    return [TextContent(type="text", text=json.dumps({"formats": list(DEFAULT_PROMPTS.keys())}, ensure_ascii=False))]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

    async def _summarize_video(self, args: Dict) -> Dict:
        """执行视频总结"""
        config = {
            k: args[k]
            for k in ("api_key", "api_url", "model")
            if args.get(k)
        }
        s = VideoSummarizer(config)
        # Bug 修复：参数名与 process() 签名一致
        result = s.process(
            url=args["url"],
            format=args.get("format", "brief"),        # 修复：原来错误写成 prompt_type=
            prompt=args.get("prompt"),                  # 修复：原来错误写成 custom_prompt=
            max_len=args.get("max_length", 500),
            clean=args.get("clean_danmaku", True),
            use_sub=args.get("use_subtitle", True),
        )
        return result

    async def run(self, port: int = None):
        if port:
            from mcp.server.http import serve_http
            await serve_http(self.server, port=port)
        else:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream,
                    self.server.create_initialization_options(),
                )


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer - MCP Server & CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python mcp_server.py --mcp-stdio
  python mcp_server.py --mcp-http --port 8080
  python mcp_server.py --url "https://youtube.com/watch?v=xxx" --format brief
        """,
    )
    parser.add_argument("--url", "-u", help="视频 URL（CLI 模式）")
    parser.add_argument("--format", "-f", choices=list(DEFAULT_PROMPTS.keys()), default="brief")
    parser.add_argument("--prompt",  "-p")
    parser.add_argument("--max-length", "-m", type=int, default=500)
    parser.add_argument("--api-key",  help="API Key")
    parser.add_argument("--api-url",  help="API URL")
    parser.add_argument("--model",    help="模型名称")
    parser.add_argument("--no-clean",    action="store_true")
    parser.add_argument("--no-subtitle", action="store_true")
    parser.add_argument("--mcp-stdio",   action="store_true", help="以 MCP Stdio 模式运行")
    parser.add_argument("--mcp-http",    action="store_true", help="以 MCP HTTP 模式运行")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--list-platforms", action="store_true")
    parser.add_argument("--list-formats",   action="store_true")

    args = parser.parse_args()

    if args.list_platforms:
        platforms = list_platforms()
        print(f"支持的平台 ({len(platforms)}):")
        for p in platforms:
            print(f"  - {p}")
        return

    if args.list_formats:
        print("可用的分析格式:")
        for f in DEFAULT_PROMPTS.keys():
            print(f"  - {f}")
        return

    if args.url:
        config = {k: getattr(args, k) for k in ("api_key", "api_url", "model") if getattr(args, k, None)}
        s = VideoSummarizer(config)
        result = s.process(
            url=args.url,
            format=args.format,
            prompt=args.prompt,
            max_len=args.max_length,
            clean=not args.no_clean,
            use_sub=not args.no_subtitle,
        )
        print("\n" + "=" * 50)
        print(result.get("summary") or result.get("error", ""))
        print("=" * 50)
        return

    server = VideoSummarizerMCPServer()
    if args.mcp_stdio:
        await server.run()
    elif args.mcp_http:
        await server.run(port=args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
