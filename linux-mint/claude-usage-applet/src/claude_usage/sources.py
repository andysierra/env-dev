"""Fuentes de datos: API de uso (consulta periódica) y statusline (archivo vigilado).

Ambas entregan un Usage al callback `on_update(usage)` o un texto de error a
`on_error(msg)`, siempre en el hilo principal de GLib.
"""
from __future__ import annotations

import json
import random
import threading
import time
import urllib.error
import urllib.request

from gi.repository import Gio, GLib

from . import model, paths

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
USER_AGENT = "mint-claude-monitor"
MAX_BACKOFF_S = 30 * 60
MANUAL_MIN_GAP_S = 30
RESET_GRACE_S = 20


class TokenUnavailable(Exception):
    pass


def read_token(path=None) -> str:
    """Lee el access token de Claude Code. Nunca lo renueva: si venció, Claude Code lo hará."""
    path = path or paths.credentials()
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        raise TokenUnavailable("No hay sesión de Claude Code (falta ~/.claude/.credentials.json). "
                               "Inicia sesión con `claude`.")
    except (OSError, ValueError):
        raise TokenUnavailable("No se pudo leer ~/.claude/.credentials.json.")
    oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
    if not isinstance(oauth, dict) or not oauth.get("accessToken"):
        raise TokenUnavailable("Claude Code no tiene sesión de claude.ai (¿usa API key?). "
                               "Usa la fuente statusline.")
    exp = oauth.get("expiresAt")
    if isinstance(exp, (int, float)) and exp / 1000 <= time.time():
        raise TokenUnavailable("El token de Claude Code venció. Abre Claude Code para que lo "
                               "renueve; el applet no lo toca.")
    return oauth["accessToken"]


def fetch_usage(token: str, timeout: float = 15):
    """GET bloqueante. Devuelve (dict, None) o (None, (mensaje, retry_after_s|None))."""
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": "Bearer " + token,
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        retry = None
        ra = e.headers.get("Retry-After") if e.headers else None
        if ra and ra.strip().isdigit():
            retry = int(ra.strip())
        if e.code == 401:
            return None, ("La API rechazó el token (401). Abre Claude Code para renovar la sesión.", retry)
        if e.code == 429:
            return None, ("La API pidió bajar el ritmo (429). Se reintentará más tarde.", retry)
        return None, (f"La API respondió HTTP {e.code}.", retry)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        return None, (f"Sin conexión con la API ({reason}).", None)
    except ValueError:
        return None, ("La API devolvió algo que no es JSON.", None)


class ApiSource:
    """Consulta la API cada `interval_min` minutos con backoff, jitter y consulta en resets_at."""

    def __init__(self, on_update, on_error, interval_min: int = 5):
        self.on_update, self.on_error = on_update, on_error
        self.interval_min = interval_min
        self.failures = 0
        self.next_at = 0.0          # consultar ya al arrancar
        self.last_attempt = 0.0
        self.last_success = 0.0
        self.last_usage = None
        self.in_flight = False
        self.timer = None

    # -- ciclo de vida --
    def start(self):
        self.timer = GLib.timeout_add_seconds(15, self._tick)
        self._tick()

    def stop(self):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None

    def set_interval(self, minutes: int):
        self.interval_min = max(1, int(minutes))
        if self.failures == 0 and self.last_success:
            self.next_at = self.last_success + self._jittered(self.interval_min * 60)

    def refresh_now(self):
        if time.time() - self.last_attempt >= MANUAL_MIN_GAP_S:
            self.next_at = 0.0
            self._tick()

    # -- lógica --
    @staticmethod
    def _jittered(seconds: float) -> float:
        return seconds * random.uniform(0.9, 1.1)

    def _reset_due(self, now) -> bool:
        u = self.last_usage
        if not u:
            return False
        for w in (u.session, u.weekly):
            if w and w.resets_at and self.last_success < w.resets_at + RESET_GRACE_S <= now:
                return True
        return False

    def _tick(self):
        now = time.time()
        if not self.in_flight and (now >= self.next_at or self._reset_due(now)):
            self._start_fetch(now)
        return True

    def _start_fetch(self, now):
        try:
            token = read_token()
        except TokenUnavailable as e:
            # sin red: se vuelve a mirar el archivo en el próximo tick (15 s)
            self.next_at = now + 15
            self.on_error(str(e))
            return
        self.in_flight = True
        self.last_attempt = now
        threading.Thread(target=self._worker, args=(token,), daemon=True).start()

    def _worker(self, token):
        data, err = fetch_usage(token)
        GLib.idle_add(self._done, data, err)

    def _done(self, data, err):
        self.in_flight = False
        now = time.time()
        if err is None:
            try:
                usage = model.parse_api(data, now)
            except ValueError as e:
                err = (f"Formato inesperado de la API: {e}", None)
        if err is not None:
            msg, retry = err
            self.failures += 1
            backoff = min(MAX_BACKOFF_S, self.interval_min * 60 * (2 ** self.failures))
            self.next_at = now + max(backoff, retry or 0)
            self.on_error(msg)
            return False
        self.failures = 0
        self.last_success = now
        self.last_usage = usage
        self.next_at = now + self._jittered(self.interval_min * 60)
        self.on_update(usage)
        return False

    def stale_after(self) -> float:
        """Segundos sin dato nuevo a partir de los cuales se considera desactualizado."""
        return max(3 * self.interval_min * 60, 15 * 60)


class StatuslineSource:
    """Vigila ~/.cache/claude-usage/usage.json, que escribe bin/claude-usage-statusline."""

    def __init__(self, on_update, on_error):
        self.on_update, self.on_error = on_update, on_error
        self.monitor = None
        self.path = paths.usage_cache()
        self.reload_id = None

    def start(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        d = Gio.File.new_for_path(str(self.path.parent))
        self.monitor = d.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.monitor.connect("changed", self._changed)
        self.reload()

    def stop(self):
        if self.monitor:
            self.monitor.cancel()
            self.monitor = None
        if self.reload_id:
            GLib.source_remove(self.reload_id)
            self.reload_id = None

    def refresh_now(self):
        self.reload()

    def _changed(self, _mon, f, other, _ev):
        names = {f.get_basename() if f else None, other.get_basename() if other else None}
        if self.path.name in names and not self.reload_id:
            # agrupa ráfagas de eventos (rename + changes-done)
            self.reload_id = GLib.timeout_add(200, self._deferred_reload)

    def _deferred_reload(self):
        self.reload_id = None
        self.reload()
        return False

    def reload(self):
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            self.on_error("No existe ~/.cache/claude-usage/usage.json. Instala el script de "
                          "statusline desde Preferencias, o cambia la fuente a API.")
            return
        except (OSError, ValueError):
            return  # escritura a medias: llegará otro evento
        usage, why = model.parse_cache(data)
        if usage is None:
            self.on_error(why)
        else:
            self.on_update(usage)
