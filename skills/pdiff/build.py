#!/usr/bin/env python3
"""
pdiff — construye el PDF final a partir de una carpeta de trabajo con:
  reporte.html   la plantilla de plantilla/reporte.html ya rellenada por el agente
                 (todos los <!--MARCADOR--> reemplazados salvo <!--DIFF-->)
  cambios.diff   la salida cruda de `git diff` (o `git show`, `git log -p`), sin tocar

Este script hace dos cosas mecánicas que NO debe hacer el agente a mano:
  1. Colorea cambios.diff línea por línea e inyecta el HTML resultante en <!--DIFF-->
  2. Renderiza el HTML final a PDF con Chrome/Brave/Chromium headless

Si el reporte usa el bloque `.mermaid` (diagrama de paraphernalia), copia el mermaid.min.js
bundleado en plantilla/ junto al HTML y da 3s de --virtual-time-budget para que el diagrama
termine de renderizar antes de imprimir — sin eso, Chrome headless puede imprimir la página
antes de que el JS de mermaid haya dibujado el SVG.

Uso:
    python3 build.py <carpeta-de-trabajo> [salida.pdf]
"""
import html, re, shutil, subprocess, sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent

CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
if not CHROME.exists():
    alt = Path('/Applications/Brave Browser.app/Contents/MacOS/Brave Browser')
    CHROME = alt if alt.exists() else CHROME
if not CHROME.exists():
    for candidato in ('google-chrome', 'chromium', 'chromium-browser', 'brave-browser', 'chrome'):
        found = shutil.which(candidato)
        if found:
            CHROME = Path(found)
            break


def diff_a_html(texto: str) -> str:
    filas = []
    for linea in texto.splitlines():
        esc = html.escape(linea) or '&nbsp;'
        if linea.startswith('+++') or linea.startswith('---'):
            cls = 'meta'
        elif linea.startswith('@@'):
            cls = 'hunk'
        elif linea.startswith('diff --git') or linea.startswith('index '):
            cls = 'file'
        elif linea.startswith('+'):
            cls = 'add'
        elif linea.startswith('-'):
            cls = 'del'
        else:
            cls = 'ctx'
        filas.append(f'<div class="{cls}">{esc}</div>')
    return '\n'.join(filas)


def main():
    if len(sys.argv) < 2:
        sys.exit('Uso: python3 build.py <carpeta-de-trabajo> [salida.pdf]')
    if not CHROME.exists():
        sys.exit('No se encontró Chrome/Brave/Chromium instalado — hace falta para renderizar el PDF.')

    carpeta = Path(sys.argv[1]).resolve()
    reporte = carpeta / 'reporte.html'
    diffile = carpeta / 'cambios.diff'
    if not reporte.exists():
        sys.exit(f'Falta {reporte} — copia plantilla/reporte.html y rellénalo primero.')

    fuente = reporte.read_text(encoding='utf-8')
    if '<!--DIFF-->' in fuente:
        crudo = diffile.read_text(encoding='utf-8') if diffile.exists() else '(sin diff)'
        fuente = fuente.replace('<!--DIFF-->', diff_a_html(crudo))

    tiene_mermaid = 'class="mermaid"' in fuente and '<!--DIAGRAMA_MERMAID-->' not in fuente
    if tiene_mermaid and '<!--MERMAID_SCRIPT-->' in fuente:
        shutil.copyfile(SKILL_DIR / 'plantilla' / 'mermaid.min.js', carpeta / 'mermaid.min.js')
        script = '<script src="mermaid.min.js"></script>\n<script>mermaid.initialize({startOnLoad:true, theme:"neutral", securityLevel:"loose"});</script>'
        fuente = fuente.replace('<!--MERMAID_SCRIPT-->', script)
    else:
        fuente = fuente.replace('<!--MERMAID_SCRIPT-->', '')

    final_html = carpeta / '_reporte-final.html'
    final_html.write_text(fuente, encoding='utf-8')

    salida = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else carpeta / 'pdiff-reporte.pdf'
    salida.parent.mkdir(parents=True, exist_ok=True)   # Chrome no crea la carpeta de destino
    args = [str(CHROME), '--headless=new', '--disable-gpu', '--hide-scrollbars',
            '--no-pdf-header-footer']
    if tiene_mermaid:
        args.append('--virtual-time-budget=3000')
    args += [f'--print-to-pdf={salida}', f'file://{final_html}']

    r = subprocess.run(args, capture_output=True, text=True)
    if not salida.exists():
        sys.exit(f'Chrome no generó el PDF:\n{r.stderr}')

    paginas = len(re.findall(rb'/Type\s*/Page[^s]', salida.read_bytes()))
    print(f'{salida.name} — {salida.stat().st_size / 1024:.0f} KB, {paginas} pág.')


if __name__ == '__main__':
    main()
