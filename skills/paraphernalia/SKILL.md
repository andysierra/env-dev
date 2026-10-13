---
name: paraphernalia
description: Introduce gráficamente un sistema complejo (una plataforma interna, un microservicio, una integración, un flujo de negocio) a un humano EXTERNO a la empresa — software engineer semi-senior que no conoce el contexto, el negocio ni el stack interno. No es un generador de diagramas: es un router pedagógico que primero decide qué modelo mental necesita el humano (comportamiento, stocks, flujos, feedback, delays, leverage points — dinámica de sistemas) y solo después elige la sintaxis Mermaid compatible con Zed que mejor lo representa. Úsala cuando el usuario diga "hazme un paraphernalia", "introduce a X en este sistema", "explícale esto a alguien que no conoce nada", "onboarding gráfico", o cuando haya que contextualizar/enseñar un sistema desde cero a alguien sin el glosario interno. NO la uses para documentación técnica interna exhaustiva, ni para GAPS/RFC de una HU (eso es /requirements-engineering), ni cuando el destinatario ya conoce el dominio.
---

# Paraphernalia

## Qué es y qué no es

**Paraphernalia** (no "parafernalia" — el nombre es en inglés, aunque se puede referenciar
en español) es el skill que **introduce** un sistema complejo a un humano que:

- **no trabaja en esta empresa**,
- **no conoce el negocio** ni su jerga,
- **apenas conoce el stack devops/tecnológico interno**,
- es **software engineer semi-senior** (sabe programar, no sabe de este sistema).

No es un generador de diagramas. Un generador de diagramas responde "¿qué puedo dibujar?".
Paraphernalia responde **"¿qué necesita entender este humano para poder razonar sobre el
sistema por sí mismo, y qué representación hace eso más fácil?"**

Métrica de éxito: **no** "cuántos diagramas generé", sino **"la persona puede ahora predecir
qué hace el sistema, no solo nombrar sus partes"**.

---

## El error que este skill evita

Enumerar componentes no es explicar un sistema. Un humano que memoriza 40 nombres de
microservicios no puede predecir nada. El objetivo es construir en él un **modelo mental
generativo**: poder decir *"si pasa X, el sistema probablemente responde Y, con este retraso,
por este mecanismo"*.

---

## Marco de comprensión: dinámica de sistemas

Antes de pensar en qué diagrama usar, recorre el sistema en **este orden** (no el orden en que
está escrito el código, ni el orden de las carpetas del repo):

```text
1. COMPORTAMIENTO   ¿qué hace el sistema en el tiempo? (qué crece, oscila, se estabiliza, explota)
2. STOCKS            ¿qué se acumula? (documentos pendientes, pólizas en cola, deuda, saldo)
3. FLUJOS             ¿qué entra y qué sale de cada stock?
4. CAUSALIDAD         ¿qué determina cada flujo?
5. FEEDBACK LOOPS     si X sube, ¿qué pasa después que termina afectando a X otra vez?
6. DELAYS             ¿cuánto tarda una causa en producir su efecto?
7. CONTROLES          ¿qué es manipulable deliberadamente?
8. RESTRICCIONES      ¿qué NO es controlable? (perturbaciones externas, reglas fijas)
9. LEVERAGE POINTS    ¿cuál es la mínima intervención con el mayor efecto?
```

No hace falta llenar las 9 capas siempre. Pero **antes de dibujar nada**, decide en qué capa
está la pregunta del humano — eso determina el modelo mental, y el modelo mental determina
el tipo de Mermaid, no al revés.

Esto es intencional: casi todo lo que ya existe en el repo (diagramas de arquitectura,
diagramas de componentes) responde "¿de qué está hecho?". Este marco fuerza a responder
primero "¿qué hace?" y "¿qué se acumula?", que es lo que un externo realmente necesita para
dejar de depender de que alguien más le explique cada caso nuevo.

---

## Cadena de decisión (antes de generar cualquier gráfico)

```text
INTENCIÓN HUMANA
      ↓
TAREA COGNITIVA        ("¿qué necesita poder responder por sí mismo?")
      ↓
CAPA DE SISTEMAS        (¿comportamiento? ¿stock? ¿feedback? ¿leverage point?)
      ↓
MODELO MENTAL            (proceso / interacción / estado / estructura / composición / experiencia...)
      ↓
SINTAXIS MERMAID SOPORTADA
```

Nunca razonar "Mermaid tiene este diagrama, lo uso". Razonar siempre de arriba hacia abajo.

---

## Qué renderiza el entorno

Solo **Mermaid**, y no todos sus tipos: la lista de lo soportado se verificó
empíricamente, no se leyó en la documentación. Hay además un bug destructivo
conocido y dos reglas de sintaxis que rompen el renderizado en silencio.

**Antes de escribir un bloque Mermaid, lee `referencia/sintaxis-mermaid.md`.**
Ahí está qué tipos funcionan, cuáles no, y las trampas verificadas.

## Matriz pedagógica: de la pregunta al diagrama

| El humano necesita entender... | Pregunta cognitiva | Mermaid |
|---|---|---|
| Qué ocurre, en qué orden, con qué decisiones | "¿qué pasa después?" | `flowchart` |
| Quién le habla a quién y cuándo | "¿quién interactúa con quién?" | `sequenceDiagram` |
| Cómo cambia de estado una entidad (documento, póliza, job) | "¿qué estados tiene X?" | `stateDiagram` |
| Estructura estática del software/dominio | "¿qué entidades y cómo se relacionan?" | `classDiagram` |
| Estructura de los datos persistidos | "¿cómo se relacionan las tablas/entidades?" | `erDiagram` |
| Cómo se organiza conceptualmente un tema nuevo | "¿cómo se agrupa este conocimiento?" | `mindmap` |
| Qué pasó y cuándo (historia, evolución) | "¿qué ocurrió, en qué orden temporal?" | `timeline` |
| Planificación con duración y dependencias | "¿cuánto dura y de qué depende?" | `gantt` |
| Composición de un todo en partes | "¿cómo se reparte el total?" | `pie` |
| Comparación en dos dimensiones (impacto/esfuerzo, riesgo/prob.) | "¿dónde cae cada cosa en dos ejes?" | `quadrantChart` |
| La experiencia del humano frente al sistema (onboarding, UX) | "¿qué vive la persona, con qué frustración?" | `journey` |
| Evolución de ramas/commits/releases | "¿cómo evolucionó el código?" | `gitGraph` |
| Qué está involucrado más allá del expediente declarado (tentáculos) | "¿hasta dónde se extiende esto?" | `flowchart` con `subgraph` + aristas punteadas |

**Reglas de desambiguación rápida:**
- *proceso* (pasos) → `flowchart` · *interacción* (quién con quién) → `sequenceDiagram`
- *pasos* → `flowchart` · *estados de una entidad* → `stateDiagram`
- *estructura del software* → `classDiagram` · *estructura de datos/cardinalidad* → `erDiagram`
- *qué ocurrió* → `timeline` · *cómo se planifica* → `gantt`
- *protagonista = el sistema* → `flowchart` · *protagonista = la persona* → `journey`
- *organización conceptual de un tema* → `mindmap` (nunca lo interpretes como arquitectura real)

Prioridad por defecto para **introducir** un sistema a un externo, cuando varias opciones
son igualmente válidas (empezar simple, escalar después): `mindmap` → `flowchart` →
`sequenceDiagram` → `stateDiagram` → `journey` → `timeline` → el resto según necesidad.
Esta prioridad es pedagógica, no técnica — se ignora en cuanto el problema pide claramente
otra cosa.

### Dos arquetipos que no se improvisan

Hay dos casos donde la forma del diagrama es una decisión tomada, no una
preferencia: el **mapa de tentáculos** (hasta dónde se extiende algo que parece
pequeño) y los **componentes de microservicios** (obligatorio cuando el flujo toca
más de un repositorio). Los dos en `referencia/arquetipos.md`.

## Cuándo NO generar un gráfico

- El concepto es trivial y una frase lo explica mejor.
- El gráfico repetiría lo que ya dice el texto sin agregar relación nueva.
- No hay una relación estructural real que mostrar (evita el "diagram dumping").
- La información es hipótesis/desconocida — no la dibujes como si fuera un hecho verificado
  (marca `INFERENCIA:` o `NO DOCUMENTADO:` en el texto en vez de graficarla con falsa certeza).
- El tipo de diagrama que le corresponde no está soportado — usa texto o `flowchart` como
  fallback general antes que forzar una sintaxis no soportada.

Anti-patrones a evitar siempre: decorar sin propósito, elegir un diagrama porque "está
disponible" (syntax-first), usar el modelo mental equivocado (mindmap para arquitectura real,
flowchart para estados), meter todo el sistema en un único gráfico saturado, y por supuesto
usar sintaxis no soportada, o `xychart-beta` con tildes/ñ en brackets/title.

---

## Progresión pedagógica

No empieces por lo más complejo. Orden preferido dentro de una misma explicación:

```text
Contexto humano → concepto fundamental → modelo mental simple → visualización →
explicación de qué observar → detalle adicional → representación avanzada (si hace falta)
```

Regla de densidad: **un gráfico = una pregunta cognitiva**. Si necesitas responder dos
preguntas distintas, son dos gráficos, no uno saturado. Nunca generes dos gráficos que dicen
lo mismo con distinta sintaxis.

---

## Formato de cada representación entregada

No es obligatorio usar exactamente estos encabezados, pero mantener el flujo:

1. **Concepto** — qué se va a explicar, en lenguaje llano, sin jerga interna sin traducir.
2. **Modelo mental** — qué relación/capa de sistemas se está representando y por qué esa y no otra.
3. **Visualización** — el bloque ```mermaid``` correspondiente.
4. **Qué observar** — 2-3 líneas señalando qué mirar en el gráfico (el loop, el cuello de
   botella, el delay, el leverage point).
5. **Contexto** — cómo se conecta esto con el resto del sistema / con lo que viene después.

---

## Criterio de completitud pedagógica

Elegir bien el diagrama no basta. Falta un segundo motor de decisión: **cuándo detenerse y si
el humano realmente quedó en condiciones de comprender.**

```text
CONTENIDO → REPRESENTACIÓN → COMPRENSIÓN → ¿QUEDAN GAPS?
                                                ├── sí → seguir (explicar/anclar término/graficar)
                                                └── no → finalizar
```

### No asumas comprensión porque explicaste

Explicar no es lo mismo que ser entendido. Clasifica lo que observas, no lo que asumes:

```text
CONFIRMADA      el humano reformula, aplica el concepto a un caso, distingue de lo cercano,
                o responde bien una pregunta de comprobación.
PROBABLE        no contradijo, preguntó un detalle (no algo de fondo), sigue el hilo.
NO DEMOSTRADA   no hay ninguna señal — trátala como pendiente de verificar, no como fallo.
```

Sin ninguna señal explícita, la comprensión es **NO DEMOSTRADA**: no cierres la explicación
ni pases al siguiente tema sin ofrecer una pregunta de comprobación o el mínimo paso siguiente.

### Profundidad por defecto: el núcleo, no todo

```text
OVERVIEW → NÚCLEO → DOMINIO → PROFUNDIZACIÓN → MAESTRÍA
```

Por defecto enseña **el núcleo**: lo mínimo que arma un mapa mental suficiente para que el
humano siga solo. Enseñar "todo lo que hay para decir" es diagram dumping en versión texto.
Sube de nivel solo si el humano lo pide, o si un prerrequisito oculto bloquea el núcleo mismo.

### Gap crítico vs. detalle omitible

No toda omisión es un problema — la pregunta no es "¿expliqué todo?" sino **"¿omití algo sin
lo cual esto no se puede entender correctamente?"**

```text
IRRELEVANTE             → omitir sin mencionar
COMPLEMENTARIO           → opcional, solo si preguntan
ÚTIL                     → mencionar en una línea
PRERREQUISITO / CRÍTICO  → explicar SIEMPRE antes de continuar
```

### Regla de dependencia semántica — el sustantivo que nadie definió

Ejemplo real: *"el COTIZADOR fue relegado al EXPEDIENTE MICROPROCEDURAL"* es sintácticamente
correcta y pedagógicamente inútil si el humano no conoce ninguno de esos dos términos.

**Regla:** no uses un término de dominio (jerga de la plataforma y del cliente: cotizador, política de
suscripción, cierre de producción, expediente microprocedural...) como premisa si el humano
lo necesita para seguir la frase y todavía no lo anclaste. Al primer uso de un término así:

```text
¿el humano ya conoce este término (por contexto previo o dominio general)?
        ├── sí → úsalo sin definir
        └── no, y es necesario para lo que sigue → ancla el término ANTES de usarlo
                (no una definición de diccionario — una frase corta que lo conecta
                con algo que el humano ya entiende, ej. "un cotizador es el
                componente que calcula el valor de una póliza antes de emitirla")
```

Hay un **presupuesto de desconocimiento**: no se define cada palabra. "El servidor recibe una
petición HTTP" no necesita glosario — la audiencia de este skill ya es software engineer. Lo
que sí exige anclaje es la jerga *propia del dominio* (la plataforma, el cliente, seguros colombiano), cada
vez que aparece por primera vez.

### Cuándo finalizar

Nunca finalices porque "ya dije todo lo que tenía planeado". Finaliza cuando:

```text
objetivo de la explicación + conceptos núcleo + relaciones núcleo +
terminología crítica ya anclada + comprensión al menos PROBABLE
```

esté cubierto. Si un gráfico adicional ya no suma comprensión nueva, no lo generes — la
parafernalia gráfica también tiene que terminar, no solo el texto.

---

## Procedimiento operativo

Antes de generar cualquier gráfico en respuesta a una pregunta de contextualización:

**Regla de uso conjunto con `/backend`:** si este skill se invoca junto con `/backend` (o sobre
material que `/backend` acaba de producir), el **arquetipo de componentes de microservicios es el
que corresponde** — no otro. Todo hallazgo técnico que involucre clases debe
entregarse con sus clases agrupadas por microservicio en `subgraph`, el mecanismo de cruce de
frontera explícito, y la tabla de dónde comprobar cada pieza. Entregar una cadena de clases sin
decir en qué servicio vive cada una es el fallo que este arquetipo existe para evitar.

Ojo: esto rige **cuando ya se decidió explicar de forma gráfica**. Este skill es opt-in — si en
el turno no se pidió parafernalia, `/backend` entrega la misma información en tabla y no invoca
este skill (ver su punto 4.5). Nada acá obliga a producir un diagrama que nadie pidió.

```text
1. ¿Qué necesita comprender realmente el humano — y en qué capa de sistemas cae eso?
2. ¿Qué término de dominio estoy a punto de usar que el humano puede no conocer?
   Si es prerrequisito crítico, anclarlo ANTES de seguir (regla de dependencia semántica).
2b. ¿Vengo de /backend o el flujo toca más de un repo?
   → SÍ: arquetipo de componentes de microservicios (el que corresponde a ese caso).
3. ¿Qué modelo mental representa mejor esa comprensión?
4. ¿La visualización aporta algo, o el texto ya lo explica mejor?
5. ¿Qué tipo de Mermaid corresponde según la matriz pedagógica?
6. ¿Ese tipo está en la lista SOPORTADO de este skill?
7. ¿Aplica alguna restricción de seguridad (xychart-beta sin tildes/ñ en brackets) o de
   sintaxis (nodo sin salto de línea real)?
8. ¿Cuál es el mínimo gráfico necesario para responder solo esa pregunta?
9. Generar el gráfico.
10. Explicar qué debe observar el humano.
11. Continuar con el contexto — nunca dejar un gráfico aislado sin texto alrededor.
12. Evaluar comprensión (confirmada/probable/no demostrada) y gaps críticos restantes.
    ¿Quedan? → repetir desde el paso 1 con la siguiente intervención (no necesariamente un
    gráfico: puede ser una definición, un ejemplo, una pregunta de comprobación).
    ¿No quedan? → finalizar.
```

---

## Batería de pruebas y ciclo de refinamiento

Este skill se valida contra casos reales de onboarding externo, no contra checklist abstracto.
Cada iteración de prueba:

1. Elegir un sistema real (ej. la plataforma interna, un microservicio, una integración SAP) y un humano
   objetivo concreto (externo, semi-senior, sin contexto).
2. Aplicar el procedimiento operativo de arriba de punta a punta.
3. Revisar contra la matriz: ¿el diagrama elegido responde la pregunta cognitiva correcta, o
   se eligió por comodidad/disponibilidad?
4. Verificar que ningún bloque generado esté en la lista NO SOPORTADO, y que ningún
   `xychart-beta` tenga tildes/ñ en brackets/title.
5. Registrar qué falló (modelo mental equivocado, densidad excesiva, gráfico sin propósito) y
   corregir esta regla, no solo el caso puntual.

## Criterio final

Paraphernalia está bien usado cuando el externo, después de leer la explicación, puede decir
algo del tipo *"entonces si el OCR falla, esto se acumula acá y tarda X en notificarse"* — es
decir, cuando puede **predecir comportamiento**, no cuando puede **repetir nombres de
componentes**.

---

## Un ejemplo completo

Una impartición entera, de punta a punta, con anclaje de términos, tres diagramas
que responden tres preguntas distintas y un cierre que no asume comprensión:
`referencia/ejemplo-completo.md`.
