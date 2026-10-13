## Entorno objetivo — solo Mermaid, verificado empíricamente en Zed

Este skill nació de una batería de pruebas real (no de documentación) contra el renderer
Mermaid embebido en Zed. Resultado:

```text
SOPORTADO                    NO SOPORTADO (confirmado, no es problema de sintaxis)
─────────────────            ───────────────────────────────────────────────────
flowchart                    architecture-beta
sequenceDiagram               sankey
classDiagram                  treemap
stateDiagram                  requirementDiagram
erDiagram                      C4
gantt                          packet
pie                             block
gitGraph                        kanban
mindmap                          radar
timeline
quadrantChart
journey

RESTRINGIDO — bug destructivo confirmado:
xychart-beta con tildes/ñ dentro de brackets [...] → panic de Rust → abort() de TODO Zed.
Usable SOLO si todo el texto entre brackets/title de ese bloque es ASCII puro, sin tildes ni ñ
(abreviar si hace falta: "Mie" no "Miércoles"). Si el texto real necesita diacríticos, no usar
xychart-beta — elegir otro tipo de la lista SOPORTADO.
```

No usar PlantUML, Graphviz/DOT ni D2 en este skill — aunque puedan renderizar con extensiones
adicionales, el objetivo es que el resultado funcione en cualquier Zed sin configuración extra.

### Regla de sintaxis — nunca partir el texto de un nodo con salto de línea real

Confirmado en pruebas: si el texto dentro de `[...]`, `(...)`, `{...}` etc. de un nodo
contiene un salto de línea **literal** (escrito así por comodidad al redactar el bloque),
Zed no lo interpreta como Mermaid válido y cae a mostrar el bloque como texto plano — no
crashea, pero tampoco renderiza nada. Cada nodo va **en una sola línea**. Si el texto necesita
salto visual, usar `<br/>` dentro del mismo string, nunca un enter real.

```text
MAL:  S[(Stock: politicas_emision
          pendientes de autorizacion)]

BIEN: S[(Stock: politicas_emision pendientes de autorizacion)]
BIEN: S["Stock: politicas_emision<br/>pendientes de autorizacion"]
```

Si el entorno cambia (nueva versión de Zed, nueva extensión) y quieres volver a probar el
repertorio no soportado, reintenta variantes de sintaxis (con y sin `-beta`, formas minimales)
antes de descartar — así se confirmó esta lista.

### Regla de gramática — verifica el bloque completo antes de entregar

Para evitar errores de sintaxis Mermaid, genera siempre el código respetando estrictamente la
gramática de Mermaid. Antes de entregar el diagrama, verifica que:

- Todas las aristas con etiquetas `-->|...|` tengan correctamente cerrado el segundo `|`.
- No se confunda la sintaxis de una etiqueta de arista con la definición de un nodo.
- Cada nodo tenga un identificador y, cuando corresponda, su texto esté entre `[...]`.
- Las relaciones entre nodos estén escritas como `A --> B` o `A -->|etiqueta| B`, nunca con una
  construcción incompleta.
- Revisa el bloque Mermaid completo para detectar errores de parseo antes de responder.
- No modifiques la semántica ni la estructura del diagrama para corregir un error sintáctico;
  corrige únicamente la sintaxis necesaria.

**IDs únicos a nivel global (no solo dentro del subgraph).** Verificado en mermaid 11: el `parse()`
acepta un nodo que comparte el ID del `subgraph` que lo contiene, pero el `render()` falla con
`Setting X as parent of X would create a cycle`. El ID de cada nodo debe ser distinto del ID de
todo subgraph, todo otro nodo y toda referencia de arista del diagrama completo. Ejemplo:

```text
MAL (parse ok, render falla):        BIEN:
    subgraph DOCSRC["doc"]                  subgraph DOCSRC["doc"]
        DOCSRC["Roles y perfiles"]              ROLES["Roles y perfiles"]
    end                                       end
```

**Conectores punteados con texto — dos formas válidas, una inválida.** Verificado en
mermaid 11 contra el parser real:

```text
VÁLIDO:    HOY -.->|"cero conexion"| DOCSRC     ← preferido (misma forma que las aristas sólidas)
VÁLIDO:    HOY -. "cero conexion" .-> DOCSRC
INVÁLIDO:  HOY -.- |"texto"| DOCSRC              ← no es gramática; no lo usar
```

Usa siempre la primera forma. Nunca `-.- |...|`.

**En `sequenceDiagram` — nunca usar `&gt;` / `&lt;` en el texto de mensajes o notas.**
Verificado en mermaid 11: el parser rechaza las entidades HTML en el texto de mensajes y
notas. El carácter `<` suelto se confunde con el inicio de la flecha `->>`. El carácter `>`
suelto sí parsea pero es más seguro evitarlo para no depender de la versión del parser.

```text
MAL (PARSE-FAIL):    CI->>CI: detecta 60% &gt; tope HU292
MAL (PARSE-FAIL):    GATE->>GATE: nivel del usuario &lt; SUPERIOR?
MAL (PARSE-FAIL):    Note over A,B: tope 60% &gt; 25%

BIEN:                CI->>CI: detecta 60% mayor a tope HU292
BIEN:                GATE->>GATE: nivel del usuario menor a SUPERIOR?
BIEN:                Note over A,B: tope 60% mayor a 25%

También válido (parsea pero no recomendado):
CI->>CI: detecta 60% > tope HU292
CI->>CI: "60% > tope"   ← comillas dobles en el mensaje sí parsean
```

Reemplazo por texto explícito: `>` → `mayor a` · `<` → `menor a` · `>=` → `mayor o igual a` ·
`<=` → `menor o igual a`.

En particular, si quieres representar `CC` y `F` conectándose al mismo nodo `Anthro`, usa:

```text
CC --> Anthro
F --> Anthro
Anthro["SDK de Claude Agent"]
```

y no mezcles la definición del nodo con una etiqueta de arista.

---
