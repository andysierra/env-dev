"""Pruebas sin GTK: modelo y formato, script de statusline e instalador.

    python3 -m unittest discover -s tests -v
"""
import base64
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from claude_usage import model, statusline_install  # noqa: E402

SCRIPT = ROOT / "bin" / "claude-usage-statusline"

# Respuesta real de /api/oauth/usage (recortada), plan team, 2026-11-14
API_SAMPLE = {
    "five_hour": {"utilization": 20.0, "resets_at": "2026-11-15T06:00:00.920692+00:00"},
    "seven_day": {"utilization": 15.0, "resets_at": "2026-11-21T04:00:00.920712+00:00"},
    "seven_day_opus": None,
    "limits": [
        {"kind": "session", "percent": 20, "scope": None},
        {"kind": "weekly_scoped", "percent": 4, "scope": {"model": {"id": None, "display_name": "Fable"}}},
    ],
}
# Bloque rate_limits real recibido por el statusline (plan team)
RL_SAMPLE = {"five_hour": {"used_percentage": 24, "resets_at": 1794722400},
             "seven_day": {"used_percentage": 15, "resets_at": 1795233600}}


class ModelTests(unittest.TestCase):
    def test_parse_api(self):
        u = model.parse_api(API_SAMPLE, now=100)
        self.assertEqual(u.session.pct, 20.0)
        self.assertEqual(u.weekly.pct, 15.0)
        self.assertAlmostEqual(u.session.resets_at, 1794722400.920692, places=3)
        self.assertEqual(u.extras, (("Semana (Fable)", 4.0),))
        self.assertEqual(u.source, "api")

    def test_parse_api_tolerates_missing(self):
        u = model.parse_api({"five_hour": {"utilization": 3}, "seven_day": None, "limits": "x"})
        self.assertEqual(u.session.pct, 3)
        self.assertIsNone(u.weekly)
        self.assertIsNone(u.session.resets_at)
        with self.assertRaises(ValueError):
            model.parse_api({"foo": 1})
        with self.assertRaises(ValueError):
            model.parse_api([])

    def test_clamp(self):
        u = model.parse_api({"five_hour": {"utilization": 130}})
        self.assertEqual(u.session.pct, 100)

    def test_parse_cache(self):
        u, why = model.parse_cache({"updated_at": 50, "rate_limits": RL_SAMPLE})
        self.assertIsNone(why)
        self.assertEqual((u.session.pct, u.weekly.pct), (24, 15))
        self.assertEqual(u.session.resets_at, 1794722400)
        self.assertEqual(u.fetched_at, 50)
        u, why = model.parse_cache({"updated_at": 50, "rate_limits": None})
        self.assertIsNone(u)
        self.assertIn("API", why)

    def test_effective_reset(self):
        w = model.Window(90, resets_at=1000)
        self.assertEqual(model.effective(w, now=999).pct, 90)
        e = model.effective(w, now=1000)
        self.assertEqual(e.pct, 0)
        self.assertTrue(e.inferred)
        self.assertIsNone(model.effective(None))

    def test_formatting(self):
        self.assertEqual(model.fmt_duration(30), "menos de 1 min")
        self.assertEqual(model.fmt_duration(4 * 3600 + 18 * 60), "4 h 18 min")
        self.assertEqual(model.fmt_pct(20.0), "20 %")
        self.assertEqual(model.fmt_pct(23.5), "23.5 %")

    def test_panel_text(self):
        import time as _t
        now = _t.mktime((2026, 11, 14, 23, 44, 0, 0, 0, -1))      # sáb 14 nov, 23:44 local
        ahora = now + 76 * 60                                       # 01:00 del domingo
        semana = _t.mktime((2026, 11, 20, 23, 0, 0, 0, 0, -1))      # vie 20, 23:00
        self.assertEqual(model.fmt_countdown(ahora, now), "1h16")
        self.assertEqual(model.fmt_when(ahora, now), "01:00")       # < 24 h: solo la hora
        self.assertEqual(model.fmt_countdown(semana, now), "5d23h")
        self.assertEqual(model.fmt_countdown(now + 2 * 86400 + 30, now), "2d")
        self.assertEqual(model.fmt_when(semana, now), "vie 20, 23:00")
        self.assertEqual(model.fmt_countdown(now + 45 * 60, now), "45m")
        self.assertEqual(model.fmt_reset(ahora, now), "se libera a la 01:00 (en 1 h 16 min)")
        self.assertEqual(model.fmt_reset(semana, now), "se libera el vie 20, 23:00")
        self.assertEqual(model.fmt_countdown(None), "")

    def test_semaphore(self):
        self.assertEqual(model.level(0, 60, 85), "green")
        self.assertEqual(model.level(59.9, 60, 85), "green")
        self.assertEqual(model.level(60, 60, 85), "yellow")
        self.assertEqual(model.level(84, 60, 85), "yellow")
        self.assertEqual(model.level(85, 60, 85), "red")
        self.assertEqual(model.level(70, 90, 50), "red")  # umbrales cruzados: gana rojo


class StatuslineScriptTests(unittest.TestCase):
    def run_script(self, payload, cache, *args):
        env = dict(os.environ, XDG_CACHE_HOME=cache)
        return subprocess.run([str(SCRIPT), *args], input=json.dumps(payload).encode(),
                              capture_output=True, env=env, timeout=10)

    def test_writes_cache_and_summary(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.run_script({"rate_limits": RL_SAMPLE}, d)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout.decode().strip(), "5h 24% · 7d 15%")
            data = json.loads((Path(d) / "claude-usage" / "usage.json").read_text())
            self.assertEqual(data["rate_limits"], RL_SAMPLE)

    def test_no_rewrite_when_unchanged_and_keeps_good_data(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "claude-usage" / "usage.json"
            self.run_script({"rate_limits": RL_SAMPLE}, d)
            first = f.read_text()
            self.run_script({"rate_limits": RL_SAMPLE}, d)
            self.assertEqual(f.read_text(), first)            # sin cambios: no reescribe
            self.run_script({"model": {}}, d)                  # sesión nueva sin rate_limits
            self.assertEqual(json.loads(f.read_text())["rate_limits"], RL_SAMPLE)

    def test_without_rate_limits_first_time(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.run_script({"model": {}}, d)
            self.assertEqual(p.stdout.decode().strip(), "Claude")
            data = json.loads((Path(d) / "claude-usage" / "usage.json").read_text())
            self.assertIsNone(data["rate_limits"])

    def test_wraps_previous_statusline(self):
        with tempfile.TemporaryDirectory() as d:
            prev = "python3 -c \"import sys,json; print('prev:'+json.load(sys.stdin)['x'])\""
            b64 = base64.b64encode(prev.encode()).decode()
            p = self.run_script({"x": "ok", "rate_limits": RL_SAMPLE}, d, "--wrap-b64", b64)
            self.assertEqual(p.stdout.decode().strip(), "prev:ok")
            self.assertTrue((Path(d) / "claude-usage" / "usage.json").exists())

    def test_garbage_input(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, XDG_CACHE_HOME=d)
            p = subprocess.run([str(SCRIPT)], input=b"not json", capture_output=True, env=env, timeout=10)
            self.assertEqual(p.returncode, 0)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Path(self.tmp.name) / "settings.json"
        self.script = Path("/opt/x/bin/claude-usage-statusline")

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_fresh_and_uninstall(self):
        self.settings.write_text(json.dumps({"theme": "dark"}))
        self.assertEqual(statusline_install.status(self.settings, self.script), "not_installed")
        backup = statusline_install.install(self.settings, self.script)
        self.assertTrue(backup and backup.exists())
        data = json.loads(self.settings.read_text())
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["statusLine"], {"type": "command", "command": str(self.script)})
        self.assertEqual(statusline_install.status(self.settings, self.script), "installed")
        self.assertIsNone(statusline_install.install(self.settings, self.script))  # idempotente
        statusline_install.uninstall(self.settings, self.script)
        self.assertEqual(json.loads(self.settings.read_text()), {"theme": "dark"})

    def test_wraps_existing_and_restores(self):
        old = "bash ~/.claude/mi-statusline.sh --flag 'a b'"
        self.settings.write_text(json.dumps({"statusLine": {"type": "command", "command": old,
                                                            "padding": 1}}))
        self.assertEqual(statusline_install.status(self.settings, self.script), "other")
        statusline_install.install(self.settings, self.script)
        sl = json.loads(self.settings.read_text())["statusLine"]
        parts = shlex.split(sl["command"])
        self.assertEqual(parts[0], str(self.script))
        self.assertEqual(base64.b64decode(parts[2]).decode(), old)
        self.assertEqual(sl["padding"], 1)
        statusline_install.uninstall(self.settings, self.script)
        self.assertEqual(json.loads(self.settings.read_text())["statusLine"],
                         {"type": "command", "command": old, "padding": 1})

    def test_missing_settings_file(self):
        statusline_install.install(self.settings, self.script)
        self.assertEqual(statusline_install.status(self.settings, self.script), "installed")


if __name__ == "__main__":
    unittest.main()
