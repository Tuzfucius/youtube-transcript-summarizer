#!/usr/bin/env python3
"""
Video Summarizer - 仅导出字幕工具
提取并保存视频字幕/弹幕内容
"""

import os
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from __init__ import extract_video, clean_danmaku


def export_subtitle(url: str, output: str = None, format: str = 'txt', 
                   clean: bool = True, use_subtitle: bool = True) -> dict:
    """
    仅导出字幕/弹幕内容
    
    Args:
        url: 视频 URL
        output: 输出文件路径
        format: 输出格式 (txt/json)
        clean: 是否清洗弹幕
        use_subtitle: 是否优先使用字幕
    
    Returns:
        dict: 包含 content 和 file_path
    """
    # 提取内容
    data = extract_video(url, use_subtitle=use_subtitle, clean_danmaku_flag=clean)
    
    content = data.get('content', '')
    if not content:
        return {'error': '无法提取内容', 'url': url}
    
    # 确定输出文件
    if not output:
        title = data.get('title', 'video')
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:50]
        output = f"{safe_title}.{format}"
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入文件
    if format == 'json':
        output_data = {
            'url': url,
            'title': data.get('title'),
            'platform': data.get('platform'),
            'content_type': data.get('content_type'),
            'content': content
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    else:
        # TXT 格式：简单按句号和换行符分割
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {data.get('title', 'Video')}\n")
            f.write(f"# URL: {url}\n")
            f.write(f"# 平台: {data.get('platform')}\n")
            f.write(f"# 类型: {data.get('content_type')}\n")
            f.write("#" * 40 + "\n\n")
            # 清理并写入内容
            lines = re.split(r'[。！？\n]', content)
            for line in lines:
                line = line.strip()
                if line:
                    f.write(f"{line}\n")
    
    return {
        'success': True,
        'title': data.get('title'),
        'platform': data.get('platform'),
        'content_type': data.get('content_type'),
        'content_length': len(content),
        'file_path': str(output_path),
        'format': format
    }


def export_batch(url_file: str, output_dir: str = '.', format: str = 'txt', **kwargs) -> list:
    """批量导出"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    results = []
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    for i, url in enumerate(urls, 1):
        output = str(output_dir / f"video_{i}.{format}")
        result = export_subtitle(url, output=output, format=format, **kwargs)
        results.append(result)
        status = "✅" if result.get('success') else "❌"
        print(f"{status} [{i}/{len(urls)}] {url[:50]}...")
    
    return results


# ============== CLI ==============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='🎬 导出视频字幕/弹幕')
    parser.add_argument('url', nargs='?', help='视频 URL')
    parser.add_argument('-o', '--output', help='输出文件')
    parser.add_argument('-f', '--format', choices=['txt', 'json'], default='txt')
    parser.add_argument('--no-clean', action='store_true')
    parser.add_argument('--no-subtitle', action='store_true')
    parser.add_argument('--batch', help='批量文件')
    parser.add_argument('-d', '--dir', default='.', help='输出目录')
    
    args = parser.parse_args()
    
    if args.url:
        result = export_subtitle(
            args.url,
            output=args.output,
            format=args.format,
            clean=not args.no_clean,
            use_subtitle=not args.no_subtitle
        )
        
        if result.get('success'):
            print(f"\n✅ 导出成功!")
            print(f"   文件: {result['file_path']}")
            print(f"   平台: {result['platform']}")
            print(f"   类型: {result['content_type']}")
            print(f"   长度: {result['content_length']} 字符")
        else:
            print(f"❌ 错误: {result.get('error')}")
    
    elif args.batch:
        results = export_batch(args.batch, output_dir=args.dir, format=args.format)
        print(f"\n📦 批量完成: {len(results)} 个")


__all__ = ['export_subtitle', 'export_batch']
