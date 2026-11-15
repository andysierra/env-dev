#!/usr/bin/python3
"""Punto de entrada del applet Claude Usage para el panel de MATE.

  claude_usage_applet.py            -> fábrica de applets (la lanza mate-panel por D-Bus)
  claude_usage_applet.py --window   -> ventana suelta para probar sin tocar el panel
"""
import os
import sys
import warnings

# Gtk.Action/ActionGroup están obsoletos en GTK3, pero es lo que pide MatePanelApplet.setup_menu
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from claude_usage.applet import ClaudeUsageWidget, make_settings  # noqa: E402

FACTORY_ID = "ClaudeUsageAppletFactory"
APPLET_ID = "ClaudeUsageApplet"

MENU_XML = """
<menuitem name="Refresh" action="Refresh" />
<menuitem name="OpenWeb" action="OpenWeb" />
<separator />
<menuitem name="SourceApi" action="SourceApi" />
<menuitem name="SourceStatusline" action="SourceStatusline" />
<separator />
<menuitem name="Prefs" action="Prefs" />
<menuitem name="About" action="About" />
"""


def build_actions(widget):
    group = Gtk.ActionGroup(name="ClaudeUsageActions")
    for name, label, icon, cb in (
            ("Refresh", "Actualizar ahora", "view-refresh", widget.refresh_now),
            ("OpenWeb", "Abrir uso en claude.ai", "web-browser", widget.open_web),
            ("Prefs", "Preferencias", "preferences-system", widget.show_prefs),
            ("About", "Acerca de", "help-about", widget.show_about)):
        a = Gtk.Action(name=name, label=label, icon_name=icon)
        a.connect("activate", lambda _a, f=cb: f())
        group.add_action(a)
    ra = Gtk.RadioAction(name="SourceApi", label="Fuente: API", value=0)
    rs = Gtk.RadioAction(name="SourceStatusline", label="Fuente: statusline", value=1)
    rs.join_group(ra)
    (rs if widget.settings.get_string("source") == "statusline" else ra).set_active(True)

    def changed(action, current):
        widget.settings.set_string("source", "statusline" if current.get_current_value() == 1 else "api")
    ra.connect("changed", changed)

    def sync(*_):
        want = rs if widget.settings.get_string("source") == "statusline" else ra
        if not want.get_active():
            want.set_active(True)
    widget.settings.connect("changed::source", sync)
    group.add_action(ra)
    group.add_action(rs)
    return group


def applet_factory(applet, iid, _data):
    if iid != APPLET_ID:
        return False
    gi.require_version("MatePanelApplet", "4.0")
    from gi.repository import MatePanelApplet

    settings = make_settings(applet.get_preferences_path())
    widget = ClaudeUsageWidget(settings, panel_height=applet.get_size())
    applet.add(widget)
    applet.set_flags(MatePanelApplet.AppletFlags.EXPAND_MINOR)
    applet.connect("change-size", lambda _a, size: widget.set_panel_height(size))
    applet.setup_menu(MENU_XML, build_actions(widget))

    def press(_w, ev):
        if ev.button == 1:
            widget.toggle_popup()
            return True
        return False
    applet.connect("button-press-event", press)
    applet.show_all()
    return True


def standalone():
    win = Gtk.Window(title="Claude Usage (prueba)")
    settings = make_settings(None)
    widget = ClaudeUsageWidget(settings)
    box = Gtk.Box(spacing=6, margin=6)
    box.add(widget)
    for label, cb in (("Detalle", widget.toggle_popup), ("Actualizar", widget.refresh_now),
                      ("Preferencias", widget.show_prefs)):
        b = Gtk.Button(label=label)
        b.connect("clicked", lambda _b, f=cb: f())
        box.add(b)
    win.add(box)
    win.set_default_size(-1, 27 + 12)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    if "--window" in sys.argv:
        standalone()
    else:
        gi.require_version("MatePanelApplet", "4.0")
        from gi.repository import MatePanelApplet
        MatePanelApplet.Applet.factory_main(FACTORY_ID, True, MatePanelApplet.Applet.__gtype__,
                                            applet_factory, None)
