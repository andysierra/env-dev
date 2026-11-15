#!/bin/bash
# Desinstala el applet Claude Usage. No borra ~/.cache/claude-usage ni toca ~/.claude/settings.json
# (para quitar el script de statusline usa Preferencias > Desinstalar antes de correr esto).
set -euo pipefail
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
PREFIX="$DATA_HOME/mint-claude-monitor"
pkill -f "$PREFIX/src/claude_usage_applet.py" 2>/dev/null || true
rm -rf "$PREFIX"
rm -f "$DATA_HOME/dbus-1/services/org.mate.panel.applet.ClaudeUsageAppletFactory.service"
rm -f "$DATA_HOME/glib-2.0/schemas/org.mate.panel.applet.claude-usage.gschema.xml"
glib-compile-schemas "$DATA_HOME/glib-2.0/schemas" 2>/dev/null || true
sudo rm -f /usr/share/mate-panel/applets/org.mate.panel.ClaudeUsageApplet.mate-panel-applet
echo "Desinstalado. Quita el applet del panel si sigue ahí (clic derecho > Quitar del panel)."
