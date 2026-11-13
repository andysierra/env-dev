#!/bin/bash
# Super+Alt+E: ventana nueva de WezTerm, maximizada, con yazi en ~/Escritorio.
# Siempre ventana nueva (mismo criterio que el Mac desde 2026-10-01).
# --always-new-process: proceso propio → corre el evento gui-startup de wezterm.lua, que maximiza
#   las ventanas cuyo comando es "yazi". yazi va directo (sin shell detrás): al salir con q se cierra.
# wezterm (/usr/bin) y yazi (/usr/local/bin) están en el PATH de la sesión de MATE.
#
# Antes de abrir, barre (GC) los yazi olvidados (equivalente a sweep() de macos/iterm-yazi/yazi-desktop.js):
#   - Candidatos: solo yazi abiertos por este atajo = padre wezterm-gui lanzado con
#     "--always-new-process ... -- yazi", y ese wezterm sin otras pestañas/paneles (único hijo: yazi).
#   - Nunca toca: yazi a mano desde un shell (`y`, padre bash), ni yazi con hijos vivos
#     (p.ej. el bash de ":" o un editor abierto desde yazi).
#   - Conserva los KEEP más recientes por atime del pty (= último input) y cierra el resto
#     matando su wezterm-gui (la ventana desaparece entera).
# Uso: yazi-term.sh [--dry-sweep]   (dry: solo reporta, no abre ni cierra)
# Log: ~/.cache/yazi-term-gc.log

KEEP=2
LOG="$HOME/.cache/yazi-term-gc.log"

sweep() {  # sweep [dry]
    local dry=$1 pid ppid tty args kids siblings atime n=0 out=() cands=()
    for pid in $(pgrep -x yazi); do
        read -r ppid tty < <(ps -o ppid=,tty= -p "$pid") || continue
        args=$(ps -o args= -p "$ppid" 2>/dev/null)
        if [[ $args != *wezterm-gui*--always-new-process*--\ yazi* ]]; then
            out+=("$tty yazi pid $pid: a mano (padre: ${args%% *}), no se toca"); continue
        fi
        kids=$(pgrep -P "$pid" | wc -l)
        if (( kids > 0 )); then
            out+=("$tty yazi pid $pid: PROTEGIDO ($kids hijo/s vivos)"); continue
        fi
        siblings=$(pgrep -P "$ppid" | wc -l)
        if (( siblings > 1 )); then
            out+=("$tty yazi pid $pid: PROTEGIDO (su wezterm tiene más pestañas/paneles)"); continue
        fi
        atime=$(stat -c %X "/dev/$tty" 2>/dev/null) || continue
        cands+=("$atime $pid $ppid $tty")
    done

    while read -r atime pid ppid tty; do
        [[ -n $pid ]] || continue
        if (( ++n <= KEEP )); then
            out+=("$tty yazi pid $pid: se conserva (#$n más reciente)"); continue
        fi
        if [[ $dry ]]; then
            out+=("$tty yazi pid $pid: se CERRARÍA (wezterm $ppid)")
        else
            kill -TERM "$ppid" 2>/dev/null
            out+=("$tty yazi pid $pid: CERRADO (wezterm $ppid)")
        fi
    done < <(printf '%s\n' "${cands[@]}" | sort -rn)

    (( ${#out[@]} )) || return 0
    if [[ $dry ]]; then
        printf '%s\n' "${out[@]}"
    else
        mkdir -p "${LOG%/*}"
        { date -Is; printf '%s\n' "${out[@]}"; } >> "$LOG"
    fi
}

if [[ $1 == --dry-sweep ]]; then sweep dry; exit 0; fi

sweep || true   # el GC nunca bloquea abrir yazi
exec wezterm start --always-new-process --cwd "$HOME/Escritorio" -- yazi "$HOME/Escritorio"
