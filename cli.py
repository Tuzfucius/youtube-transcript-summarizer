#!/usr/bin/env python3
"""
Video Summarizer CLI - 增强版命令行工具
支持异步、批量、对比、历史记录
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent
sys.path.insert(0, str(SKILL_DIR))

from video_summarizer import summarize, detect_platform, DEFAULT_PROMPTS
from advanced import (
    AsyncSummarizer, summarize_batch_sync, LLMFactories,
    HistoryStore, VideoComparator, quick_summarize
)


def load_config(config_file: str = None) -> dict:
    """加载配置"""
    paths = [config_file, "config.json", str(SKILL_DIR / "config.json")]
    for p in paths:
        if p and os.path.exists(p):
            with open(p, 'r') as f:
                return json.load(f)
    return {}


def cmd_summarize(args):
    """命令: summarize / url"""
    config = load_config(args.config)
    
    api_key = args.api_key or config.get('api_key')
    api_url = args.api_url or config.get('api_url')
    model = args.model or config.get('model', 'MiniMax-M2.1')
    
    urls = []
    if args.url:
        urls = [args.url]
    elif args.file:
        with open(args.file, 'r') as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    
    if not urls:
        print("❌ 请提供 URL 或文件")
        return
    
    # 异步或同步
    if args.async_mode and len(urls) > 1:
        print(f"🚀 异步处理 {len(urls)} 个视频...\n")
        
        async def run():
            async_s = AsyncSummarizer(
                max_concurrent=args.concurrent,
                api_key=api_key, api_url=api_url, model=model
            )
            
            async def progress(url, result):
                print(f"✅ {url[:40]}... 完成")
            
            results = await async_s.summarize_batch(urls, args.format, progress)
            
            for r in results:
                if not args.quiet:
                    print_result(r, args)
        
        asyncio.run(run())
    else:
        print(f"📹 处理 {len(urls)} 个视频...\n")
        
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url[:50]}...")
            try:
                result = summarize(
                    url=url, format=args.format,
                    api_key=api_key, api_url=api_url, model=model,
                    use_subtitle=not args.no_subtitle,
                    clean_danmaku_flag=not args.no_clean
                )
                
                if not args.quiet:
                    print_result(result, args)
                
                # 保存到历史
                if args.save_history:
                    store = HistoryStore()
                    info = result.get('video_info', {})
                    store.add(
                        url=url,
                        title=info.get('title', ''),
                        platform=result.get('platform', ''),
                        summary=result.get('summary', ''),
                        format=args.format,
                        tags=args.tags
                    )
                
                print(f"  ✅ 完成\n")
            except Exception as e:
                print(f"  ❌ 错误: {e}\n")


def cmd_compare(args):
    """命令: compare - 视频对比"""
    print(f"🔍 对比 {len(args.urls)} 个视频\n")
    
    comparator = VideoComparator()
    report = comparator.compare(args.urls, args.format)
    
    # 打印报告
    print("=" * 60)
    print("视频对比报告")
    print("=" * 60)
    
    for i, v in enumerate(report['videos'], 1):
        print(f"\n[{i}] {v['title']}")
        print(f"    平台: {v['platform']}")
        print(f"    预览: {v['summary_preview']}...")
    
    print("\n" + "=" * 60)
    print("平台分布:")
    for p, c in report['comparison']['platforms'].items():
        print(f"  - {p}: {c}")
    
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📁 已保存到: {output_file}")


def cmd_history(args):
    """命令: history - 历史记录"""
    store = HistoryStore()
    
    if args.clear:
        confirm = input("确认清除所有历史? (y/n): ")
        if confirm.lower() == 'y':
            store.clear()
            print("✅ 历史已清除")
        return
    
    if args.search:
        results = store.search(args.search)
        print(f"🔍 搜索 '{args.search}': {len(results)} 条结果\n")
    else:
        results = store.get_all(limit=args.limit)
        print(f"📚 历史记录: {len(results)} 条\n")
    
    for r in results:
        print(f"- [{r['platform']}] {r['title'][:40]}")
        print(f"  {r['created_at']}")
        print(f"  {r['summary'][:100]}...")
        print()


def cmd_stats(args):
    """命令: stats - 统计信息"""
    store = HistoryStore()
    stats = store.get_stats()
    
    print("📊 统计信息")
    print("=" * 40)
    print(f"总记录数: {stats['total']}")
    print("\n平台分布:")
    for p, c in stats['by_platform'].items():
        print(f"  - {p}: {c}")


def cmd_providers(args):
    """命令: providers - LLM 提供商"""
    print("支持的 LLM 提供商:")
    for p in LLMFactories.list_providers():
        print(f"  - {p}")
    print("\n使用: --provider openai")


def print_result(result: dict, args):
    """打印结果"""
    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result.get('summary', result.get('error', '错误'))
        print(f"\n{'='*60}")
        print(f"平台: {result.get('platform', 'unknown')}")
        print(f"标题: {result.get('video_info', {}).get('title', 'N/A')}")
        print(f"{'='*60}")
        print(summary)


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s url "https://youtube.com/watch?v=xxx" -f brief
  %(prog)s url "URL" --provider openai
  %(prog)s batch urls.txt -o results.json
  %(prog)s compare "URL1" "URL2" "URL3"
  %(prog)s history
  %(prog)s history --search AI
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # === url 命令 ===
    p_url = subparsers.add_parser('url', help='总结视频')
    p_url.add_argument('url', nargs='?', help='视频 URL')
    p_url.add_argument('-f', '--format', choices=list(DEFAULT_PROMPTS.keys()), default='brief')
    p_url.add_argument('-o', '--output', help='输出文件')
    p_url.add_argument('--file', help='URL 文件')
    p_url.add_argument('--provider', choices=LLMFactories.list_providers(), help='LLM 提供商')
    p_url.add_argument('--api-key', dest='api_key')
    p_url.add_argument('--api-url', dest='api_url')
    p_url.add_argument('--model')
    p_url.add_argument('--no-subtitle', action='store_true')
    p_url.add_argument('--no-clean', action='store_true')
    p_url.add_argument('-q', '--quiet', action='store_true')
    p_url.add_argument('--save-history', action='store_true', help='保存到历史')
    p_url.add_argument('--tags', nargs='*', help='标签')
    p_url.add_argument('--async', dest='async_mode', action='store_true', help='异步模式')
    p_url.add_argument('-c', '--concurrent', type=int, default=3, help='并发数')
    
    # === batch 命令 ===
    p_batch = subparsers.add_parser('batch', help='批量处理')
    p_batch.add_argument('file', nargs='?', help='URL 文件')
    p_batch.add_argument('-f', '--format', default='brief')
    p_batch.add_argument('-o', '--output', help='输出文件')
    p_batch.add_argument('--provider')
    p_batch.add_argument('--async', dest='async_mode', action='store_true')
    p_batch.add_argument('-c', '--concurrent', type=int, default=3)
    
    # === compare 命令 ===
    p_cmp = subparsers.add_parser('compare', help='对比视频')
    p_cmp.add_argument('urls', nargs='+', help='多个视频 URL')
    p_cmp.add_argument('-f', '--format', default='brief')
    p_cmp.add_argument('-o', '--output', help='输出文件')
    
    # === history 命令 ===
    p_hist = subparsers.add_parser('history', help='历史记录')
    p_hist.add_argument('--search', help='搜索关键词')
    p_hist.add_argument('--limit', type=int, default=50)
    p_hist.add_argument('--clear', action='store_true', help='清除历史')
    
    # === stats 命令 ===
    subparsers.add_parser('stats', help='统计信息')
    
    # === providers 命令 ===
    subparsers.add_parser('providers', help='LLM 提供商')
    
    # === config 命令 ===
    p_config = subparsers.add_parser('config', help='配置管理')
    p_config.add_argument('--set', help='设置 (key=value)')
    p_config.add_argument('--get', help='获取')
    
    args = parser.parse_args()
    
    if args.command == 'url':
        cmd_summarize(args)
    elif args.command == 'batch':
        cmd_summarize(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'history':
        cmd_history(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'providers':
        cmd_providers(args)
    elif args.command == 'config':
        config = load_config()
        if args.set:
            k, v = args.set.split('=', 1)
            config[k] = v
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ {k} = {v}")
        elif args.get:
            print(f"{args.get} = {config.get(args.get, '未设置')}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
