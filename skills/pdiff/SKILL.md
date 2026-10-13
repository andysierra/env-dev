---
name: pdiff
description: Convierte un cambio que se acaba de hacer en un repositorio (un diff, uno o varios commits) en un reporte PDF de varias páginas — un diagrama Mermaid de paraphernalia primero (el modelo mental del cambio: antes/después, causa-raíz), luego problema, diagnóstico, decisiones, cambios aplicados y el diff completo coloreado. Úsala cuando el usuario escriba "/pdiff", o frases como "hice unos cambios en el repo, /pdiff", "hice unos cambios entonces /pdiff", "pásame esto a PDF", "repórtame este cambio en PDF", o cuando un diff que ibas a mostrar en el chat sea tan largo que el panel del host pueda no renderizarlo bien (el motivo original por el que existe esta skill). NO la uses para comunicados de una sola página pidiendo una decisión a alguien — eso es /comunicado-onepager. NO la uses solo para explicar un sistema sin que exista un cambio de código de por medio — eso es /paraphernalia solo.
---

# /pdiff — reporte en PDF de un cambio de código

## Para qué existe

Nació de un caso real: un diff de ~370 líneas mostrado en el chat rompió el renderizado del
panel del agente. Un PDF no tiene ese problema — es vectorial, paginado, se abre en cualquier
lado, y de paso queda como registro permanente del cambio (a diferencia del chat, que se pierde
o se resume).

No es un generador de diffs bonitos. Es un **reporte que explica un cambio**: primero el modelo
mental (un diagrama), después el porqué, después el qué, y solo al final el diff línea por
línea — en ese orden, porque es el orden en que un humano lo puede entender sin haber estado
en la conversación donde se decidió.

## Cómo funciona

**1. Resuelve el diff objetivo.** Por defecto, en este orden (usa el primero que tenga
contenido):

```text
git diff                    cambios sin stagear
git diff --cached           cambios ya en stage
git diff HEAD~1             el último commit, si el working tree está limpio
```

Si el usuario menciona un rango explícito ("compara main con esta rama", "el PR #42", "los
últimos 3 commits"), usa ese en su lugar (`git diff main...HEAD`, `git diff HEAD~3`, etc.).
Si no hay ningún diff que mostrar, dilo y detente — no generes un PDF vacío.

**2. Diagnóstico y decisiones — de la conversación, nunca inventados.** Si tú mismo hiciste el
cambio en esta sesión, ya sabes el problema, el diagnóstico y las decisiones — reutilízalos, no
los redescubras leyendo el diff a ciegas. Si te invocan sobre un diff que no generaste tú (un
commit ajeno, una rama que no tocaste), infiere el problema y el diagnóstico del propio diff y
de los mensajes de commit (`git log -p` / `git log --format=%B -1`), y dilo explícitamente como
inferencia si no hay una fuente que lo confirme — nunca lo presentes como si el autor te lo
hubiera contado.

**3. Diagrama de paraphernalia — SIEMPRE primero, un solo diagrama.** Antes de escribir una
sola sección de prosa, decide el modelo mental del cambio con el marco de `/paraphernalia`
(comportamiento, causalidad, antes/después — no hace falta recorrer las 9 capas, solo la que
aplique) y dibuja **un** diagrama Mermaid que lo represente. Para un fix, el modelo casi siempre
es **causa-raíz / antes-después**: qué producía el síntoma, qué lo produce ahora. No inviertas
tiempo en un diagrama de arquitectura si el cambio no lo amerita — un diagrama pobre es peor que
ninguno. Si el diff es trivial (un typo, un bump de versión) omite el diagrama por completo:
borra el bloque `.diagrama` y `<!--MERMAID_SCRIPT-->` de la plantilla en vez de forzar uno.

**4. Arma el HTML.** Copia `plantilla/reporte.html` a una carpeta de trabajo (`/tmp/pdiff-<algo>/`
es suficiente, es contenido efímero) y reemplaza cada `<!--MARCADOR-->`:

```text
TITULO              una frase: qué cambió (no el nombre del repo a secas)
SUBTITULO           repo · rama/commit · fecha
DIAGRAMA_MERMAID    el código Mermaid del paso 3 (sin las comillas de code fence, va crudo
                    dentro de <pre class="mermaid">)
PROBLEMA            qué estaba mal, en prosa llana, 2-4 líneas
DIAGNOSTICO         causa(s) raíz, en bloques `.box` (uno por causa si hay más de una)
DECISIONES          bloques `.box.decision` — omite toda la sección <h2> si no hubo ninguna
CAMBIOS             lista por archivo de qué se tocó y por qué (no repitas el diff, resume)
PENDIENTES          bloques `.box.pendiente` — omite toda la sección <h2> si no queda nada
PIE                 una línea: de dónde sale este reporte (rama, si está commiteado o no)
```

**No toques `<!--DIFF-->`** — eso lo rellena `build.py` mecánicamente a partir de
`cambios.diff`, para no gastar turnos coloreando texto a mano y para que el coloreado sea
consistente siempre.

Guarda el diff crudo tal cual (`git diff > cambios.diff` en la misma carpeta de trabajo, sin
editarlo ni resumirlo).

**5. Renderiza.**

```bash
python3 ~/.claude/skills/pdiff/build.py <carpeta-de-trabajo> [ruta-de-salida.pdf]
```

Sin segundo argumento, el PDF queda en `<carpeta-de-trabajo>/pdiff-reporte.pdf` — muévelo o
indica la ruta de salida explícita si el usuario quiere el archivo en un sitio concreto (por
convención de esta skill, si no dice nada: `<escritorio>/<repo>-pdiff-<fecha>.pdf`, donde
`<escritorio>` es `$(xdg-user-dir DESKTOP)` en Linux — `~/Escritorio` en un sistema en español — y `~/Desktop` en macOS).

`build.py` decide solo si hace falta esperar a que Mermaid renderice (`--virtual-time-budget`)
— no se lo pidas ni se lo expliques al usuario, es mecánico.

**Requiere Chrome, Brave o Chromium instalado.** Sin dependencias de red para el PDF en sí —
`mermaid.min.js` ya viene bundleado en `plantilla/`, así que el diagrama renderiza offline.

## Estructura

```text
~/.claude/skills/pdiff/
├── SKILL.md
├── build.py                    diff -> HTML coloreado + HTML -> PDF (Chrome headless)
└── plantilla/
    ├── reporte.html             la plantilla con los <!--MARCADOR--> comentados
    └── mermaid.min.js           bundleado, para que el diagrama renderice sin red
```

## Checklist antes de entregar

- [ ] ¿El diagrama es el primero que ve el lector, antes de cualquier prosa?
- [ ] ¿El diagrama tiene un modelo mental real (causa-raíz/antes-después), no es decoración?
- [ ] ¿El diagnóstico distingue causas reales de síntomas?
- [ ] ¿Las secciones Decisiones/Pendientes están, o se borraron limpio si no aplicaban?
- [ ] ¿El diff se generó con `build.py`, no coloreado a mano?
- [ ] ¿Le dijiste al usuario la ruta final del PDF?
