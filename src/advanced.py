#!/usr/bin/env python3
"""
异步处理、历史记录、多 LLM 工厂、视频对比
"""

import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional


# ============== 异步批量总结 ==============
class AsyncSummarizer:
    """支持并发的异步批量总结器"""

    def __init__(self, max_concurrent: int = 3, **kwargs):
        """
        Args:
            max_concurrent: 最大并发数
            **kwargs: 传递给 summarize() 的参数（api_key/api_url/model 等）
        """
        self.max_concurrent = max_concurrent
        self.kwargs = kwargs
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _summarize_one(
        self, url: str, format: str, progress_callback: Callable = None
    ) -> Dict:
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                from .core import summarize
                result = await loop.run_in_executor(
                    executor,
                    lambda: summarize(url=url, format=format, **self.kwargs),
                )
            if progress_callback:
                progress_callback(url, result)
            return result

    async def summarize_batch(
        self,
        urls: List[str],
        format: str = "brief",
        progress_callback: Callable[[str, Dict], None] = None,
    ) -> List[Dict]:
        """并发批量总结多个视频"""
        tasks = [self._summarize_one(url, format, progress_callback) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final: List[Dict] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final.append({"url": urls[i], "error": str(r)})
            else:
                final.append(r)
        return final


def summarize_batch_sync(
    urls: List[str],
    format: str = "brief",
    **kwargs,
) -> List[Dict]:
    """同步批量总结（顺序处理）"""
    from .core import summarize

    results: List[Dict] = []
    for url in urls:
        try:
            results.append(summarize(url=url, format=format, **kwargs))
        except Exception as e:
            results.append({"url": url, "error": str(e)})
    return results


# ============== 多 LLM 工厂 ==============
class LLMFactories:
    """LLM 提供商工厂，支持 minimax / openai / deepseek / anthropic"""

    _FACTORIES: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(func):
            cls._FACTORIES[name] = func
            return func
        return decorator

    @classmethod
    def create(cls, name: str, api_key: str, api_url: str = None, model: str = None) -> Dict:
        if name not in cls._FACTORIES:
            raise ValueError(f"未知的 LLM 提供商: {name}（支持: {cls.list_providers()}）")
        return cls._FACTORIES[name](api_key, api_url, model)

    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._FACTORIES.keys())


@LLMFactories.register("minimax")
def _minimax(api_key, api_url=None, model=None):
    return {
        "name": "MiniMax",
        "api_url": api_url or "https://api.minimaxi.com/v1/chat/completions",
        "model": model or "MiniMax-M2.1",
        "api_key": api_key,
    }


@LLMFactories.register("openai")
def _openai(api_key, api_url=None, model=None):
    return {
        "name": "OpenAI",
        "api_url": api_url or "https://api.openai.com/v1/chat/completions",
        "model": model or "gpt-4o",
        "api_key": api_key,
    }


@LLMFactories.register("deepseek")
def _deepseek(api_key, api_url=None, model=None):
    return {
        "name": "DeepSeek",
        "api_url": api_url or "https://api.deepseek.com/v1/chat/completions",
        "model": model or "deepseek-chat",
        "api_key": api_key,
    }


@LLMFactories.register("anthropic")
def _anthropic(api_key, api_url=None, model=None):
    return {
        "name": "Anthropic",
        "api_url": api_url or "https://api.anthropic.com/v1/messages",
        "model": model or "claude-3-5-sonnet-20241022",
        "api_key": api_key,
    }


# ============== 历史记录存储 ==============
class HistoryStore:
    """基于 SQLite 的历史记录存储"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path(__file__).parent.parent / "history.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    platform TEXT,
                    summary TEXT,
                    format TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS history_tags (
                    history_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (history_id, tag_id)
                );
            """)

    def add(
        self,
        url: str,
        title: str,
        platform: str,
        summary: str,
        format: str,
        tags: List[str] = None,
    ):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO history (url, title, platform, summary, format) VALUES (?,?,?,?,?)",
                [url, title, platform, summary, format],
            )
            row = conn.execute("SELECT id FROM history WHERE url=?", [url]).fetchone()
            history_id = row[0]
            for tag in tags or []:
                conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", [tag])
                tag_row = conn.execute("SELECT id FROM tags WHERE name=?", [tag]).fetchone()
                conn.execute(
                    "INSERT OR IGNORE INTO history_tags VALUES (?,?)",
                    [history_id, tag_row[0]],
                )

    def get_all(self, limit: int = 100) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", [limit]
            ).fetchall()
            return [dict(r) for r in rows]

    def search(self, keyword: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM history WHERE title LIKE ? OR summary LIKE ? ORDER BY created_at DESC",
                [f"%{keyword}%", f"%{keyword}%"],
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
            by_platform = conn.execute(
                "SELECT platform, COUNT(*) FROM history GROUP BY platform"
            ).fetchall()
            return {"total": total, "by_platform": dict(by_platform)}

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("DELETE FROM history_tags; DELETE FROM history;")


# ============== 视频对比 ==============
class VideoComparator:
    """对比多个视频的总结内容"""

    def compare(self, urls: List[str], format: str = "brief") -> Dict:
        from .core import summarize

        results = [summarize(url, format=format) for url in urls]
        platforms = [r.get("platform") for r in results]

        return {
            "videos": [
                {
                    "platform":       r.get("platform"),
                    "title":          r.get("video_info", {}).get("title"),
                    "url":            r.get("video_info", {}).get("url"),
                    "summary_preview": r.get("summary", "")[:200],
                }
                for r in results
            ],
            "comparison": {
                "platforms": {p: platforms.count(p) for p in set(platforms)}
            },
        }


# ============== 便捷函数 ==============
def quick_summarize(url: str, provider: str = "minimax", **kwargs) -> Dict:
    """指定 LLM 提供商快速总结"""
    from .core import summarize

    api_key = kwargs.pop("api_key", "")
    cfg = LLMFactories.create(provider, api_key)
    return summarize(url=url, api_url=cfg["api_url"], model=cfg["model"], api_key=api_key, **kwargs)


def add_to_history(url: str, title: str, platform: str, summary: str, format: str, tags: List[str] = None):
    HistoryStore().add(url, title, platform, summary, format, tags)


__all__ = [
    "AsyncSummarizer", "summarize_batch_sync",
    "LLMFactories",
    "HistoryStore", "VideoComparator",
    "quick_summarize", "add_to_history",
]
