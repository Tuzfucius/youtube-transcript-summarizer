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
from datetime import datetime
from typing import Optional, List, Dict, Callable
from pathlib import Path


# ============== 平台检测 ==============
def detect_platform(url: str) -> str:
    """检测视频平台"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'bilibili.com' in url or 'b站' in url.lower():
        return 'bilibili'
    elif 'tiktok.com' in url:
        return 'tiktok'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'instagram.com' in url:
        return 'instagram'
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
    def get_danmaku(cid: int) -> List[Dict]:
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


# ============== 主总结器 ==============
class VideoSummarizer:
    """多平台视频总结器"""
    
    PLATFORMS = {
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
    
    def extract_content(self, url: str) -> Dict:
        """提取视频内容"""
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
                'language': transcript['language']
            }
        
        elif platform == 'bilibili':
            bvid = extractor.extract_bvid(url)
            info = extractor.get_video_info(bvid)
            danmaku = extractor.get_danmaku(info['cid'])
            danmaku_text = ' '.join([d['text'] for d in danmaku[:500]])
            return {
                'platform': platform,
                'info': info,
                'content': danmaku_text,
                'content_type': '弹幕',
                'danmaku_count': len(danmaku),
                'danmaku': danmaku_text[:500],
                'language': 'zh'
            }
    
    def summarize(self, content: Dict, prompt_type: str = "brief", 
                 custom_prompt: str = None, max_length: int = 500) -> str:
        """生成总结"""
        
        # 构建变量
        platform_info = self.PLATFORMS.get(content['platform'], {})
        info = content['info']
        
        variables = {
            'platform': platform_info.get('name', content['platform']),
            'title': info.get('title', ''),
            'author': info.get('owner', info.get('name', '')),
            'desc': info.get('desc', ''),
            'duration': info.get('duration', 0),
            'views': info.get('stat', {}).get('view', 0),
            'likes': info.get('stat', {}).get('like', 0),
            'coins': info.get('stat', {}).get('coin', 0),
            'subtitle': content.get('content', '')[:2000],
            'danmaku': content.get('danmaku', '')[:2000],
            'danmaku_count': content.get('danmaku_count', 0),
            'max_length': max_length,
            **info
        }
        
        # 选择 prompt
        if custom_prompt:
            prompt_template = custom_prompt
        else:
            prompt_template = self.prompts.get(prompt_type, self.prompts["brief"])
        
        # 渲染 prompt
        prompt = prompt_template.format(**variables)
        
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
                save: bool = True) -> Dict:
        """完整处理流程"""
        
        platform = detect_platform(url)
        platform_name = self.PLATFORMS.get(platform, {}).get('name', platform)
        
        print(f"🎬 提取 {platform_name} 视频内容...")
        content = self.extract_content(url)
        print(f"✅ 获取到: {content['info'].get('title', content['info'].get('id', ''))}")
        
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
        
        if save:
            video_id = content['info'].get('bvid') or content['info'].get('id', 'unknown')
            filename = f"video-summary-{video_id}.md"
            self._save_to_file(output, filename)
            output["saved_file"] = filename
        
        return output
    
    def _save_to_file(self, output: Dict, filename: str):
        """保存到文件"""
        info = output['video_info']
        content = f"""# {info.get('title', '视频总结')}

## 视频信息
- **平台**: {output['platform']}
- **标题**: {info.get('title', '')}
- **作者**: {info.get('owner', info.get('name', ''))}
- **链接**: {info.get('url', '')}
{"- **弹幕数**: " + str(output.get('danmaku_count', 'N/A')) if output.get('danmaku_count') else ""}
- **生成时间**: {output['timestamp']}

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
  
  # B站 详细分析
  python video_summarizer.py "https://bilibili.com/video/BVxxx" -f detailed
  
  # 自定义 prompt
  python video_summarizer.py "URL" --prompt "请用100字总结这个视频"
  
  # 情感分析
  python video_summarizer.py "URL" -f sentiment

支持的平台:
  - YouTube (字幕分析)
  - Bilibili (弹幕分析)
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
            save=not args.no_save
        )
        print(f"\n✅ 完成!\n\n{result['summary'][:600]}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
