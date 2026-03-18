#!/usr/bin/env python3
"""视频字幕/弹幕导出入口。

该模块只负责把已提取的文本落盘，不调用 LLM。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extractors import BilibiliExtractor, DanmakuCleaner, YouTubeExtractor, detect_platform


def safe_filename(name: str, fallback: str = "video") -> str:
    """把标题转换成适合 Windows 的文件名。"""

    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name or "").strip()
    return cleaned[:80] or fallback


def split_text_lines(text: str) -> List[str]:
    """把长文本拆成更适合导出的行。"""

    chunks = re.split(r"[。！？!?;\n\r]+", text or "")
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def extract_content(url: str, use_subtitle: bool = True, clean: bool = True) -> Dict:
    """提取视频原文、字幕或弹幕。"""

    platform = detect_platform(url)

    if platform == "youtube":
        video_id = YouTubeExtractor.extract_video_id(url)
        if not video_id:
            return {"error": "无法解析 YouTube 视频 ID", "platform": platform, "url": url}

        transcript = YouTubeExtractor.get_transcript(video_id)
        text = transcript["text"] if transcript else ""
        return {
            "platform": platform,
            "url": url,
            "title": "",
            "content": text,
            "content_type": "字幕",
            "source_type": "subtitle",
            "language": transcript.get("language") if transcript else "",
        }

    if platform == "bilibili":
        bvid = BilibiliExtractor.extract_bvid(url)
        if not bvid:
            return {"error": "无法解析 B 站 BV 号", "platform": platform, "url": url}

        info = BilibiliExtractor.get_video_info(bvid) or {}
        content = ""
        source_type = "subtitle"
        content_type = "字幕"

        if use_subtitle:
            subtitle = BilibiliExtractor.get_subtitles(info.get("bvid", bvid), info.get("cid", 0))
            if subtitle.get("has_subtitle"):
                content = subtitle.get("text", "")

        if not content:
            source_type = "danmaku"
            content_type = "弹幕"
            danmaku = BilibiliExtractor.get_danmaku(info.get("cid", 0))
            if clean:
                danmaku, _ = DanmakuCleaner.clean(danmaku)
            content = " ".join(item.get("text", "") for item in danmaku[:500]).strip()

        return {
            "platform": platform,
            "url": url,
            "title": info.get("title", ""),
            "owner": info.get("owner", ""),
            "content": content,
            "content_type": content_type,
            "source_type": source_type,
            "language": "",
        }

    return {
        "platform": platform,
        "url": url,
        "title": f"{platform} 内容",
        "content": "",
        "content_type": "描述",
        "source_type": "description",
        "language": "",
    }


def export_subtitle(
    url: str,
    output: Optional[str] = None,
    format: str = "txt",
    clean: bool = True,
    use_subtitle: bool = True,
) -> Dict:
    """导出字幕、弹幕或原文文本。"""

    data = extract_content(url, use_subtitle=use_subtitle, clean=clean)
    if data.get("error"):
        return {"error": data["error"], "url": url, "platform": data.get("platform", "unknown")}

    content = data.get("content", "").strip()
    if not content:
        return {"error": "未提取到可导出的内容", "url": url, "platform": data.get("platform", "unknown")}

    if not output:
        title = data.get("title") or "video"
        output = f"{safe_filename(title)}.{format}"

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        payload = dict(data)
        payload["url"] = url
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    else:
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(f"# {data.get('title') or 'Video'}\n")
            handle.write(f"# URL: {url}\n")
            handle.write(f"# 平台: {data.get('platform', '')}\n")
            handle.write(f"# 内容类型: {data.get('content_type', '')}\n")
            handle.write(f"# 来源: {data.get('source_type', '')}\n")
            handle.write("#" * 40 + "\n\n")
            for line in split_text_lines(content):
                handle.write(f"{line}\n")

    return {
        "success": True,
        "title": data.get("title", ""),
        "platform": data.get("platform", ""),
        "content_type": data.get("content_type", ""),
        "source_type": data.get("source_type", ""),
        "content_length": len(content),
        "file_path": str(output_path),
        "format": format,
    }


def export_batch(url_file: str, output_dir: str = ".", format: str = "txt", **kwargs) -> List[Dict]:
    """批量导出。"""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with Path(url_file).open("r", encoding="utf-8") as handle:
        urls = [line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#")]

    results: List[Dict] = []
    for index, url in enumerate(urls, start=1):
        result = export_subtitle(
            url,
            output=str(output_path / f"video_{index}.{format}"),
            format=format,
            **kwargs,
        )
        results.append(result)
        status = "成功" if result.get("success") else "失败"
        print(f"[{index}/{len(urls)}] {status} {url}")

    return results


def build_parser() -> argparse.ArgumentParser:
    """构建导出工具的参数解析器。"""

    parser = argparse.ArgumentParser(description="导出视频字幕或弹幕")
    parser.add_argument("url", nargs="?", help="视频 URL")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-f", "--format", choices=["txt", "json"], default="txt")
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--no-subtitle", action="store_true")
    parser.add_argument("--batch", help="批量 URL 文件")
    parser.add_argument("-d", "--dir", default=".", help="批量输出目录")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    """命令行入口。"""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.url:
        result = export_subtitle(
            args.url,
            output=args.output,
            format=args.format,
            clean=not args.no_clean,
            use_subtitle=not args.no_subtitle,
        )
        if result.get("success"):
            print("导出成功")
            print(f"文件: {result['file_path']}")
            print(f"平台: {result['platform']}")
            print(f"内容类型: {result['content_type']}")
            print(f"来源: {result['source_type']}")
            print(f"长度: {result['content_length']}")
            return 0
        print(f"导出失败: {result.get('error', '未知错误')}")
        return 1

    if args.batch:
        export_batch(args.batch, output_dir=args.dir, format=args.format)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["extract_content", "export_subtitle", "export_batch", "safe_filename", "split_text_lines"]
