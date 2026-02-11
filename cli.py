#!/usr/bin/env python3
"""
Video Summarizer CLI - 命令行工具
支持单视频、批量处理、多种输出格式
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加 skill 路径
SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from video_summarizer import summarize, detect_platform, setup_logger, DEFAULT_PROMPTS


def load_config(config_file: str = None) -> dict:
    """加载配置"""
    config_paths = [
        config_file,
        "config.json",
        str(SKILL_DIR / "config.json"),
        os.path.expanduser("~/.video_summarizer.json")
    ]
    
    for path in config_paths:
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return {}


def save_config(config: dict, config_file: str):
    """保存配置"""
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def process_single(url: str, args) -> dict:
    """处理单个视频"""
    return summarize(
        url=url,
        format=args.format,
        api_key=args.api_key,
        api_url=args.api_url,
        model=args.model,
        use_subtitle=not args.no_subtitle,
        clean_danmaku_flag=not args.no_clean
    )


def output_result(result: dict, args):
    """输出结果"""
    # 控制台输出
    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result.get('summary', result.get('error', '错误'))
        print(f"\n{'='*60}")
        print(f"平台: {result.get('platform', 'unknown')}")
        print(f"视频: {result.get('video_info', {}).get('title', 'N/A')}")
        print(f"{'='*60}")
        print(summary)
    
    # 文件输出
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if args.output.endswith('.json'):
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            summary = result.get('summary', result.get('error', '错误'))
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# 视频总结\n\n")
                f.write(f"- 平台: {result.get('platform', 'unknown')}\n")
                f.write(f"- 视频: {result.get('video_info', {}).get('title', 'N/A')}\n")
                f.write(f"- 时间: {result.get('timestamp', '')}\n")
                f.write(f"- 格式: {result.get('format', 'brief')}\n\n")
                f.write(f"{'='*60}\n\n")
                f.write(summary)
        
        print(f"\n📁 已保存到: {output_file}")


def cmd_summarize(args):
    """命令: summarize"""
    config = load_config(args.config)
    
    # 合并配置
    api_key = args.api_key or config.get('api_key') or os.getenv('MINIMAX_API_KEY')
    api_url = args.api_url or config.get('api_url')
    model = args.model or config.get('model', 'MiniMax-M2.1')
    
    # 解析 URL 列表
    urls = []
    if args.url:
        urls = [args.url]
    elif args.file:
        with open(args.file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    elif args批量:
        for f in Path('.').glob(args批量):
            if f.suffix in ['.txt', '.md', '.json']:
                with open(f, 'r') as file:
                    urls.extend([line.strip() for line in file if line.strip()])
    
    if not urls:
        print("❌ 请提供 URL (--url) 或文件 (--file)")
        return
    
    print(f"📹 将处理 {len(urls)} 个视频...\n")
    
    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] 处理: {url[:50]}...")
        try:
            result = summarize(
                url=url,
                format=args.format,
                api_key=api_key,
                api_url=api_url,
                model=model,
                use_subtitle=not args.no_subtitle,
                clean_danmaku_flag=not args.no_clean
            )
            results.append(result)
            
            # 输出结果
            if not args.quiet:
                output_result(result, args)
            
            print(f"  ✅ 完成\n")
        except Exception as e:
            print(f"  ❌ 错误: {e}\n")
            results.append({'url': url, 'error': str(e)})
    
    # 批量输出
    if len(urls) > 1 and args.output:
        batch_file = Path(args.output)
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"📁 批量结果已保存到: {batch_file}")


def cmd_config(args):
    """命令: config"""
    config = load_config(args.config)
    
    if args.set:
        key, value = args.set.split('=', 1)
        # 转换值为适当类型
        if value.isdigit():
            value = int(value)
        elif value in ['true', 'false']:
            value = value == 'true'
        config[key] = value
        save_config(config, args.config or "config.json")
        print(f"✅ 已设置: {key} = {value}")
    
    elif args.get:
        value = config.get(args.get, '未设置')
        print(f"{args.get} = {value}")
    
    else:
        print("当前配置:")
        print(json.dumps(config, indent=2, ensure_ascii=False))


def cmd_platforms(args):
    """命令: platforms"""
    print("支持的平台:")
    platforms = {
        'youtube': 'YouTube',
        'bilibili': 'Bilibili',
        'douyin': '抖音/TikTok',
        'kuaishou': '快手',
        'xigua': '西瓜视频',
        'twitter': 'Twitter/X',
        'instagram': 'Instagram',
        'xiaohongshu': '小红书',
        'zhihu': '知乎',
        'twitch': 'Twitch',
        'reddit': 'Reddit',
    }
    for k, v in platforms.items():
        print(f"  - {k}: {v}")


def cmd_cache(args):
    """命令: cache"""
    cache_file = SKILL_DIR / ".cache.json"
    
    if args.clear:
        if cache_file.exists():
            cache_file.unlink()
        print("✅ 缓存已清除")
    
    elif args.list:
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cache = json.load(f)
            print(f"缓存了 {len(cache)} 个视频:")
            for url, data in cache.items():
                print(f"  - {url[:50]}...")
        else:
            print("暂无缓存")


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer - 视频内容总结工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s url "https://youtube.com/watch?v=xxx" -f brief
  %(prog)s url "https://bilibili.com/video/BVxxx" -f detailed --output result.md
  %(prog)s batch -f urls.txt --output results.json
  %(prog)s config --set api_key=xxx
  %(prog)s platforms
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # === url 命令 ===
    p_url = subparsers.add_parser('url', help='总结单个视频')
    p_url.add_argument('url', nargs='?', help='视频 URL')
    p_url.add_argument('-f', '--format', choices=['brief', 'detailed', 'timestamp', 'sentiment', 'trend'], default='brief')
    p_url.add_argument('-o', '--output', help='输出文件')
    p_url.add_argument('--api-key', dest='api_key')
    p_url.add_argument('--api-url', dest='api_url')
    p_url.add_argument('--model')
    p_url.add_argument('--no-subtitle', action='store_true')
    p_url.add_argument('--no-clean', action='store_true')
    p_url.add_argument('-q', '--quiet', action='store_true')
    
    # === batch 命令 ===
    p_batch = subparsers.add_parser('batch', help='批量处理视频')
    p_batch.add_argument('file', nargs='?', help='URL 文件 (每行一个)')
    p_batch.add_argument('-f', '--format', choices=['brief', 'detailed', 'timestamp', 'sentiment', 'trend'], default='brief')
    p_batch.add_argument('-o', '--output', help='输出文件')
    p_batch.add_argument('--api-key', dest='api_key')
    p_batch.add_argument('--no-subtitle', action='store_true')
    p_batch.add_argument('--no-clean', action='store_true')
    p_batch.add_argument('-q', '--quiet', action='store_true')
    
    # === config 命令 ===
    p_config = subparsers.add_parser('config', help='管理配置')
    p_config.add_argument('--config', default='config.json')
    p_config.add_argument('--set', help='设置配置项 (key=value)')
    p_config.add_argument('--get', help='获取配置项')
    
    # === platforms 命令 ===
    subparsers.add_parser('platforms', help='列出支持平台')
    
    # === cache 命令 ===
    p_cache = subparsers.add_parser('cache', help='管理缓存')
    p_cache.add_argument('--clear', action='store_true', help='清除缓存')
    p_cache.add_argument('--list', action='store_true', help='列出缓存')
    
    args = parser.parse_args()
    
    if args.command == 'url':
        cmd_summarize(args)
    elif args.command == 'batch':
        cmd_summarize(args)
    elif args.command == 'config':
        cmd_config(args)
    elif args.command == 'platforms':
        cmd_platforms(args)
    elif args.command == 'cache':
        cmd_cache(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
