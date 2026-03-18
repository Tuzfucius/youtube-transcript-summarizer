#!/usr/bin/env python3
"""
运行时配置加载与归一化。
支持本地 config.json、环境变量和显式参数覆盖。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "api_url": "https://api.minimaxi.com/v1/chat/completions",
    "model": "MiniMax-M2.1",
    "format": "brief",
    "use_subtitle": True,
    "clean_danmaku": True,
    "cache_enabled": True,
    "log_level": "INFO",
}

ENV_ALIASES = {
    "api_key": ("VIDEO_SUMMARIZER_API_KEY", "MINIMAX_API_KEY", "OPENAI_API_KEY"),
    "api_url": ("VIDEO_SUMMARIZER_API_URL",),
    "model": ("VIDEO_SUMMARIZER_MODEL",),
    "format": ("VIDEO_SUMMARIZER_FORMAT",),
    "use_subtitle": ("VIDEO_SUMMARIZER_USE_SUBTITLE",),
    "clean_danmaku": ("VIDEO_SUMMARIZER_CLEAN_DANMAKU",),
    "cache_enabled": ("VIDEO_SUMMARIZER_CACHE_ENABLED",),
    "log_level": ("VIDEO_SUMMARIZER_LOG_LEVEL",),
}


def _coerce_bool(value: Any) -> Optional[bool]:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None


def _coerce_value(key: str, value: Any) -> Any:
    if key in {"use_subtitle", "clean_danmaku", "cache_enabled"}:
        coerced = _coerce_bool(value)
        return value if coerced is None else coerced
    if key in {"api_key", "api_url", "model", "format", "log_level"}:
        return "" if value is None else str(value)
    return value


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"config file must contain a JSON object: {path}")
    return data


def load_env_config(env: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    source = env or os.environ
    result: Dict[str, Any] = {}
    for key, names in ENV_ALIASES.items():
        for name in names:
            if name in source and source[name] != "":
                result[key] = _coerce_value(key, source[name])
                break
    return result


def _merge_mapping(base: MutableMapping[str, Any], override: Mapping[str, Any]) -> None:
    for key, value in override.items():
        if value is not None:
            base[key] = value


@dataclass(frozen=True)
class AppConfig:
    api_key: str = ""
    api_url: str = DEFAULT_CONFIG["api_url"]
    model: str = DEFAULT_CONFIG["model"]
    format: str = DEFAULT_CONFIG["format"]
    use_subtitle: bool = DEFAULT_CONFIG["use_subtitle"]
    clean_danmaku: bool = DEFAULT_CONFIG["clean_danmaku"]
    cache_enabled: bool = DEFAULT_CONFIG["cache_enabled"]
    log_level: str = DEFAULT_CONFIG["log_level"]

    @classmethod
    def from_mapping(cls, mapping: Optional[Mapping[str, Any]] = None) -> "AppConfig":
        merged: Dict[str, Any] = dict(DEFAULT_CONFIG)
        if mapping:
            _merge_mapping(merged, mapping)
        normalized = {
            key: _coerce_value(key, merged.get(key))
            for key in DEFAULT_CONFIG
        }
        return cls(**normalized)

    def to_dict(self, redact_secret: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if redact_secret:
            data["api_key"] = mask_secret(data.get("api_key", ""))
        return data


def mask_secret(value: Any, visible: int = 4) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    if len(text) <= visible * 2:
        return "*" * len(text)
    return f"{text[:visible]}...{text[-visible:]}"


def redact_config(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    data = dict(mapping)
    if "api_key" in data:
        data["api_key"] = mask_secret(data.get("api_key"))
    return data


def resolve_runtime_config(
    config: Optional[Mapping[str, Any]] = None,
    config_path: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> AppConfig:
    merged: Dict[str, Any] = dict(DEFAULT_CONFIG)
    try:
        file_config = load_config(config_path)
    except Exception:
        file_config = {}
    env_config = load_env_config(env)

    _merge_mapping(merged, file_config)
    _merge_mapping(merged, env_config)
    if config:
        _merge_mapping(merged, config)

    return AppConfig.from_mapping(merged)


__all__ = [
    "AppConfig",
    "DEFAULT_CONFIG",
    "DEFAULT_CONFIG_PATH",
    "ENV_ALIASES",
    "load_config",
    "load_env_config",
    "mask_secret",
    "redact_config",
    "resolve_runtime_config",
]
