#!/usr/bin/env python3
"""
Video Summarizer CLI - 命令行工具
支持单视频、批量、对比、历史记录、LLM 提供商管理
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 确保根目录在 sys.path 中（支持直接运行）
sys.path.insert(0, str(Path(__file__).parent))

from src.core import summarize, detect_platform, DEFAULT_PROMPTS
from src.advanced import (
    AsyncSummarizer, summarize_batch_sync,
    LLMFactories, HistoryStore, VideoComparator, quick_summarize,
)


def load_config(config_file: str = None) -> dict:
    """加载配置文件（优先使用指定路径，否则查找 config.json）"""
    search_paths = [config_file, "config.json", str(Path(__file__).parent / "config.json")]
    for p in search_paths:
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def print_result(result: dict, args):
    """格式化打印单条结果"""
    summary = result.get("summary") or result.get("error", "❌ 未知错误")
    print(f"\n{'='*60}")
    print(f"平台: {result.get('platform', 'unknown')}")
    print(f"标题: {result.get('video_info', {}).get('title', 'N/A')}")
    print(f"{'='*60}")
    print(summary)
    if hasattr(args, "output") and args.output:
        _save_result(result, args.output)


def _save_result(result: dict, output: str):
    """保存结果到文件（JSON 或 Markdown）"""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output.endswith(".json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            info = result.get("video_info", {})
            f.write(f"# {info.get('title', '视频总结')}\n\n")
            f.write(f"- **平台**: {result.get('platform')}\n")
            f.write(f"- **URL**: {info.get('url')}\n")
            f.write(f"- **格式**: {result.get('format')}\n")
            f.write(f"- **时间**: {result.get('timestamp')}\n\n")
            f.write(result.get("summary", ""))
    print(f"\n📁 已保存到: {output_path}")


def cmd_summarize(args):
    """url / batch 子命令"""
    config = load_config(getattr(args, "config", None))

    api_key = getattr(args, "api_key", None) or config.get("api_key")
    api_url = getattr(args, "api_url", None) or config.get("api_url")
    model   = getattr(args, "model", None)   or config.get("model", "MiniMax-M2.1")

    # 收集 URL 列表
    urls: list = []
    if getattr(args, "url", None):
        urls = [args.url]
    elif getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    if not urls:
        print("❌ 请提供 URL 或文件")
        return

    # 异步并发模式
    if getattr(args, "async_mode", False) and len(urls) > 1:
        print(f"🚀 异步处理 {len(urls)} 个视频...\n")

        async def _run():
            async_s = AsyncSummarizer(
                max_concurrent=getattr(args, "concurrent", 3),
                api_key=api_key, api_url=api_url, model=model,
            )

            def progress(url, _result):
                print(f"  ✅ {url[:50]}... 完成")

            results = await async_s.summarize_batch(urls, args.format, progress)
            for r in results:
                if not getattr(args, "quiet", False):
                    print_result(r, args)

        asyncio.run(_run())
        return

    # 同步顺序模式
    print(f"📹 处理 {len(urls)} 个视频...\n")
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url[:60]}...")
        try:
            result = summarize(
                url=url,
                format=args.format,
                api_key=api_key,
                api_url=api_url,
                model=model,
                use_subtitle=not getattr(args, "no_subtitle", False),
                clean_danmaku=not getattr(args, "no_clean", False),
            )
            if not getattr(args, "quiet", False):
                print_result(result, args)

            if getattr(args, "save_history", False):
                store = HistoryStore()
                info = result.get("video_info", {})
                store.add(
                    url=url,
                    title=info.get("title", ""),
                    platform=result.get("platform", ""),
                    summary=result.get("summary", ""),
                    format=args.format,
                    tags=getattr(args, "tags", None),
                )
            print("  ✅ 完成\n")
        except Exception as e:
            print(f"  ❌ 错误: {e}\n")


def cmd_compare(args):
    """compare 子命令 - 对比多个视频"""
    print(f"🔍 对比 {len(args.urls)} 个视频\n")
    comparator = VideoComparator()
    report = comparator.compare(args.urls, args.format)

    print("=" * 60)
    print("视频对比报告")
    print("=" * 60)
    for i, v in enumerate(report["videos"], 1):
        print(f"\n[{i}] {v['title']}")
        print(f"    平台: {v['platform']}")
        print(f"    预览: {v['summary_preview']}...")

    print("\n平台分布:")
    for p, c in report["comparison"]["platforms"].items():
        print(f"  - {p}: {c}")

    if args.output:
        _save_result(report, args.output)


def cmd_history(args):
    """history 子命令"""
    store = HistoryStore()
    if args.clear:
        if input("确认清除所有历史? (y/n): ").lower() == "y":
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
        print(f"- [{r['platform']}] {r['title'][:50]}")
        print(f"  {r['created_at']}")
        print(f"  {r['summary'][:120]}...")
        print()


def cmd_stats(args):
    stats = HistoryStore().get_stats()
    print("📊 统计信息")
    print("=" * 40)
    print(f"总记录数: {stats['total']}")
    print("\n平台分布:")
    for p, c in stats["by_platform"].items():
        print(f"  - {p}: {c}")


def cmd_providers(args):
    print("支持的 LLM 提供商:")
    for p in LLMFactories.list_providers():
        print(f"  - {p}")
    print("\n用法: python cli.py url URL --provider openai")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  %(prog)s url "https://youtube.com/watch?v=xxx" -f brief
  %(prog)s url "URL" --provider openai --api-key sk-xxx
  %(prog)s batch urls.txt -f detailed -o results.json
  %(prog)s compare "URL1" "URL2" "URL3"
  %(prog)s history --search AI
  %(prog)s stats
  %(prog)s providers
        """,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # ------ url ------
    p_url = sub.add_parser("url", help="总结单个视频")
    p_url.add_argument("url", nargs="?", help="视频 URL")
    p_url.add_argument("-f", "--format", choices=list(DEFAULT_PROMPTS.keys()), default="brief")
    p_url.add_argument("-o", "--output", help="输出文件 (.json 或 .md)")
    p_url.add_argument("--config", help="配置文件路径")
    p_url.add_argument("--provider", choices=LLMFactories.list_providers(), help="LLM 提供商")
    p_url.add_argument("--api-key",  dest="api_key")
    p_url.add_argument("--api-url",  dest="api_url")
    p_url.add_argument("--model")
    p_url.add_argument("--no-subtitle", action="store_true", help="不使用字幕")
    p_url.add_argument("--no-clean",    action="store_true", help="不清洗弹幕")
    p_url.add_argument("-q", "--quiet", action="store_true", help="安静模式")
    p_url.add_argument("--save-history", action="store_true", dest="save_history")
    p_url.add_argument("--tags", nargs="*")

    # ------ batch ------
    p_batch = sub.add_parser("batch", help="批量处理")
    p_batch.add_argument("file", nargs="?", help="URL 文件（每行一个）")
    p_batch.add_argument("-f", "--format", default="brief")
    p_batch.add_argument("-o", "--output")
    p_batch.add_argument("--config")
    p_batch.add_argument("--provider", choices=LLMFactories.list_providers())
    p_batch.add_argument("--api-key",  dest="api_key")
    p_batch.add_argument("--api-url",  dest="api_url")
    p_batch.add_argument("--model")
    p_batch.add_argument("--async",    dest="async_mode", action="store_true", help="异步并发")
    p_batch.add_argument("-c", "--concurrent", type=int, default=3)
    p_batch.add_argument("--no-subtitle", action="store_true")
    p_batch.add_argument("--no-clean",    action="store_true")
    p_batch.add_argument("-q", "--quiet", action="store_true")

    # ------ compare ------
    p_cmp = sub.add_parser("compare", help="对比多个视频")
    p_cmp.add_argument("urls", nargs="+")
    p_cmp.add_argument("-f", "--format", default="brief")
    p_cmp.add_argument("-o", "--output")

    # ------ history ------
    p_hist = sub.add_parser("history", help="历史记录")
    p_hist.add_argument("--search", help="搜索关键词")
    p_hist.add_argument("--limit", type=int, default=50)
    p_hist.add_argument("--clear", action="store_true")

    # ------ stats ------
    sub.add_parser("stats", help="统计信息")

    # ------ providers ------
    sub.add_parser("providers", help="查看 LLM 提供商")

    # ------ config ------
    p_cfg = sub.add_parser("config", help="配置管理")
    p_cfg.add_argument("--set", help="设置项（key=value）")
    p_cfg.add_argument("--get", help="读取某项")

    args = parser.parse_args()

    dispatch = {
        "url":       cmd_summarize,
        "batch":     cmd_summarize,
        "compare":   cmd_compare,
        "history":   cmd_history,
        "stats":     cmd_stats,
        "providers": cmd_providers,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    elif args.command == "config":
        config = load_config()
        if args.set:
            k, v = args.set.split("=", 1)
            config[k] = v
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ {k} = {v}")
        elif args.get:
            print(f"{args.get} = {config.get(args.get, '（未设置）')}")
        else:
            print(json.dumps(config, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
