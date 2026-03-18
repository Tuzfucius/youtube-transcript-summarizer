#!/usr/bin/env python3
"""Web UI 入口。

只负责界面与参数收集，不承载核心提取逻辑。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import gradio as gr

    GRADIO_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on local environment
    gr = None
    GRADIO_AVAILABLE = False

from export_subtitle import extract_content
from src import DEFAULT_PROMPTS, summarize


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """读取本地配置。"""

    candidates = []
    if config_file:
        candidates.append(Path(config_file))
    candidates.append(PROJECT_ROOT / "config.json")

    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
    return {}


def _default_api_key() -> str:
    config = load_config()
    return str(
        config.get("api_key")
        or os.getenv("VIDEO_SUMMARIZER_API_KEY")
        or os.getenv("MINIMAX_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )


def _render_summary_markdown(result: Dict[str, Any]) -> str:
    """把总结结果渲染成 Markdown。"""

    if not isinstance(result, dict):
        return f"```\n{result}\n```"

    summary = result.get("summary") or result.get("error") or "没有可用结果"
    info = result.get("video_info", {})

    lines = [
        f"# {info.get('title') or '视频总结'}",
        "",
        f"- 平台: {result.get('platform', 'unknown')}",
        f"- URL: {info.get('url', '')}",
        f"- 格式: {result.get('format', '')}",
        f"- 时间: {result.get('timestamp', '')}",
        "",
        "## 输出",
        summary,
    ]
    return "\n".join(lines)


def _render_extract_markdown(result: Dict[str, Any]) -> str:
    """把提取结果渲染成 Markdown。"""

    if not isinstance(result, dict):
        return f"```\n{result}\n```"

    if result.get("error"):
        return f"## 提取失败\n\n{result['error']}"

    content = result.get("content", "").strip() or "没有提取到内容"
    return "\n".join(
        [
            f"# {result.get('title') or '提取结果'}",
            "",
            f"- 平台: {result.get('platform', 'unknown')}",
            f"- 内容类型: {result.get('content_type', '')}",
            f"- 来源: {result.get('source_type', '')}",
            "",
            "## 内容",
            content,
        ]
    )


def _summarize_video(
    url: str,
    format_choice: str,
    api_key: str,
    api_url: str,
    model: str,
    use_subtitle: bool,
    clean_danmaku: bool,
    summarize_func: Optional[Callable[..., Dict[str, Any]]] = None,
) -> str:
    """总结按钮的回调。"""

    summarize_impl = summarize_func or summarize
    result = summarize_impl(
        url=url,
        format=format_choice,
        api_key=api_key,
        api_url=api_url,
        model=model,
        use_subtitle=use_subtitle,
        clean_danmaku=clean_danmaku,
    )
    return _render_summary_markdown(result)


def _extract_video(
    url: str,
    model: str,
    language: str,
    use_subtitle: bool,
    clean_danmaku: bool,
    transcribe_func: Optional[Callable[..., Any]] = None,
) -> str:
    """提取按钮的回调。"""

    if callable(transcribe_func):
        result = transcribe_func(url, model=model, language=language or None)
        if isinstance(result, dict):
            if result.get("error"):
                return f"## 提取失败\n\n{result['error']}"
            return _render_extract_markdown(
                {
                    "title": result.get("title", ""),
                    "platform": result.get("platform", "unknown"),
                    "content_type": result.get("content_type", "转写"),
                    "source_type": result.get("source_type", "transcribe"),
                    "content": result.get("text", "") or result.get("content", ""),
                }
            )
        return str(result)

    result = extract_content(url, use_subtitle=use_subtitle, clean=clean_danmaku)
    return _render_extract_markdown(result)


def create_ui(
    summarize_func: Optional[Callable[..., Dict[str, Any]]] = None,
    transcribe_func: Optional[Callable[..., Any]] = None,
) -> "gr.Blocks":
    """构建 Gradio 界面。"""

    if not GRADIO_AVAILABLE:
        raise ImportError("Gradio 未安装，请先执行 `pip install gradio`。")

    with gr.Blocks(title="Video Summarizer", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# Video Summarizer")
        gr.Markdown("聚焦字幕、弹幕与文本总结，不再夸大平台覆盖范围。")

        with gr.Tabs():
            with gr.TabItem("总结"):
                with gr.Row():
                    with gr.Column(scale=3):
                        url_input = gr.Textbox(label="视频 URL", placeholder="https://www.youtube.com/watch?v=...")
                        api_key_input = gr.Textbox(
                            label="API Key",
                            type="password",
                            value=_default_api_key(),
                        )
                        api_url_input = gr.Textbox(
                            label="API URL",
                            value="https://api.minimaxi.com/v1/chat/completions",
                        )
                        model_input = gr.Textbox(label="模型", value="MiniMax-M2.1")
                        format_dropdown = gr.Dropdown(
                            choices=list(DEFAULT_PROMPTS.keys()),
                            value="brief",
                            label="总结格式",
                        )
                        subtitle_check = gr.Checkbox(label="优先使用字幕", value=True)
                        clean_check = gr.Checkbox(label="清洗弹幕", value=True)
                        summarize_btn = gr.Button("开始总结", variant="primary")

                    with gr.Column(scale=7):
                        summary_output = gr.Markdown()

                summarize_btn.click(
                    fn=lambda url, fmt, key, api_url, model, use_subtitle, clean: _summarize_video(
                        url,
                        fmt,
                        key,
                        api_url,
                        model,
                        use_subtitle,
                        clean,
                        summarize_func=summarize_func,
                    ),
                    inputs=[
                        url_input,
                        format_dropdown,
                        api_key_input,
                        api_url_input,
                        model_input,
                        subtitle_check,
                        clean_check,
                    ],
                    outputs=summary_output,
                )

            with gr.TabItem("提取文本"):
                with gr.Row():
                    with gr.Column(scale=3):
                        extract_url_input = gr.Textbox(label="视频 URL", placeholder="https://www.youtube.com/watch?v=...")
                        extract_model_input = gr.Textbox(label="模型", value="small")
                        language_input = gr.Textbox(label="语言", placeholder="zh / en / ja")
                        extract_subtitle_check = gr.Checkbox(label="优先使用字幕", value=True)
                        extract_clean_check = gr.Checkbox(label="清洗弹幕", value=True)
                        extract_btn = gr.Button("开始提取", variant="secondary")

                    with gr.Column(scale=7):
                        extract_output = gr.Markdown()

                extract_btn.click(
                    fn=lambda url, model, language, use_subtitle, clean: _extract_video(
                        url,
                        model,
                        language,
                        use_subtitle,
                        clean,
                        transcribe_func=transcribe_func,
                    ),
                    inputs=[
                        extract_url_input,
                        extract_model_input,
                        language_input,
                        extract_subtitle_check,
                        extract_clean_check,
                    ],
                    outputs=extract_output,
                )

        gr.Markdown("---")
        gr.Markdown("本地运行，建议只在可信环境中填写 API Key。`config.json` 仅保留在本机，不要提交到仓库。")

    return demo


def launch_ui(
    summarize_func: Optional[Callable[..., Dict[str, Any]]] = None,
    transcribe_func: Optional[Callable[..., Any]] = None,
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    **kwargs,
) -> None:
    """启动 Web UI。"""

    if not GRADIO_AVAILABLE:
        print("Gradio 未安装。")
        print("安装命令: pip install gradio")
        return

    os.environ["NO_PROXY"] = "localhost,127.0.0.1,0.0.0.0"
    demo = create_ui(summarize_func=summarize_func, transcribe_func=transcribe_func)
    print(f"Web UI 启动在 http://{server_name}:{server_port}")
    demo.launch(server_name=server_name, server_port=server_port, **kwargs)


def check_gradio() -> Dict[str, Any]:
    """检查 Gradio 是否可用。"""

    return {"available": GRADIO_AVAILABLE}


def install_gradio() -> bool:
    """安装 Gradio。"""

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "gradio"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("Gradio 安装成功。")
        return True

    print(f"Gradio 安装失败: {result.stderr}")
    return False


def build_parser() -> argparse.ArgumentParser:
    """构建参数解析器。"""

    parser = argparse.ArgumentParser(description="Video Summarizer Web UI")
    parser.add_argument("--check", action="store_true", help="检查 Gradio 状态")
    parser.add_argument("--install", action="store_true", help="安装 Gradio")
    parser.add_argument("--port", type=int, default=7860, help="端口")
    parser.add_argument("--host", default="127.0.0.1", help="服务地址")
    parser.add_argument("--share", action="store_true", help="创建公开链接")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    """命令行入口。"""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.check:
        status = check_gradio()
        print(f"Gradio 可用: {status['available']}")
        return 0

    if args.install:
        return 0 if install_gradio() else 1

    try:
        from whisper_transcribe import transcribe_audio
    except ImportError:
        transcribe_audio = None

    launch_ui(
        summarize_func=summarize,
        transcribe_func=transcribe_audio,
        server_name=args.host,
        server_port=args.port,
        share=args.share,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "create_ui",
    "launch_ui",
    "check_gradio",
    "install_gradio",
    "GRADIO_AVAILABLE",
    "_render_summary_markdown",
    "_render_extract_markdown",
]
