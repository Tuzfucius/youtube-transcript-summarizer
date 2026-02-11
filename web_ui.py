#!/usr/bin/env python3
"""
Video Summarizer - Gradio Web UI（可选功能）
"""

import os
import sys
from pathlib import Path

# 可选导入
try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False


def create_ui(summarize_func=None, transcribe_func=None) -> gr.Interface:
    """
    创建 Gradio 界面
    
    Args:
        summarize_func: 总结函数
        transcribe_func: 转录函数（可选）
    
    Returns:
        gr.Interface: Gradio 界面
    """
    if not GRADIO_AVAILABLE:
        raise ImportError("Gradio 未安装: pip install gradio")
    
    def summarize_video(url, format_choice, api_key):
        """总结视频"""
        if summarize_func:
            result = summarize_func(url, format=format_choice, api_key=api_key)
            return result.get('summary', str(result))
        return "请配置 summarize_func"
    
    def transcribe_video(url, model, language):
        """转录视频"""
        if transcribe_func:
            result = transcribe_func(url, model=model, language=language)
            if 'error' in result:
                return f"❌ 错误: {result['error']}"
            return f"✅ 转录成功!\n\n语言: {result.get('language')}\n\n{result.get('text', '')}"
        return "请配置 transcribe_func"
    
    # 创建界面
    with gr.Blocks(title="Video Summarizer", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🎬 Video Summarizer")
        gr.Markdown("视频内容总结工具 - 支持 45+ 平台")
        
        with gr.Tabs():
            with gr.TabItem("📝 总结"):
                with gr.Row():
                    with gr.Column(scale=3):
                        url_input = gr.Textbox(label="视频 URL", placeholder="https://youtube.com/...")
                        api_key_input = gr.Textbox(label="API Key", type="password", placeholder="输入你的 API Key")
                        format_dropdown = gr.Dropdown(
                            choices=["brief", "detailed", "timestamp", "sentiment", "trend"],
                            value="brief",
                            label="总结格式"
                        )
                        summarize_btn = gr.Button("🚀 开始总结", variant="primary")
                    
                    with gr.Column(scale=7):
                        summary_output = gr.Markdown(label="总结结果")
                
                summarize_btn.click(
                    fn=summarize_video,
                    inputs=[url_input, format_dropdown, api_key_input],
                    outputs=summary_output
                )
            
            with gr.TabItem("🎙️ 转录"):
                gr.Markdown("## Whisper 转录（需要安装 faster-whisper）")
                
                with gr.Row():
                    with gr.Column(scale=3):
                        transcribe_url = gr.Textbox(label="视频 URL", placeholder="https://youtube.com/...")
                        model_dropdown = gr.Dropdown(
                            choices=["tiny", "base", "small", "medium", "large-v3"],
                            value="small",
                            label="Whisper 模型"
                        )
                        lang_input = gr.Textbox(label="语言", placeholder="zh/en/ja/ko...（留空则自动检测）")
                        transcribe_btn = gr.Button("🎙️ 开始转录", variant="secondary")
                    
                    with gr.Column(scale=7):
                        transcript_output = gr.Markdown(label="转录结果")
                
                transcribe_btn.click(
                    fn=transcribe_video,
                    inputs=[transcribe_url, model_dropdown, lang_input],
                    outputs=transcript_output
                )
        
        gr.Markdown("---")
        gr.Markdown("📚 GitHub: https://github.com/Tuzfucius/youtube-transcript-summarizer")
    
    return demo


def launch_ui(summarize_func=None, transcribe_func=None, server_name: str = "0.0.0.0", server_port: int = 7860, **kwargs):
    """
    启动 Gradio 服务
    
    Args:
        summarize_func: 总结函数
        transcribe_func: 转录函数
        server_name: 服务地址
        server_port: 端口
    """
    if not GRADIO_AVAILABLE:
        print("❌ Gradio 未安装")
        print("💡 安装: pip install gradio")
        return
    
    demo = create_ui(summarize_func, transcribe_func)
    
    print(f"🎬 启动 Web UI...")
    print(f"📍 访问地址: http://{server_name}:{server_port}")
    
    demo.launch(server_name=server_name, server_port=server_port, **kwargs)


def check_gradio() -> dict:
    """检查 Gradio 是否可用"""
    return {'available': GRADIO_AVAILABLE}


def install_gradio():
    """安装 Gradio"""
    print("📦 正在安装 Gradio...")
    print("  pip install gradio")
    
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'gradio'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Gradio 安装成功！")
        print("💡 重启程序后生效")
        return True
    else:
        print(f"❌ 安装失败: {result.stderr}")
        return False


# ============== CLI ==============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='🎬 Video Summarizer Web UI')
    parser.add_argument('--check', action='store_true', help='检查 Gradio 状态')
    parser.add_argument('--install', action='store_true', help='安装 Gradio')
    parser.add_argument('--port', type=int, default=7860, help='端口')
    parser.add_argument('--host', default='0.0.0.0', help='服务地址')
    parser.add_argument('--share', action='store_true', help='创建公开链接')
    
    args = parser.parse_args()
    
    if args.check:
        status = check_gradio()
        print(f"Gradio 可用: {status['available']}")
    
    elif args.install:
        install_gradio()
    
    else:
        print("💡 使用 --check 检查状态")
        print("💡 使用 --install 安装")


__all__ = ['create_ui', 'launch_ui', 'check_gradio', 'install_gradio', 'GRADIO_AVAILABLE']
