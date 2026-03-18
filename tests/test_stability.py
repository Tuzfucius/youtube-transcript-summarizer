#!/usr/bin/env python3
"""
稳定性测试 - 测试工具函数、平台检测、工具定义等无需 API 的功能
"""

import sys
import time
from pathlib import Path

# 支持直接运行和从项目根目录运行
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import (
    detect, detect_platform, list_platforms,
    get_all_tools, get_tool_definition,
    logger, setup_logger, Timer, retry, DEFAULT_PROMPTS,
)


def test_logger():
    print("\n=== 测试日志系统 ===")
    logger.info("INFO 正常")
    logger.warning("WARNING 正常")
    logger.error("ERROR 正常")
    logger.success("success 正常")
    print("✅ 日志系统 OK")


def test_timer():
    print("\n=== 测试计时器 ===")
    with Timer("测试操作") as t:
        time.sleep(0.1)
    assert t.elapsed >= 0.1, "计时误差过大"
    print(f"✅ 计时器 OK ({t.elapsed:.2f}s)")


def test_retry():
    print("\n=== 测试重试机制 ===")
    call_count = [0]

    @retry(max_attempts=3, delay=0.05)
    def unstable():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ValueError("模拟失败")
        return "成功"

    result = unstable()
    assert result == "成功"
    assert call_count[0] == 3
    print(f"✅ 重试机制 OK (共调用 {call_count[0]} 次)")


def test_platform_detection():
    print("\n=== 测试平台检测 ===")
    cases = [
        ("https://www.youtube.com/watch?v=abc123",        "youtube"),
        ("https://youtu.be/abc123",                        "youtube"),
        ("https://www.bilibili.com/video/BV1xxxxxxxx",     "bilibili"),
        ("https://twitter.com/user/status/123",            "twitter"),
        ("https://x.com/user/status/456",                  "twitter"),
        ("https://www.reddit.com/r/python",                "reddit"),
        ("https://example-unknown.com/video",              "unknown"),
    ]
    all_pass = True
    for url, expected in cases:
        result = detect_platform(url)
        ok = result == expected
        if not ok:
            all_pass = False
        print(f"  {'✅' if ok else '❌'} {url[:50]} → {result} (期望: {expected})")
    assert all_pass, "平台检测存在错误"
    print("✅ 平台检测 OK")


def test_list_platforms():
    print("\n=== 测试平台列表 ===")
    platforms = list_platforms()
    assert len(platforms) > 10
    print(f"✅ 共 {len(platforms)} 个平台")


def test_prompts():
    print("\n=== 测试 Prompt 模板 ===")
    required = {"brief", "detailed", "timestamp", "sentiment", "trend"}
    assert required.issubset(DEFAULT_PROMPTS.keys()), "缺少必要的 Prompt 模板"
    # 验证模板可以正常格式化
    for name, tmpl in DEFAULT_PROMPTS.items():
        try:
            tmpl.format(
                title="测试标题", author="作者", desc="描述",
                views=1000, likes=100, content="内容", max_length=500,
            )
        except KeyError as e:
            print(f"  ⚠️  {name} 模板缺少变量: {e}")
    print("✅ Prompt 模板 OK")


def test_tool_definition():
    print("\n=== 测试工具定义 ===")
    tool = get_tool_definition()
    assert tool.get("name") == "summarize_video"
    assert "url" in tool["inputSchema"]["properties"]
    print(f"✅ get_tool_definition OK: {tool['name']}")

    tools = get_all_tools()
    assert len(tools) >= 3
    names = [t["name"] for t in tools]
    print(f"✅ get_all_tools OK: {names}")


def main():
    print("=" * 50)
    print("Video Summarizer - 稳定性测试")
    print("=" * 50)

    tests = [
        test_logger,
        test_timer,
        test_retry,
        test_platform_detection,
        test_list_platforms,
        test_prompts,
        test_tool_definition,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"结果: {passed} 通过 / {failed} 失败")
    print("=" * 50)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
