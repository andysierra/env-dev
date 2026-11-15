#!/usr/bin/python3
"""Prueba de humo con GTK real, sin mostrar nada en pantalla ni tocar dconf.

Compila el esquema en un directorio temporal, usa el backend de GSettings en memoria,
construye el widget dentro de un Gtk.OffscreenWindow, espera el primer dato de la fuente
elegida y guarda una captura ampliada + el texto del tooltip.

    python3 tools/smoke_test.py [api|statusline] [salida.png]
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
source = sys.argv[1] if len(sys.argv) > 1 else "api"
out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/claude-usage-smoke.png"

schema_dir = tempfile.mkdtemp(prefix="cu-schema-")
subprocess.run(["glib-compile-schemas", "--targetdir", schema_dir, str(ROOT / "data")], check=True)
os.environ["GSETTINGS_SCHEMA_DIR"] = schema_dir
os.environ["GSETTINGS_BACKEND"] = "memory"
os.environ["XDG_CACHE_HOME"] = os.environ.get("SMOKE_CACHE", tempfile.mkdtemp(prefix="cu-cache-"))
sys.path.insert(0, str(ROOT / "src"))

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from claude_usage.applet import ClaudeUsageWidget, make_settings  # noqa: E402

settings = make_settings(None)
settings.set_string("source", source)
win = Gtk.OffscreenWindow()
widget = ClaudeUsageWidget(settings, panel_height=27)
win.add(widget)
win.set_size_request(-1, 27)
win.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(28 / 255, 29 / 255, 31 / 255, 1))
win.show_all()

state = {"done": False}


def check():
    if widget.usage or widget.error:
        state["done"] = True
        Gtk.main_quit()
        return False
    return True


GLib.timeout_add(200, check)
GLib.timeout_add_seconds(20, Gtk.main_quit)
Gtk.main()
while Gtk.events_pending():
    Gtk.main_iteration()

pb = win.get_pixbuf()
pb.scale_simple(pb.get_width() * 6, pb.get_height() * 6, GdkPixbuf.InterpType.NEAREST).savev(out, "png", [], [])
print("estado:", widget.status(), "| error:", widget.error)
print("panel:", [r[:4] for r in widget.rows()] if widget.usage else "Claude")
print("detalle:\n" + widget.detail_markup())
print("captura:", out)
