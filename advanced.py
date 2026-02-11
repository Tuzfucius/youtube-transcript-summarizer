#!/usr/bin/env python3
"""
Video Summarizer - 异步支持模块
支持并发处理多个视频
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Optional


class AsyncSummarizer:
    """异步总结器"""
    
    def __init__(self, max_concurrent: int = 3, **kwargs):
        self.max_concurrent = max_concurrent
        self.kwargs = kwargs
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _summarize_one(self, url: str, format: str, progress_callback: Callable = None) -> Dict:
        """异步总结单个视频"""
        async with self.semaphore:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                from video_summarizer import summarize
                result = await loop.run_in_executor(
                    executor,
                    lambda: summarize(url=url, format=format, **self.kwargs)
                )
            
            if progress_callback:
                progress_callback(url, result)
            
            return result
    
    async def summarize_batch(
        self, 
        urls: List[str], 
        format: str = 'brief',
        progress_callback: Callable[[str, Dict], None] = None
    ) -> List[Dict]:
        """批量异步总结"""
        tasks = [self._summarize_one(url, format, progress_callback) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append({'url': urls[i], 'error': str(r)})
            else:
                final_results.append(r)
        
        return final_results


def summarize_batch_sync(
    urls: List[str], 
    format: str = 'brief',
    max_workers: int = 3,
    **kwargs
) -> List[Dict]:
    """同步批量总结（简单版）"""
    from video_summarizer import summarize
    
    results = []
    for url in urls:
        try:
            result = summarize(url=url, format=format, **kwargs)
            results.append(result)
        except Exception as e:
            results.append({'url': url, 'error': str(e)})
    
    return results


# ============== 多 API 支持 ==============
class LLMFactories:
    """LLM 工厂类"""
    
    FACTORIES = {}
    
    @classmethod
    def register(cls, name: str):
        def decorator(func):
            cls.FACTORIES[name] = func
            return func
        return decorator
    
    @classmethod
    def create(cls, name: str, api_key: str, api_url: str = None, model: str = None):
        if name not in cls.FACTORIES:
            raise ValueError(f"Unknown LLM provider: {name}")
        return cls.FACTORIES[name](api_key, api_url, model)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls.FACTORIES.keys())


@LLMFactories.register('minimax')
def create_minimax(api_key: str, api_url: str = None, model: str = None):
    api_url = api_url or 'https://api.minimaxi.com/v1/chat/completions'
    model = model or 'MiniMax-M2.1'
    return {'name': 'MiniMax', 'api_url': api_url, 'model': model, 'api_key': api_key}


@LLMFactories.register('openai')
def create_openai(api_key: str, api_url: str = None, model: str = None):
    api_url = api_url or 'https://api.openai.com/v1/chat/completions'
    model = model or 'gpt-4'
    return {'name': 'OpenAI', 'api_url': api_url, 'model': model, 'api_key': api_key}


@LLMFactories.register('deepseek')
def create_deepseek(api_key: str, api_url: str = None, model: str = None):
    api_url = api_url or 'https://api.deepseek.com/v1/chat/completions'
    model = model or 'deepseek-chat'
    return {'name': 'DeepSeek', 'api_url': api_url, 'model': model, 'api_key': api_key}


@LLMFactories.register('anthropic')
def create_anthropic(api_key: str, api_url: str = None, model: str = None):
    api_url = api_url or 'https://api.anthropic.com/v1/chat/completions'
    model = model or 'claude-3-opus-20240229'
    return {'name': 'Anthropic', 'api_url': api_url, 'model': model, 'api_key': api_key}


# ============== 历史记录存储 ==============
import sqlite3
from pathlib import Path


class HistoryStore:
    """历史记录存储"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path(__file__).parent / "history.db")
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    platform TEXT,
                    summary TEXT,
                    format TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history_tags (
                    history_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (history_id, tag_id)
                )
            """)
    
    def add(self, url: str, title: str, platform: str, summary: str, format: str, tags: List[str] = None):
        """添加记录"""
        with sqlite3.connect(self.db_path) as conn:
            # 添加历史
            conn.execute("""
                INSERT OR REPLACE INTO history (url, title, platform, summary, format)
                VALUES (?, ?, ?, ?, ?)
            """, [url, title, platform, summary, format])
            
            # 获取历史 ID
            cursor = conn.execute("SELECT id FROM history WHERE url = ?", [url])
            history_id = cursor.fetchone()[0]
            
            # 添加标签
            if tags:
                for tag in tags:
                    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", [tag])
                    cursor = conn.execute("SELECT id FROM tags WHERE name = ?", [tag])
                    tag_id = cursor.fetchone()[0]
                    conn.execute("INSERT OR IGNORE INTO history_tags VALUES (?, ?)", [history_id, tag_id])
    
    def get_all(self, limit: int = 100) -> List[Dict]:
        """获取所有记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", [limit]
            ).fetchall()
            return [dict(row) for row in rows]
    
    def search(self, keyword: str) -> List[Dict]:
        """搜索"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM history WHERE title LIKE ? OR summary LIKE ? ORDER BY created_at DESC",
                [f'%{keyword}%', f'%{keyword}%']
            ).fetchall()
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
            by_platform = conn.execute(
                "SELECT platform, COUNT(*) as count FROM history GROUP BY platform"
            ).fetchall()
            return {'total': total, 'by_platform': dict(by_platform)}
    
    def clear(self):
        """清除历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM history_tags")
            conn.execute("DELETE FROM history")


# ============== 对比功能 ==============
class VideoComparator:
    """视频对比器"""
    
    def __init__(self):
        from video_summarizer import summarize
    
    def compare(self, urls: List[str], format: str = 'brief') -> Dict:
        """对比多个视频"""
        from video_summarizer import summarize
        
        results = []
        for url in urls:
            result = summarize(url, format=format)
            results.append(result)
        
        # 生成对比报告
        report = {
            'videos': [],
            'comparison': {},
            'insights': []
        }
        
        for r in results:
            report['videos'].append({
                'platform': r.get('platform'),
                'title': r.get('video_info', {}).get('title'),
                'url': r.get('video_info', {}).get('url'),
                'summary_preview': r.get('summary', '')[:200]
            })
        
        # 平台分布
        platforms = [r.get('platform') for r in results]
        report['comparison']['platforms'] = {p: platforms.count(p) for p in set(platforms)}
        
        return report


# ============== 便捷函数 ==============
def quick_summarize(url: str, provider: str = 'minimax', **kwargs) -> Dict:
    """快速总结（指定 provider）"""
    from video_summarizer import summarize
    
    config = LLMFactories.create(provider, kwargs.get('api_key', ''))
    
    return summarize(
        url=url,
        api_url=config['api_url'],
        model=config['model'],
        **kwargs
    )


def add_to_history(url: str, title: str, platform: str, summary: str, format: str, tags: List[str] = None):
    """添加到历史记录"""
    store = HistoryStore()
    store.add(url, title, platform, summary, format, tags)


__all__ = [
    'AsyncSummarizer', 'summarize_batch_sync',
    'LLMFactories', 'HistoryStore', 'VideoComparator',
    'quick_summarize', 'add_to_history'
]
