from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cli
import export_subtitle
import web_ui
from src import summarize
import src.core as core


def test_cli_config_roundtrip_and_mask(tmp_path):
    config_path = tmp_path / "config.json"
    payload = {"api_key": "secret-key", "api_url": "https://example.com", "model": "demo"}

    saved_path = cli.save_config(payload, str(config_path))
    assert saved_path == config_path

    loaded = cli.load_config(str(config_path))
    assert loaded["api_key"] == "secret-key"
    assert loaded["model"] == "demo"

    masked = cli.mask_sensitive_config(loaded)
    assert masked["api_key"] == "***"


def test_cli_save_result_writes_markdown_and_json(tmp_path):
    result = {
        "platform": "youtube",
        "video_info": {
            "title": "测试标题",
            "url": "https://www.youtube.com/watch?v=demo",
        },
        "summary": "总结内容",
        "format": "brief",
        "timestamp": "2026-03-18T08:00:00",
    }

    md_path = cli.save_result(result, str(tmp_path / "result.md"))
    json_path = cli.save_result(result, str(tmp_path / "result.json"))

    assert md_path.exists()
    assert json_path.exists()
    assert "测试标题" in md_path.read_text(encoding="utf-8")
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"] == "总结内容"


def test_web_ui_render_helpers():
    summary_md = web_ui._render_summary_markdown(
        {
            "platform": "youtube",
            "video_info": {"title": "标题", "url": "https://example.com"},
            "summary": "摘要",
            "format": "brief",
            "timestamp": "2026-03-18T08:00:00",
        }
    )
    extract_md = web_ui._render_extract_markdown(
        {
            "platform": "bilibili",
            "title": "标题",
            "content_type": "字幕",
            "source_type": "subtitle",
            "content": "正文",
        }
    )

    assert "摘要" in summary_md
    assert "正文" in extract_md


def test_real_youtube_summary_chain_without_network(monkeypatch):
    monkeypatch.setattr(core.YouTubeExtractor, "extract_video_id", lambda url: "demo123")
    monkeypatch.setattr(
        core.YouTubeExtractor,
        "get_transcript",
        lambda video_id, langs=None: {"text": "第一句 第二句", "language": "zh-Hans"},
    )
    monkeypatch.setattr(
        core.VideoSummarizer,
        "_call_llm",
        lambda self, prompt: {"ok": True, "summary": "总结结果", "error": None},
    )

    result = summarize("https://www.youtube.com/watch?v=demo123", api_key="local-test-key")

    assert result["summary"] == "总结结果"
    assert result["video_info"]["content_type"] == "字幕"
    assert result["platform"] == "youtube"


def test_bilibili_extract_and_export_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(export_subtitle, "detect_platform", lambda url: "bilibili")
    monkeypatch.setattr(export_subtitle.BilibiliExtractor, "extract_bvid", lambda url: "BVDEMO12345")
    monkeypatch.setattr(
        export_subtitle.BilibiliExtractor,
        "get_video_info",
        lambda bvid: {"bvid": bvid, "title": "B 站标题", "owner": "作者", "cid": 12},
    )
    monkeypatch.setattr(
        export_subtitle.BilibiliExtractor,
        "get_subtitles",
        lambda bvid, cid: {"has_subtitle": False, "text": ""},
    )
    monkeypatch.setattr(
        export_subtitle.BilibiliExtractor,
        "get_danmaku",
        lambda cid: [{"text": "弹幕一"}, {"text": "弹幕二"}],
    )

    extracted = export_subtitle.extract_content("https://www.bilibili.com/video/BVDEMO12345", use_subtitle=True, clean=False)
    assert extracted["content"] == "弹幕一 弹幕二"
    assert extracted["content_type"] == "弹幕"

    monkeypatch.setattr(
        export_subtitle,
        "extract_content",
        lambda url, use_subtitle=True, clean=True: {
            "platform": "bilibili",
            "title": "B 站标题",
            "content_type": "字幕",
            "source_type": "subtitle",
            "content": "第一行\n第二行",
            "url": url,
        },
    )

    output_path = tmp_path / "subtitle.txt"
    result = export_subtitle.export_subtitle(
        "https://www.bilibili.com/video/BVDEMO12345",
        output=str(output_path),
        format="txt",
        clean=False,
        use_subtitle=True,
    )

    assert result["success"] is True
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "B 站标题" in text
    assert "第一行" in text
