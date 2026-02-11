#!/usr/bin/env python3
"""
Video Summarizer MCP Server
支持 Claude Code、OpenCode 等大模型框架接入

Usage:
    python mcp_server.py --port 8080
"""

import asyncio
import json
import argparse
from typing import Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from video_summarizer import VideoSummarizer, detect_platform


# ============== MCP Server ==============
class VideoSummarizerMCPServer:
    """Video Summarizer MCP Server"""
    
    def __init__(self):
        self.server = Server("video-summarizer")
        self.summarizer = None
        self.setup_handlers()
    
    def setup_handlers(self):
        """设置 MCP 处理器"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="summarize_video",
                    description="Summarize video content from any platform (YouTube, Bilibili, Twitter, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Video URL to summarize"
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
                                "description": "LLM API URL"
                            },
                            "model": {
                                "type": "string",
                                "description": "LLM model name"
                            },
                            "clean_danmaku": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to clean danmaku (BiliBili)"
                            },
                            "use_subtitle": {
                                "type": "boolean",
                                "default": True,
                                "description": "Prefer subtitle over danmaku (BiliBili)"
                            }
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="detect_platform",
                    description="Detect the platform of a URL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to detect"
                            }
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="list_platforms",
                    description="List all supported platforms",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_summary_formats",
                    description="List all available summary formats",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent]:
            try:
                if name == "summarize_video":
                    result = await self.summarize_video(arguments)
                    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                
                elif name == "detect_platform":
                    platform = detect_platform(arguments.get("url", ""))
                    return [TextContent(type="text", text=json.dumps({"platform": platform}, ensure_ascii=False))]
                
                elif name == "list_platforms":
                    platforms = list(VideoSummarizer.PLATFORMS.keys())
                    return [TextContent(type="text", text=json.dumps({"platforms": platforms, "count": len(platforms)}, ensure_ascii=False))]
                
                elif name == "get_summary_formats":
                    formats = ["brief", "detailed", "timestamp", "sentiment", "trend"]
                    return [TextContent(type="text", text=json.dumps({"formats": formats}, ensure_ascii=False))]
                
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def summarize_video(self, args: Dict) -> Dict:
        """执行视频总结"""
        # 初始化 summarizer
        config = {}
        if args.get("api_key"):
            config["api_key"] = args["api_key"]
        if args.get("api_url"):
            config["api_url"] = args["api_url"]
        if args.get("model"):
            config["model"] = args["model"]
        
        s = VideoSummarizer(config)
        
        # 执行总结
        result = s.process(
            url=args["url"],
            prompt_type=args.get("format", "brief"),
            custom_prompt=args.get("prompt"),
            max_length=args.get("max_length", 500),
            clean_danmaku=args.get("clean_danmaku", True),
            use_subtitle=args.get("use_subtitle", True)
        )
        
        return result
    
    async def run(self, port: int = None):
        """运行 MCP Server"""
        if port:
            # HTTP 模式
            from mcp.server.http import serve_http
            await serve_http(self.server, port=port)
        else:
            # Stdio 模式
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )


# ============== CLI Interface ==============
def create_cli():
    """创建 CLI 接口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer - MCP Server & CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # CLI 模式
  python mcp_server.py --url "https://youtube.com/watch?v=xxx" --format brief
  
  # MCP Stdio 模式
  python mcp_server.py --mcp-stdio
  
  # MCP HTTP 模式
  python mcp_server.py --mcp-http --port 8080
  
  # Claude Code 接入
  {"tool": "summarize_video", "arguments": {"url": "..."}}
        """
    )
    
    parser.add_argument("--url", "-u", help="Video URL to summarize")
    parser.add_argument("--format", "-f", choices=["brief", "detailed", "timestamp", "sentiment", "trend"], 
                       default="brief", help="Summary format")
    parser.add_argument("--prompt", "-p", help="Custom prompt")
    parser.add_argument("--max-length", "-m", type=int, default=500, help="Max length")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--api-url", help="API URL")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--no-clean", action="store_true", help="Don't clean danmaku")
    parser.add_argument("--no-subtitle", action="store_true", help="Don't use subtitle")
    
    # MCP 模式
    parser.add_argument("--mcp-stdio", action="store_true", help="Run as MCP Stdio Server")
    parser.add_argument("--mcp-http", action="store_true", help="Run as MCP HTTP Server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port for MCP Server")
    
    # 列表模式
    parser.add_argument("--list-platforms", action="store_true", help="List all platforms")
    parser.add_argument("--list-formats", action="store_true", help="List all formats")
    
    return parser


async def main():
    """主函数"""
    parser = create_cli()
    args = parser.parse_args()
    
    # 列表模式
    if args.list_platforms:
        platforms = list(VideoSummarizer.PLATFORMS.keys())
        print(f"Supported platforms ({len(platforms)}):")
        for p in platforms:
            print(f"  - {p}")
        return
    
    if args.list_formats:
        formats = ["brief", "detailed", "timestamp", "sentiment", "trend"]
        print(f"Available formats:")
        for f in formats:
            print(f"  - {f}")
        return
    
    # CLI 模式
    if args.url:
        config = {}
        if args.api_key:
            config["api_key"] = args.api_key
        if args.api_url:
            config["api_url"] = args.api_url
        if args.model:
            config["model"] = args.model
        
        s = VideoSummarizer(config)
        result = s.process(
            url=args.url,
            prompt_type=args.format,
            custom_prompt=args.prompt,
            max_length=args.max_length,
            clean_danmaku=not args.no_clean,
            use_subtitle=not args.no_subtitle
        )
        
        print("\n" + "="*50)
        print(result["summary"])
        print("="*50)
        return
    
    # MCP 模式
    server = VideoSummarizerMCPServer()
    
    if args.mcp_stdio:
        await server.run()
    elif args.mcp_http:
        await server.run(port=args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
