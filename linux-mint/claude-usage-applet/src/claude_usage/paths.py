"""Rutas usadas por el applet y por el script de statusline (todas por usuario)."""
import os
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home())


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    return Path(base) / "claude-usage" if base else home() / ".cache" / "claude-usage"


def usage_cache() -> Path:
    return cache_dir() / "usage.json"


def claude_dir() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(base) if base else home() / ".claude"


def credentials() -> Path:
    return claude_dir() / ".credentials.json"


def claude_settings() -> Path:
    return claude_dir() / "settings.json"
