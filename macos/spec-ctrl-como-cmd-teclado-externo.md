# macOS — Ctrl como Cmd en teclados externos

Quien viene de Windows / Linux copia con Ctrl+C y pega con Ctrl+V; en macOS es Cmd+C / Cmd+V.
En el teclado de la MacBook está bien que se quede como en Mac, pero con un **teclado externo**
el reflejo es Ctrl. Este spec hace que, **solo en teclados externos**, Ctrl+tecla funcione como
Cmd+tecla. Cmd sigue funcionando igual.

## Para el humano

```text
ANTES          teclado externo: Ctrl+C no copia, Ctrl+V no pega, Ctrl+Z no deshace...
DESPUÉS        teclado externo: Ctrl+tecla = Cmd+tecla (Ctrl+Shift+Z = Cmd+Shift+Z, etc.)
NO CAMBIA      teclado interno de la MacBook; Cmd en cualquier teclado
TERMINALES     iTerm2, Terminal, Ghostty, Warp, kitty, Alacritty, WezTerm quedan con Ctrl real
               (Ctrl+C sigue interrumpiendo procesos, incluido Claude Code)
PERSISTENCIA   es una regla de Karabiner-Elements: vive mientras Karabiner corra
REVERSIBLE     sí, un script (o apagar la regla en Karabiner > Complex Modifications)
```

### Instalar / revertir

```text
INSTALAR    macos/ctrl-como-cmd/install.sh  [--dry-run]   (idempotente)
REVERTIR    macos/ctrl-como-cmd/uninstall.sh
VERIFICAR   Karabiner-Elements > Complex Modifications ->
            "Teclado externo: Ctrl+tecla actua como Cmd+tecla (salvo terminales)"
            y con el teclado externo: Ctrl+C / Ctrl+V en Notas
```

### Para replicar en un mac nuevo
Compartí este archivo con Claude Code (o cualquier IA con acceso a shell) y pedile:
*"implementá la sección **Para la IA** de este spec en este mac"*.

---

# Para la IA — leé esto antes de tocar nada

Este spec es autocontenido: **no necesitás nada de la conversación en la que se creó.**

## Qué vas a dejar instalado

```text
1. una regla (complex modification) en ~/.config/karabiner/karabiner.json, perfil activo
2. backup previo en ~/.config/karabiner/automatic_backups/karabiner-pre-ctrlcmd-<fecha>.json
```

Nada más: no hay binarios, ni LaunchAgents, ni permisos nuevos (los de Karabiner ya existen).

## Entorno donde se construyó y verificó

```text
fecha       2026-10-15
macOS       26.5.1 (build 25F80) — Darwin 25.5.0, Apple Silicon arm64
Karabiner   Karabiner-Elements 16.3.0 (karabiner_cli para el lint)
jq          /usr/bin/jq (viene con macOS) o /opt/homebrew/bin/jq
teclado     Logitech MX Mechanical Mini (vendor 1133, product 45927)
sudo        NO se necesita
```

## Decisión: regla de Karabiner, NO una app propia

Se pidió originalmente "una app". Se descartó porque **Karabiner se apodera (grab) de los
teclados físicos** y todo lo que tecleás le llega al sistema desde su teclado virtual
(`Karabiner DriverKit VirtualHIDKeyboard`, `Built-In = 0`). Una app con CGEventTap + IOHIDManager
no puede distinguir interno de externo mientras Karabiner corra; Karabiner sí, porque ve el
dispositivo de origen.

Si algún día se quita Karabiner, la alternativa nativa sin código es
Ajustes > Teclado > Atajos > Teclas modificadoras > (elegir el teclado externo) > Control → Command,
pero eso cambia la tecla entera (se pierde Ctrl en ese teclado) y no excluye terminales.

## Cómo es la regla (`ctrl-como-cmd/karabiner-rule.json`)

```text
condiciones   device_unless { is_built_in_keyboard: true }     -> solo teclados externos
              frontmost_application_unless <terminales>         -> Ctrl real en terminales
from          key_code X + mandatory [control] + optional [shift, option, caps_lock]
to            key_code X + modifiers [command]                  (shift/option se conservan)
teclas        a–z menos q, 0–9, - = [ ] \ ; ' , . / ` §, Enter
```

Excluidas a propósito:

```text
q                     el perfil tiene "Disable Command+Q"; Ctrl+Q -> Cmd+Q se saltaría esa protección
flechas, Tab,         Cmd en ellas hace otra cosa que Ctrl en Windows (inicio/fin de línea,
espacio, Esc, borrar  Spotlight, cambio de app...) -> se dejan como Ctrl
Ctrl+Cmd+tecla        command no está en optional -> no matchea (Ctrl+Cmd+Q bloquear, Ctrl+Cmd+F...)
```

⚠️ **Trampa:** Karabiner **no re-procesa** la salida de una regla con otras reglas. Por eso
Ctrl+Option+E / Ctrl+Option+N no dispararían los atajos de Cmd+Option+E (yazi, ver
`spec-iterm-yazi-hotkey.md`) y Cmd+Option+N (ni-open). La regla los replica con su
`shell_command` propio. El JSON del repo los trae con `__HOME__/bin/...`; `install.sh` lo
reemplaza por el `$HOME` real y **solo los incluye si el script existe** en esa máquina.

## Pasos exactos (lo que hace `install.sh`)

```text
1. sed __HOME__ -> $HOME sobre karabiner-rule.json; filtrar manipuladores de scripts inexistentes
2. karabiner_cli --lint-complex-modifications <regla envuelta en {title, rules}>   -> ok
3. jq: en el perfil selected, quitar la regla con la misma description y añadir la nueva
4. backup de karabiner.json y mv del resultado (Karabiner lo recarga solo, sin reiniciar)
```

## Verificación

```text
~/.local/share/karabiner/log/console_user_server.log    "core_configuration is updated."
Karabiner-EventViewer, con el teclado externo:           Ctrl+C sale como left_command + c
```

## Limitaciones conocidas

```text
- Probado: lint OK, Karabiner cargó la regla, install/reinstall/uninstall en un HOME vacío.
  NO probado aún pulsando teclas en el teclado externo (pendiente del humano).
- Terminales integradas en otras apps (Zed, VS Code, IntelliJ) NO se distinguen: Ctrl+C ahí
  copia en vez de interrumpir. Karabiner solo ve la app, no el panel.
- Una terminal nueva no listada (otro bundle id) también recibe Cmd: añadirla a
  frontmost_application_unless en karabiner-rule.json y re-correr install.sh.
```
