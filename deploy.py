#!/usr/bin/env python3
"""
Video Summarizer - 部署配置
支持轻量化部署和全部部署两种模式
"""

import os
import sys
from pathlib import Path

# ============== 部署模式定义 ==============
DEPLOY_MODES = {
    'light': {
        'name': '轻量化部署',
        'description': '仅核心功能，适合快速使用',
        'features': [
            'summarize() - 单视频总结',
            'extract_video() - 视频内容提取',
            'detect_platform() - 平台检测',
            'clean_danmaku() - 弹幕清洗',
        ],
        'files': [
            'video_summarizer.py',
            '__init__.py',
        ],
        'dependencies': [
            'youtube-transcript-api',
            'requests',
        ],
        'size_estimate': '~500KB',
    },
    'full': {
        'name': '全部部署',
        'description': '完整功能，包含 CLI、异步、历史记录等',
        'features': [
            '轻量化所有功能',
            'CLI 工具 (cli.py)',
            '异步并发 (async)',
            '历史记录 (SQLite)',
            '视频对比 (compare)',
            'MCP Server',
            'Claude Code 集成',
            '成本追踪',
            'Whisper 支持',
        ],
        'files': [
            'video_summarizer.py',
            '__init__.py',
            'cli.py',
            'advanced.py',
            'mcp_server.py',
            'claude_code.py',
        ],
        'dependencies': [
            'youtube-transcript-api',
            'requests',
        ],
        'optional_dependencies': [
            'faster-whisper',  # Whisper 转录
            'yt-dlp',          # 视频下载
        ],
        'size_estimate': '~2MB',
    }
}


# ============== 安装脚本生成 ==============
def generate_install_script(mode: str = 'light') -> str:
    """生成安装脚本"""
    config = DEPLOY_MODES[mode]
    
    script = f'''#!/bin/bash
# Video Summarizer - {config['name']}
# Mode: {mode}

echo "🎬 Video Summarizer 安装脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "模式: {config['name']}"
echo "描述: {config['description']}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    exit 1
fi

echo "✅ Python 3 已安装"

# 安装依赖
echo ""
echo "📦 安装依赖..."
'''

    for dep in config['dependencies']:
        script += f'''
pip install {dep} 2>/dev/null || echo "  ⚠️ {dep} 安装失败"
'''

    if mode == 'full' and config.get('optional_dependencies'):
        script += f'''
echo ""
echo "📦 安装可选依赖 (Whisper 转录等)..."
for dep in {" ".join(config['optional_dependencies'])}; do
    read -p "是否安装 $dep? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install $dep 2>/dev/null || echo "  ⚠️ $dep 安装失败"
    fi
done
'''

    script += f'''
# 验证安装
echo ""
echo "✅ 安装完成!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "使用方式:"
echo ""
echo "  Python API:"
echo "    from video_summarizer import summarize"
echo "    result = summarize('URL', format='brief')"
echo ""
echo "  CLI:"
echo "    python cli.py url 'URL' -f brief"
echo ""
'''

    if mode == 'full':
        script += '''echo "  Claude Code:"
echo "    /video-summarizer URL"
echo ""
'''

    script += '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
'''
    
    return script


def generate_requirements(mode: str = 'light') -> str:
    """生成 requirements.txt"""
    config = DEPLOY_MODES[mode]
    
    lines = ['# Video Summarizer Requirements', f'# Mode: {mode}', '']
    
    for dep in config['dependencies']:
        lines.append(dep)
    
    if mode == 'full' and config.get('optional_dependencies'):
        lines.append('')
        lines.append('# Optional Dependencies')
        lines.append('# Install manually if needed')
        for dep in config['optional_dependencies']:
            lines.append(f'# {dep}')
    
    return '\n'.join(lines)


def check_installation(mode: str = 'light') -> dict:
    """检查安装状态"""
    status = {
        'mode': mode,
        'python': False,
        'dependencies': [],
        'optional': [],
        'files': [],
        'ready': False,
    }
    
    # 检查 Python
    try:
        import youtube_transcript_api
        import requests
        status['python'] = True
    except ImportError:
        pass
    
    # 检查依赖
    for dep in DEPLOY_MODES[mode]['dependencies']:
        try:
            __import__(dep.replace('-', '_'))
            status['dependencies'].append({'name': dep, 'installed': True})
        except ImportError:
            status['dependencies'].append({'name': dep, 'installed': False})
    
    # 检查可选依赖
    for dep in DEPLOY_MODES['full'].get('optional_dependencies', []):
        try:
            __import__(dep.replace('-', '_'))
            status['optional'].append({'name': dep, 'installed': True})
        except ImportError:
            status['optional'].append({'name': dep, 'installed': False})
    
    # 检查文件
    skill_dir = Path(__file__).parent
    for f in DEPLOY_MODES[mode]['files']:
        path = skill_dir / f
        status['files'].append({'name': f, 'exists': path.exists()})
    
    # 判断是否就绪
    status['ready'] = (
        status['python'] and
        all(d['installed'] for d in status['dependencies']) and
        all(f['exists'] for f in status['files'])
    )
    
    return status


def suggest_mode() -> str:
    """根据环境建议部署模式"""
    status = check_installation('full')
    
    if status['ready']:
        return 'full'
    
    status_light = check_installation('light')
    if status_light['ready']:
        return 'light'
    
    # 默认建议轻量化
    return 'light'


# ============== 便捷函数 ==============
def install(mode: str = 'light', verbose: bool = True):
    """执行安装"""
    config = DEPLOY_MODES[mode]
    
    if verbose:
        print(f"🎬 安装 Video Summarizer ({config['name']})")
        print("=" * 50)
    
    # 生成并保存脚本
    script_content = generate_install_script(mode)
    install_script = Path(__file__).parent / f"install_{mode}.sh"
    
    with open(install_script, 'w') as f:
        f.write(script_content)
    os.chmod(str(install_script), 0o755)
    
    if verbose:
        print(f"✅ 安装脚本已生成: {install_script}")
        print(f"\n运行以下命令完成安装:")
        print(f"  bash {install_script}")
    
    return str(install_script)


def quick_start(mode: str = None):
    """快速开始向导"""
    if mode is None:
        mode = suggest_mode()
    
    config = DEPLOY_MODES[mode]
    
    print("\n" + "=" * 60)
    print(f"🎬 Video Summarizer - {config['name']}")
    print("=" * 60)
    print()
    print("📦 功能特性:")
    for i, feature in enumerate(config['features'][:5], 1):
        print(f"  {i}. {feature}")
    if len(config['features']) > 5:
        print(f"  ... 共 {len(config['features'])} 项")
    print()
    print(f"💾 预估大小: {config['size_estimate']}")
    print()
    
    # 检查安装状态
    status = check_installation(mode)
    if status['ready']:
        print("✅ 安装状态: 已就绪")
        print("\n🚀 开始使用:")
        print()
        print("  Python:")
        print('    from video_summarizer import summarize')
        print('    result = summarize("URL", format="brief")')
        print()
        print("  CLI:")
        print('    python cli.py url "URL" -f brief')
    else:
        print("⚠️  安装状态: 未完成")
        print()
        print("💡 安装建议:")
        print(f"  1. 运行: python deploy.py --install {mode}")
        print(f"  2. 或查看: install_{mode}.sh")
    print()
    print("=" * 60)


def show_modes():
    """显示部署模式对比"""
    print("\n🎬 Video Summarizer - 部署模式对比")
    print("=" * 70)
    
    for mode, config in DEPLOY_MODES.items():
        print(f"\n📦 {config['name']} ({mode})")
        print(f"   {config['description']}")
        print(f"   大小: {config['size_estimate']}")
        print(f"   文件: {len(config['files'])} 个")
        print(f"   依赖: {len(config['dependencies'])} 个")
        print()
        print("   功能:")
        for feature in config['features'][:4]:
            print(f"     ✓ {feature}")
        if len(config['features']) > 4:
            print(f"     ... 共 {len(config['features'])} 项")
    
    print()
    print("=" * 70)
    print("💡 选择建议:")
    print("   - 轻量化: 快速体验，仅核心功能")
    print("   - 全部:   完整功能，需要更多依赖")
    print()
    print("📖 查看文档: README.md")
    print()


# ============== CLI ==============
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🎬 Video Summarizer - 部署管理",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--install', choices=['light', 'full'], help='生成安装脚本')
    parser.add_argument('--check', action='store_true', help='检查安装状态')
    parser.add_argument('--quick', action='store_true', help='快速开始')
    parser.add_argument('--show', action='store_true', help='显示模式对比')
    
    args = parser.parse_args()
    
    if args.show:
        show_modes()
    elif args.quick:
        quick_start(args.mode)
    elif args.check:
        status = check_installation(args.mode or 'full')
        import json
        print(json.dumps(status, indent=2, ensure_ascii=False))
    elif args.install:
        script = install(args.install, verbose=True)
        print(f"✅ 安装脚本已生成: {script}")
    else:
        quick_start(args.mode)


__all__ = [
    'DEPLOY_MODES', 'generate_install_script', 'generate_requirements',
    'check_installation', 'suggest_mode', 'install', 'quick_start', 'show_modes'
]
