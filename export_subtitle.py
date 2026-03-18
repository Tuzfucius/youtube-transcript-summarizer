#!/usr/bin/env python3
"""
仅导出字幕/弹幕工具
提取并保存视频字幕或弹幕内容（不调用 LLM）
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.extractors import (
    YouTubeExtractor,
    BilibiliExtractor,
    DanmakuCleaner,
    detect_platform,
)
from src.utils import logger


def extract_content(url: str, use_subtitle: bool = True, clean: bool = True) -> dict:
    """提取视频内容，返回统一格式的 dict"""
    platform = detect_platform(url)

    if platform == "youtube":
        vid = YouTubeExtractor.extract_video_id(url)
        if not vid:
            return {"error": "无法解析视频 ID"}
        tr = YouTubeExtractor.get_transcript(vid)
        return {
            "platform": platform,
            "title": "",
            "content": tr["text"] if tr else "",
            "content_type": "字幕",
        }

    elif platform == "bilibili":
        bvid = BilibiliExtractor.extract_bvid(url)
        if not bvid:
            return {"error": "无法解析 BV 号"}
        info = BilibiliExtractor.get_video_info(bvid) or {}
        content = ""

        if use_subtitle:
            sub = BilibiliExtractor.get_subtitles(info.get("bvid", bvid), info.get("cid", 0))
            if sub.get("has_subtitle"):
                content = sub.get("text", "")

        if not content:
            danmaku = BilibiliExtractor.get_danmaku(info.get("cid", 0))
            if clean:
                danmaku, _ = DanmakuCleaner.clean(danmaku)
            content = " ".join(d["text"] for d in danmaku[:500])

        return {
            "platform":     platform,
            "title":        info.get("title", ""),
            "content":      content,
            "content_type": "字幕" if use_subtitle and content else "弹幕",
        }

    return {"platform": platform, "title": f"{platform} 内容", "content": "", "content_type": "描述"}


def export_subtitle(
    url: str,
    output: str = None,
    format: str = "txt",
    clean: bool = True,
    use_subtitle: bool = True,
) -> dict:
    """
    仅导出字幕/弹幕内容，不调用 LLM。

    Args:
        url:          视频 URL
        output:       输出文件路径（自动推断扩展名）
        format:       输出格式（txt / json）
        clean:        是否清洗弹幕
        use_subtitle: 是否优先使用字幕

    Returns:
        包含 success/error 信息的 dict
    """
    data = extract_content(url, use_subtitle=use_subtitle, clean=clean)
    if "error" in data:
        return {"error": data["error"], "url": url}

    content = data.get("content", "")
    if not content:
        return {"error": "无法提取内容", "url": url}

    if not output:
        title = data.get("title", "video")
        safe_title = re.sub(r'[\/:*?"<>|\\]', "_", title)[:50]
        output = f"{safe_title}.{format}"

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({**data, "url": url}, f, ensure_ascii=False, indent=2)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {data.get('title', 'Video')}\n")
            f.write(f"# URL: {url}\n")
            f.write(f"# 平台: {data.get('platform')}\n")
            f.write(f"# 类型: {data.get('content_type')}\n")
            f.write("#" * 40 + "\n\n")
            for line in re.split(r"[。！？\n]", content):
                line = line.strip()
                if line:
                    f.write(f"{line}\n")

    return {
        "success":        True,
        "title":          data.get("title"),
        "platform":       data.get("platform"),
        "content_type":   data.get("content_type"),
        "content_length": len(content),
        "file_path":      str(output_path),
        "format":         format,
    }


def export_batch(url_file: str, output_dir: str = ".", format: str = "txt", **kwargs) -> list:
    """批量导出字幕"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    with open(url_file, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    results = []
    for i, url in enumerate(urls, 1):
        result = export_subtitle(url, output=str(output_dir / f"video_{i}.{format}"), format=format, **kwargs)
        results.append(result)
        status = "✅" if result.get("success") else "❌"
        print(f"{status} [{i}/{len(urls)}] {url[:60]}...")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="🎬 导出视频字幕/弹幕（不调用 LLM）")
    parser.add_argument("url", nargs="?", help="视频 URL")
    parser.add_argument("-o", "--output", help="输出文件")
    parser.add_argument("-f", "--format", choices=["txt", "json"], default="txt")
    parser.add_argument("--no-clean",    action="store_true")
    parser.add_argument("--no-subtitle", action="store_true")
    parser.add_argument("--batch", help="批量文件")
    parser.add_argument("-d", "--dir", default=".", help="批量输出目录")

    args = parser.parse_args()

    if args.url:
        result = export_subtitle(
            args.url,
            output=args.output,
            format=args.format,
            clean=not args.no_clean,
            use_subtitle=not args.no_subtitle,
        )
        if result.get("success"):
            print(f"\n✅ 导出成功!")
            print(f"   文件: {result['file_path']}")
            print(f"   平台: {result['platform']}")
            print(f"   类型: {result['content_type']}")
            print(f"   长度: {result['content_length']} 字符")
        else:
            print(f"❌ 错误: {result.get('error')}")
    elif args.batch:
        results = export_batch(args.batch, output_dir=args.dir, format=args.format)
        print(f"\n📦 完成: {len(results)} 个")

__all__ = ["export_subtitle", "export_batch"]
