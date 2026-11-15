"""Diálogo de Preferencias (ver design/03-preferencias.png)."""
from __future__ import annotations

from gi.repository import Gdk, Gio, Gtk

from . import statusline_install

INTERVALS = (1, 5, 8)
COLOR_KEYS = (("color-green", "Verde"), ("color-yellow", "Amarillo"), ("color-red", "Rojo"))


def _section(title):
    lbl = Gtk.Label(xalign=0)
    lbl.set_markup(f"<b>{title}</b>")
    lbl.set_margin_top(6)
    return lbl


def _hint(text):
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.set_line_wrap(True)
    lbl.set_max_width_chars(60)
    lbl.get_style_context().add_class("dim-label")
    lbl.set_margin_start(26)
    return lbl


class PrefsDialog(Gtk.Dialog):
    def __init__(self, settings: Gio.Settings):
        super().__init__(title="Preferencias de Claude Usage")
        self.settings = settings
        self.set_default_size(560, -1)
        self.set_resizable(False)
        self.add_button("Cerrar", Gtk.ResponseType.CLOSE)
        self.connect("response", lambda d, r: d.destroy())

        box = self.get_content_area()
        box.set_spacing(6)
        for m in ("start", "end", "top", "bottom"):
            getattr(box, f"set_margin_{m}")(18)

        # ---- fuente ----
        box.add(_section("Fuente de datos"))
        self.rb_api = Gtk.RadioButton.new_with_label(None, "API de uso de Claude")
        self.rb_sl = Gtk.RadioButton.new_with_label_from_widget(self.rb_api, "Statusline de Claude Code")
        box.add(self.rb_api)
        box.add(_hint("Consulta api.anthropic.com con el token de Claude Code (solo lectura, "
                      "nunca lo renueva). Endpoint no oficial: puede cambiar."))
        row = Gtk.Box(spacing=8, margin_start=26)
        row.add(Gtk.Label(label="Consultar cada"))
        self.cb_interval = Gtk.ComboBoxText()
        for m in INTERVALS:
            self.cb_interval.append(str(m), f"{m} min")
        self.cb_interval.set_active_id(str(settings.get_int("api-interval")))
        self.cb_interval.connect("changed", self._interval_changed)
        row.add(self.cb_interval)
        box.add(row)
        box.add(self.rb_sl)
        box.add(_hint("Lee ~/.cache/claude-usage/usage.json, que escribe un script de statusline. "
                      "Sin red ni token; se actualiza mientras usas Claude Code."))
        row = Gtk.Box(spacing=10, margin_start=26)
        self.bt_install = Gtk.Button()
        self.bt_install.connect("clicked", self._toggle_install)
        self.lb_install = Gtk.Label(xalign=0)
        row.add(self.bt_install)
        row.add(self.lb_install)
        box.add(row)
        self._refresh_install()

        (self.rb_sl if settings.get_string("source") == "statusline" else self.rb_api).set_active(True)
        self.rb_api.connect("toggled", self._source_toggled)
        self._sync_sensitive()

        box.add(Gtk.Separator(margin_top=8, margin_bottom=4))

        # ---- texto ----
        box.add(_section("Texto en el panel"))
        for key, text in (("show-weekly", "Mostrar la fila «Semana»"),
                          ("show-reset-time", "Mostrar a qué hora / qué día se libera cada límite")):
            cb = Gtk.CheckButton(label=text)
            settings.bind(key, cb, "active", Gio.SettingsBindFlags.DEFAULT)
            box.add(cb)

        box.add(Gtk.Separator(margin_top=8, margin_bottom=4))

        # ---- semáforo ----
        box.add(_section("Semáforo (según el porcentaje usado)"))
        grid = Gtk.Grid(column_spacing=10, row_spacing=6)
        for i, (key, text) in enumerate((("yellow-from", "Amarillo desde"), ("red-from", "Rojo desde"))):
            grid.attach(Gtk.Label(label=text, xalign=0), 0, i, 1, 1)
            spin = Gtk.SpinButton.new_with_range(1, 100, 1)
            settings.bind(key, spin, "value", Gio.SettingsBindFlags.DEFAULT)
            grid.attach(spin, 1, i, 1, 1)
            grid.attach(Gtk.Label(label="% usado", xalign=0), 2, i, 1, 1)
        box.add(grid)
        row = Gtk.Box(spacing=10, margin_top=6)
        for key, text in COLOR_KEYS:
            rgba = Gdk.RGBA()
            rgba.parse(settings.get_string(key))
            btn = Gtk.ColorButton.new_with_rgba(rgba)
            btn.connect("color-set", self._color_set, key)
            row.add(btn)
            row.add(Gtk.Label(label=text, margin_end=12))
        box.add(row)
        self.show_all()

    # ---- callbacks ----
    def _interval_changed(self, combo):
        if combo.get_active_id():
            self.settings.set_int("api-interval", int(combo.get_active_id()))

    def _source_toggled(self, *_):
        self.settings.set_string("source", "api" if self.rb_api.get_active() else "statusline")
        self._sync_sensitive()

    def _sync_sensitive(self):
        self.cb_interval.set_sensitive(self.rb_api.get_active())

    def _color_set(self, btn, key):
        c = btn.get_rgba()
        self.settings.set_string(key, "#%02X%02X%02X" % (round(c.red * 255), round(c.green * 255),
                                                         round(c.blue * 255)))

    def _refresh_install(self):
        st = statusline_install.status()
        if st == "installed":
            self.bt_install.set_label("Desinstalar script de statusline")
            self.lb_install.set_markup("<span foreground='#73C991'>• instalado</span>")
        else:
            self.bt_install.set_label("Instalar script de statusline…")
            extra = " (envolverá tu statusline actual)" if st == "other" else ""
            self.lb_install.set_markup(f"<span foreground='#F0B45A'>• no instalado{extra}</span>")

    def _toggle_install(self, _btn):
        installing = statusline_install.status() != "installed"
        try:
            backup = (statusline_install.install if installing else statusline_install.uninstall)()
        except (OSError, ValueError) as e:
            self._message(Gtk.MessageType.ERROR, "No se pudo modificar ~/.claude/settings.json", str(e))
            return
        self._refresh_install()
        detail = f"Respaldo: {backup}" if backup else ""
        if installing:
            self._message(Gtk.MessageType.INFO, "Script de statusline instalado",
                          "Claude Code lo usará desde el próximo mensaje. " + detail)
        else:
            self._message(Gtk.MessageType.INFO, "Script de statusline desinstalado", detail)

    def _message(self, kind, title, text):
        md = Gtk.MessageDialog(transient_for=self, modal=True, message_type=kind,
                               buttons=Gtk.ButtonsType.OK, text=title)
        md.format_secondary_text(text)
        md.run()
        md.destroy()
