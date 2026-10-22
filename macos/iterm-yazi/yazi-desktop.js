// Lanzador de yazi en iTerm: SIEMPRE una ventana nueva, en ~/Desktop, maximizada, titulada "yazi".
// Excepcion: si iTerm estaba cerrado, reutiliza la ventana que abre al lanzarse (solo si es un shell inactivo).
// Antes de abrir la nueva, barre (GC) los yazi olvidados: conserva los KEEP mas recientes
// (por atime del tty = ultimo input) y cierra el resto. Nunca toca un yazi con hijos vivos
// (p.ej. el bash de ":" -> bash) ni un yazi lanzado a mano desde un shell (`y`).
// Uso: osascript -l JavaScript yazi-desktop.js [--dry-sweep]   (dry: solo reporta, no abre ni cierra)

const CMD = "/bin/zsh -lc 'cd ~/Desktop && exec yazi'";
const TITLE = "yazi";
const KEEP = 2;
const SHELLS = ["login", "zsh", "-zsh", "bash", "-bash", "sh", "-sh"];

function run(argv) {
  ObjC.import('AppKit');
  const sh = Application.currentApplication();
  sh.includeStandardAdditions = true;

  const iTerm = Application('iTerm');
  const wasRunning = iTerm.running();

  if (argv[0] === "--dry-sweep") return sweep(iTerm, sh, true);
  if (wasRunning) { try { sweep(iTerm, sh, false); } catch (e) { /* el GC nunca bloquea abrir yazi */ } }

  if (!wasRunning) {
    iTerm.launch();                     // launch (no activate) para no forzar ventana extra
    for (let i = 0; i < 40 && iTerm.windows().length === 0; i++) delay(0.25);
  }

  // Arranque en frio: reutilizar la ventana que iTerm abre al lanzarse,
  // pero solo si es un shell inactivo (nunca escribir sobre trabajo ajeno).
  let win = null;
  if (!wasRunning) {
    try {
      win = findWindow(iTerm, w => isIdleShellWindow(w, sh));
      if (win) win.currentTab.currentSession.write({ text: "cd ~/Desktop && exec yazi" });
    } catch (e) { win = null; }
  }

  // Si no habia nada reutilizable (o iTerm ya corria), ventana nueva con yazi.
  if (!win) win = iTerm.createWindowWithDefaultProfile({ command: CMD });

  try { win.currentTab.currentSession.name = TITLE; } catch (e) { /* titulo opcional */ }
  iTerm.activate();
  win.select();
  maximize(win);
  return String(win.id());
}

// GC de yazi olvidados. Candidato = ventana de 1 tab/1 sesion cuyo tty tiene un yazi nacido del
// hotkey (padre NO es un shell) y sin hijos vivos. Se conservan los KEEP con input mas reciente.
function sweep(iTerm, sh, dry) {
  const out = (cmd) => sh.doShellScript(cmd).split("\r").join("\n");
  const cands = [], log = [];
  let ws = [];
  try { ws = iTerm.windows(); } catch (e) { return ""; }
  for (let i = 0; i < ws.length; i++) {
    try {
      const w = ws[i];
      if (w.tabs().length !== 1 || w.tabs()[0].sessions().length !== 1) continue;
      const tty = w.tabs()[0].sessions()[0].tty().replace("/dev/", "");
      const rows = out("ps -t " + tty + " -o pid=,ppid=,comm= 2>/dev/null").split("\n")
        .map(l => l.trim().split(/\s+/)).filter(r => r.length >= 3);
      const y = rows.find(r => basename(r.slice(2).join(" ")) === "yazi");
      if (!y) continue;
      const parent = out("ps -o comm= -p " + y[1] + " 2>/dev/null").trim();
      if (/sh$/.test(basename(parent))) { log.push(tty + " yazi pid " + y[0] + ": a mano (padre shell), no se toca"); continue; }
      const kids = out("pgrep -P " + y[0] + " | wc -l").trim();
      if (kids !== "0") { log.push(tty + " yazi pid " + y[0] + ": PROTEGIDO (" + kids + " hijo/s vivos)"); continue; }
      const atime = parseInt(out("stat -f %a /dev/" + tty).trim(), 10);
      cands.push({ w: w, pid: y[0], tty: tty, atime: atime });
    } catch (e) { /* ventana cerrandose */ }
  }
  cands.sort((a, b) => b.atime - a.atime);
  cands.forEach((c, n) => {
    if (n < KEEP) { log.push(c.tty + " yazi pid " + c.pid + ": se conserva (#" + (n + 1) + " mas reciente)"); return; }
    log.push(c.tty + " yazi pid " + c.pid + ": " + (dry ? "se CERRARIA" : "CERRADO"));
    if (dry) return;
    try { sh.doShellScript("kill -TERM " + c.pid); } catch (e) { /* ya murio */ }
    delay(0.4);
    try { c.w.close(); } catch (e) { /* iTerm ya la cerro al morir el proceso */ }
  });
  if (!dry && log.length) {
    try { sh.doShellScript("mkdir -p ~/.cache && printf '%s\\n' " + JSON.stringify(new Date().toISOString() + "\n" + log.join("\n")) + " >> ~/.cache/yazi-desktop-gc.log"); } catch (e) {}
  }
  return log.join("\n");
}

// Recorre las ventanas tolerando referencias muertas (ventanas cerrandose).
function findWindow(iTerm, pred) {
  let ws;
  try { ws = iTerm.windows(); } catch (e) { return null; }
  for (let i = 0; i < ws.length; i++) {
    try { if (pred(ws[i])) return ws[i]; } catch (e) { /* siguiente */ }
  }
  return null;
}

// Ventana de un solo shell en reposo: 1 tab, 1 sesion y ningun proceso
// aparte del shell/login corriendo en su tty.
function isIdleShellWindow(w, sh) {
  try {
    if (w.tabs().length !== 1) return false;
    const tab = w.tabs()[0];
    if (tab.sessions().length !== 1) return false;
    const tty = tab.sessions()[0].tty().replace("/dev/", "");
    const procs = sh.doShellScript("ps -t " + tty + " -o comm= 2>/dev/null")
      .split("\r").join("\n").split("\n")
      .map(s => s.trim()).filter(s => s.length);
    return procs.length > 0 && procs.every(p => SHELLS.indexOf(basename(p)) !== -1);
  } catch (e) {
    return false;
  }
}

function basename(p) {
  const parts = p.split("/");
  return parts[parts.length - 1];
}

// Maximizado real: ocupa el area visible (sin menu bar ni Dock) de la pantalla
// donde esta la ventana. No es pantalla completa de macOS.
function maximize(win) {
  const primaryHeight = $.NSScreen.screens.objectAtIndex(0).frame.size.height;
  const screen = screenOf(win, primaryHeight);
  const vis = screen.visibleFrame;
  win.bounds = {
    x: vis.origin.x,
    y: primaryHeight - (vis.origin.y + vis.size.height),
    width: vis.size.width,
    height: vis.size.height
  };
}

function screenOf(win, primaryHeight) {
  try {
    const b = win.bounds();
    // bounds de AppleScript: origen arriba-izquierda; NSScreen: abajo-izquierda.
    const center = $.NSMakePoint(b.x + b.width / 2, primaryHeight - (b.y + b.height / 2));
    const screens = $.NSScreen.screens;
    for (let i = 0; i < screens.count; i++) {
      const s = screens.objectAtIndex(i);
      if ($.NSPointInRect(center, s.frame)) return s;
    }
  } catch (e) { /* cae al default */ }
  return $.NSScreen.mainScreen;
}
