#!/bin/zsh
# Quita la regla "Ctrl como Cmd en teclado externo" de todos los perfiles de Karabiner.
set -euo pipefail
KB="$HOME/.config/karabiner/karabiner.json"
JQ=/usr/bin/jq; [[ -x $JQ ]] || JQ=/opt/homebrew/bin/jq
DESC=$($JQ -r .description "${0:A:h}/karabiner-rule.json")
TMP=$(mktemp -t ctrlcmd)
cp "$KB" "$HOME/.config/karabiner/automatic_backups/karabiner-pre-ctrlcmd-uninstall-$(date +%Y%m%d-%H%M%S).json"
$JQ --arg d "$DESC" '.profiles[].complex_modifications.rules |= map(select(.description != $d))' "$KB" > "$TMP"
mv "$TMP" "$KB"
echo "revertido: regla \"$DESC\" eliminada"
