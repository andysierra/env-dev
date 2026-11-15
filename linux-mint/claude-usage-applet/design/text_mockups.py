#!/usr/bin/python3
"""Mockups de la variante en TEXTO del applet (sin gráfica).

Uso: python3 -I text_mockups.py /tmp/full.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
SHOT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/full.png"
FONT_FILE = "/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf"
K = 2  # escala de los mockups

PANEL_BG = (28, 29, 31)
TEXT = (222, 222, 224)
DIM = (150, 150, 155)
ALERT = (240, 110, 100)
WARN = (240, 180, 90)
SESSION = (217, 119, 87)
BG = (18, 18, 20)
TIP_BG = (24, 24, 26)
TIP_BORDER = (70, 70, 75)
NOTE = (122, 162, 247)


def font(px, weight="Regular"):
    f = ImageFont.truetype(FONT_FILE, px)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def tlen(text, f):
    return ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=f)


# Cada variante: lista de líneas; cada línea = lista de (texto, color, negrita)
VARIANTS = {
    "A": ("Una línea", "Solo porcentajes. Lo mínimo; el resto, al hacer clic.",
          [[("5h ", DIM, False), ("43%", TEXT, True), ("  7d ", DIM, False), ("18%", TEXT, True)]]),
    "B": ("Dos líneas + hora de reinicio", "Como el tooltip, resumido. Las horas son las del reinicio.",
          [[("5h ", DIM, False), ("43%", TEXT, True), (" · 01:00", DIM, False)],
           [("7d ", DIM, False), ("18%", TEXT, True), (" · vie 23:00", DIM, False)]]),
    "C": ("Dos líneas + cuenta regresiva", "Cuánto falta para el reinicio en vez de la hora.",
          [[("5h ", DIM, False), ("43%", TEXT, True), (" · 1h16", DIM, False)],
           [("7d ", DIM, False), ("18%", TEXT, True), (" · 6d", DIM, False)]]),
}


def render_text_widget(lines, h_px=27 * K):
    """Dibuja el widget de texto a escala K, alto = alto del panel."""
    one = len(lines) == 1
    f_reg = font((12 if one else 10) * K)
    f_bold = font((12 if one else 10) * K, "Bold")
    widths = [sum(tlen(t, f_bold if b else f_reg) for t, _, b in ln) for ln in lines]
    w = int(max(widths)) + 8 * K
    im = Image.new("RGB", (w, h_px), PANEL_BG)
    d = ImageDraw.Draw(im)
    lh = h_px / len(lines)
    for i, ln in enumerate(lines):
        x = 4 * K
        y = lh * i + lh / 2
        for t, c, b in ln:
            f = f_bold if b else f_reg
            d.text((x, y), t, fill=c, font=f, anchor="lm")
            x += tlen(t, f)
    return im


def render_grid(rows, h_px=27 * K, gap=5 * K):
    """Como render_text_widget pero con columnas alineadas entre las dos líneas."""
    f_reg, f_bold = font(10 * K), font(10 * K, "Bold")
    ncol = max(len(r) for r in rows)
    colw = [0] * ncol
    for r in rows:
        for j, (t, _, b) in enumerate(r):
            colw[j] = max(colw[j], tlen(t, f_bold if b else f_reg))
    w = int(sum(colw) + gap * (ncol - 1)) + 8 * K
    im = Image.new("RGB", (w, h_px), PANEL_BG)
    d = ImageDraw.Draw(im)
    lh = h_px / len(rows)
    for i, r in enumerate(rows):
        x = 4 * K
        for j, (t, c, b) in enumerate(r):
            f = f_bold if b else f_reg
            # porcentajes alineados a la derecha, el resto a la izquierda
            dx = colw[j] - tlen(t, f) if t.endswith("%") else 0
            d.text((x + dx, lh * i + lh / 2), t, fill=c, font=f, anchor="lm")
            x += colw[j] + gap
    return im


def with_dates_image():
    T, D = TEXT, DIM
    options = [
        ("1 · Columnas alineadas", "Porcentaje, cuenta regresiva y fecha-hora de liberación en columnas.",
         render_grid([[("Ahora", D, False), ("43%", T, True), ("1h16", T, False), ("01:00", D, False)],
                      [("Semana", D, False), ("18%", T, True), ("6d", T, False), ("vie 20, 23:00", D, False)]])),
        ("2 · En línea, con paréntesis", "Lo que pediste tal cual: cuenta regresiva y entre paréntesis la hora.",
         render_text_widget([[("Ahora  ", D, False), ("43%", T, True), (" · 1h16 (01:00)", D, False)],
                             [("Semana ", D, False), ("18%", T, True), (" · 6d (vie 20, 23:00)", D, False)]])),
        ("3 · Hora primero, cuenta regresiva entre paréntesis", "Prioriza «a qué hora» sobre «cuánto falta».",
         render_text_widget([[("Ahora  ", D, False), ("43%", T, True), (" · 01:00 (1h16)", D, False)],
                             [("Semana ", D, False), ("18%", T, True), (" · vie 20, 23:00 (6d)", D, False)]])),
    ]
    rows = []
    for title, sub, w in options:
        panel, wx = panel_with(w)
        rows.append((title, sub, panel, wx, w.width))
    W = rows[0][2].width
    H = 70 + len(rows) * 170 + 40
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((20, 18), "09 · «Ahora / Semana» con hora y fecha-hora de liberación (escala 2×, tu panel real)",
           fill=TEXT, font=font(17, "Bold"))
    y = 70
    for title, sub, panel, wx, ww in rows:
        d.text((20, y), title, fill=SESSION, font=font(16, "Bold"))
        d.text((20, y + 24), sub, fill=DIM, font=font(13))
        im.paste(panel, (0, y + 56))
        d.rectangle([wx - 2, y + 54, wx + ww + 1, y + 56 + panel.height + 1], outline=NOTE, width=2)
        y += 170
    d.text((20, H - 34), "Ejemplo con tus datos: el bloque corto se libera hoy 01:00 (en 1 h 16 min); "
           "el semanal, el viernes 20 a las 23:00 (en 6 días).", fill=DIM, font=font(13))
    im.save(os.path.join(OUT, "09-texto-con-fechas.png"))


def panel_with(widget):
    """Inserta el widget en el panel real, a la derecha de las gráficas de MultiLoad."""
    shot = Image.open(SHOT).convert("RGB")
    x0, x1, py = 1330, 1920, 1053
    strip = shot.crop((x0, py, x1, 1080))
    strip = strip.resize((strip.width * K, strip.height * K), Image.NEAREST)
    at = (1600 - x0) * K
    gap = 4 * K
    out = Image.new("RGB", (strip.width, strip.height), PANEL_BG)
    shift = widget.width + gap
    out.paste(strip.crop((shift, 0, at, strip.height)), (0, 0))
    out.paste(widget, (at - shift + gap // 2, 0))
    out.paste(strip.crop((at, 0, strip.width, strip.height)), (at, 0))
    return out, at - shift + gap // 2


def tooltip_block():
    lines = [("Claude usage", TEXT, True),
             ("Sesión (5 h):  43 %  · reinicia 01:00 (en 1 h 16 min)", TEXT, False),
             ("Semanal:  18 %  · reinicia vie 20, 23:00", TEXT, False),
             ("Semanal Fable:  4 %", TEXT, False),
             ("Fuente: API · actualizado hace 3 min", DIM, False)]
    f, fb = font(10 * K), font(10 * K, "Bold")
    pad, lh = 9 * K, 15 * K
    w = int(max(tlen(t, fb if b else f) for t, _, b in lines)) + 2 * pad
    h = lh * len(lines) + 2 * pad - 3 * K + 30 * K
    im = Image.new("RGB", (w, h), TIP_BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=TIP_BORDER, width=K)
    y = pad
    for t, c, b in lines:
        d.text((pad, y), t, fill=c, font=fb if b else f)
        y += lh
    # botones de la ventanita
    by = y + 4 * K
    for i, t in enumerate(("Actualizar", "Abrir claude.ai")):
        bx = pad + i * 110 * K
        bw = tlen(t, f) + 16 * K
        d.rounded_rectangle([bx, by, bx + bw, by + 20 * K], 3 * K, fill=(55, 55, 60), outline=(80, 80, 85))
        d.text((bx + bw / 2, by + 10 * K), t, fill=TEXT, font=f, anchor="mm")
    return im


def arrow(d, a, b, c=NOTE):
    d.line([a, b], fill=c, width=2)
    d.polygon([b, (b[0] - 6, b[1] + 10), (b[0] + 6, b[1] + 10)], fill=c)


def variants_image():
    rows = []
    for key, (title, sub, lines) in VARIANTS.items():
        w = render_text_widget(lines)
        panel, wx = panel_with(w)
        rows.append((key, title, sub, panel, wx, w.width))
    W = rows[0][3].width
    H = 70 + len(rows) * 170
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((20, 18), "06 · Variante TEXTO: qué se ve en el panel (escala 2×, tu panel real)",
           fill=TEXT, font=font(17, "Bold"))
    y = 70
    for key, title, sub, panel, wx, ww in rows:
        d.text((20, y), f"Opción {key} · {title}", fill=SESSION, font=font(16, "Bold"))
        d.text((20, y + 24), sub, fill=DIM, font=font(13))
        im.paste(panel, (0, y + 56))
        d.rectangle([wx - 2, y + 54, wx + ww + 1, y + 56 + panel.height + 1], outline=NOTE, width=2)
        y += 170
    im.save(os.path.join(OUT, "06-texto-opciones.png"))


def popup_image():
    w = render_text_widget(VARIANTS["B"][2])
    panel, wx = panel_with(w)
    tip = tooltip_block()
    W = panel.width
    H = 120 + tip.height + 30 + panel.height + 120
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((20, 18), "07 · Clic en el texto: ventanita con el detalle completo (como el calendario del reloj)",
           fill=TEXT, font=font(17, "Bold"))
    py = H - panel.height - 120
    im.paste(panel, (0, py))
    tx = max(10, min(W - tip.width - 10, wx + w.width // 2 - tip.width // 2))
    im.paste(tip, (tx, py - tip.height - 8))
    d.text((20, py + panel.height + 24),
           "Clic izquierdo abre/cierra la ventanita. El tooltip al pasar el mouse sigue existiendo.",
           fill=DIM, font=font(13))
    d.text((20, py + panel.height + 44),
           "Clic derecho: menú (Actualizar, Fuente, Preferencias…).", fill=DIM, font=font(13))
    im.save(os.path.join(OUT, "07-texto-popup.png"))


def states_image():
    base = VARIANTS["B"][2]
    states = [
        ("Normal", base),
        ("Alerta (≥ 80 %)", [[("5h ", DIM, False), ("86%", ALERT, True), (" · 01:00", DIM, False)],
                             base[1]]),
        ("Desactualizado", [[("5h ", DIM, False), ("43%?", DIM, True), (" · 01:00", DIM, False)],
                            [("7d ", DIM, False), ("18%?", DIM, True), (" · vie 23:00", DIM, False)]]),
        ("Sin datos", [[("Claude", DIM, False)], ]),
        ("Ventana reiniciada", [[("5h ", DIM, False), ("0%", TEXT, True), (" · nueva", DIM, False)],
                                base[1]]),
    ]
    tiles = []
    for name, lines in states:
        tiles.append((name, render_text_widget(lines)))
    W = 20 + sum(t.width + 40 for _, t in tiles)
    H = 200
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((20, 18), "08 · Estados en texto (opción B, escala 2×)", fill=TEXT, font=font(17, "Bold"))
    x = 20
    for name, t in tiles:
        im.paste(t, (x, 70))
        d.text((x, 70 + t.height + 14), name, fill=TEXT, font=font(14, "Bold"))
        x += t.width + 40
    d.text((20, H - 30), "Alerta = porcentaje en rojo. Desactualizado = todo gris con «?». "
           "Sin datos = «Claude» en gris (el tooltip explica por qué).", fill=DIM, font=font(13))
    im.save(os.path.join(OUT, "08-texto-estados.png"))


if __name__ == "__main__":
    variants_image()
    popup_image()
    states_image()
    with_dates_image()
    print("ok")
