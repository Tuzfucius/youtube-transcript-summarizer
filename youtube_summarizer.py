#!/usr/bin/env python3
"""
YouTube Transcript Summarizer
支持自定义 API 配置的 YouTube 视频字幕总结工具
"""

import os
import sys
import argparse
import json
import requests
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# 尝试导入依赖
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("❌ 缺少依赖: youtube-transcript-api")
    print("   安装: pip install youtube-transcript-api requests")
    sys.exit(1)


class Config:
    """配置管理"""
    
    @staticmethod
    def load(config_path: str = None) -> Dict:
        """加载配置"""
        # 默认路径
        if not config_path:
            config_path = os.getenv("YOUTUBE_SUMMARIZER_CONFIG") or ".youtube-summarizer.json"
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def get_api_key(config: Dict) -> str:
        """获取 API Key（优先级：配置 > 环境变量 > 默认）"""
        return (config.get("api_key") or 
                os.getenv("MINIMAX_API_KEY") or 
                os.getenv("OPENAI_API_KEY") or 
                "")
    
    @staticmethod
    def get_api_url(config: Dict) -> str:
        """获取 API URL（优先级：配置 > 默认）"""
        return (config.get("api_url") or 
                os.getenv("YOUTUBE_SUMMARIZER_API_URL") or 
                "https://api.minimaxi.com/v1/chat/completions")
    
    @staticmethod
    def get_model(config: Dict) -> str:
        """获取模型"""
        return config.get("model") or os.getenv("YOUTUBE_SUMMARIZER_MODEL") or "MiniMax-M2.1"


class YouTubeSummarizer:
    """YouTube 字幕总结器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化
        
        Args:
            config: 可选的配置字典，若为 None 则从配置文件加载
        """
        if config is None:
            config = Config.load()
        
        self.config = config
        self.api_key = Config.get_api_key(config)
        self.api_url = Config.get_api_url(config)
        self.model = Config.get_model(config)
    
    def extract_video_id(self, url: str) -> str:
        """从 URL 提取视频 ID"""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"无法解析视频 ID: {url}")
    
    def get_transcript(self, video_id: str, languages: List[str] = None) -> Dict:
        """获取字幕"""
        transcript_api = YouTubeTranscriptApi()
        transcript_list = transcript_api.list(video_id)
        target_langs = languages or ['en', 'zh-Hans', 'zh-CN', 'zh']
        
        for lang in target_langs:
            try:
                transcript = transcript_list.find_transcript([lang])
                data = transcript.fetch()
                text = ' '.join(data.text_entries) if hasattr(data, 'text_entries') else str(data)
                return {'text': text, 'language': lang, 'is_generated': transcript.is_generated}
            except:
                continue
        raise ValueError("无法获取视频字幕")
    
    def summarize(self, text: str, format: str = "brief", max_length: int = 500) -> str:
        """使用 LLM 分析字幕"""
        
        if not self.api_key:
            raise ValueError("需要设置 API Key，可通过配置文件、环境变量或直接传入")
        
        # 构建 prompt
        if format == "brief":
            prompt = f"""请总结以下 YouTube 字幕（{max_length}字内）：

{text[:5000]}

回复格式：
## 摘要
[简短总结]
## 关键要点
- [要点1]
- [要点2]
- [要点3]"""
        elif format == "detailed":
            prompt = f"""请详细总结以下 YouTube 字幕：

{text[:5000]}

回复格式：
## 完整摘要
[详细总结]
## 核心要点
1. [要点1]
2. [要点2]
3. [要点3]
4. [要点4]
5. [要点5]
## 结论
[结论或建议]"""
        else:  # timestamp
            prompt = f"""从以下字幕提取时间戳要点：

{text[:5000]}

回复格式：
## 一句话总结
[总结]
## 时间戳要点
- [03:12] [话题]
- [08:45] [观点]
## 核心要点
- [要点1]
- [要点2]
- [要点3]"""
        
        # 调用 API
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
            result_data = resp.json()
            return result_data['choices'][0]['message']['content']
        except Exception as e:
            raise ValueError(f"API 调用失败: {e}")
    
    def process_video(self, url: str, format: str = "brief", 
                      max_length: int = 500, save: bool = True) -> Dict:
        """完整流程"""
        video_id = self.extract_video_id(url)
        print(f"📹 获取字幕中...")
        transcript_info = self.get_transcript(video_id)
        print(f"✍️ 分析中...")
        
        summary = self.summarize(transcript_info['text'], format, max_length)
        
        output = {
            "video_info": {
                "id": video_id,
                "url": url,
                "language": transcript_info['language']
            },
            "summary": summary,
            "format": format,
            "timestamp": datetime.now().isoformat()
        }
        
        if save:
            filename = f"youtube-summary-{video_id}.md"
            self._save_to_file(output, filename)
            output["saved_file"] = filename
        
        return output
    
    def _save_to_file(self, output: Dict, filename: str):
        """保存到文件"""
        content = f"""# YouTube 视频总结

## 视频信息
- **链接**: {output['video_info']['url']}
- **ID**: {output['video_info']['id']}
- **字幕语言**: {output['video_info']['language']}
- **生成时间**: {output['timestamp']}

---

{output['summary']}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已保存: {filename}")


def main():
    """CLI"""
    parser = argparse.ArgumentParser(description="YouTube 字幕总结工具")
    parser.add_argument("url", help="YouTube 链接")
    parser.add_argument("-f", "--format", choices=["brief", "detailed", "timestamp"], default="brief")
    parser.add_argument("-m", "--max-length", type=int, default=500)
    parser.add_argument("-c", "--config", help="配置文件路径")
    parser.add_argument("--api-key", help="API Key（覆盖配置）")
    parser.add_argument("--api-url", help="API URL（覆盖配置）")
    parser.add_argument("--model", help="模型名称（覆盖配置）")
    parser.add_argument("--no-save", action="store_true", help="不保存到文件")
    args = parser.parse_args()
    
    # 构建配置
    config = {}
    if args.config:
        config = Config.load(args.config)
    if args.api_key:
        config["api_key"] = args.api_key
    if args.api_url:
        config["api_url"] = args.api_url
    if args.model:
        config["model"] = args.model
    
    try:
        s = YouTubeSummarizer(config)
        result = s.process_video(args.url, args.format, args.max_length, save=not args.no_save)
        print(f"\n✅ 完成!\n\n{result['summary'][:500]}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
