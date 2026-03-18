#!/usr/bin/env python3
"""
公共工具函数
包含日志系统、重试装饰器、错误处理、计时器
"""

import os
import time
import logging
import functools
from datetime import datetime
from pathlib import Path


# ============== 日志系统 ==============
def setup_logger(
    name: str = "VideoSummarizer",
    level: int = logging.INFO,
    log_file: str = None,
    log_dir: str = "logs"
) -> logging.Logger:
    """配置并返回 logger 实例"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    # 添加 success 便捷方法
    def success(msg: str):
        logger.log(logging.INFO, f"✅ {msg}")
    logger.success = success

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_file or log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(exist_ok=True)
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir_path / f"video_summarizer_{timestamp}.log"

        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s"
        ))
        logger.addHandler(fh)

    return logger


# 全局默认 logger
logger = setup_logger()


# ============== 重试装饰器 ==============
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """指数退避重试装饰器"""
    def decorator(func):
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
                        logger.error(
                            f"{func.__name__} 失败 ({attempt}/{max_attempts}): {e}"
                        )
                        raise
                    logger.warning(
                        f"{func.__name__} 失败，{current_delay:.1f}s 后重试... "
                        f"({attempt}/{max_attempts})"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_exc
        return wrapper
    return decorator


# ============== 错误处理装饰器 ==============
def handle_errors(default_return=None, log_error: bool = True):
    """捕获异常并返回默认值的装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"{func.__name__} 出错: {e}")
                return default_return
        return wrapper
    return decorator


# ============== 计时器上下文管理器 ==============
class Timer:
    """操作计时器，用作上下文管理器"""

    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start = None
        self.elapsed = 0.0

    def __enter__(self):
        self.start = time.time()
        logger.debug(f"开始: {self.name}")
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self.start
        logger.debug(f"完成: {self.name} ({self.elapsed:.2f}s)")
        return False


__all__ = [
    "setup_logger", "logger",
    "retry", "handle_errors",
    "Timer",
]
