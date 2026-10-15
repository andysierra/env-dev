#!/bin/zsh
# macOS - en teclados EXTERNOS, Ctrl+tecla actua como Cmd+tecla (Karabiner). Idempotente.
#
#   zsh /ruta/al/repo/macos/ctrl-como-cmd/install.sh [--dry-run]
#
# Spec completo: ../spec-ctrl-como-cmd-teclado-externo.md
set -euo pipefail

HERE=${0:A:h}
DRY=0
[[ ${1:-} == "--dry-run" ]] && DRY=1

RULE_SRC="$HERE/karabiner-rule.json"
KB="$HOME/.config/karabiner/karabiner.json"
CLI="/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli"
STAMP=$(date +%Y%m%d-%H%M%S)
JQ=/usr/bin/jq; [[ -x $JQ ]] || JQ=/opt/homebrew/bin/jq

die() { print -u2 -- "  ERROR $*"; exit 1 }

# 0. preflight
[[ "$(uname -s)" == Darwin ]] || die "esto es solo para macOS"
[[ -x $JQ ]] || die "falta jq -> brew install jq"
[[ -d /Applications/Karabiner-Elements.app ]] \
  || die "falta Karabiner-Elements -> brew install --cask karabiner-elements"
[[ -f "$KB" ]] || die "no existe $KB — abrí Karabiner-Elements una vez (crea el perfil) y repetí"

# 1. regla con el $HOME de esta maquina; los atajos replicados (Ctrl+Option+E / N)
#    solo entran si su script existe aqui (los instalan iterm-yazi y ni-open).
EXISTENTES=""
for s in "$HOME/bin/yazi-desktop.sh" "$HOME/bin/ni-open"; do
  [[ -x "$s" ]] && EXISTENTES+="$s:"
done
export EXISTENTES
RULE=$(sed "s#__HOME__#$HOME#g" "$RULE_SRC" | $JQ '
  .manipulators |= map(select(
    (.to[0].shell_command // "") as $c
    | $c == "" or (($ENV.EXISTENTES | split(":")) | index($c | split(" ")[0])) != null))')
DESC=$($JQ -r .description <<< "$RULE")
print -- "  regla: $DESC ($($JQ '.manipulators | length' <<< "$RULE") manipuladores)"

# 2. lint con el CLI oficial ANTES de tocar karabiner.json
TMP=$(mktemp -t ctrlcmd)
$JQ -n --argjson r "$RULE" '{title: "ctrl-como-cmd", rules: [$r]}' > "$TMP"
"$CLI" --lint-complex-modifications "$TMP" >/dev/null || die "la regla no pasa el lint ($TMP)"

# 3. insertar en el perfil activo, reemplazando la version anterior (misma description)
IDX=$($JQ '[.profiles[].selected] | index(true) // 0' "$KB")
$JQ --argjson i "$IDX" --argjson r "$RULE" --arg d "$DESC" '
  .profiles[$i].complex_modifications.rules =
    ((.profiles[$i].complex_modifications.rules // []) | map(select(.description != $d))) + [$r]
' "$KB" > "$TMP"

if (( DRY )); then
  print -- "  DRY  no se escribe nada; resultado en $TMP"
  exit 0
fi
mkdir -p "$HOME/.config/karabiner/automatic_backups"
cp "$KB" "$HOME/.config/karabiner/automatic_backups/karabiner-pre-ctrlcmd-$STAMP.json"
mv "$TMP" "$KB"
print -- "  OK   instalada en el perfil $IDX; Karabiner recarga solo"
