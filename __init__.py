#!/usr/bin/env python3
"""
Video Summarizer - Multi-Platform Video Content Analyzer
支持 45+ 平台的视频内容总结工具

Features:
- 完善的日志系统
- 重试机制
- 错误处理
- 性能监控
- 大模型友好接入
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

# ============== 日志系统 ==============
def setup_logger(name: str = "VideoSummarizer", level: int = logging.INFO, log_file: str = None, log_dir: str = "logs"):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    # 添加 success 方法
    def success(msg):
        logger.log(logging.INFO, f"✅ {msg}")
    logger.success = success
    
    fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
    
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    
    if log_file or log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(exist_ok=True)
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"video_summarizer_{timestamp}.log"
        
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s'))
        logger.addHandler(fh)
    
    return logger

logger = setup_logger()


# ============== 工具函数 ==============
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func):
        import functools
        @functools.wraps(func)
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
                    logger.warning(f"{func.__name__} failed, retry in {current_delay:.1f}s... ({attempt}/{max_attempts})")
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_exc
        return wrapper
    return decorator


def handle_errors(default_return=None, log_error: bool = True):
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
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


def detect(url: str) -> str:
    """检测平台"""
    return detect_platform(url)


# ============== 默认 Prompts ==============
DEFAULT_PROMPTS = {
    "brief": """请总结以下视频内容：

标题：{title}
描述：{desc}
内容：{content}

请用中文回复：
## 摘要
[简短总结，{max_length}字内]
## 关键要点
- [要点1]
- [要点2]
- [要点3]""",

    "detailed": """请详细分析以下视频：

标题：{title}
作者：{author}
描述：{desc}
播放：{views:,}
点赞：{likes:,}

内容：{content}

请详细分析：
1. 视频内容是什么？
2. 创作者的风格和亮点？
3. 观众反馈反映了什么？
4. 为什么受欢迎？
5. 有哪些值得学习的点？

用中文结构化输出。""",

    "timestamp": """从以下内容提取要点：

标题：{title}
内容：{content}

请输出：
## 一句话总结
## 时间戳要点
- [时间] [话题]
## 核心要点
- [要点]""",

    "sentiment": """分析情感：

标题：{title}
弹幕/评论：{content}

请分析：
1. 整体情感倾向
2. 主要情绪反应
3. 互动热度
简洁回答。""",

    "trend": """分析趋势：

标题：{title}
播放：{views:,}
内容：{content}

请分析：
1. 内容类型
2. 热门原因
3. 趋势启示
详细分析。"""
}


# ============== 弹幕清洗 ==============
@handle_errors(default_return=[])
def clean_danmaku(danmaku: List[Dict], min_len: int = 2, max_len: int = 50) -> List[Dict]:
    """清洗弹幕"""
    if not danmaku:
        return []
    
    from collections import Counter
    import re
    
    text_counter = Counter([d.get('text', '') for d in danmaku])
    spam_threshold = max(3, len(danmaku) // 100)
    spam_texts = {t for t, c in text_counter.items() if c >= spam_threshold}
    
    patterns_remove = [r'^[\d\.\,\-\+\=\s]+$', r'^.{1,2}$', r'^[\w\s]{1,5}$']
    patterns_keep = [r'[\u4e00-\u9fff]{2,}', r'[，。！？]{2,}', r'笑|哭|泪|牛逼|顶|赞']
    
    cleaned = []
    for d in danmaku:
        text = d.get('text', '').strip()
        if not text or len(text) < min_len or len(text) > max_len:
            continue
        if text in spam_texts:
            continue
        if any(re.search(p, text) for p in patterns_remove):
            if not any(re.search(p, text) for p in patterns_keep):
                continue
        cleaned.append(d)
    
    logger.info(f"弹幕清洗: {len(danmaku)} → {len(cleaned)} (保留率: {len(cleaned)/max(1,len(danmaku))*100:.1f}%)")
    return cleaned


def clean_danmaku_text(text: str) -> str:
    """清洗弹幕文本"""
    dm = [{'text': text}]
    cleaned = clean_danmaku(dm)
    return ' '.join([d['text'] for d in cleaned])


# ============== 视频提取 ==============
@handle_errors(default_return={'error': 'failed'})
@retry(max_attempts=3, delay=2.0)
def extract_video(url: str, use_subtitle: bool = True, clean_danmaku_flag: bool = True) -> Dict:
    """提取视频内容"""
    import requests
    import gzip
    import xml.etree.ElementTree as ET
    import re
    
    platform = detect_platform(url)
    logger.info(f"提取 {platform} 视频: {url[:50]}...")
    
    if platform == 'youtube':
        m = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url) or re.search(r'youtu\.be\/([0-9A-Za-z_-]{11})', url)
        if not m: return {'error': '无法解析视频ID'}
        video_id = m.group(1)
        
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            lst = api.list(video_id)
            for lang in ['en', 'zh-Hans']:
                try:
                    tr = lst.find_transcript([lang])
                    data = tr.fetch()
                    text = ' '.join(getattr(data, 'text_entries', [str(data)]))
                    return {
                        'platform': 'youtube', 'id': video_id, 'url': url,
                        'content': text, 'content_type': '字幕', 'language': lang
                    }
                except: continue
        except: pass
        
        return {'platform': 'youtube', 'id': video_id, 'url': url, 'content': '', 'content_type': '字幕', 'error': '无字幕'}
    
    elif platform == 'bilibili':
        m = re.search(r'BV[A-Za-z0-9]{10}', url)
        if not m: return {'error': '无法解析BV号'}
        bvid = m.group(0)
        
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
        
        r = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, timeout=10)
        d = r.json()
        if d.get('code') != 0: return {'error': d.get('message')}
        info = d['data']
        cid = info['cid']
        
        content = ""
        if use_subtitle:
            try:
                r = requests.get(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", headers=headers, timeout=10)
                d = r.json()
                subs = d.get('data', {}).get('subtitle', {}).get('subtitles', [])
                if subs:
                    sub_url = f"https:{subs[0].get('subtitle_url')}"
                    r = requests.get(sub_url, timeout=10)
                    sub_data = r.json()
                    content = ' '.join([line.get('content', '') for line in sub_data if isinstance(line, dict)])
            except: pass
        
        if not content:
            r = requests.get(f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}", headers=headers, timeout=10)
            try:
                dm_content = r.content
                # 尝试解压
                try:
                    dm_content = gzip.decompress(dm_content)
                except:
                    pass
                
                # 尝试解析 XML，处理格式错误
                danmaku = []
                try:
                    root = ET.fromstring(dm_content)
                    for d_elem in root.findall(".//d"):
                        p = d_elem.get("p", "").split(",")
                        if len(p) >= 1:
                            try:
                                danmaku.append({'time': float(p[0]), 'text': d_elem.text or ''})
                            except:
                                danmaku.append({'time': 0, 'text': d_elem.text or ''})
                except ET.ParseError as e:
                    # XML 解析错误，尝试清理内容后重试
                    logger.warning(f"弹幕 XML 解析错误，尝试清理: {e}")
                    import re
                    # 清理损坏的 XML 标签
                    cleaned = re.sub(b'<[^>]+>', b'', dm_content)
                    try:
                        content_str = cleaned.decode('utf-8', errors='ignore')
                        # 提取所有文本
                        texts = re.findall(r'>([^<]+)<', content_str)
                        danmaku = [{'time': 0, 'text': t.strip()} for t in texts if t.strip()][:500]
                    except:
                        danmaku = []
                
                if clean_danmaku_flag:
                    danmaku = clean_danmaku(danmaku)
                
                content = ' '.join([d['text'] for d in danmaku[:500]])
            except Exception as e:
                logger.warning(f"弹幕获取失败: {e}")
                content = ""
        
        return {
            'platform': 'bilibili', 'id': bvid, 'url': url,
            'title': info['title'], 'owner': info['owner']['name'],
            'cid': cid, 'duration': info['duration'],
            'views': info['stat']['view'], 'likes': info['stat']['like'],
            'content': content, 'content_type': '字幕' if use_subtitle else '弹幕'
        }
    
    return {'platform': platform, 'id': url, 'url': url, 'title': f'{platform} 内容', 'content': '', 'content_type': '描述'}


# ============== LLM 调用 ==============
@handle_errors(default_return="API failed")
def call_llm(prompt: str, api_key: str = None, api_url: str = None, model: str = None) -> str:
    """调用 LLM"""
    import requests
    
    api_key = api_key or os.getenv('MINIMAX_API_KEY') or os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "⚠️ 未配置 API Key"
    
    api_url = api_url or os.getenv('VIDEO_SUMMARIZER_API_URL') or 'https://api.minimaxi.com/v1/chat/completions'
    model = model or os.getenv('VIDEO_SUMMARIZER_MODEL') or 'MiniMax-M2.1'
    
    try:
        r = requests.post(
            api_url,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 2000, 'temperature': 0.5},
            timeout=60
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return f"❌ API 错误: {e}"


# ============== 主函数 ==============
def summarize(url: str, format: str = 'brief', prompt: str = None,
             max_length: int = 500, api_key: str = None, api_url: str = None,
             model: str = None, use_subtitle: bool = True, 
             clean_danmaku_flag: bool = True) -> Dict:
    """总结视频内容"""
    with Timer(f"处理 {url[:30]}"):
        content_data = extract_video(url, use_subtitle, clean_danmaku_flag)
        content = content_data.get('content', '')[:3000]
        platform = content_data.get('platform', 'unknown')
        
        prompt_template = prompt or DEFAULT_PROMPTS.get(format, DEFAULT_PROMPTS['brief'])
        prompt_text = prompt_template.format(
            title=content_data.get('title', ''),
            author=content_data.get('owner', ''),
            desc=content_data.get('desc', ''),
            views=content_data.get('views', 0),
            likes=content_data.get('likes', 0),
            content=content.replace('{', '{{').replace('}', '}}'),
            max_length=max_length
        )
        
        logger.info(f"调用 LLM 分析...")
        summary = call_llm(prompt_text, api_key, api_url, model)
        
        result = {
            'platform': platform,
            'video_info': {
                'id': content_data.get('id'),
                'url': url,
                'title': content_data.get('title'),
                'owner': content_data.get('owner'),
                'content_type': content_data.get('content_type')
            },
            'summary': summary,
            'format': format,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.success("处理完成")
        return result


# ============== 大模型工具定义 ==============
def get_tool_definition() -> Dict:
    return {
        "name": "summarize_video",
        "description": "Summarize video content from any platform (YouTube, Bilibili, Douyin, Twitter, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Video URL (required)"},
                "format": {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                "prompt": {"type": "string", "description": "Custom prompt"},
                "max_length": {"type": "integer"},
                "api_key": {"type": "string"},
                "api_url": {"type": "string"},
                "model": {"type": "string"}
            },
            "required": ["url"]
        }
    }


def get_all_tools() -> list:
    return [
        {
            "name": "summarize_video",
            "description": "Summarize video content from any platform",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Video URL"},
                    "format": {"type": "string", "enum": ["brief", "detailed", "timestamp", "sentiment", "trend"]},
                    "prompt": {"type": "string"},
                    "max_length": {"type": "integer"},
                    "api_key": {"type": "string"},
                    "api_url": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "detect_platform",
            "description": "Detect platform of a URL",
            "inputSchema": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL"}},
                "required": ["url"]
            }
        },
        {
            "name": "list_platforms",
            "description": "List all supported platforms",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]


# ============== 导出 ==============
__all__ = [
    'summarize', 'extract_video', 'detect', 'detect_platform',
    'clean_danmaku', 'clean_danmaku_text', 'call_llm',
    'get_tool_definition', 'get_all_tools',
    'logger', 'setup_logger', 'Timer', 'retry', 'handle_errors',
    'DEFAULT_PROMPTS'
]

__version__ = "3.8.7"
