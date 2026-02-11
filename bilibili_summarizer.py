#!/usr/bin/env python3
"""
Bilibili Video Summarizer
基于弹幕和元数据的 B 站视频总结工具
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
from typing import Optional, List, Dict
from pathlib import Path


class BilibiliSummarizer:
    """B 站视频总结器"""
    
    def __init__(self, config: Dict = None):
        """初始化"""
        if config is None:
            config = {}
        
        self.config = config
        self.api_key = (config.get("api_key") or 
                       os.getenv("MINIMAX_API_KEY") or 
                       os.getenv("OPENAI_API_KEY") or "")
        self.api_url = (config.get("api_url") or 
                       os.getenv("YOUTUBE_SUMMARIZER_API_URL") or 
                       "https://api.minimaxi.com/v1/chat/completions")
        self.model = (config.get("model") or 
                    os.getenv("YOUTUBE_SUMMARIZER_MODEL") or 
                    "MiniMax-M2.1")
        
        # B站 API 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
    
    def extract_bvid(self, url: str) -> Optional[str]:
        """从 URL 提取 BV 号"""
        patterns = [
            r'BV[A-Za-z0-9]{10}',
            r'(?:bilibili\.com\/video\/)(BV[A-Za-z0-9]{10})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1) if match.lastindex else match.group(0)
        return None
    
    def get_video_info(self, bvid: str) -> Dict:
        """获取视频信息"""
        resp = requests.get(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers=self.headers,
            timeout=15
        )
        
        if resp.status_code != 200:
            raise ValueError(f"无法获取视频信息: HTTP {resp.status_code}")
        
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
            "cid": info["cid"],
            "duration": info["duration"],
            "pic": info["pic"],
            "stat": info["stat"]
        }
    
    def get_danmaku(self, cid: int) -> List[Dict]:
        """获取弹幕"""
        resp = requests.get(
            f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}",
            headers=self.headers,
            timeout=15
        )
        
        if resp.status_code != 200:
            return []
        
        # 解析 XML
        try:
            content = resp.content
            # 尝试解压
            try:
                content = gzip.decompress(content)
            except:
                pass
            
            root = ET.fromstring(content)
            danmaku = []
            
            for d in root.findall(".//d"):
                p = d.get("p", "").split(",")
                if len(p) >= 5:
                    danmaku.append({
                        "time": float(p[0]),
                        "type": p[1],
                        "size": p[2],
                        "color": p[3],
                        "timestamp": int(p[4]),
                        "pool": p[5] if len(p) > 5 else "0",
                        "text": d.text or ""
                    })
            
            return danmaku
        except Exception as e:
            print(f"弹幕解析错误: {e}")
            return []
    
    def summarize(self, video_info: Dict, danmaku: List[Dict], 
                  format: str = "brief", max_length: int = 500) -> str:
        """使用 LLM 总结"""
        
        # 构建内容
        danmaku_text = " ".join([d["text"] for d in danmaku[:500]])[:3000]
        
        if format == "brief":
            prompt = f"""这是一个 B 站视频的信息：

标题：{video_info['title']}
UP主：{video_info['owner']}
简介：{video_info['desc']}
弹幕数：{len(danmaku)}

弹幕内容摘要：
{danmaku_text}

请用一句话总结这个视频的内容和风格：
"""
        elif format == "detailed":
            prompt = f"""这是一个 B 站视频的详细信息：

标题：{video_info['title']}
UP主：{video_info['owner']}
简介：{video_info['desc']}
时长：{video_info['duration']}秒
弹幕数：{len(danmaku)}
播放量：{video_info['stat']['view']}
点赞数：{video_info['stat']['like']}
硬币数：{video_info['stat']['coin']}

弹幕样例（按时间排序）：
{danmaku_text}

请详细分析：
1. 视频内容是什么？
2. 弹幕反映了观众什么反应？
3. 视频的亮点和风格是什么？
4. 为什么这个视频受欢迎？
"""
        else:
            prompt = f"""分析这个 B 站视频：

标题：{video_info['title']}
UP主：{video_info['owner']}
弹幕数：{len(danmaku)}

弹幕关键词和时间分布：
{danmaku_text}

请输出：
1. 一句话总结
2. 弹幕反映的观众情绪
3. 视频高光时刻推测
"""
        
        # 调用 API
        if not self.api_key:
            return f"⚠️ 未配置 API Key，无法生成总结\n\n视频信息：\n{json.dumps(video_info, ensure_ascii=False, indent=2)}"
        
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
            return f"❌ API 错误: {e}\n\n视频信息：\n{json.dumps(video_info, ensure_ascii=False, indent=2)}"
    
    def process_video(self, url: str, format: str = "brief", 
                     max_length: int = 500, save: bool = True) -> Dict:
        """完整流程"""
        print("🎬 获取视频信息...")
        bvid = self.extract_bvid(url)
        if not bvid:
            raise ValueError(f"无法解析 B 站链接: {url}")
        
        video_info = self.get_video_info(bvid)
        print(f"✅ 获取到: {video_info['title']}")
        
        print("💬 获取弹幕...")
        danmaku = self.get_danmaku(video_info['cid'])
        print(f"✅ 获取到 {len(danmaku)} 条弹幕")
        
        if not danmaku:
            print("⚠️ 无弹幕，仅使用视频信息总结")
        
        print("✍️ 生成总结...")
        summary = self.summarize(video_info, danmaku, format, max_length)
        
        output = {
            "video_info": video_info,
            "danmaku_count": len(danmaku),
            "summary": summary,
            "format": format,
            "timestamp": datetime.now().isoformat()
        }
        
        if save:
            filename = f"bilibili-summary-{bvid}.md"
            self._save_to_file(output, filename)
            output["saved_file"] = filename
        
        return output
    
    def _save_to_file(self, output: Dict, filename: str):
        """保存到文件"""
        info = output["video_info"]
        content = f"""# B 站视频总结

## 视频信息
- **标题**: {info['title']}
- **UP主**: {info['owner']}
- **BV号**: {info['bvid']}
- **简介**: {info['desc']}
- **时长**: {info['duration']}秒
- **弹幕数**: {output['danmaku_count']}
- **播放量**: {info['stat']['view']:,}
- **点赞**: {info['stat']['like']:,}
- **硬币**: {info['stat']['coin']:,}
- **生成时间**: {output['timestamp']}

---

{output['summary']}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已保存: {filename}")


def main():
    """CLI"""
    parser = argparse.ArgumentParser(description="B 站视频总结工具")
    parser.add_argument("url", help="B 站视频链接")
    parser.add_argument("-f", "--format", choices=["brief", "detailed", "timestamp"], default="brief")
    parser.add_argument("-m", "--max-length", type=int, default=500)
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--api-url", help="API URL")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--no-save", action="store_true", help="不保存")
    args = parser.parse_args()
    
    # 构建配置
    config = {}
    if args.api_key:
        config["api_key"] = args.api_key
    if args.api_url:
        config["api_url"] = args.api_url
    if args.model:
        config["model"] = args.model
    
    try:
        s = BilibiliSummarizer(config)
        result = s.process_video(args.url, args.format, args.max_length, save=not args.no_save)
        print(f"\n✅ 完成!\n\n{result['summary'][:500]}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
