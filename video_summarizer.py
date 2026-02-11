#!/usr/bin/env python3
"""
Video Summarizer - Multi-Platform Video Content Analyzer
支持 45+ 平台的视频内容总结工具
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
import gzip
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from collections import Counter
from functools import wraps

# ============== 日志系统 ==============
def setup_logger(name: str = "VideoSummarizer", log_file: str = None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    # 添加 success 方法
    def success(msg):
        logger.log(logging.INFO, f"✅ {msg}")
    logger.success = success
    
    fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    if log_file:
        Path(log_file).parent.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s'))
        logger.addHandler(fh)
    return logger

logger = setup_logger()


# ============== 工具装饰器 ==============
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed ({attempt}/{max_attempts}): {e}")
                        raise
                    logger.warning(f"{func.__name__} failed, retry in {current_delay:.1f}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_exc
        return wrapper
    return decorator


def handle_errors(default_return=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} error: {e}")
                return default_return
        return wrapper
    return decorator


class Timer:
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start = None
        self.elapsed = 0
    
    def __enter__(self):
        self.start = time.time()
        logger.debug(f"开始: {self.name}")
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start
        logger.debug(f"完成: {self.name} ({self.elapsed:.2f}s)")
        return False


# ============== 弹幕清洗器 ==============
class DanmakuCleaner:
    PATTERNS = [r'^[\d\.\,\-\+\=\s]+$', r'^.{1,2}$', r'^[\w\s]{1,5}$']
    KEEP_PATTERNS = [r'[\u4e00-\u9fff]{2,}', r'[，。！？]{2,}', r'笑|哭|泪|牛逼|顶|赞|帅|美|可爱|哈哈']
    
    @classmethod
    @handle_errors(default_return=([], {"total":0,"kept":0}))
    def clean(cls, danmaku: List[Dict], min_len: int = 2, max_len: int = 50) -> Tuple[List[Dict], Dict]:
        stats = {"total": len(danmaku), "kept": 0, "removed": 0}
        spam = Counter(d['text'] for d in danmaku if len(d.get('text','')) > 5)
        spam_texts = {t for t, c in spam.items() if c > 3}
        
        cleaned = []
        for d in danmaku:
            text = d.get('text', '').strip()
            if len(text) < min_len or len(text) > max_len or text in spam_texts:
                stats["removed"] += 1
                continue
            if any(re.search(p, text) for p in cls.PATTERNS) and not any(re.search(p, text) for p in cls.KEEP_PATTERNS):
                stats["removed"] += 1
                continue
            cleaned.append(d)
            stats["kept"] += 1
        
        logger.info(f"弹幕清洗: {stats['total']} → {stats['kept']} (保留率: {stats['kept']/max(1,stats['total'])*100:.1f}%)")
        return cleaned, stats


# ============== 平台检测 ==============
def detect_platform(url: str) -> str:
    url_l = url.lower()
    platforms = {
        'youtube': ['youtube.com', 'youtu.be'], 'bilibili': ['bilibili.com', 'b站'],
        'douyin': ['tiktok.com', 'douyin'], 'kuaishou': ['kuaishou.com', '快手'],
        'xigua': ['ixigua.com', '西瓜视频'], 'twitch': ['twitch.tv'], 'vimeo': ['vimeo.com'],
        'weibo': ['weibo.com'], 'twitter': ['twitter.com', 'x.com'], 'instagram': ['instagram.com'],
        'xiaohongshu': ['xiaohongshu.com', '小红书'], 'zhihu': ['zhihu.com'], 'telegram': ['t.me'],
        'reddit': ['reddit.com'], 'medium': ['medium.com'], 'quora': ['quora.com'], 'pinterest': ['pinterest.com'],
        'netease': ['music.163.com'], 'qqmusic': ['qq.com'], 'soundcloud': ['soundcloud.com'],
        'taobao': ['taobao.com', '天猫'], 'tmall': ['tmall.com'], 'jd': ['jd.com', '京东'],
        'dewu': ['dewu.com', '得物'], 'zhuanzhuan': ['zhuanzhuan.com', '转转'], 'xianyu': ['xianyu.com', '闲鱼'],
        'amazon': ['amazon.'], 'ebay': ['ebay.com'], 'etsy': ['etsy.com'], 'shopify': ['shopify'],
        'meituan': ['meituan.com', '大众点评'], 'eleme': ['ele.me'], 'ctrip': ['ctrip.com', '携程'],
        'mafengwo': ['mafengwo.cn', '马蜂窝'], 'airbnb': ['airbnb.com'],
        'codeforces': ['codeforces.com'], 'leetcode': ['leetcode.com'],
        'douban': ['douban.com'], 'tieba': ['tieba.baidu.com'], 'lofter': ['lofter.com'],
        'cyzone': ['cyzone.cn'], 'douyu': ['douyu.com'], 'huya': ['huya.com'], 'yy': ['yy.com'],
        'snapchat': ['snapchat.com'],
    }
    for p, patterns in platforms.items():
        if any(k in url_l for k in patterns):
            return p
    return 'unknown'


# ============== 默认 Prompts ==============
DEFAULT_PROMPTS = {
    "brief": "请总结：标题{title}，描述{desc}，内容{content}。格式：## 摘要\n- 要点",
    "detailed": "请详细分析：标题{title}，作者{author}，播放{views}，点赞{likes}。输出：## 摘要\n## 要点\n## 结论",
    "timestamp": "提取时间戳要点：标题{title}，内容{content}。格式：## 总结\n- [时间] 要点",
    "sentiment": "分析情感：标题{title}，弹幕{content}。输出：## 情感分析\n- 倾向\n- 主要情绪",
    "trend": "分析趋势：标题{title}，播放{views}。输出：## 趋势分析\n- 类型\n- 热门原因\n- 启示"
}


# ============== YouTube 提取器 ==============
class YouTubeExtractor:
    @staticmethod
    @handle_errors(default_return=None)
    @retry(max_attempts=3, delay=2.0)
    def extract_video_id(url: str) -> Optional[str]:
        m = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url) or re.search(r'youtu\.be\/([0-9A-Za-z_-]{11})', url)
        return m.group(1) if m else None
    
    @staticmethod
    @handle_errors(default_return=None)
    @retry(max_attempts=3, delay=2.0)
    def get_transcript(video_id: str, langs: List[str] = None) -> Dict:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        lst = api.list(video_id)
        for lang in langs or ['en', 'zh-Hans']:
            try:
                tr = lst.find_transcript([lang])
                data = tr.fetch()
                return {'text': ' '.join(getattr(data, 'text_entries', [str(data)])), 'language': lang}
            except: continue
        raise ValueError("无法获取字幕")


# ============== Bilibili 提取器 ==============
BILIBILI_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}

class BilibiliExtractor:
    @staticmethod
    @handle_errors(default_return=None)
    def extract_bvid(url: str) -> Optional[str]:
        m = re.search(r'BV[A-Za-z0-9]{10}', url)
        return m.group(0) if m else None
    
    @staticmethod
    @handle_errors(default_return=None)
    @retry(max_attempts=3, delay=1.0)
    def get_video_info(bvid: str) -> Dict:
        r = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=BILIBILI_HEADERS, timeout=10)
        d = r.json()
        if d.get('code') != 0: raise ValueError(d.get('message'))
        info = d['data']
        return {'bvid': info['bvid'], 'title': info['title'], 'owner': info['owner']['name'], 
                'cid': info['cid'], 'duration': info['duration'], 'stat': info['stat'], 'desc': info['desc']}
    
    @staticmethod
    @handle_errors(default_return={"has_subtitle": False})
    @retry(max_attempts=2, delay=1.0)
    def get_subtitles(bvid: str, cid: int) -> Dict:
        r = requests.get(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", headers=BILIBILI_HEADERS, timeout=10)
        d = r.json()
        if d.get('code') != 0: return {"has_subtitle": False}
        sub = d.get('data', {}).get('subtitle', {}).get('subtitles', [])
        if not sub: return {"has_subtitle": False}
        return {"has_subtitle": True, "subtitles": sub}
    
    @staticmethod
    @handle_errors(default_return=[])
    @retry(max_attempts=3, delay=1.0)
    def get_danmaku(cid: int) -> List[Dict]:
        r = requests.get(f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}", headers=BILIBILI_HEADERS, timeout=10)
        try: content = gzip.decompress(r.content)
        except: content = r.content
        root = ET.fromstring(content)
        result = []
        for d in root.findall('.//d'):
            p_str = d.get('p', '')
            if not p_str:
                continue
            p = p_str.split(',')
            if len(p) >= 1:
                try:
                    result.append({'time': float(p[0]), 'text': d.text or ''})
                except:
                    pass
        return result
    
    @staticmethod
    @handle_errors(default_return=([], {"total":0,"kept":0}))
    def clean_danmaku(danmaku: List[Dict]) -> Tuple[List[Dict], Dict]:
        return DanmakuCleaner.clean(danmaku)


# ============== 通用提取器 ==============
class GenericExtractor:
    @staticmethod
    @handle_errors(default_return={})
    def get_info(url: str, platform: str = None) -> Dict:
        p = platform or detect_platform(url)
        return {'id': url, 'url': url, 'title': f'{p} 内容', 'platform': p}


# ============== 主总结器 ==============
class VideoSummarizer:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.api_key = self.config.get('api_key') or os.getenv('MINIMAX_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.api_url = self.config.get('api_url') or os.getenv('VIDEO_SUMMARIZER_API_URL') or 'https://api.minimaxi.com/v1/chat/completions'
        self.model = self.config.get('model') or os.getenv('VIDEO_SUMMARIZER_MODEL') or 'MiniMax-M2.1'
        self.prompts = DEFAULT_PROMPTS.copy()
    
    @handle_errors(default_return={'error': 'failed'})
    def process(self, url: str, format: str = 'brief', prompt: str = None, max_len: int = 500,
                clean: bool = True, use_sub: bool = True) -> Dict:
        platform = detect_platform(url)
        logger.info(f"处理 {platform} 视频: {url[:50]}...")
        
        with Timer(f"提取 {platform}"):
            if platform == 'youtube':
                vid = YouTubeExtractor.extract_video_id(url)
                if not vid: return {'error': '无法解析视频ID'}
                tr = YouTubeExtractor.get_transcript(vid)
                content = tr['text']
                info = {'id': vid, 'url': url, 'platform': platform, 'content_type': '字幕'}
            elif platform == 'bilibili':
                bv = BilibiliExtractor.extract_bvid(url)
                info = BilibiliExtractor.get_video_info(bv) if bv else {'error': '无法解析BV号'}
                content = ''
                if use_sub:
                    sub = BilibiliExtractor.get_subtitles(info.get('bvid'), info.get('cid'))
                    if sub.get('has_subtitle'): content = sub.get('subtitle_text', '')
                if not content:
                    dm = BilibiliExtractor.get_danmaku(info.get('cid'))
                    if clean:
                        dm, _ = BilibiliExtractor.clean_danmaku(dm)
                    content = ' '.join([d['text'] for d in dm[:500]])
            else:
                info = GenericExtractor.get_info(url, platform)
                content = info.get('desc', info.get('title', ''))
        
        with Timer("LLM 分析"):
            prompt_text = (prompt or self.prompts.get(format, self.prompts['brief'])).format(
                title=info.get('title',''), author=info.get('owner',''),
                desc=info.get('desc',''), views=info.get('stat',{}).get('view',0),
                likes=info.get('stat',{}).get('like',0),
                content=content[:2000].replace('{','{{').replace('}','}}'),
                max_length=max_len
            )
            
            if not self.api_key:
                summary = f"⚠️ 未配置 API Key\n\n视频信息：{json.dumps(info, ensure_ascii=False, indent=2)}"
            else:
                try:
                    r = requests.post(self.api_url, 
                        headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                        json={'model': self.model, 'messages': [{'role': 'user', 'content': prompt_text}], 'max_tokens': 2000}, timeout=60)
                    r.raise_for_status()
                    summary = r.json()['choices'][0]['message']['content']
                except Exception as e:
                    summary = f"❌ API 错误: {e}\n\n视频信息：{json.dumps(info, ensure_ascii=False, indent=2)}"
        
        logger.success("处理完成")
        return {'platform': platform, 'video_info': info, 'summary': summary, 'format': format, 'timestamp': datetime.now().isoformat()}


# ============== 便捷函数 ==============
def summarize(url: str, format: str = 'brief', prompt: str = None, max_length: int = 500,
             api_key: str = None, api_url: str = None, model: str = None,
             use_subtitle: bool = True, clean_danmaku: bool = True) -> Dict:
    """总结视频"""
    s = VideoSummarizer({'api_key': api_key, 'api_url': api_url, 'model': model})
    return s.process(url, format, prompt, max_length, clean_danmaku, use_subtitle)


def detect(url: str) -> str:
    """检测平台"""
    return detect_platform(url)


def clean_danmaku_text(text: str) -> str:
    """清洗弹幕文本"""
    dm = [{'text': text}]
    cleaned, _ = DanmakuCleaner.clean(dm)
    return ' '.join([d['text'] for d in cleaned])


def get_tool_definition() -> Dict:
    return {"name": "summarize_video", "description": "Summarize video content",
            "inputSchema": {"type": "object", "properties": {
                "url": {"type": "string"}, "format": {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                "prompt": {"type": "string"}, "max_length": {"type": "integer"},
                "api_key": {"type": "string"}, "api_url": {"type": "string"}, "model": {"type": "string"}
            }, "required": ["url"]}}


def get_all_tools() -> list:
    return [
        {"name": "summarize_video", "description": "Summarize video content",
         "inputSchema": {"type": "object", "properties": {
            "url": {"type": "string"}, "format": {"type": "string"}, "prompt": {"type": "string"},
            "max_length": {"type": "integer"}, "api_key": {"type": "string"}
         }, "required": ["url"]}},
        {"name": "detect_platform", "description": "Detect platform of URL",
         "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
        {"name": "list_platforms", "description": "List all platforms", "inputSchema": {"type": "object", "properties": {}}}
    ]


__all__ = ['summarize', 'detect', 'clean_danmaku_text', 'VideoSummarizer', 
           'get_tool_definition', 'get_all_tools', 'logger', 'Timer']

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='🎬 Video Summarizer')
    parser.add_argument('url', help='Video URL')
    parser.add_argument('-f', '--format', choices=['brief','detailed','timestamp','sentiment','trend'], default='brief')
    parser.add_argument('-p', '--prompt')
    args = parser.parse_args()
    
    r = summarize(args.url, args.format, args.prompt)
    print('\n' + '='*50)
    print(r.get('summary', r.get('error', '错误')))
    print('='*50)
