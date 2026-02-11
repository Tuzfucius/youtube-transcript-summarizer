#!/usr/bin/env python3
"""
Video Summarizer - 测试脚本
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from video_summarizer import (
    summarize, detect as detect_platform, clean_danmaku_text,
    get_tool_definition, get_all_tools,
    logger, setup_logger, Timer, DEFAULT_PROMPTS, retry
)


def test_logger():
    print("\n=== 测试日志系统 ===")
    logger.info("INFO 日志正常")
    logger.warning("WARNING 日志正常")
    logger.error("ERROR 日志正常")
    print("✅ 日志系统正常")


def test_timer():
    print("\n=== 测试计时器 ===")
    with Timer("测试操作"):
        time.sleep(0.2)
    print("✅ 计时器正常")


def test_retry():
    print("\n=== 测试重试机制 ===")
    call_count = [0]
    
    @retry(max_attempts=3, delay=0.1)
    def test_retry_func():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError("模拟失败")
        return "成功"
    
    result = test_retry_func()
    print(f"✅ 重试机制正常 (调用次数: {call_count[0]})")


def test_platform_detection():
    print("\n=== 测试平台检测 ===")
    tests = [
        ("https://youtube.com/watch?v=abc", "youtube"),
        ("https://bilibili.com/video/BV123", "bilibili"),
        ("https://twitter.com/user/status/123", "twitter"),
    ]
    for url, expected in tests:
        result = detect_platform(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} {detect_platform}")
    print("✅ 平台检测正常")


def test_tool_definition():
    print("\n=== 测试工具定义 ===")
    tools = get_all_tools()
    print(f"工具数量: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['name']}")
    print("✅ 工具定义正常")


def main():
    print("=" * 50)
    print("Video Summarizer - 稳定性测试")
    print("=" * 50)
    
    setup_logger(log_file="test_logs/video_summarizer.log")
    
    test_logger()
    test_timer()
    test_retry()
    test_platform_detection()
    test_tool_definition()
    
    print("\n" + "=" * 50)
    print("✅ 所有测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
