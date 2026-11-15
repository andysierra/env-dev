"""Modelo de datos: uso de Claude normalizado, venga de la API o del statusline.

Sin dependencias de GTK para poder probarlo con unittest.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Window:
    """Una ventana de límite: porcentaje usado (0-100) y cuándo se reinicia (epoch s)."""
    pct: float
    resets_at: float | None = None
    inferred: bool = False  # True si el valor se dedujo (la ventana ya se reinició)


@dataclass(frozen=True)
class Usage:
    session: Window | None          # ventana de 5 h
    weekly: Window | None           # ventana de 7 días
    fetched_at: float               # cuándo se obtuvo el dato (epoch s)
    source: str                     # "api" | "statusline"
    extras: tuple = field(default_factory=tuple)  # ((etiqueta, pct), ...) p. ej. semanal por modelo


def _num(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _clamp(p: float) -> float:
    return max(0.0, min(100.0, p))


def parse_iso(s) -> float | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_api(data: dict, now: float | None = None) -> Usage:
    """Respuesta de GET /api/oauth/usage. Tolerante: los campos ausentes o nulos se ignoran."""
    now = time.time() if now is None else now
    if not isinstance(data, dict):
        raise ValueError("respuesta de la API no es un objeto JSON")

    def window(key):
        w = data.get(key)
        if not isinstance(w, dict):
            return None
        pct = _num(w.get("utilization"))
        if pct is None:
            return None
        return Window(_clamp(pct), parse_iso(w.get("resets_at")))

    extras = []
    for lim in data.get("limits") or []:
        if not isinstance(lim, dict) or lim.get("kind") != "weekly_scoped":
            continue
        pct = _num(lim.get("percent"))
        scope = lim.get("scope") or {}
        model = (scope.get("model") or {}) if isinstance(scope, dict) else {}
        name = model.get("display_name") if isinstance(model, dict) else None
        if pct is not None and name:
            extras.append((f"Semana ({name})", _clamp(pct)))

    session, weekly = window("five_hour"), window("seven_day")
    if session is None and weekly is None:
        raise ValueError("la respuesta no trae five_hour ni seven_day")
    return Usage(session, weekly, now, "api", tuple(extras))


def parse_rate_limits(rl, fetched_at: float, source: str = "statusline") -> Usage | None:
    """Bloque `rate_limits` del JSON del statusline (o del caché que escribe nuestro script)."""
    if not isinstance(rl, dict):
        return None

    def window(key):
        w = rl.get(key)
        if not isinstance(w, dict):
            return None
        pct = _num(w.get("used_percentage"))
        if pct is None:
            return None
        return Window(_clamp(pct), _num(w.get("resets_at")))

    session, weekly = window("five_hour"), window("seven_day")
    if session is None and weekly is None:
        return None
    return Usage(session, weekly, fetched_at, source)


def parse_cache(data: dict) -> tuple[Usage | None, str | None]:
    """Archivo ~/.cache/claude-usage/usage.json. Devuelve (uso, motivo si no hay uso)."""
    if not isinstance(data, dict):
        return None, "el archivo de caché no es JSON válido"
    updated = _num(data.get("updated_at")) or 0.0
    usage = parse_rate_limits(data.get("rate_limits"), updated)
    if usage is None:
        return None, ("Claude Code todavía no envió datos de uso al statusline "
                      "(llegan tras la primera respuesta de una sesión). Si no aparecen nunca, "
                      "tu plan no los envía: cambia la fuente a API.")
    return usage, None


def effective(w: Window | None, now: float | None = None) -> Window | None:
    """Si la ventana ya se reinició, el uso real es 0 aunque el dato sea viejo."""
    if w is None:
        return None
    now = time.time() if now is None else now
    if w.resets_at is not None and now >= w.resets_at:
        return Window(0.0, None, inferred=True)
    return w


# ---- formato para el tooltip ---------------------------------------------------
_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def fmt_duration(seconds: float) -> str:
    m = max(0, int(seconds // 60))
    if m < 1:
        return "menos de 1 min"
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    if h < 48:
        return f"{h} h {m} min" if m else f"{h} h"
    d, h = divmod(h, 24)
    return f"{d} d {h} h"


def fmt_when(ts: float | None, now: float | None = None) -> str:
    """Hora de liberación: "01:00" si es dentro de las próximas 24 h, si no "vie 20, 23:00"."""
    if ts is None:
        return ""
    now = time.time() if now is None else now
    t = datetime.fromtimestamp(ts)
    hhmm = t.strftime("%H:%M")
    if 0 <= ts - now < 24 * 3600:
        return hhmm
    return f"{_DIAS[t.weekday()]} {t.day}, {hhmm}"


def fmt_countdown(ts: float | None, now: float | None = None) -> str:
    """Cuenta regresiva compacta para el panel: "45m", "1h16", "5d23h", "6d"."""
    if ts is None:
        return ""
    now = time.time() if now is None else now
    m = max(0, int((ts - now) // 60))
    if m < 60:
        return f"{m}m"
    if m < 24 * 60:
        h, m = divmod(m, 60)
        return f"{h}h{m:02d}"
    d, h = divmod(m // 60, 24)
    return f"{d}d{h}h" if h else f"{d}d"


def fmt_reset(ts: float | None, now: float | None = None) -> str:
    """Texto largo para la ventanita: "se libera a la 01:00 (en 1 h 16 min)"."""
    if ts is None:
        return ""
    now = time.time() if now is None else now
    when = fmt_when(ts, now)
    if ts - now < 24 * 3600:
        art = "a la" if when.startswith("01:") else "a las"
        return f"se libera {art} {when} (en {fmt_duration(ts - now)})"
    return f"se libera el {when}"


def level(pct: float, yellow_from: float, red_from: float) -> str:
    """Semáforo según el porcentaje usado: green | yellow | red."""
    if pct >= red_from:
        return "red"
    if pct >= yellow_from:
        return "yellow"
    return "green"


def fmt_pct(p: float) -> str:
    return f"{p:.0f} %" if abs(p - round(p)) < 0.05 else f"{p:.1f} %"
