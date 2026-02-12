#!/usr/bin/env python3
"""
Bilibili Video Summarizer - Enhanced
基于弹幕和字幕的 B 站视频总结工具
支持手动开启字幕、获取并解析字幕内容
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
from typing import Optional, List, Dict, Tuple
from pathlib import Path


class BilibiliSubtitleFetcher:
    """B站字幕获取器"""
    
    def __init__(self):
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
            "stat": info["stat"],
            "subtitle": info.get("subtitle", {})
        }
    
    def check_subtitle_status(self, bvid: str, cid: int) -> Dict:
        """检查字幕开关状态"""
        try:
            resp = requests.get(
                f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}",
                headers=self.headers,
                timeout=15
            )
            if resp.status_code != 200:
                return {"has_subtitle": False, "reason": f"HTTP {resp.status_code}"}
            
            data = resp.json()
            if data.get("code") != 0:
                return {"has_subtitle": False, "reason": data.get("message", "未知错误")}
            
            subtitle_list = data.get("data", [])
            
            # 获取字幕数据
            subtitles = []
            for page in subtitle_list:
                page_cid = page.get("cid")
                if page_cid:
                    sub_resp = requests.get(
                        f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={page_cid}",
                        headers=self.headers,
                        timeout=15
                    )
                    if sub_resp.status_code == 200:
                        sub_data = sub_resp.json()
                        if sub_data.get("code") == 0:
                            sub_list = sub_data.get("data", {}).get("subtitle", {}).get("subtitles", [])
                            subtitles.extend(sub_list)
            
            if subtitles:
                return {
                    "has_subtitle": True,
                    "subtitles": subtitles,
                    "count": len(subtitles)
                }
            else:
                return {"has_subtitle": False, "reason": "该视频没有字幕"}
                
        except Exception as e:
            return {"has_subtitle": False, "reason": str(e)}
    
    def get_subtitle_list(self, bvid: str) -> List[Dict]:
        """获取字幕列表"""
        status = self.check_subtitle_status(bvid, 0)
        if status.get("has_subtitle"):
            return status.get("subtitles", [])
        return []
    
    def download_subtitle(self, subtitle_url: str) -> Dict:
        """下载字幕文件"""
        try:
            resp = requests.get(subtitle_url, headers=self.headers, timeout=30)
            if resp.status_code != 200:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
            
            content = resp.content
            # 尝试解压
            try:
                content = gzip.decompress(content)
            except:
                pass
            
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def parse_json_subtitle(self, content: bytes) -> List[Dict]:
        """解析 JSON 格式字幕（B站标准格式）"""
        try:
            data = json.loads(content)
            body = data.get("body", [])
            subtitles = []
            
            for item in body:
                subtitles.append({
                    "from": item.get("from", 0),
                    "to": item.get("to", 0),
                    "content": item.get("content", ""),
                    "location": item.get("location", 2)
                })
            
            return subtitles
        except Exception as e:
            print(f"JSON 字幕解析错误: {e}")
            return []
    
    def parse_ass_subtitle(self, content: bytes) -> List[Dict]:
        """解析 ASS 格式字幕"""
        try:
            text = content.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            subtitles = []
            
            for line in lines:
                if line.startswith('Dialogue:'):
                    # 解析 ASS 字幕行
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        try:
                            start_time = self._ass_time_to_seconds(parts[1])
                            end_time = self._ass_time_to_seconds(parts[2])
                            content = parts[9].strip()
                            if content:
                                subtitles.append({
                                    "from": start_time,
                                    "to": end_time,
                                    "content": content
                                })
                        except:
                            pass
            
            return subtitles
        except Exception as e:
            print(f"ASS 字幕解析错误: {e}")
            return []
    
    def _ass_time_to_seconds(self, time_str: str) -> float:
        """ASS 时间转换为秒"""
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2])
                return h * 3600 + m * 60 + s
            return 0
        except:
            return 0
    
    def get_subtitles(self, bvid: str, cid: int = None) -> Dict:
        """完整字幕获取流程"""
        result = {
            "bvid": bvid,
            "has_subtitle": False,
            "subtitles": [],
            "subtitle_text": "",
            "raw_data": None
        }
        
        # 获取字幕列表
        subtitles = self.get_subtitle_list(bvid)
        
        if not subtitles:
            result["reason"] = "该视频没有字幕"
            return result
        
        # 下载第一个字幕
        first_sub = subtitles[0]
        subtitle_url = first_sub.get("subtitle_url", "")
        
        if not subtitle_url:
            result["reason"] = "字幕链接为空"
            return result
        
        # 补充完整 URL
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        
        # 下载字幕
        download_result = self.download_subtitle(subtitle_url)
        if not download_result.get("success"):
            result["reason"] = f"下载失败: {download_result.get('error')}"
            return result
        
        result["raw_data"] = download_result["content"]
        
        # 解析字幕
        subtitles_parsed = self.parse_json_subtitle(download_result["content"])
        
        if not subtitles_parsed:
            # 尝试 ASS 格式
            subtitles_parsed = self.parse_ass_subtitle(download_result["content"])
        
        if subtitles_parsed:
            result["has_subtitle"] = True
            result["subtitles"] = subtitles_parsed
            result["subtitle_text"] = " ".join([s["content"] for s in subtitles_parsed])
            result["subtitle_count"] = len(subtitles_parsed)
        else:
            result["reason"] = "无法解析字幕格式"
        
        return result
    
    def get_subtitle_text(self, url: str) -> Tuple[bool, str]:
        """便捷函数：获取字幕纯文本"""
        bvid = self.extract_bvid(url)
        if not bvid:
            return False, f"无法解析 URL: {url}"
        
        result = self.get_subtitles(bvid)
        
        if result.get("has_subtitle"):
            return True, result["subtitle_text"]
        else:
            return False, result.get("reason", "获取字幕失败")


class BilibiliSubtitleCleaner:
    """字幕内容清洗器"""
    
    def __init__(self):
        # 短文本阈值
        self.min_length = 2
        # 需要过滤的模式
        self.filter_patterns = [
            r'^[^a-zA-Z0-9\u4e00-\u9fff]+$',  # 纯符号
            r'^(.{1,2})$',  # 1-2字符
            r'^\d+$',  # 纯数字
        ]
        # 重复检测窗口
        self.dedupe_window = 5
    
    def clean(self, text: str, max_length: int = 5000) -> str:
        """清洗字幕文本"""
        if not text:
            return ""
        
        # 基础清理
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # 按句子分割
        sentences = re.split(r'[。！？.!?\n]', text)
        cleaned_sentences = []
        recent_contents = []
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            # 过滤短文本
            if len(sent) < self.min_length:
                continue
            
            # 过滤纯符号
            if re.match(self.filter_patterns[0], sent):
                continue
            
            # 过滤纯数字
            if re.match(self.filter_patterns[2], sent):
                continue
            
            # 去重
            is_duplicate = False
            for recent in recent_contents[-self.dedupe_window:]:
                if sent == recent or sent in recent:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                cleaned_sentences.append(sent)
                recent_contents.append(sent)
        
        result = "。".join(cleaned_sentences[:max_length // 10])
        
        # 保留中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', result)
        if len(chinese_chars) < len(result) * 0.3:
            # 如果中文字符太少，尝试提取中文部分
            chinese_only = "".join(chinese_chars)
            if len(chinese_only) > 50:
                result = chinese_only
        
        return result


class BilibiliSummarizer:
    """B 站视频总结器（增强版：支持字幕）"""
    
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
        
        # 初始化字幕获取器和清洗器
        self.subtitle_fetcher = BilibiliSubtitleFetcher()
        self.subtitle_cleaner = BilibiliSubtitleCleaner()
        
        # B站 API 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
    
    def extract_bvid(self, url: str) -> Optional[str]:
        """从 URL 提取 BV 号"""
        return self.subtitle_fetcher.extract_bvid(url)
    
    def get_video_info(self, bvid: str) -> Dict:
        """获取视频信息"""
        return self.subtitle_fetcher.get_video_info(bvid)
    
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
    
    def get_subtitles(self, bvid: str, cid: int = None) -> Dict:
        """获取字幕"""
        return self.subtitle_fetcher.get_subtitles(bvid, cid)
    
    def summarize_with_subtitle(self, video_info: Dict, subtitle_result: Dict,
                                 format: str = "brief", max_length: int = 500) -> str:
        """使用字幕生成总结"""
        
        subtitle_text = subtitle_result.get("subtitle_text", "")
        subtitle_count = subtitle_result.get("subtitle_count", 0)
        
        if not subtitle_text:
            # 回退到弹幕
            return None
        
        # 清洗字幕
        cleaned_subtitle = self.subtitle_cleaner.clean(subtitle_text)
        
        if format == "brief":
            prompt = f"""这是一个 B 站视频的字幕内容：

标题：{video_info['title']}
UP主：{video_info['owner']}
简介：{video_info['desc']}
字幕数：{subtitle_count}

字幕内容：
{cleaned_subtitle[:3000]}

请用一句话总结这个视频的内容和风格：
"""
        elif format == "detailed":
            prompt = f"""这是 B 站视频的详细字幕：

标题：{video_info['title']}
UP主：{video_info['owner']}
简介：{video_info['desc']}
时长：{video_info['duration']}秒
字幕数：{subtitle_count}

字幕内容：
{cleaned_subtitle[:4000]}

请详细分析：
1. 视频内容是什么？
2. 主要讨论了什么话题？
3. 视频的亮点和观点是什么？
4. 整体风格和节奏如何？
"""
        else:
            prompt = f"""分析这个 B 站视频的字幕：

标题：{video_info['title']}
字幕数：{subtitle_count}

字幕内容：
{cleaned_subtitle[:3000]}

请输出：
1. 一句话总结
2. 3-5个关键话题
"""
        
        # 调用 API
        return self._call_api(prompt, video_info)
    
    def summarize(self, video_info: Dict, danmaku: List[Dict], 
                  format: str = "brief", max_length: int = 500) -> str:
        """使用 LLM 总结（弹幕版）"""
        
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
        
        return self._call_api(prompt, video_info)
    
    def _call_api(self, prompt: str, video_info: Dict) -> str:
        """调用 API"""
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
                     max_length: int = 500, save: bool = True,
                     use_subtitle: bool = True) -> Dict:
        """完整流程 - 增强版"""
        print("🎬 获取视频信息...")
        bvid = self.extract_bvid(url)
        if not bvid:
            raise ValueError(f"无法解析 B 站链接: {url}")
        
        video_info = self.get_video_info(bvid)
        print(f"✅ 获取到: {video_info['title']}")
        
        output = {
            "video_info": video_info,
            "danmaku_count": 0,
            "subtitle_count": 0,
            "summary": "",
            "format": format,
            "timestamp": datetime.now().isoformat(),
            "source": "danmaku"
        }
        
        # 优先使用字幕
        if use_subtitle:
            print("📝 检查字幕状态...")
            subtitle_result = self.get_subtitles(bvid, video_info['cid'])
            
            if subtitle_result.get("has_subtitle"):
                print(f"✅ 获取到 {subtitle_result.get('subtitle_count', 0)} 条字幕")
                output["subtitle_count"] = subtitle_result.get("subtitle_count", 0)
                
                # 使用字幕生成总结
                summary = self.summarize_with_subtitle(video_info, subtitle_result, format, max_length)
                if summary:
                    output["summary"] = summary
                    output["source"] = "subtitle"
                    print("✍️ 基于字幕生成总结...")
                else:
                    print("⚠️ 字幕总结失败，回退到弹幕...")
                    use_subtitle = False
            else:
                reason = subtitle_result.get("reason", "未知原因")
                print(f"⚠️ 该视频没有字幕（{reason}），使用弹幕...")
                use_subtitle = False
        
        # 回退到弹幕
        if not use_subtitle or output.get("source") == "danmaku":
            print("💬 获取弹幕...")
            danmaku = self.get_danmaku(video_info['cid'])
            output["danmaku_count"] = len(danmaku)
            print(f"✅ 获取到 {len(danmaku)} 条弹幕")
            
            if danmaku:
                print("✍️ 基于弹幕生成总结...")
                output["summary"] = self.summarize(video_info, danmaku, format, max_length)
            else:
                print("⚠️ 无弹幕，仅使用视频信息总结")
                output["summary"] = f"无法获取弹幕和字幕\n\n视频信息：\n{json.dumps(video_info, ensure_ascii=False, indent=2)}"
        
        if save:
            filename = f"bilibili-summary-{bvid}.md"
            self._save_to_file(output, filename)
            output["saved_file"] = filename
        
        return output
    
    def _save_to_file(self, output: Dict, filename: str):
        """保存到文件"""
        info = output["video_info"]
        source = output.get("source", "danmaku")
        
        content = f"""# B 站视频总结

## 视频信息
- **标题**: {info['title']}
- **UP主**: {info['owner']}
- **BV号**: {info['bvid']}
- **简介**: {info['desc']}
- **时长**: {info['duration']}秒
- **字幕数**: {output.get('subtitle_count', 0)}
- **弹幕数**: {output.get('danmaku_count', 0)}
- **播放量**: {info['stat']['view']:,}
- **点赞**: {info['stat']['like']:,}
- **硬币**: {info['stat']['coin']:,}
- **生成时间**: {output['timestamp']}
- **内容来源**: {'字幕' if source == 'subtitle' else '弹幕'}

---

{output['summary']}
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已保存: {filename}")


def main():
    """CLI"""
    parser = argparse.ArgumentParser(description="B 站视频总结工具（增强版）")
    parser.add_argument("url", help="B 站视频链接")
    parser.add_argument("-f", "--format", choices=["brief", "detailed", "timestamp"], default="brief")
    parser.add_argument("-m", "--max-length", type=int, default=500)
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--api-url", help="API URL")
    parser.add_argument("--model", help="模型名称")
    parser.add_argument("--no-save", action="store_true", help="不保存")
    parser.add_argument("--danmaku-only", action="store_true", help="仅使用弹幕（不使用字幕）")
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
        result = s.process_video(
            args.url, 
            args.format, 
            args.max_length, 
            save=not args.no_save,
            use_subtitle=not args.danmaku_only
        )
        print(f"\n✅ 完成!\n\n{result['summary'][:500]}")
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
