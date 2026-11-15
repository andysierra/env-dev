"""Widget principal: dos filas de texto en columnas alineadas, con color de semáforo.

    Ahora   43%  1h16  01:00
    Semana  18%  6d    vie 20, 23:00

Clic izquierdo abre una ventanita con el detalle completo. Sirve dentro del panel o en una
ventana suelta (modo --window, para probar sin tocar el panel).
"""
from __future__ import annotations

import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

from . import SCHEMA_ID, VERSION, model  # noqa: E402
from .sources import ApiSource, StatuslineSource  # noqa: E402

TICK_S = 30            # refresco del texto (cuenta regresiva)
USAGE_URL_WEB = "https://claude.ai/settings/usage"
GRAY = "#8A8A90"
LEVEL_KEYS = {"green": "color-green", "yellow": "color-yellow", "red": "color-red"}


def make_settings(path: str | None) -> Gio.Settings:
    return Gio.Settings.new_with_path(SCHEMA_ID, path or "/org/mate/panel/objects/claude-usage-standalone/prefs/")


def esc(s: str) -> str:
    return GLib.markup_escape_text(s)


class ClaudeUsageWidget(Gtk.EventBox):
    def __init__(self, settings: Gio.Settings, panel_height: int = 27):
        super().__init__()
        self.set_visible_window(False)
        self.settings = settings
        self.usage: model.Usage | None = None
        self.error: str | None = None
        self.source = None
        self.prefs = None
        self.popup = None
        self.panel_height = panel_height

        self.grid = Gtk.Grid(column_spacing=5, row_spacing=0, valign=Gtk.Align.CENTER)
        self.grid.set_margin_start(3)
        self.grid.set_margin_end(3)
        self.cells = []
        for r in range(2):
            row = []
            for c in range(4):
                lbl = Gtk.Label(xalign=1.0 if c == 1 else 0.0)
                lbl.set_no_show_all(True)  # render() decide qué se ve
                self.grid.attach(lbl, c, r, 1, 1)
                row.append(lbl)
            self.cells.append(row)
        self.single = Gtk.Label()  # para "Claude" (sin datos)
        self.single.set_no_show_all(True)
        self.grid.attach(self.single, 0, 0, 4, 2)
        self.add(self.grid)

        self.css = Gtk.CssProvider()
        self.get_style_context()  # asegura contexto
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.grid.get_style_context().add_class("claude-usage")
        self.set_panel_height(panel_height)

        self.set_has_tooltip(True)
        self.connect("query-tooltip", self._tooltip)
        self.settings.connect("changed", self._setting_changed)
        self._start_source()
        self.tick = GLib.timeout_add_seconds(TICK_S, self._on_tick)
        self.connect("destroy", self._on_destroy)

    # ---- tamaño de letra según el alto del panel ----
    def set_panel_height(self, h: int):
        self.panel_height = max(16, h)
        px = max(7, int((self.panel_height - 1) / 2 * 0.78))
        self.css.load_from_data(f".claude-usage label {{ font-size: {px}px; padding: 0; }}".encode())

    # ---- fuentes ----
    def _start_source(self):
        if self.source:
            self.source.stop()
        self.usage, self.error = None, None
        if self.settings.get_string("source") == "statusline":
            self.source = StatuslineSource(self._on_update, self._on_error)
        else:
            self.source = ApiSource(self._on_update, self._on_error, self.settings.get_int("api-interval"))
        self.source.start()
        self.render()

    def _on_update(self, usage):
        self.usage, self.error = usage, None
        self.render()

    def _on_error(self, msg):
        self.error = msg
        self.render()

    def refresh_now(self):
        self.source.refresh_now()

    def _on_tick(self):
        self.render()
        return True

    # ---- estado ----
    def current(self, now=None):
        if not self.usage:
            return None, None
        return model.effective(self.usage.session, now), model.effective(self.usage.weekly, now)

    def status(self, now=None) -> str:
        now = time.time() if now is None else now
        if not self.usage:
            return "nodata"
        if isinstance(self.source, ApiSource):
            if self.error or now - self.usage.fetched_at > self.source.stale_after():
                return "stale"
        return "ok"

    def color_for(self, pct: float) -> str:
        lvl = model.level(pct, self.settings.get_int("yellow-from"), self.settings.get_int("red-from"))
        return self.settings.get_string(LEVEL_KEYS[lvl])

    def _setting_changed(self, _s, key):
        if key == "source":
            self._start_source()
            return
        if key == "api-interval" and isinstance(self.source, ApiSource):
            self.source.set_interval(self.settings.get_int("api-interval"))
        self.render()

    # ---- texto del panel ----
    def rows(self, now=None):
        """[(nombre, pct_txt, cuenta, cuando, color)] para el panel."""
        now = time.time() if now is None else now
        st = self.status(now)
        s, w = self.current(now)
        out = []
        for name, win in (("Ahora", s), ("Semana", w)):
            if win is None:
                continue
            if name == "Semana" and not self.settings.get_boolean("show-weekly"):
                continue
            pct = f"{win.pct:.0f}%" + ("?" if st == "stale" else "")
            if win.inferred:
                cnt, when = "nuevo", ""
            else:
                cnt, when = model.fmt_countdown(win.resets_at, now), model.fmt_when(win.resets_at, now)
            if not self.settings.get_boolean("show-reset-time"):
                when = ""
            color = GRAY if st == "stale" else self.color_for(win.pct)
            out.append((name, pct, cnt, when, color))
        return out

    def render(self):
        rows = self.rows() if self.status() != "nodata" else []
        for r in range(2):
            for c in range(4):
                lbl = self.cells[r][c]
                if r < len(rows):
                    name, pct, cnt, when, color = rows[r]
                    text = (name, pct, cnt, when)[c]
                    weight = " weight='bold'" if c == 1 else ""
                    lbl.set_markup(f"<span foreground='{color}'{weight}>{esc(text)}</span>")
                    lbl.show()
                else:
                    lbl.set_text("")
                    lbl.hide()
        if rows:
            self.single.hide()
        else:
            self.single.set_markup(f"<span foreground='{GRAY}'>Claude</span>")
            self.single.show()
        if self.popup:
            self.popup.update()

    # ---- detalle (tooltip y ventanita) ----
    def detail_markup(self, now=None) -> str:
        now = time.time() if now is None else now
        st = self.status(now)
        src_name = "API" if self.settings.get_string("source") == "api" else "statusline"
        if st == "nodata":
            lines = ["<b>Claude usage — sin datos</b>"]
            if self.error:
                lines.append(esc(self.error))
            elif isinstance(self.source, ApiSource):
                lines.append("Consultando la API…")
            lines.append(f"<span alpha='65%'>Fuente: {src_name}</span>")
            return "\n".join(lines)
        s, w = self.current(now)
        title = "Claude usage" + (" — dato desactualizado" if st == "stale" else "")
        lines = [f"<b>{title}</b>"]
        for name, win in (("Ahora", s), ("Semana", w)):
            if win is None:
                continue
            color = GRAY if st == "stale" else self.color_for(win.pct)
            pct = f"<span foreground='{color}' weight='bold'>{model.fmt_pct(win.pct)} usado</span>"
            if win.inferred:
                tail = " · bloque nuevo (el anterior ya se liberó)"
            else:
                reset = model.fmt_reset(win.resets_at, now)
                tail = f" · {reset}" if reset else ""
            lines.append(f"{name}:  {pct}{esc(tail)}")
        for label, pct in self.usage.extras:
            lines.append(f"{esc(label)}:  {model.fmt_pct(pct)} usado")
        if st == "stale" and self.error:
            lines.append(f"<span foreground='#F0B45A'>{esc(self.error)}</span>")
        age = model.fmt_duration(now - self.usage.fetched_at)
        foot = (f"Fuente: API · actualizado hace {age}" if src_name == "API"
                else f"Fuente: statusline · último cambio hace {age}")
        lines.append(f"<span alpha='65%'>{foot}</span>")
        lines.append("<span alpha='50%' size='small'>Ahora = bloque de 5 h que empieza con tu primer "
                     "mensaje · Semana = bloque de 7 días</span>")
        return "\n".join(lines)

    def _tooltip(self, _w, _x, _y, _kb, tip):
        if self.popup and self.popup.get_visible():
            return False
        tip.set_markup(self.detail_markup())
        return True

    def toggle_popup(self):
        if self.popup and self.popup.get_visible():
            self.popup.destroy()
            return
        self.popup = DetailPopup(self)
        self.popup.connect("destroy", lambda *_: setattr(self, "popup", None))
        self.popup.show_near(self)

    # ---- acciones de menú ----
    def show_prefs(self):
        from .prefs import PrefsDialog
        if self.prefs:
            self.prefs.present()
            return
        self.prefs = PrefsDialog(self.settings)
        self.prefs.connect("destroy", lambda *_: setattr(self, "prefs", None))
        self.prefs.present()

    def open_web(self):
        Gtk.show_uri_on_window(None, USAGE_URL_WEB, Gtk.get_current_event_time())

    def show_about(self):
        d = Gtk.AboutDialog(program_name="Claude Usage", version=VERSION,
                            comments="Uso de Claude (bloque de 5 h y semanal) en el panel de MATE.",
                            logo_icon_name="utilities-system-monitor", license_type=Gtk.License.GPL_2_0)
        d.connect("response", lambda d, r: d.destroy())
        d.present()

    def _on_destroy(self, *_):
        if self.source:
            self.source.stop()
        GLib.source_remove(self.tick)
        if self.popup:
            self.popup.destroy()


class DetailPopup(Gtk.Window):
    """Ventanita sin bordes junto al applet, como el calendario del reloj."""

    def __init__(self, owner: ClaudeUsageWidget):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.owner = owner
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.OUT)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=10)
        self.label = Gtk.Label(xalign=0)
        box.add(self.label)
        buttons = Gtk.Box(spacing=6)
        for text, cb in (("Actualizar", owner.refresh_now), ("Abrir claude.ai", owner.open_web)):
            b = Gtk.Button(label=text)
            b.connect("clicked", lambda _b, f=cb: f())
            buttons.add(b)
        box.add(buttons)
        frame.add(box)
        self.add(frame)
        self.connect("focus-out-event", lambda *_: self.destroy())
        self.connect("key-press-event", self._key)
        self.update()

    def _key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def update(self):
        self.label.set_markup(self.owner.detail_markup())

    def show_near(self, widget):
        self.show_all()
        win = widget.get_window()
        if win is None:
            self.present()
            return
        _, ox, oy = win.get_origin()
        alloc = widget.get_allocation()
        ox, oy = ox + alloc.x, oy + alloc.y
        w, h = self.get_size()
        mon = widget.get_display().get_monitor_at_window(win).get_geometry()
        x = min(max(mon.x, ox + alloc.width // 2 - w // 2), mon.x + mon.width - w)
        # panel abajo -> ventanita arriba; panel arriba -> abajo
        y = oy - h - 4 if oy + alloc.height > mon.y + mon.height / 2 else oy + alloc.height + 4
        self.move(x, y)
        self.present_with_time(Gtk.get_current_event_time())
