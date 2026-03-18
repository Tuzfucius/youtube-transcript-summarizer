#!/usr/bin/env python3
"""命令行入口。

这一层只负责参数解析、配置合并、结果展示和文件输出，不承载核心提取逻辑。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config.json"
DEFAULT_API_URL = "https://api.minimaxi.com/v1/chat/completions"
DEFAULT_MODEL = "MiniMax-M2.1"

try:
    from src import DEFAULT_PROMPTS, summarize
except Exception as exc:  # pragma: no cover - import failure is surfaced at runtime
    raise RuntimeError(f"无法导入核心模块: {exc}") from exc

try:
    from src.advanced import AsyncSummarizer, HistoryStore, LLMFactories, VideoComparator
except Exception:  # pragma: no cover - optional dependency path
    AsyncSummarizer = None
    HistoryStore = None
    LLMFactories = None
    VideoComparator = None


def configure_stdio() -> None:
    """尽量把标准输出切到 UTF-8，避免 Windows 控制台编码报错。"""

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载本地配置文件。

    仅用于读取本机的 `config.json`，不会向外部写入任何内容。
    """

    candidates: List[Path] = []
    if config_file:
        candidates.append(Path(config_file))
    candidates.append(CONFIG_PATH)

    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
    return {}


def save_config(config: Dict[str, Any], config_file: Optional[str] = None) -> Path:
    """保存本地配置文件。"""

    target = Path(config_file) if config_file else CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return target


def mask_sensitive_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """返回适合打印的配置副本，避免暴露密钥。"""

    masked = dict(config)
    if masked.get("api_key"):
        masked["api_key"] = "***"
    return masked


def read_urls_from_args(args: argparse.Namespace) -> List[str]:
    """从命令行参数中收集 URL 列表。"""

    if getattr(args, "url", None):
        return [args.url]
    if getattr(args, "file", None):
        with Path(args.file).open("r", encoding="utf-8") as handle:
            return [
                line.strip()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            ]
    return []


def resolve_provider_defaults(provider: Optional[str]) -> Dict[str, str]:
    """根据 provider 补齐默认 API 地址和模型。"""

    if not provider or LLMFactories is None:
        return {}

    try:
        provider_config = LLMFactories.create(provider, api_key="")
    except Exception:
        return {}

    return {
        "api_url": provider_config.get("api_url", DEFAULT_API_URL),
        "model": provider_config.get("model", DEFAULT_MODEL),
    }


def resolve_runtime_options(args: argparse.Namespace) -> Dict[str, Any]:
    """合并命令行参数、本地配置和环境变量。"""

    config = load_config(getattr(args, "config", None))
    provider_defaults = resolve_provider_defaults(getattr(args, "provider", None))

    return {
        "api_key": (
            getattr(args, "api_key", None)
            or config.get("api_key")
            or os.getenv("VIDEO_SUMMARIZER_API_KEY")
            or os.getenv("MINIMAX_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        ),
        "api_url": (
            getattr(args, "api_url", None)
            or config.get("api_url")
            or os.getenv("VIDEO_SUMMARIZER_API_URL")
            or provider_defaults.get("api_url")
            or DEFAULT_API_URL
        ),
        "model": (
            getattr(args, "model", None)
            or config.get("model")
            or os.getenv("VIDEO_SUMMARIZER_MODEL")
            or provider_defaults.get("model")
            or DEFAULT_MODEL
        ),
        "config": config,
    }


def save_result(result: Dict[str, Any], output: str) -> Path:
    """保存单个总结结果。"""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".json":
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return output_path

    info = result.get("video_info", {}) if isinstance(result, dict) else {}
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# {info.get('title') or '视频总结'}\n\n")
        handle.write(f"- 平台: {result.get('platform', 'unknown')}\n")
        handle.write(f"- URL: {info.get('url', '')}\n")
        handle.write(f"- 格式: {result.get('format', '')}\n")
        handle.write(f"- 时间: {result.get('timestamp', '')}\n\n")
        handle.write(str(result.get("summary", "")))

    return output_path


def save_batch_results(results: List[Dict[str, Any]], output: str) -> Path:
    """保存批量结果。"""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".json":
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return output_path

    with output_path.open("w", encoding="utf-8") as handle:
        for index, result in enumerate(results, start=1):
            info = result.get("video_info", {})
            handle.write(f"# {index}. {info.get('title') or '视频总结'}\n\n")
            handle.write(f"- 平台: {result.get('platform', 'unknown')}\n")
            handle.write(f"- URL: {info.get('url', '')}\n")
            handle.write(f"- 格式: {result.get('format', '')}\n")
            handle.write(f"- 时间: {result.get('timestamp', '')}\n\n")
            handle.write(str(result.get("summary", "")))
            handle.write("\n\n")

    return output_path


def print_result(result: Dict[str, Any], output: Optional[str] = None) -> None:
    """打印单条结果，并在需要时保存到文件。"""

    summary = result.get("summary") or result.get("error") or "没有可用结果"
    info = result.get("video_info", {})

    print()
    print("=" * 72)
    print(f"平台: {result.get('platform', 'unknown')}")
    print(f"标题: {info.get('title', 'N/A')}")
    print(f"URL: {info.get('url', '')}")
    print("=" * 72)
    print(summary)

    if output:
        saved = save_result(result, output)
        print()
        print(f"结果已保存到: {saved}")


def run_summarize(args: argparse.Namespace) -> int:
    """执行单条或批量总结。"""

    runtime = resolve_runtime_options(args)
    urls = read_urls_from_args(args)
    if not urls:
        print("请提供 URL 或 URL 列表文件。")
        return 1

    if getattr(args, "async_mode", False) and len(urls) > 1 and AsyncSummarizer is not None:
        async def _run() -> List[Dict[str, Any]]:
            summarizer = AsyncSummarizer(
                max_concurrent=getattr(args, "concurrent", 3),
                api_key=runtime["api_key"],
                api_url=runtime["api_url"],
                model=runtime["model"],
                prompt=getattr(args, "prompt", None),
                max_length=getattr(args, "max_length", 500),
                use_subtitle=not getattr(args, "no_subtitle", False),
                clean_danmaku=not getattr(args, "no_clean", False),
            )
            return await summarizer.summarize_batch(urls, format=args.format)

        results = asyncio.run(_run())
        for item in results:
            if not getattr(args, "quiet", False):
                print_result(item, None)
        if getattr(args, "output", None):
            save_batch_results(results, args.output)
        return 0

    collected_results: List[Dict[str, Any]] = []
    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] {url}")
        result = summarize(
            url=url,
            format=args.format,
            prompt=getattr(args, "prompt", None),
            max_length=getattr(args, "max_length", 500),
            api_key=runtime["api_key"],
            api_url=runtime["api_url"],
            model=runtime["model"],
            use_subtitle=not getattr(args, "no_subtitle", False),
            clean_danmaku=not getattr(args, "no_clean", False),
        )
        collected_results.append(result)
        if not getattr(args, "quiet", False):
            print_result(result, getattr(args, "output", None) if len(urls) == 1 else None)
        if getattr(args, "save_history", False) and HistoryStore is not None:
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
    if getattr(args, "output", None) and len(collected_results) > 1:
        save_batch_results(collected_results, args.output)
    return 0


def run_compare(args: argparse.Namespace) -> int:
    """执行多视频对比。"""

    if VideoComparator is None:
        print("当前环境不支持对比功能。")
        return 1

    report = VideoComparator().compare(args.urls, args.format)
    print()
    print("=" * 72)
    print("视频对比结果")
    print("=" * 72)
    for index, video in enumerate(report.get("videos", []), start=1):
        print(f"[{index}] {video.get('title', '')}")
        print(f"    平台: {video.get('platform', '')}")
        print(f"    预览: {video.get('summary_preview', '')}")
    print()
    print("平台分布:")
    for platform, count in report.get("comparison", {}).get("platforms", {}).items():
        print(f"  - {platform}: {count}")
    if getattr(args, "output", None):
        save_result(report, args.output)
    return 0


def run_history(args: argparse.Namespace) -> int:
    """查看或清理历史记录。"""

    if HistoryStore is None:
        print("当前环境不支持历史记录功能。")
        return 1

    store = HistoryStore()
    if getattr(args, "clear", False):
        confirm = input("确认清空全部历史记录吗？(y/n): ").strip().lower()
        if confirm == "y":
            store.clear()
            print("历史记录已清空。")
        return 0

    if getattr(args, "search", None):
        rows = store.search(args.search)
        print(f"检索到 {len(rows)} 条记录。")
    else:
        rows = store.get_all(limit=getattr(args, "limit", 50))
        print(f"历史记录共 {len(rows)} 条。")

    for row in rows:
        print(f"- [{row.get('platform', '')}] {row.get('title', '')}")
        print(f"  {row.get('created_at', '')}")
        print(f"  {row.get('summary', '')[:120]}")
    return 0


def run_stats(_: argparse.Namespace) -> int:
    """打印统计信息。"""

    if HistoryStore is None:
        print("当前环境不支持统计功能。")
        return 1

    stats = HistoryStore().get_stats()
    print("统计信息")
    print("=" * 40)
    print(f"总记录数: {stats.get('total', 0)}")
    print("平台分布:")
    for platform, count in stats.get("by_platform", {}).items():
        print(f"  - {platform}: {count}")
    return 0


def run_providers(_: argparse.Namespace) -> int:
    """打印可用的 provider 列表。"""

    providers = LLMFactories.list_providers() if LLMFactories is not None else []
    if not providers:
        print("当前环境没有可用的 LLM provider。")
        return 1

    print("支持的 LLM provider:")
    for provider in providers:
        print(f"  - {provider}")
    return 0


def run_config(args: argparse.Namespace) -> int:
    """读取、修改或显示本地配置。"""

    config = load_config(getattr(args, "config", None))
    if getattr(args, "set", None):
        key, value = args.set.split("=", 1)
        config[key] = value
        target = save_config(config, getattr(args, "config", None))
        print(f"已更新配置: {key} 写入 {target}")
        return 0

    if getattr(args, "get", None):
        value = config.get(args.get, "")
        print(value if args.get != "api_key" else value)
        return 0

    print(json.dumps(mask_sensitive_config(config), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器。"""

    providers = LLMFactories.list_providers() if LLMFactories is not None else None

    parser = argparse.ArgumentParser(
        description="Video Summarizer 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    url_parser = subparsers.add_parser("url", help="总结单个视频")
    url_parser.add_argument("url", nargs="?", help="视频 URL")
    url_parser.add_argument("-f", "--format", choices=list(DEFAULT_PROMPTS.keys()), default="brief")
    url_parser.add_argument("-o", "--output", help="输出文件路径")
    url_parser.add_argument("--config", help="配置文件路径")
    url_parser.add_argument("--provider", choices=providers, help="LLM provider")
    url_parser.add_argument("--api-key", dest="api_key")
    url_parser.add_argument("--api-url", dest="api_url")
    url_parser.add_argument("--model")
    url_parser.add_argument("--prompt")
    url_parser.add_argument("--max-length", type=int, default=500)
    url_parser.add_argument("--no-subtitle", action="store_true")
    url_parser.add_argument("--no-clean", action="store_true")
    url_parser.add_argument("-q", "--quiet", action="store_true")
    url_parser.add_argument("--save-history", action="store_true", dest="save_history")
    url_parser.add_argument("--tags", nargs="*")
    url_parser.set_defaults(func=run_summarize)

    batch_parser = subparsers.add_parser("batch", help="批量总结")
    batch_parser.add_argument("file", nargs="?", help="URL 列表文件")
    batch_parser.add_argument("-f", "--format", choices=list(DEFAULT_PROMPTS.keys()), default="brief")
    batch_parser.add_argument("-o", "--output", help="输出文件路径")
    batch_parser.add_argument("--config", help="配置文件路径")
    batch_parser.add_argument("--provider", choices=providers, help="LLM provider")
    batch_parser.add_argument("--api-key", dest="api_key")
    batch_parser.add_argument("--api-url", dest="api_url")
    batch_parser.add_argument("--model")
    batch_parser.add_argument("--async", dest="async_mode", action="store_true")
    batch_parser.add_argument("-c", "--concurrent", type=int, default=3)
    batch_parser.add_argument("--no-subtitle", action="store_true")
    batch_parser.add_argument("--no-clean", action="store_true")
    batch_parser.add_argument("-q", "--quiet", action="store_true")
    batch_parser.set_defaults(func=run_summarize)

    compare_parser = subparsers.add_parser("compare", help="对比多个视频")
    compare_parser.add_argument("urls", nargs="+", help="视频 URL 列表")
    compare_parser.add_argument("-f", "--format", choices=list(DEFAULT_PROMPTS.keys()), default="brief")
    compare_parser.add_argument("-o", "--output", help="输出文件路径")
    compare_parser.set_defaults(func=run_compare)

    history_parser = subparsers.add_parser("history", help="查看历史记录")
    history_parser.add_argument("--search", help="搜索关键字")
    history_parser.add_argument("--limit", type=int, default=50)
    history_parser.add_argument("--clear", action="store_true")
    history_parser.set_defaults(func=run_history)

    stats_parser = subparsers.add_parser("stats", help="查看统计信息")
    stats_parser.set_defaults(func=run_stats)

    providers_parser = subparsers.add_parser("providers", help="查看可用 provider")
    providers_parser.set_defaults(func=run_providers)

    config_parser = subparsers.add_parser("config", help="管理本地配置")
    config_parser.add_argument("--config", help="配置文件路径")
    config_parser.add_argument("--set", help="写入配置，格式为 key=value")
    config_parser.add_argument("--get", help="读取配置项")
    config_parser.set_defaults(func=run_config)

    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    """CLI 入口。"""

    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
