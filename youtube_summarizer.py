#!/usr/bin/env python3
"""
YouTube Transcript Summarizer
基于字幕的 YouTube 视频总结工具
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# 尝试导入依赖
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("❌ 缺少依赖: youtube-transcript-api")
    print("   安装: pip install youtube-transcript-api openai")
    sys.exit(1)

try:
    import openai
except ImportError:
    print("❌ 缺少依赖: openai")
    print("   安装: pip install openai")
    sys.exit(1)


class YouTubeSummarizer:
    """YouTube 字幕总结器"""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "deepseek"):
        """
        初始化
        
        Args:
            api_key: API Key（优先使用环境变量）
            provider: LLM 提供商 (deepseek / openai)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider
        
        if not self.api_key:
            raise ValueError("需要设置 API Key")
        
        # 配置客户端
        if provider == "deepseek":
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            self.model = "deepseek-chat"
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
            self.model = "gpt-3.5-turbo"
    
    def extract_video_id(self, url: str) -> str:
        """从 URL 提取视频 ID"""
        import re
        
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11})',  # 标准 URL
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',  # 短链接
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"无法解析视频 ID: {url}")
    
    def get_transcript(self, video_id: str, languages: List[str] = None) -> Dict:
        """
        获取字幕
        
        Args:
            video_id: YouTube 视频 ID
            languages: 首选语言列表
            
        Returns:
            字幕信息字典
        """
        transcript_api = YouTubeTranscriptApi()
        
        # 获取可用字幕
        available = transcript_api.list_transcripts(video_id)
        
        # 尝试获取首选语言
        target_langs = languages or ['en', 'zh-Hans', 'zh-CN', 'zh']
        
        for lang in target_langs:
            try:
                transcript = available.find_transcript(lang)
                return {
                    'text': ' '.join([t['text'] for t in transcript.fetch_transcript()]),
                    'language': lang,
                    'is_generated': transcript.is_generated,
                }
            except:
                continue
        
        # 尝试自动检测
        try:
            transcript = available.find_manually_created_transcript()
            return {
                'text': ' '.join([t['text'] for t in transcript.fetch_transcript()]),
                'language': 'auto',
                'is_generated': False,
            }
        except:
            raise ValueError("无法获取视频字幕")
    
    def summarize(self, text: str, format: str = "brief", max_length: int = 500) -> Dict:
        """
        生成总结
        
        Args:
            text: 字幕文本
            format: 输出格式 (brief/detailed/timestamp)
            max_length: 最大长度
            
        Returns:
            总结结果
        """
        # 分段处理（避免超出上下文限制）
        chunks = self._split_text(text, max_tokens=4000)
        
        if len(chunks) == 1:
            prompt = self._build_prompt(chunks[0], format, max_length)
            result = self._call_llm(prompt)
        else:
            # 多段总结
            summaries = []
            for i, chunk in enumerate(chunks):
                prompt = self._build_prompt(chunk, "brief", 300)
                summary = self._call_llm(prompt)
                summaries.append(summary)
            
            # 汇总总结
            combined = "\n\n".join(summaries)
            prompt = self._build_prompt(combined, format, max_length)
            result = self._call_llm(prompt)
        
        return result
    
    def _split_text(self, text: str, max_tokens: int = 4000) -> List[str]:
        """分段文本"""
        # 简单按段落分段
        words = text.split()
        chunk = []
        chunks = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) > max_tokens * 4:  # 粗略估计
                chunks.append(' '.join(chunk))
                chunk = [word]
                current_size = 0
            else:
                chunk.append(word)
                current_size += len(word) + 1
        
        if chunk:
            chunks.append(' '.join(chunk))
        
        return chunks
    
    def _build_prompt(self, text: str, format: str, max_length: int) -> str:
        """构建 Prompt"""
        
        base_prompt = f"""请总结以下 YouTube 视频字幕内容：

{text[:3000]}...  # 限制输入长度

请按照以下格式输出："""
        
        if format == "brief":
            return f"""{base_prompt}

## 摘要 (不超过 {max_length} 字)
[简洁的摘要]

## 关键要点
- [要点 1]
- [要点 2]
- [要点 3]
"""
        
        elif format == "detailed":
            return f"""{base_prompt}

## 完整摘要
[详细的摘要，{max_length} 字左右]

## 关键要点
1. [要点 1]
2. [要点 2]
3. [要点 3]
4. [要点 4]
5. [要点 5]

## 结论
[视频的结论或建议]
"""
        
        elif format == "timestamp":
            return f"""{base_prompt}

请从字幕中提取关键信息和对应时间戳：

## 摘要
[一句话总结]

## 时间戳要点
- [03:12] [相关话题或观点]
- [08:45] [重要信息]
- [12:30] [关键结论]

## 核心要点
- [要点 1]
- [要点 2]
- [要点 3]
"""
        
        return base_prompt
    
    def _call_llm(self, prompt: str) -> Dict:
        """调用 LLM"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.5,
        )
        
        return {
            "summary": response.choices[0].message.content,
            "model": self.model,
            "tokens": response.usage.total_tokens if hasattr(response, 'usage') else None,
        }
    
    def process_video(self, url: str, format: str = "brief", 
                      max_length: int = 500, save: bool = True) -> Dict:
        """
        完整处理流程
        
        Args:
            url: YouTube 视频 URL
            format: 输出格式
            max_length: 最大长度
            save: 是否保存到文件
            
        Returns:
            处理结果
        """
        import re
        
        # 提取信息
        video_id = self.extract_video_id(url)
        
        print(f"📹 获取字幕中...")
        transcript_info = self.get_transcript(video_id)
        
        print(f"✍️  生成总结中...")
        result = self.summarize(transcript_info['text'], format, max_length)
        
        # 获取视频信息（简化）
        video_info = {
            "id": video_id,
            "url": url,
            "language": transcript_info['language'],
            "is_generated": transcript_info['is_generated'],
        }
        
        output = {
            "video_info": video_info,
            "summary": result["summary"],
            "format": format,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 保存文件
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
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="YouTube 视频字幕总结工具"
    )
    parser.add_argument("url", help="YouTube 视频 URL")
    parser.add_argument("--format", "-f", choices=["brief", "detailed", "timestamp"],
                        default="brief", help="总结格式")
    parser.add_argument("--max-length", "-m", type=int, default=500,
                        help="最大长度")
    parser.add_argument("--save/--no-save", default=True, help="是否保存文件")
    parser.add_argument("--provider", "-p", choices=["deepseek", "openai"],
                        default="deepseek", help="LLM 提供商")
    parser.add_argument("--api-key", "-k", help="API Key")
    
    args = parser.parse_args()
    
    try:
        summarizer = YouTubeSummarizer(api_key=args.api_key, provider=args.provider)
        
        result = summarizer.process_video(
            url=args.url,
            format=args.format,
            max_length=args.max_length,
            save=args.save,
        )
        
        print(f"\n✅ 完成!")
        print(f"📝 总结预览:\n{result['summary'][:200]}...")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
