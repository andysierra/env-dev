#!/bin/bash
# Instala el applet Claude Usage para el usuario actual.
# Todo queda en ~/.local salvo un archivo de descripción del applet, que mate-panel solo busca
# en /usr/share/mate-panel/applets (ese paso pide sudo).
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
PREFIX="$DATA_HOME/mint-claude-monitor"
APPLET_BIN="$PREFIX/src/claude_usage_applet.py"
SCHEMA_DIR="$DATA_HOME/glib-2.0/schemas"
DBUS_DIR="$DATA_HOME/dbus-1/services"
PANEL_DIR=/usr/share/mate-panel/applets
DESC=org.mate.panel.ClaudeUsageApplet.mate-panel-applet
SERVICE=org.mate.panel.applet.ClaudeUsageAppletFactory.service

echo "==> Código en $PREFIX"
rm -rf "$PREFIX"
mkdir -p "$PREFIX"
cp -r "$REPO/src" "$REPO/bin" "$PREFIX/"
find "$PREFIX" -name '__pycache__' -prune -exec rm -rf {} +
chmod +x "$APPLET_BIN" "$PREFIX/bin/claude-usage-statusline"

echo "==> Esquema GSettings en $SCHEMA_DIR"
mkdir -p "$SCHEMA_DIR"
cp "$REPO/data/org.mate.panel.applet.claude-usage.gschema.xml" "$SCHEMA_DIR/"
glib-compile-schemas "$SCHEMA_DIR"

echo "==> Servicio D-Bus en $DBUS_DIR"
mkdir -p "$DBUS_DIR"
sed "s|@APPLET_BIN@|$APPLET_BIN|" "$REPO/data/$SERVICE.in" > "$DBUS_DIR/$SERVICE"

tmp="$(mktemp)"
sed "s|@APPLET_BIN@|$APPLET_BIN|" "$REPO/data/$DESC.in" > "$tmp"
if cmp -s "$tmp" "$PANEL_DIR/$DESC"; then
  echo "==> Descripción del applet en $PANEL_DIR: sin cambios (no hace falta sudo)"
else
  echo "==> Descripción del applet en $PANEL_DIR (sudo)"
  sudo install -m 644 "$tmp" "$PANEL_DIR/$DESC"
fi
rm -f "$tmp"

# restos de la versión con gráfica
rm -f "${XDG_CACHE_HOME:-$HOME/.cache}/claude-usage/history.json"

# si el applet ya estaba corriendo, que el panel lo relance con el código nuevo
pkill -f "^/usr/bin/python3 $APPLET_BIN" 2>/dev/null || true

cat <<MSG

Listo. Para agregarlo: clic derecho en el panel > "Añadir al panel…" > "Uso de Claude".
Si no aparece en la lista, reinicia el panel:  mate-panel --replace &disown
Script de statusline (opcional): Preferencias del applet > "Instalar script de statusline…".
MSG
