#!/usr/bin/env python3
"""
Video Summarizer - Claude Code Skill 配置
整合优秀开源项目设计的增强版
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# ============== Claude Code Skill Manifest ==============
SKILL_MANIFEST = {
    "name": "video-summarizer",
    "description": "Summarize video content from YouTube, Bilibili, Twitter, and 45+ platforms using AI",
    "version": "3.8.4",
    "author": "OpenClaw",
    "commands": [
        {
            "name": "summarize",
            "description": "Summarize a video URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Video URL to summarize"},
                    "format": {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                    "provider": {"type": "string", "description": "LLM provider: minimax, openai, deepseek, anthropic"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "batch",
            "description": "Process multiple videos",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "File containing URLs"},
                    "format": {"type": "string"}
                }
            }
        },
        {
            "name": "history",
            "description": "View summary history",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string"}
                }
            }
        }
    ],
    "triggers": [
        "summarize this video:",
        "download this video:",
        "总结这个视频：",
        "视频总结："
    ]
}


# ============== 自然语言处理 ==============
import re

NATURAL_LANGUAGE_PATTERNS = [
    # 英文模式
    (r'summarize\s+(?:this\s+)?video[:\s]+(.+)', 'summarize'),
    (r'download\s+(?:this\s+)?video[:\s]+(.+)', 'download'),
    (r"what'?s?\s+(?:in|about)\s+this\s+video[:\s]+(.+)", 'summarize'),
    (r'transcribe\s+(?:this\s+)?video[:\s]+(.+)', 'transcribe'),
    # 中文模式
    (r'总结这个视频[：:\s]+(.+)', 'summarize'),
    (r'总结视频[：:\s]+(.+)', 'summarize'),
    (r'下载这个视频[：:\s]+(.+)', 'download'),
    (r'下载视频[：:\s]+(.+)', 'download'),
    (r'这个视频(?:是|讲)[：:\s]+(.+)', 'summarize'),
]


def parse_natural_language(text: str) -> dict:
    """解析自然语言命令"""
    text = text.strip()
    
    for pattern, cmd in NATURAL_LANGUAGE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            url = match.group(1).strip()
            return {'command': cmd, 'url': url}
    
    return None


# ============== 依赖管理 ==============
DEPENDENCIES = {
    'required': [
        ('youtube-transcript-api', 'youtube_transcript_api'),
        ('requests', 'requests'),
    ],
    'optional': [
        ('faster-whisper', 'faster_whisper'),
        ('yt-dlp', 'yt_dlp'),
        ('ffmpeg', None),  # 系统命令
    ]
}


def check_dependencies(install: bool = False) -> dict:
    """检查依赖"""
    status = {'installed': [], 'missing': []}
    
    for pkg, import_name in DEPENDENCIES['required']:
        try:
            if import_name:
                __import__(import_name)
            status['installed'].append(pkg)
        except ImportError:
            status['missing'].append(pkg)
            if install:
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', pkg], check=True)
                    status['installed'].append(pkg)
                    status['missing'].remove(pkg)
                except:
                    pass
    
    for pkg, import_name in DEPENDENCIES['optional']:
        if import_name:
            try:
                __import__(import_name)
                status['installed'].append(pkg)
            except ImportError:
                status['missing'].append(pkg)
        else:
            # 系统命令
            try:
                subprocess.run(['which', pkg], check=True, stdout=subprocess.DEVNULL)
                status['installed'].append(pkg)
            except:
                status['missing'].append(pkg)
    
    return status


def install_dependencies():
    """自动安装依赖"""
    print("📦 正在安装依赖...")
    status = check_dependencies(install=True)
    
    for pkg in status['installed']:
        print(f"  ✅ {pkg}")
    
    for pkg in status['missing']:
        print(f"  ❌ {pkg} (安装失败)")
    
    return len(status['missing']) == 0


# ============== Token 统计 ==============
class CostTracker:
    """成本追踪器"""
    
    PRICING = {
        'MiniMax-M2.1': {'input': 0.001, 'output': 0.001},  # per 1K tokens
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'deepseek-chat': {'input': 0.00014, 'output': 0.00028},
        'claude-3-opus': {'input': 0.015, 'output': 0.075},
    }
    
    def __init__(self):
        self.history = []
    
    def track(self, model: str, prompt_tokens: int, completion_tokens: int):
        """记录使用情况"""
        price = self.PRICING.get(model, {'input': 0.001, 'output': 0.001})
        cost = (prompt_tokens * price['input'] + completion_tokens * price['output']) / 1000
        
        entry = {
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'cost': cost,
            'timestamp': str(datetime.now())
        }
        self.history.append(entry)
        return cost
    
    def get_summary(self) -> dict:
        """获取统计摘要"""
        total_cost = sum(e['cost'] for e in self.history)
        total_tokens = sum(e['prompt_tokens'] + e['completion_tokens'] for e in self.history)
        
        return {
            'total_requests': len(self.history),
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'by_model': {}
        }
    
    def export_json(self, filepath: str = "cost_report.json"):
        """导出报告"""
        report = {
            'summary': self.get_summary(),
            'history': self.history
        }
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        return filepath


# ============== Claude Code 集成 ==============
def claude_code_tool_definitions() -> list:
    """生成 Claude Code 工具定义"""
    return [
        {
            "name": "summarize_video",
            "description": "Summarize video content from any platform",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Video URL (YouTube, Bilibili, Twitter, etc.)"},
                    "format": {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                    "provider": {"type": "string", "description": "LLM provider (minimax, openai, deepseek, anthropic)"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "batch_summarize",
            "description": "Summarize multiple videos from a file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "description": "File containing URLs (one per line)"},
                    "format": {"type": "string"},
                    "async": {"type": "boolean", "description": "Enable async processing"}
                }
            }
        },
        {
            "name": "video_history",
            "description": "View and search summary history",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Search keyword"},
                    "limit": {"type": "integer"}
                }
            }
        }
    ]


# ============== 配置文件模板 ==============
DEFAULT_CONFIG = {
    # API 配置
    "api_key": "",
    "api_url": "https://api.minimaxi.com/v1/chat/completions",
    "model": "MiniMax-M2.1",
    
    # LLM 提供商
    "providers": {
        "minimax": {
            "api_url": "https://api.minimaxi.com/v1/chat/completions",
            "model": "MiniMax-M2.1"
        },
        "openai": {
            "api_url": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4"
        },
        "deepseek": {
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "model": "deepseek-chat"
        },
        "anthropic": {
            "api_url": "https://api.anthropic.com/v1/chat/completions",
            "model": "claude-3-opus-20240229"
        }
    },
    
    # 功能开关
    "use_subtitle": True,
    "clean_danmaku": True,
    "enable_cache": True,
    "enable_history": True,
    "track_cost": False,
    
    # 输出设置
    "output_dir": "./outputs",
    "save_video": False,
    "save_audio": False,
    "save_subtitle": False,
    
    # Whisper 设置（可选）
    "whisper_model": "small",
    "whisper_language": "auto",
    
    # 并发设置
    "concurrency": 3,
    
    # 其他
    "timeout": 60,
    "retry_times": 3
}


def create_default_config(filepath: str = "config.json"):
    """创建默认配置"""
    with open(filepath, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    return filepath


# ============== 便捷函数 ==============
def quick_summarize(url: str, **kwargs) -> dict:
    """快速总结（自然语言友好）"""
    from video_summarizer import summarize
    
    return summarize(url, **kwargs)


def natural_command(text: str) -> dict:
    """处理自然语言命令"""
    parsed = parse_natural_language(text)
    if parsed:
        if parsed['command'] == 'summarize':
            return quick_summarize(parsed['url'])
        elif parsed['command'] == 'download':
            return {'status': '需要 yt-dlp', 'url': parsed['url']}
    return None


# ============== 导出 ==============
__all__ = [
    'SKILL_MANIFEST', 'NATURAL_LANGUAGE_PATTERNS', 'parse_natural_language',
    'DEPENDENCIES', 'check_dependencies', 'install_dependencies',
    'CostTracker', 'claude_code_tool_definitions',
    'DEFAULT_CONFIG', 'create_default_config',
    'quick_summarize', 'natural_command'
]


# ============== CLI 入口 ==============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="🎬 Video Summarizer - Enhanced")
    parser.add_argument('command', choices=['summarize', 'batch', 'history', 'cost', 'install', 'config'])
    parser.add_argument('args', nargs='*', help='Command arguments')
    
    args = parser.parse_args()
    
    if args.command == 'install':
        install_dependencies()
    
    elif args.command == 'config':
        if '--default' in args.args:
            create_default_config()
            print("✅ 默认配置已创建: config.json")
        else:
            print(json.dumps(DEFAULT_CONFIG, indent=2))
    
    elif args.command == 'cost':
        tracker = CostTracker()
        summary = tracker.get_summary()
        print(f"总请求: {summary['total_requests']}")
        print(f"总 Token: {summary['total_tokens']}")
        print(f"总成本: ${summary['total_cost']:.4f}")
