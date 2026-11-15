# claude-usage-applet — uso de Claude en el panel de MATE

Texto de dos líneas en el panel, con columnas alineadas:

```
Ahora   43%  1h16   01:00
Semana  18%  5d23h  vie 20, 23:00
```

- **Ahora:** el límite del bloque de 5 h, que empieza con tu primer mensaje. **Semana:** el
  límite del bloque de 7 días. Las dos duraciones son fijas para todos los planes; lo que cambia
  según el plan es cuánto uso cabe en cada bloque.
- **Columnas:** % usado · cuánto falta para que se libere · a qué hora o qué día se libera.
- **Semáforo por fila**, según el % usado: verde hasta 59 %, amarillo desde 60 %, rojo desde
  85 %. Los umbrales y los colores se configuran en Preferencias.
- **Estados:** desactualizado = todo gris con «?»; sin datos = «Claude» en gris; bloque ya
  liberado = `0%` · `nuevo`.
- **Clic izquierdo:** abre una ventanita con el detalle completo y los botones *Actualizar* y
  *Abrir claude.ai*. El mismo detalle aparece en el tooltip.
- **Clic derecho:** menú con actualizar, abrir uso en claude.ai, cambiar la fuente y Preferencias.

Diseño: [`design/`](design/) tiene los mockups y su generador, `text_mockups.py`.

## Fuentes de datos (configurables)

| Fuente | Cómo obtiene el dato | Ventajas | Límites |
|---|---|---|---|
| **API** (por defecto) | `GET api.anthropic.com/api/oauth/usage` con el token OAuth de Claude Code (`~/.claude/.credentials.json`), cada 1, 5 u 8 min (5 por defecto) | Siempre al día, incluye el semanal por modelo | Endpoint **no oficial**: puede cambiar. |
| **Statusline** | `bin/claude-usage-statusline`, configurado como statusline de Claude Code, escribe `~/.cache/claude-usage/usage.json`; el applet lo vigila con inotify | Sin red ni token | Solo se actualiza mientras usas Claude Code de terminal (no Zed/ACP) |

Las dos se verificaron con un plan **Team**.

Protecciones de la fuente API:
- **No renueva nunca el token.** Si venció, espera a que Claude Code lo renueve, sin usar la red.
- **Ante errores, 429 o falta de red,** el intervalo se duplica en cada fallo, hasta 30 min, y
  respeta `Retry-After`.
- **En `resets_at`** hace una consulta para que la caída a 0 se vea a tiempo.
- **El intervalo varía ±10 % al azar,** para no consultar siempre en el mismo segundo.
- **"Actualizar ahora"** consulta como máximo una vez cada 30 s.

El token nunca se escribe en logs ni en el tooltip.

**Si ya tienes un statusline propio,** el instalador (Preferencias > "Instalar script de
statusline…") no lo reemplaza: lo **envuelve**. El script nuestro guarda el uso y devuelve la
salida del tuyo tal cual. Antes de escribir guarda un respaldo de `~/.claude/settings.json`.

## Instalar

```bash
./install.sh
```

El script instala todo en `~/.local/share`: el código, el esquema de GSettings y el servicio
D-Bus. La única excepción es el descriptor del applet: mate-panel solo lo busca en
`/usr/share/mate-panel/applets/`, así que ese paso pide `sudo`.

Después: clic derecho en el panel > **Añadir al panel…** > **Uso de Claude**. Si no aparece en
la lista, ejecuta `mate-panel --replace &disown`.

Desinstalar: `./uninstall.sh`. Si instalaste el script de statusline, quítalo antes desde
Preferencias.

## Desarrollo

```bash
python3 -m unittest discover -s tests -v       # modelo/formato, script de statusline, instalador
python3 tools/smoke_test.py api /tmp/x.png     # GTK real fuera de pantalla + consulta real
python3 src/claude_usage_applet.py --window    # ventana suelta, sin tocar el panel
```

Stack: Python 3 + GTK 3 + `MatePanelApplet-4.0` (GObject Introspection), el mismo que mintMenu.
No hay que compilar nada.

```
src/claude_usage_applet.py      entrada: fábrica de applets (D-Bus) o --window
src/claude_usage/applet.py      widget de texto, semáforo, ventanita de detalle, acciones
src/claude_usage/sources.py     ApiSource (consulta + backoff) y StatuslineSource (inotify)
src/claude_usage/model.py       Usage/Window, parseo tolerante, reinicio inferido, formato, semáforo
src/claude_usage/prefs.py       diálogo de Preferencias
src/claude_usage/statusline_install.py  instalar/envolver/desinstalar en settings.json
bin/claude-usage-statusline     script de statusline para Claude Code
data/                           esquema GSettings, servicio D-Bus, descriptor del applet
```
