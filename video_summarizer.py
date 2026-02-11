#!/usr/bin/env python3
"""
Video Summarizer - Multi-Platform Video Content Analyzer
支持 YouTube、B站等视频平台的字幕/弹幕总结工具

Features:
- 多平台支持（YouTube、B站）
- 字幕/弹幕内容分析
- 自定义 Prompt
- 灵活 API 配置
"""

import os
import sys
import argparse
import json
import requests
import gzip
import xml.etree.ElementTree as ET
import re
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Callable, Tuple
from pathlib import Path
from collections import Counter


# ============== 弹幕清洗器 ==============
class DanmakuCleaner:
    """弹幕清洗器 - 去除无意义内容"""
    
    # 无意义弹幕模式
    PATTERNS = [
        r'^[\d\.\,\-\+\=\s]+$',           # 纯数字/符号
        r'^[\uD83C-\uDBFF\uDC00-\uDFFF]+$',  # 单独表情
        r'^.{1,2}$',                       # 少于3字符
        r'^[\w\s]{1,5}$',                  # 极短英文/数字
        r'^(he|hi|ok|yes|no|up|666)+$',   # 常见刷屏词
    ]
    
    # 保留模式（高价值弹幕）
    KEEP_PATTERNS = [
        r'[\u4e00-\u9fff]{2,}',            # 2个以上中文字
        r'[，。！？\.\!\?]{2,}',            # 有标点的完整句
        r'笑|哭|泪|牛逼|顶|赞|帅|美|可爱|哈哈|呜呜',  # 情感词
        r'\d{1,2}:\d{2}',                  # 时间戳
        r'\[\S+\]',                        # 括号内容（如[支持]）
    ]
    
    @classmethod
    def clean(cls, danmaku: List[Dict], 
              remove_short: bool = True,
              remove_spam: bool = True,
              min_length: int = 2,
              max_length: int = 50) -> Tuple[List[Dict], Dict]:
        """
        清洗弹幕
        
        Args:
            danmaku: 原始弹幕列表
            remove_short: 去除极短弹幕
            remove_spam: 去除刷屏内容
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            (清洗后弹幕, 统计信息)
        """
        cleaned = []
        stats = {
            "total": len(danmaku),
            "removed_short": 0,
            "removed_spam": 0,
            "removed_pattern": 0,
            "kept": 0
        }
        
        # 统计刷屏内容
        if remove_spam:
            text_counter = Counter([d['text'] for d in danmaku])
            spam_threshold = max(3, len(danmaku) // 100)  # 超过此数量视为刷屏
            spam_texts = {text for text, count in text_counter.items() 
                         if count >= spam_threshold}
        else:
            spam_texts = set()
        
        for d in danmaku:
            text = d.get('text', '').strip()
            length = len(text)
            
            # 长度过滤
            if length < min_length or length > max_length:
                stats["removed_short"] += 1
                continue
            
            # 刷屏过滤
            if text in spam_texts:
                stats["removed_spam"] += 1
                continue
            
            # 模式过滤（去除无意义）
            is_meaningless = True
            for pattern in cls.KEEP_PATTERNS:
                if re.search(pattern, text):
                    is_meaningless = False
                    break
            
            if is_meaningless:
                # 检查是否匹配无意义模式
                for pattern in cls.PATTERNS:
                    if re.match(pattern, text):
                        stats["removed_pattern"] += 1
                        break
                else:
                    # 什么都没匹配到，也可能是无意义的
                    if not re.search(r'[\u4e00-\u9fff]', text):
                        stats["removed_pattern"] += 1
                        continue
            
            cleaned.append({
                'time': d.get('time', 0),
                'text': text,
                'hash': hashlib.md5(text.encode()).hexdigest()[:8]
            })
            stats["kept"] += 1
        
        return cleaned, stats
    
    @classmethod
    def extract_keywords(cls, danmaku: List[Dict], top_n: int = 20) -> List[Tuple[str, int]]:
        """提取高频词"""
        stop_words = {'的', '是', '了', '在', '我', '有', '和', '就', '不', '人', '都', '一',
                     '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
                     '没有', '看', '好', '自己', '这', '那', '什么', '这个', '那个'}
        
        word_freq = Counter()
        for d in danmaku:
            text = d.get('text', '')
            # 提取中文词
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
            for word in words:
                if word not in stop_words:
                    word_freq[word] += 1
        
        return word_freq.most_common(top_n)
    
    @classmethod
    def extract_emotions(cls, danmaku: List[Dict]) -> Dict:
        """情感分析"""
        emotions = {
            'positive': 0,    # 正面
            'negative': 0,    # 负面
            'neutral': 0,     # 中性
            'funny': 0,       # 搞笑
            'moved': 0,       # 感动
            'surprised': 0,   # 惊讶
        }
        
        patterns = {
            'positive': r'赞|顶|好|棒|帅|美|爱|支持|加油|牛',
            'negative': r'差|烂|丑|垃圾|失望|无聊|困|睡着',
            'funny': r'笑|哈哈|嘻嘻|逗|搞笑|有趣|乐',
            'moved': r'泪|哭|感动|戳|暖|戳心|破防',
            'surprised': r'卧槽|卧操|卧槽|震惊|惊了|牛逼|牛',
        }
        
        for d in danmaku:
            text = d.get('text', '')
            matched = False
            for emotion, pattern in patterns.items():
                if re.search(pattern, text):
                    emotions[emotion] += 1
                    matched = True
            if not matched:
                emotions['neutral'] += 1
        
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: f"{v/total*100:.1f}%" for k, v in emotions.items()}
        
        return emotions


# ============== 平台检测 ==============
def detect_platform(url: str) -> str:
    """检测视频平台"""
    url_lower = url.lower()
    
    # 视频平台
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'bilibili.com' in url_lower or 'b站' in url:
        return 'bilibili'
    elif 'tiktok.com' in url_lower or 'douyin' in url_lower:
        return 'douyin'
    elif 'kuaishou.com' in url_lower or '快手' in url:
        return 'kuaishou'
    elif 'ixigua.com' in url_lower or '西瓜视频' in url:
        return 'xigua'
    elif 'twitch.tv' in url_lower:
        return 'twitch'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    
    # 社交媒体
    elif 'weibo.com' in url_lower:
        return 'weibo'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'xiaohongshu.com' in url_lower or '小红书' in url:
        return 'xiaohongshu'
    elif 'zhihu.com' in url_lower:
        return 'zhihu'
    
    # 音乐平台
    elif 'music.163.com' in url_lower:
        return 'netease'
    elif 'qq.com' in url_lower and 'music' in url_lower:
        return 'qqmusic'
    elif 'soundcloud.com' in url_lower:
        return 'soundcloud'
    elif '.rss' in url_lower or 'podcast' in url_lower:
        return 'podcast'
    
    # 电商平台
    elif 'taobao.com' in url_lower or '天猫' in url:
        return 'taobao'
    elif 'tmall.com' in url_lower:
        return 'tmall'
    elif 'jd.com' in url_lower or '京东' in url:
        return 'jd'
    elif 'dewu.com' in url_lower or '得物' in url:
        return 'dewu'
    elif 'zhuanzhuan.com' in url_lower or '转转' in url:
        return 'zhuanzhuan'
    elif 'xianyu.com' in url_lower or '闲鱼' in url:
        return 'xianyu'
    elif 'amazon.' in url_lower:
        return 'amazon'
    
    else:
        return 'unknown'


# ============== 默认 Prompts ==============
DEFAULT_PROMPTS = {
    "brief": """请总结以下视频内容（{platform}）：

标题：{title}
描述：{desc}
{"弹幕：{danmaku}" if danmaku else "字幕：{subtitle}"}

请用中文回复：
## 摘要
[简短总结，{max_length}字内]
## 关键要点
- [要点1]
- [要点2]
- [要点3]""",

    "detailed": """请详细分析以下视频内容（{platform}）：

【基本信息】
标题：{title}
UP主/作者：{author}
描述：{desc}
时长：{duration}秒
{"弹幕数：{danmaku_count}，样例：{danmaku}" if danmaku else "字幕：{subtitle}"}

【播放数据】
播放：{views:,}
点赞：{likes:,}
{"硬币/分享：{coins}" if coins else ""}

请详细分析：
1. 视频内容是什么？
2. 创作者的风格和亮点？
3. 观众反馈反映了什么？
4. 为什么这个视频受欢迎？
5. 有哪些值得学习的点？

用中文回复，结构化输出。""",

    "timestamp": """从以下视频内容提取时间戳要点（{platform}）：

标题：{title}
{"弹幕样例（按时间）：{danmaku}" if danmaku else "字幕：{subtitle}"}

请输出：
## 一句话总结
[总结]
## 时间戳要点
- [时间] [话题/事件]
- [时间] [话题/事件]
## 核心要点
- [要点1]
- [要点2]
- [要点3]""",

    "sentiment": """分析这个视频的观众情感（{platform}）：

标题：{title}
弹幕/评论：{danmaku}

请分析：
1. 整体情感倾向（正面/负面/中性）
2. 观众的主要情绪反应
3. 是否有争议或负面评论？
4. 互动热度如何？
用中文简洁回答。""",

    "trend": """分析这个视频的趋势特点（{platform}）：

标题：{title}
描述：{desc}
播放数据：{views:,} 播放，{likes:,} 点赞
{"弹幕：{danmaku}" if danmaku else "字幕：{subtitle}"}

请分析：
1. 这个内容属于什么类型/领域？
2. 为什么能获得这么多关注？
3. 反映了什么趋势或热点？
4. 对创作者/行业有什么启示？
用中文详细分析。"""
}


# ============== YouTube 平台 ==============
class YouTubeExtractor:
    """YouTube 视频提取器"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def get_transcript(video_id: str, languages: List[str] = None) -> Dict:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        target_langs = languages or ['en', 'zh-Hans', 'zh-CN', 'zh']
        
        for lang in target_langs:
            try:
                transcript = transcript_list.find_transcript([lang])
                data = transcript.fetch()
                text = ' '.join(data.text_entries) if hasattr(data, 'text_entries') else str(data)
                return {
                    'text': text,
                    'language': lang,
                    'is_generated': transcript.is_generated
                }
            except:
                continue
        
        raise ValueError("无法获取 YouTube 字幕")


# ============== Bilibili 平台 ==============
class BilibiliExtractor:
    """B站视频提取器"""
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    
    @staticmethod
    def extract_bvid(url: str) -> Optional[str]:
        match = re.search(r'BV[A-Za-z0-9]{10}', url)
        return match.group(0) if match else None
    
    @staticmethod
    def get_video_info(bvid: str) -> Dict:
        resp = requests.get(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers=BilibiliExtractor.HEADERS,
            timeout=15
        )
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"API 错误: {data.get('message')}")
        
        info = data["data"]
        return {
            "bvid": info["bvid"],
            "aid": info["aid"],
            "title": info["title"],
            "desc": info["desc"],
            "owner": info["owner"]["name"],
            "owner_face": info["owner"]["face"],
            "cid": info["cid"],
            "duration": info["duration"],
            "pic": info["pic"],
            "stat": info["stat"]
        }
    
    @staticmethod
    def get_subtitles(bvid: str, cid: int) -> Dict:
        """
        获取 B站字幕（CC字幕/自动字幕）
        
        Returns:
            {
                "has_subtitle": bool,
                "subtitles": [{"lang": "zh-CN", "url": "..."}],
                "subtitle_url": str or None,
                "subtitle_text": str or None
            }
        """
        try:
            # 获取字幕列表
            resp = requests.get(
                f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}",
                headers=BilibiliExtractor.HEADERS,
                timeout=10
            )
            data = resp.json()
            
            if data.get("code") != 0:
                return {"has_subtitle": False, "error": data.get("message")}
            
            subtitle_data = data.get("data", {}).get("subtitle")
            if not subtitle_data or not subtitle_data.get("subtitles"):
                return {"has_subtitle": False, "reason": "no_subtitle"}
            
            subtitles = []
            for sub in subtitle_data.get("subtitles", []):
                subtitles.append({
                    "lang": sub.get("lan", "unknown"),
                    "url": sub.get("subtitle_url"),
                    "id": sub.get("id")
                })
            
            # 下载第一个可用字幕
            subtitle_text = None
            for sub in subtitles:
                if sub["url"]:
                    sub_resp = requests.get(
                        f"https:{sub['url']}",
                        timeout=10
                    )
                    try:
                        sub_data = sub_resp.json()
                        # 解析字幕格式
                        lines = []
                        for line in sub_data:
                            if isinstance(line, dict):
                                content = line.get("content", "")
                                if content:
                                    lines.append(content)
                        subtitle_text = " ".join(lines)
                        break
                    except:
                        continue
            
            return {
                "has_subtitle": True,
                "subtitles": subtitles,
                "subtitle_text": subtitle_text,
                "subtitle_url": subtitles[0].get("url") if subtitles else None
            }
        except Exception as e:
            return {"has_subtitle": False, "error": str(e)}
    
    @staticmethod
    def get_danmaku(cid: int) -> List[Dict]:
        """获取弹幕"""
        resp = requests.get(
            f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}",
            headers=BilibiliExtractor.HEADERS,
            timeout=15
        )
        
        try:
            content = gzip.decompress(resp.content)
        except:
            content = resp.content
        
        root = ET.fromstring(content)
        danmaku = []
        
        for d in root.findall(".//d"):
            p = d.get("p", "").split(",")
            if len(p) >= 5:
                danmaku.append({
                    "time": float(p[0]),
                    "text": d.text or ""
                })
        
        return danmaku
    
    @staticmethod
    def clean_danmaku(danmaku: List[Dict], 
                     remove_short: bool = True,
                     remove_spam: bool = True,
                     min_length: int = 2) -> Tuple[List[Dict], Dict]:
        """
        清洗弹幕
        
        Args:
            danmaku: 原始弹幕列表
            remove_short: 去除极短弹幕
            remove_spam: 去除刷屏内容
            min_length: 最小长度
            
        Returns:
            (清洗后弹幕, 统计信息)
        """
        return DanmakuCleaner.clean(
            danmaku, remove_short, remove_spam, min_length
        )


# ============== 抖音/TikTok 平台 ==============
class DouyinExtractor:
    """抖音/TikTok 视频提取器"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """从 URL 提取视频 ID"""
        patterns = [
            r'/video/(\d+)',
            r'v/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取视频信息（模拟）"""
        video_id = DouyinExtractor.extract_video_id(url)
        return {
            'id': video_id,
            'url': url,
            'title': f'抖音视频 {video_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'douyin'
        }


# ============== 西瓜视频 平台 ==============
class XiguaExtractor:
    """西瓜视频提取器"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """提取视频 ID"""
        match = re.search(r'/video/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取视频信息"""
        video_id = XiguaExtractor.extract_video_id(url)
        return {
            'id': video_id,
            'url': url,
            'title': f'西瓜视频 {video_id}',
            'desc': '',
            'author': '未知创作者',
            'platform': 'xigua'
        }


# ============== 微博 平台 ==============
class WeiboExtractor:
    """微博视频提取器"""
    
    @staticmethod
    def extract_status_id(url: str) -> Optional[str]:
        """提取微博 ID"""
        match = re.search(r'/(\d+)/(?:album|video)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取视频信息"""
        status_id = WeiboExtractor.extract_status_id(url)
        return {
            'id': status_id,
            'url': url,
            'title': f'微博视频 {status_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'weibo'
        }


# ============== Twitter/X 平台 ==============
class TwitterExtractor:
    """Twitter/X 视频提取器"""
    
    @staticmethod
    def extract_tweet_id(url: str) -> Optional[str]:
        """提取推文 ID"""
        match = re.search(r'/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取推文信息"""
        tweet_id = TwitterExtractor.extract_tweet_id(url)
        return {
            'id': tweet_id,
            'url': url,
            'title': f'Twitter 推文 {tweet_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'twitter'
        }


# ============== Instagram 平台 ==============
class InstagramExtractor:
    """Instagram 视频提取器"""
    
    @staticmethod
    def extract_media_id(url: str) -> Optional[str]:
        """提取媒体 ID"""
        match = re.search(r'/p/([A-Za-z0-9_-]+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取媒体信息"""
        media_id = InstagramExtractor.extract_media_id(url)
        return {
            'id': media_id,
            'url': url,
            'title': f'Instagram 帖子 {media_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'instagram'
        }


# ============== 快手 平台 ==============
class KuaishouExtractor:
    """快手视频提取器"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """提取视频 ID"""
        match = re.search(r'/video/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取视频信息"""
        video_id = KuaishouExtractor.extract_video_id(url)
        return {
            'id': video_id,
            'url': url,
            'title': f'快手视频 {video_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'kuaishou'
        }


# ============== 小红书 平台 ==============
class XiaohongshuExtractor:
    """小红书笔记提取器"""
    
    @staticmethod
    def extract_note_id(url: str) -> Optional[str]:
        """提取笔记 ID"""
        match = re.search(r'/explore/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/pin/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取笔记信息"""
        note_id = XiaohongshuExtractor.extract_note_id(url)
        return {
            'id': note_id,
            'url': url,
            'title': f'小红书笔记 {note_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'xiaohongshu'
        }


# ============== 知乎 平台 ==============
class ZhihuExtractor:
    """知乎回答提取器"""
    
    @staticmethod
    def extract_answer_id(url: str) -> Optional[str]:
        """提取回答 ID"""
        match = re.search(r'/question/(\d+)/answer/(\d+)', url)
        if match:
            return match.group(2)
        match = re.search(r'/p/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取回答信息"""
        answer_id = ZhihuExtractor.extract_answer_id(url)
        return {
            'id': answer_id,
            'url': url,
            'title': f'知乎回答 {answer_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'zhihu'
        }


# ============== Twitch 平台 ==============
class TwitchExtractor:
    """Twitch 直播提取器"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """提取视频 ID"""
        match = re.search(r'videos/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取视频信息"""
        video_id = TwitchExtractor.extract_video_id(url)
        return {
            'id': video_id,
            'url': url,
            'title': f'Twitch 视频 {video_id}',
            'desc': '',
            'author': '未知主播',
            'platform': 'twitch'
        }


# ============== Vimeo 平台 ==============
class VimeoExtractor:
    """Vimeo 视频提取器"""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """提取视频 ID"""
        match = re.search(r'/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取视频信息"""
        video_id = VimeoExtractor.extract_video_id(url)
        return {
            'id': video_id,
            'url': url,
            'title': f'Vimeo 视频 {video_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'vimeo'
        }


# ============== 网易云音乐 平台 ==============
class NetEaseMusicExtractor:
    """网易云音乐歌曲提取器"""
    
    @staticmethod
    def extract_song_id(url: str) -> Optional[str]:
        """提取歌曲 ID"""
        match = re.search(r'/song/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取歌曲信息"""
        song_id = NetEaseMusicExtractor.extract_song_id(url)
        return {
            'id': song_id,
            'url': url,
            'title': f'网易云音乐 {song_id}',
            'desc': '',
            'author': '未知歌手',
            'platform': 'netease'
        }


# ============== QQ音乐 平台 ==============
class QQMusicExtractor:
    """QQ音乐歌曲提取器"""
    
    @staticmethod
    def extract_song_id(url: str) -> Optional[str]:
        """提取歌曲 ID"""
        match = re.search(r'/song/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取歌曲信息"""
        song_id = QQMusicExtractor.extract_song_id(url)
        return {
            'id': song_id,
            'url': url,
            'title': f'QQ音乐 {song_id}',
            'desc': '',
            'author': '未知歌手',
            'platform': 'qqmusic'
        }


# ============== SoundCloud 平台 ==============
class SoundCloudExtractor:
    """SoundCloud 音频提取器"""
    
    @staticmethod
    def extract_track_id(url: str) -> Optional[str]:
        """提取曲目 ID"""
        match = re.search(r'/(\w+)$', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取曲目信息"""
        track_id = SoundCloudExtractor.extract_track_id(url)
        return {
            'id': track_id,
            'url': url,
            'title': f'SoundCloud {track_id}',
            'desc': '',
            'author': '未知用户',
            'platform': 'soundcloud'
        }


# ============== 淘宝/天猫 平台 ==============
class TaobaoExtractor:
    """淘宝/天猫商品提取器"""
    
    @staticmethod
    def extract_item_id(url: str) -> Optional[str]:
        """提取商品 ID"""
        match = re.search(r'id=(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取商品信息"""
        item_id = TaobaoExtractor.extract_item_id(url)
        return {
            'id': item_id,
            'url': url,
            'title': f'淘宝商品 {item_id}',
            'desc': '',
            'author': '未知店铺',
            'platform': 'taobao'
        }


# ============== 京东 平台 ==============
class JDExtractor:
    """京东商品提取器"""
    
    @staticmethod
    def extract_item_id(url: str) -> Optional[str]:
        """提取商品 ID"""
        match = re.search(r'/(\d+)\.html', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取商品信息"""
        item_id = JDExtractor.extract_item_id(url)
        return {
            'id': item_id,
            'url': url,
            'title': f'京东商品 {item_id}',
            'desc': '',
            'author': '未知店铺',
            'platform': 'jd'
        }


# ============== 得物 平台 ==============
class DewuExtractor:
    """得物商品提取器"""
    
    @staticmethod
    def extract_item_id(url: str) -> Optional[str]:
        """提取商品 ID"""
        match = re.search(r'/goods/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取商品信息"""
        item_id = DewuExtractor.extract_item_id(url)
        return {
            'id': item_id,
            'url': url,
            'title': f'得物商品 {item_id}',
            'desc': '',
            'author': '未知卖家',
            'platform': 'dewu'
        }


# ============== 转转 平台 ==============
class ZhuanzhuanExtractor:
    """转转商品提取器"""
    
    @staticmethod
    def extract_item_id(url: str) -> Optional[str]:
        """提取商品 ID"""
        match = re.search(r'/i/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取商品信息"""
        item_id = ZhuanzhuanExtractor.extract_item_id(url)
        return {
            'id': item_id,
            'url': url,
            'title': f'转转商品 {item_id}',
            'desc': '',
            'author': '未知卖家',
            'platform': 'zhuanzhuan'
        }


# ============== 闲鱼 平台 ==============
class XianyuExtractor:
    """闲鱼商品提取器"""
    
    @staticmethod
    def extract_item_id(url: str) -> Optional[str]:
        """提取商品 ID"""
        match = re.search(r'/(\d+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取商品信息"""
        item_id = XianyuExtractor.extract_item_id(url)
        return {
            'id': item_id,
            'url': url,
            'title': f'闲鱼商品 {item_id}',
            'desc': '',
            'author': '未知卖家',
            'platform': 'xianyu'
        }


# ============== Podcast RSS 平台 ==============
class PodcastExtractor:
    """Podcast RSS 提取器"""
    
    @staticmethod
    def extract_feed_info(url: str) -> Dict:
        """提取播客信息"""
        return {
            'id': url,
            'url': url,
            'title': f'Podcast Feed',
            'desc': '',
            'author': '未知播客',
            'platform': 'podcast'
        }


# ============== 亚马逊 平台 ==============
class AmazonExtractor:
    """亚马逊商品提取器"""
    
    @staticmethod
    def extract_asin(url: str) -> Optional[str]:
        """提取 ASIN"""
        match = re.search(r'/dp/([A-Z0-9]{10})', url)
        return match.group(1) if match else None
    
    @staticmethod
    def get_video_info(url: str) -> Dict:
        """获取商品信息"""
        asin = AmazonExtractor.extract_asin(url)
        return {
            'id': asin,
            'url': url,
            'title': f'Amazon {asin}',
            'desc': '',
            'author': '未知商家',
            'platform': 'amazon'
        }


# ============== 主总结器 ==============
class VideoSummarizer:
    """多平台视频总结器"""
    
    PLATFORMS = {
        # 视频平台
        'youtube': {
            'name': 'YouTube',
            'extractor': YouTubeExtractor,
            'content_type': '字幕',
            'api_required': True
        },
        'bilibili': {
            'name': 'Bilibili',
            'extractor': BilibiliExtractor,
            'content_type': '弹幕',
            'api_required': True
        },
        'douyin': {
            'name': '抖音',
            'extractor': DouyinExtractor,
            'content_type': '描述',
            'api_required': False
        },
        'kuaishou': {
            'name': '快手',
            'extractor': KuaishouExtractor,
            'content_type': '描述',
            'api_required': False
        },
        'xigua': {
            'name': '西瓜视频',
            'extractor': XiguaExtractor,
            'content_type': '描述',
            'api_required': False
        },
        'twitch': {
            'name': 'Twitch',
            'extractor': TwitchExtractor,
            'content_type': '描述',
            'api_required': False
        },
        'vimeo': {
            'name': 'Vimeo',
            'extractor': VimeoExtractor,
            'content_type': '描述',
            'api_required': False
        },
        
        # 社交媒体
        'weibo': {
            'name': '微博',
            'extractor': WeiboExtractor,
            'content_type': '文本',
            'api_required': False
        },
        'twitter': {
            'name': 'Twitter/X',
            'extractor': TwitterExtractor,
            'content_type': '文本',
            'api_required': False
        },
        'instagram': {
            'name': 'Instagram',
            'extractor': InstagramExtractor,
            'content_type': '文本',
            'api_required': False
        },
        'xiaohongshu': {
            'name': '小红书',
            'extractor': XiaohongshuExtractor,
            'content_type': '文本',
            'api_required': False
        },
        'zhihu': {
            'name': '知乎',
            'extractor': ZhihuExtractor,
            'content_type': '回答',
            'api_required': False
        },
        
        # 音乐平台
        'netease': {
            'name': '网易云音乐',
            'extractor': NetEaseMusicExtractor,
            'content_type': '歌曲',
            'api_required': False
        },
        'qqmusic': {
            'name': 'QQ音乐',
            'extractor': QQMusicExtractor,
            'content_type': '歌曲',
            'api_required': False
        },
        'soundcloud': {
            'name': 'SoundCloud',
            'extractor': SoundCloudExtractor,
            'content_type': '音频',
            'api_required': False
        },
        'podcast': {
            'name': 'Podcast',
            'extractor': PodcastExtractor,
            'content_type': 'RSS',
            'api_required': False
        },
        
        # 电商平台
        'taobao': {
            'name': '淘宝',
            'extractor': TaobaoExtractor,
            'content_type': '商品',
            'api_required': False
        },
        'tmall': {
            'name': '天猫',
            'extractor': TaobaoExtractor,
            'content_type': '商品',
            'api_required': False
        },
        'jd': {
            'name': '京东',
            'extractor': JDExtractor,
            'content_type': '商品',
            'api_required': False
        },
        'dewu': {
            'name': '得物',
            'extractor': DewuExtractor,
            'content_type': '商品',
            'api_required': False
        },
        'zhuanzhuan': {
            'name': '转转',
            'extractor': ZhuanzhuanExtractor,
            'content_type': '商品',
            'api_required': False
        },
        'xianyu': {
            'name': '闲鱼',
            'extractor': XianyuExtractor,
            'content_type': '商品',
            'api_required': False
        },
        'amazon': {
            'name': '亚马逊',
            'extractor': AmazonExtractor,
            'content_type': '商品',
            'api_required': False
        }
    }
    
    def __init__(self, config: Dict = None):
        """初始化"""
        if config is None:
            config = {}
        
        self.config = config
        self.api_key = (config.get("api_key") or 
                       os.getenv("MINIMAX_API_KEY") or 
                       os.getenv("OPENAI_API_KEY") or "")
        self.api_url = (config.get("api_url") or 
                       os.getenv("VIDEO_SUMMARIZER_API_URL") or 
                       "https://api.minimaxi.com/v1/chat/completions")
        self.model = (config.get("model") or 
                    os.getenv("VIDEO_SUMMARIZER_MODEL") or 
                    "MiniMax-M2.1")
        
        # 加载自定义 prompts
        self.prompts = DEFAULT_PROMPTS.copy()
        if config.get("prompts"):
            self.prompts.update(config["prompts"])
    
    def add_custom_prompt(self, name: str, template: str):
        """添加自定义 prompt"""
        self.prompts[name] = template
    
    def extract_content(self, url: str, 
                        clean_danmaku: bool = True,
                        use_subtitle: bool = True) -> Dict:
        """
        提取视频内容
        
        Args:
            url: 视频链接
            clean_danmaku: 是否清洗弹幕
            use_subtitle: 是否优先使用字幕（B站）
        """
        platform = detect_platform(url)
        
        if platform not in self.PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}")
        
        extractor = self.PLATFORMS[platform]['extractor']
        
        if platform == 'youtube':
            video_id = extractor.extract_video_id(url)
            info = {'id': video_id, 'url': url}
            transcript = extractor.get_transcript(video_id)
            return {
                'platform': platform,
                'info': info,
                'content': transcript['text'],
                'content_type': '字幕',
                'language': transcript['language'],
                'danmaku_count': 0
            }
        
        elif platform == 'bilibili':
            bvid = extractor.extract_bvid(url)
            info = extractor.get_video_info(bvid)
            
            # 优先使用字幕
            content_text = ""
            content_type = "弹幕"
            subtitle_info = None
            
            if use_subtitle:
                subtitle_info = extractor.get_subtitles(bvid, info['cid'])
                if subtitle_info.get("has_subtitle") and subtitle_info.get("subtitle_text"):
                    content_text = subtitle_info["subtitle_text"]
                    content_type = "字幕"
            
            # 如果没有字幕，使用弹幕
            if not content_text:
                danmaku = extractor.get_danmaku(info['cid'])
                
                # 弹幕清洗
                clean_data, stats = extractor.clean_danmaku(danmaku)
                content_text = " ".join([d['text'] for d in clean_data])
                
                return {
                    'platform': platform,
                    'info': info,
                    'content': content_text,
                    'content_type': content_type,
                    'language': 'zh',
                    'danmaku_count': len(danmaku),
                    'danmaku_cleaned': len(clean_data),
                    'danmaku_stats': stats,
                    'subtitle_info': subtitle_info
                }
            
            return {
                'platform': platform,
                'info': info,
                'content': content_text,
                'content_type': content_type,
                'language': 'zh',
                'danmaku_count': 0,
                'subtitle_info': subtitle_info
            }
        
        # 其他平台（抖音、西瓜、微博、Twitter、Instagram）
        else:
            info = extractor.get_video_info(url)
            return {
                'platform': platform,
                'info': info,
                'content': info.get('desc', ''),
                'content_type': self.PLATFORMS[platform]['content_type'],
                'language': 'unknown',
                'danmaku_count': 0
            }
    
    def summarize(self, content: Dict, prompt_type: str = "brief", 
                 custom_prompt: str = None, max_length: int = 500) -> str:
        """生成总结"""
        
        # 构建变量（转义花括号）
        platform_info = self.PLATFORMS.get(content['platform'], {})
        info = content['info']
        
        # 安全转义文本
        danmaku_text = (content.get('content', '') or '')[:2000]
        danmaku_text = danmaku_text.replace('{', '{{').replace('}', '}}')
        subtitle_text = danmaku_text
        
        # 只取安全的字段，不用 danmaku 变量
        variables = {
            'platform': platform_info.get('name', content['platform']),
            'title': info.get('title', ''),
            'author': info.get('owner', info.get('name', '')),
            'desc': info.get('desc', ''),
            'duration': info.get('duration', 0),
            'views': info.get('stat', {}).get('view', 0),
            'likes': info.get('stat', {}).get('like', 0),
            'coins': info.get('stat', {}).get('coin', 0),
            'max_length': max_length,
        }
        
        # 获取内容文本
        content_text = (content.get('content', '') or '')[:3000]
        
        # 替换变量
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self.prompts.get(prompt_type, self.prompts["brief"])
        
        # 简单替换
        prompt = prompt.replace('{platform}', variables['platform'])
        prompt = prompt.replace('{title}', variables['title'])
        prompt = prompt.replace('{author}', variables['author'])
        prompt = prompt.replace('{desc}', variables['desc'])
        prompt = prompt.replace('{duration}', str(variables['duration']))
        prompt = prompt.replace('{views}', str(variables['views']))
        prompt = prompt.replace('{likes}', str(variables['likes']))
        prompt = prompt.replace('{coins}', str(variables['coins']))
        prompt = prompt.replace('{max_length}', str(variables['max_length']))
        
        # 替换 danmaku/subtitle
        safe_content = content_text.replace('{', '{{').replace('}', '}}')
        prompt = prompt.replace('{danmaku}', safe_content)
        prompt = prompt.replace('{subtitle}', safe_content)
        
        # 调用 API
        if not self.api_key:
            return f"⚠️ 未配置 API Key\n\n视频信息：\n{json.dumps(content['info'], ensure_ascii=False, indent=2)}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.5
        }
        
        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"❌ API 错误: {e}"
    
    def process(self, url: str, prompt_type: str = "brief", 
                custom_prompt: str = None, max_length: int = 500, 
                save: bool = True,
                clean_danmaku: bool = True,
                use_subtitle: bool = True) -> Dict:
        """
        完整处理流程
        
        Args:
            url: 视频链接
            prompt_type: 总结格式
            custom_prompt: 自定义 prompt
            max_length: 最大长度
            save: 是否保存
            clean_danmaku: 是否清洗弹幕
            use_subtitle: 是否优先使用字幕（B站）
        """
        platform = detect_platform(url)
        platform_name = self.PLATFORMS.get(platform, {}).get('name', platform)
        
        print(f"🎬 提取 {platform_name} 视频内容...")
        content = self.extract_content(
            url, 
            clean_danmaku=clean_danmaku,
            use_subtitle=use_subtitle
        )
        print(f"✅ 获取到: {content['info'].get('title', content['info'].get('id', ''))}")
        
        # 显示统计信息
        if content.get('danmaku_stats'):
            stats = content['danmaku_stats']
            print(f"📊 弹幕统计: 总计{stats['total']} → 保留{stats['kept']} (移除{stats['total']-stats['kept']})")
        
        if content.get('subtitle_info'):
            if content['subtitle_info'].get('has_subtitle'):
                print(f"✅ 使用字幕内容")
            else:
                print(f"ℹ️ 无字幕，使用弹幕")
        
        print(f"✍️ 生成总结...")
        summary = self.summarize(content, prompt_type, custom_prompt, max_length)
        
        output = {
            "platform": platform,
            "video_info": content['info'],
            "content_type": content['content_type'],
            "summary": summary,
            "prompt_type": prompt_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加额外信息
        if content.get('danmaku_stats'):
            output['danmaku_stats'] = content['danmaku_stats']
        if content.get('subtitle_info'):
            output['subtitle_info'] = content['subtitle_info']
        
        if save:
            video_id = content['info'].get('bvid') or content['info'].get('id', 'unknown')
            filename = f"video-summary-{video_id}.md"
            self._save_to_file(output, filename)
            output["saved_file"] = filename
        
        return output
    
    def _save_to_file(self, output: Dict, filename: str):
        """保存到文件"""
        info = output['video_info']
        
        # 构建额外信息
        extra_info = []
        if output.get('danmaku_stats'):
            stats = output['danmaku_stats']
            extra_info.append(f"- **弹幕统计**: {stats['kept']}/{stats['total']} (保留率{stats['kept']/max(1,stats['total'])*100:.1f}%)")
        if output.get('subtitle_info'):
            sub = output['subtitle_info']
            if sub.get('has_subtitle'):
                extra_info.append(f"- **字幕**: 已获取")
        
        content = f"""# {info.get('title', '视频总结')}

## 视频信息
- **平台**: {output['platform']}
- **标题**: {info.get('title', '')}
- **作者**: {info.get('owner', info.get('name', ''))}
- **链接**: {info.get('url', '')}
{"- **弹幕数**: " + str(output.get('danmaku_count', 'N/A')) if output.get('danmaku_count') else ""}
- **内容类型**: {output['content_type']}
- **生成时间**: {output['timestamp']}
{chr(10).join(['  ' + line for line in extra_info]) if extra_info else ""}

---

{output['summary']}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已保存: {filename}")


# ============== CLI ==============
def main():
    parser = argparse.ArgumentParser(
        description="🎬 多平台视频总结器 - YouTube/B站",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # YouTube 简要总结
  python video_summarizer.py "https://youtube.com/watch?v=xxx" -f brief
  
  # B站 详细分析（自动清洗弹幕）
  python video_summarizer.py "https://bilibili.com/video/BVxxx" -f detailed
  
  # B站 强制使用弹幕（不洗）
  python video_summarizer.py "https://bilibili.com/video/BVxxx" --no-clean
  
  # 自定义 prompt
  python video_summarizer.py "URL" -p "请用100字总结这个视频"
  
  # 情感分析
  python video_summarizer.py "URL" -f sentiment

支持的平台:
  - YouTube (字幕分析)
  - Bilibili (弹幕 + 字幕分析)
        """
    )
    
    parser.add_argument("url", help="视频链接")
    parser.add_argument("-f", "--format", 
                       choices=["brief", "detailed", "timestamp", "sentiment", "trend"],
                       default="brief",
                       help="总结格式")
    parser.add_argument("-p", "--prompt", help="自定义 prompt 模板")
    parser.add_argument("-m", "--max-length", type=int, default=500, help="最大长度")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--api-url", help="API URL")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件")
    parser.add_argument("--no-clean", action="store_true", help="不清洗弹幕")
    parser.add_argument("--no-subtitle", action="store_true", help="不使用字幕（强制用弹幕）")
    parser.add_argument("--list-prompts", action="store_true", help="列出所有可用 prompt")
    
    args = parser.parse_args()
    
    # 列出 prompts
    if args.list_prompts:
        print("可用 Prompt 类型:")
        for name in DEFAULT_PROMPTS:
            print(f"  - {name}")
        return
    
    # 构建配置
    config = {}
    if args.api_key:
        config["api_key"] = args.api_key
    if args.api_url:
        config["api_url"] = args.api_url
    if args.model:
        config["model"] = args.model
    
    try:
        s = VideoSummarizer(config)
        result = s.process(
            args.url, 
            args.format, 
            args.prompt, 
            args.max_length,
            save=not args.no_save,
            clean_danmaku=not args.no_clean,
            use_subtitle=not args.no_subtitle
        )
        print(f"\n✅ 完成!\n\n{result['summary'][:600]}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
