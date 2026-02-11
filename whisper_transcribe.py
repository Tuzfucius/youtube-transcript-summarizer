#!/usr/bin/env python3
"""
Video Summarizer - Whisper 转录模块（可选功能）
用于无字幕视频的语音转文字
"""

import os
import sys
from pathlib import Path

# 可选导入
try:
    from faster_whisper import Whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def check_whisper() -> dict:
    """检查 Whisper 是否可用"""
    return {
        'available': WHISPER_AVAILABLE,
        'models': ['tiny', 'base', 'small', 'medium', 'large-v3'] if WHISPER_AVAILABLE else []
    }


def transcribe_audio(audio_path: str, model: str = "small", language: str = None) -> dict:
    """
    使用 Whisper 转录音频
    
    Args:
        audio_path: 音频文件路径
        model: 模型大小 (tiny/base/small/medium/large-v3)
        language: 语言代码，None 表示自动检测
    
    Returns:
        dict: 包含 text 和 segments
    """
    if not WHISPER_AVAILABLE:
        return {'error': 'Whisper 未安装', 'hint': 'pip install faster-whisper'}
    
    try:
        # 初始化模型
        model_instance = Whisper(model, device="cpu", compute_type="int8")
        
        # 转录
        options = {}
        if language:
            options["language"] = language
            
        segments, info = model_instance.transcribe(audio_path, **options)
        
        # 收集结果
        text_parts = []
        full_text = ""
        
        for segment in segments:
            text_parts.append(segment.text)
            full_text += segment.text + " "
        
        return {
            'success': True,
            'text': full_text.strip(),
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'segments': [
                {'start': s.start, 'end': s.end, 'text': s.text}
                for s in segments
            ]
        }
        
    except Exception as e:
        return {'error': str(e)}


def transcribe_video(video_path: str, model: str = "small", language: str = None) -> dict:
    """
    转录视频文件（提取音频后转录）
    
    Args:
        video_path: 视频文件路径
        model: Whisper 模型
        language: 语言
    
    Returns:
        dict: 转录结果
    """
    if not WHISPER_AVAILABLE:
        return {'error': 'Whisper 未安装'}
    
    try:
        import ffmpeg
        
        # 提取音频
        audio_path = video_path.replace(Path(video_path).suffix, ".wav")
        
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, ar=16000, ac=1)
            .overwrite_output()
            .run(quiet=True)
        )
        
        # 转录
        result = transcribe_audio(audio_path, model, language)
        
        # 清理临时音频
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        return result
        
    except Exception as e:
        return {'error': str(e)}


def transcribe_youtube(url: str, model: str = "small", language: str = None) -> dict:
    """
    转录 YouTube 视频
    
    Args:
        url: YouTube 视频 URL
        model: Whisper 模型
        language: 语言
    
    Returns:
        dict: 转录结果
    """
    if not WHISPER_AVAILABLE:
        return {'error': 'Whisper 未安装'}
    
    try:
        import yt_dlp
        
        # 下载音频
        audio_path = "/tmp/youtube_audio.wav"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'outtmpl': '/tmp/youtube_audio',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 转录
        result = transcribe_audio(audio_path, model, language)
        
        # 清理
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return result
        
    except Exception as e:
        return {'error': str(e)}


def install_whisper():
    """安装 Whisper 依赖"""
    print("📦 正在安装 Whisper...")
    print("  pip install faster-whisper")
    
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'faster-whisper'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Whisper 安装成功！")
        print("💡 重启程序后生效")
        return True
    else:
        print(f"❌ 安装失败: {result.stderr}")
        return False


# ============== CLI ==============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='🎙️ Whisper 转录工具')
    parser.add_argument('input', nargs='?', help='音频/视频文件或 URL')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large-v3'], default='small')
    parser.add_argument('--lang', help='语言代码 (zh/en/ja/ko...)')
    parser.add_argument('--check', action='store_true', help='检查 Whisper 状态')
    parser.add_argument('--install', action='store_true', help='安装 Whisper')
    
    args = parser.parse_args()
    
    if args.check:
        status = check_whisper()
        print(f"Whisper 可用: {status['available']}")
        if status['available']:
            print(f"可用模型: {status['models']}")
    
    elif args.install:
        install_whisper()
    
    elif args.input:
        result = transcribe_audio(args.input, args.model, args.lang)
        
        if 'error' in result:
            print(f"❌ 错误: {result['error']}")
            if 'hint' in result:
                print(f"💡 {result['hint']}")
        else:
            print(f"✅ 转录成功!")
            print(f"语言: {result['language']} ({result['language_probability']:.2f})")
            print(f"时长: {result['duration']:.1f}s")
            print(f"\n📝 内容预览:")
            print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])


__all__ = [
    'check_whisper', 'transcribe_audio', 'transcribe_video',
    'transcribe_youtube', 'install_whisper', 'WHISPER_AVAILABLE'
]
