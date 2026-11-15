"""Instala / desinstala el script de statusline en ~/.claude/settings.json.

Si ya había un statusline configurado, no se reemplaza: se envuelve (el script nuestro lo
ejecuta y devuelve su salida). Antes de escribir se guarda una copia de respaldo.
"""
from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import tempfile
import time
from pathlib import Path

from . import paths

WRAP_FLAG = "--wrap-b64"


def script_path() -> Path:
    """Ruta absoluta del script instalado (junto a este paquete: <prefijo>/bin/...)."""
    return Path(__file__).resolve().parent.parent.parent / "bin" / "claude-usage-statusline"


def _load(settings: Path) -> dict:
    try:
        data = json.loads(settings.read_text())
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError("settings.json no es un objeto JSON")
    return data


def _write(settings: Path, data: dict) -> Path | None:
    backup = None
    if settings.exists():
        backup = settings.with_name(f"settings.json.bak-claude-usage-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(settings, backup)
    settings.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=settings.parent, prefix=".settings-")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, settings)
    return backup


def _ours(cmd: str, script: Path) -> bool:
    try:
        first = shlex.split(cmd)[0]
    except (ValueError, IndexError):
        return False
    return first == str(script) or first.endswith("/claude-usage-statusline")


def status(settings: Path | None = None, script: Path | None = None) -> str:
    """'installed' | 'not_installed' | 'other' (hay otro statusline; se envolvería)."""
    settings, script = settings or paths.claude_settings(), script or script_path()
    try:
        sl = _load(settings).get("statusLine")
    except (OSError, ValueError):
        return "not_installed"
    if not isinstance(sl, dict) or not sl.get("command"):
        return "not_installed"
    return "installed" if _ours(sl["command"], script) else "other"


def install(settings: Path | None = None, script: Path | None = None) -> Path | None:
    settings, script = settings or paths.claude_settings(), script or script_path()
    data = _load(settings)
    sl = data.get("statusLine") if isinstance(data.get("statusLine"), dict) else {}
    old = sl.get("command") if sl.get("type", "command") == "command" else None
    if old and _ours(old, script):
        return None  # ya instalado
    cmd = shlex.quote(str(script))
    if old:
        cmd += f" {WRAP_FLAG} " + base64.b64encode(old.encode()).decode()
    new = dict(sl)
    new.update({"type": "command", "command": cmd})
    data["statusLine"] = new
    return _write(settings, data)


def uninstall(settings: Path | None = None, script: Path | None = None) -> Path | None:
    settings, script = settings or paths.claude_settings(), script or script_path()
    data = _load(settings)
    sl = data.get("statusLine")
    if not isinstance(sl, dict) or not _ours(sl.get("command", ""), script):
        return None
    parts = shlex.split(sl["command"])
    if WRAP_FLAG in parts and parts.index(WRAP_FLAG) + 1 < len(parts):
        old = base64.b64decode(parts[parts.index(WRAP_FLAG) + 1]).decode()
        sl = dict(sl)
        sl["command"] = old
        data["statusLine"] = sl
    else:
        del data["statusLine"]
    return _write(settings, data)
