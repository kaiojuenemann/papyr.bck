#!/usr/bin/env python3
# setup_web.py — papyr.bck setup wizard
# chmod +x setup_web.py  →  ./setup_web.py
#
# stdlib-only: no pip installs required.
# Starts a local HTTP server, opens the browser, walks through 6 config steps,
# writes .env, and optionally launches docker compose up -d --build.

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE   = SCRIPT_DIR / ".env"
GITIGNORE  = SCRIPT_DIR / ".gitignore"

# ── Compose output state ───────────────────────────────────────────────────────
_compose_lines  = []
_compose_done   = False
_compose_ok     = False
_compose_lock   = threading.Lock()

# ── Utilities ─────────────────────────────────────────────────────────────────

def find_free_port(start: int) -> int:
    port = start
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    raise RuntimeError("No free port found")


def get_docker_gid() -> int:
    sock = "/var/run/docker.sock"
    try:
        return os.stat(sock).st_gid
    except Exception:
        return 999


def check_docker():
    result = {"docker_ok": False, "compose_ok": False, "docker_gid": 999, "docker_error": ""}
    result["docker_gid"] = get_docker_gid()

    # docker installed?
    if not shutil.which("docker"):
        result["docker_error"] = "docker binary not found in PATH"
        return result
    result["docker_ok"] = False  # will be overwritten below

    # docker daemon reachable?
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=8
        )
        result["docker_ok"] = (r.returncode == 0)
        if r.returncode != 0:
            result["docker_error"] = r.stderr.decode(errors="replace").strip().splitlines()[-1]
    except subprocess.TimeoutExpired:
        result["docker_error"] = "docker info timed out"
    except Exception as e:
        result["docker_error"] = str(e)

    # docker compose available?
    try:
        r2 = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, timeout=6
        )
        result["compose_ok"] = (r2.returncode == 0)
    except Exception:
        result["compose_ok"] = False

    return result


def ensure_gitignore():
    try:
        if GITIGNORE.exists():
            content = GITIGNORE.read_text()
            if ".env" not in content.splitlines():
                with GITIGNORE.open("a") as f:
                    f.write("\n.env\n")
        else:
            GITIGNORE.write_text(".env\n")
    except Exception:
        pass


def run_compose():
    global _compose_lines, _compose_done, _compose_ok
    with _compose_lock:
        _compose_lines = []
        _compose_done  = False
        _compose_ok    = False

    try:
        proc = subprocess.Popen(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=str(SCRIPT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            with _compose_lock:
                _compose_lines.append(line.rstrip())
        proc.wait()
        with _compose_lock:
            _compose_done = True
            _compose_ok   = (proc.returncode == 0)
    except Exception as e:
        with _compose_lock:
            _compose_lines.append(f"ERROR: {e}")
            _compose_done = True
            _compose_ok   = False


# ── Embedded HTML ─────────────────────────────────────────────────────────────
# Not an f-string — CSS braces are literal.
WIZARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>papyr.bck · Setup</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0d0f0f;
      --surface:   #141717;
      --border:    #1f2424;
      --border-hi: #2e3535;
      --text:      #c8d0ce;
      --text-dim:  #566060;
      --text-hi:   #e8f0ee;
      --accent:    #00c896;
      --accent-dim:#00543f;
      --warn:      #e8a320;
      --err:       #e84040;
      --err-dim:   #3d1010;
      --mono:      'IBM Plex Mono', monospace;
      --sans:      'IBM Plex Sans', sans-serif;
    }

    html, body {
      min-height: 100%;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
      line-height: 1.6;
    }

    .shell {
      max-width: 720px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }

    /* ── Header ── */
    header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
      margin-bottom: 32px;
    }
    .logo { display: flex; align-items: center; gap: 12px; }
    .logo-icon {
      width: 36px; height: 36px;
      background: var(--accent-dim);
      border: 1px solid var(--accent);
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
    }
    .logo-text h1 {
      font-family: var(--mono);
      font-size: 15px;
      font-weight: 600;
      color: var(--text-hi);
      letter-spacing: 0.04em;
    }
    .logo-text p {
      font-size: 11px;
      color: var(--text-dim);
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    /* ── Step indicator ── */
    .step-bar {
      display: flex;
      gap: 0;
      margin-bottom: 32px;
      border: 1px solid var(--border);
      overflow: hidden;
    }
    .step-item {
      flex: 1;
      padding: 8px 4px;
      text-align: center;
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-dim);
      border-right: 1px solid var(--border);
      transition: background 0.2s, color 0.2s;
      cursor: default;
      user-select: none;
    }
    .step-item:last-child { border-right: none; }
    .step-item.active {
      background: var(--accent-dim);
      color: var(--accent);
      border-color: var(--accent-dim);
    }
    .step-item.done {
      color: var(--text-dim);
      background: transparent;
    }
    .step-item.done::before { content: "✓ "; color: var(--accent); }

    /* ── Panel ── */
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      margin-bottom: 16px;
    }
    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border);
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-dim);
    }
    .panel-body { padding: 20px 18px; }

    /* ── Checklist ── */
    .checklist { list-style: none; }
    .checklist li {
      font-family: var(--mono);
      font-size: 13px;
      padding: 6px 0;
      display: flex;
      align-items: center;
      gap: 10px;
      border-bottom: 1px solid var(--border);
    }
    .checklist li:last-child { border-bottom: none; }
    .ck-icon { font-size: 14px; width: 16px; text-align: center; flex-shrink: 0; }
    .ck-ok   { color: var(--accent); }
    .ck-err  { color: var(--err); }
    .ck-spin { color: var(--warn); animation: spin 1s linear infinite; display: inline-block; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .ck-label { color: var(--text); flex: 1; }
    .ck-detail { color: var(--text-dim); font-size: 11px; margin-left: auto; }

    /* ── Stat row ── */
    .stat { background: var(--surface); padding: 10px 14px; }
    .stat-label {
      font-size: 10px; letter-spacing: 0.1em;
      text-transform: uppercase; color: var(--text-dim); margin-bottom: 4px;
    }
    .stat-value {
      font-family: var(--mono); font-size: 13px; font-weight: 500;
      color: var(--text-hi); display: flex; align-items: center; gap: 6px;
    }
    .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-dim); flex-shrink: 0; }
    .dot.ok   { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
    .dot.err  { background: var(--err);    box-shadow: 0 0 6px var(--err); }
    .dot.warn { background: var(--warn);   box-shadow: 0 0 6px var(--warn); }

    /* ── Form fields ── */
    .field { margin-bottom: 18px; }
    .field label {
      display: block;
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-dim);
      margin-bottom: 6px;
    }
    .field input[type=text],
    .field input[type=password] {
      width: 100%;
      background: #0a0c0c;
      border: 1px solid var(--border);
      color: var(--text-hi);
      font-family: var(--mono);
      font-size: 13px;
      padding: 10px 12px;
      outline: none;
      transition: border-color 0.15s;
    }
    .field input:focus { border-color: var(--accent); }
    .field input.invalid { border-color: var(--err); }
    .field-hint {
      font-family: var(--mono);
      font-size: 11px;
      color: var(--text-dim);
      margin-top: 5px;
    }
    .field-hint.ok  { color: var(--accent); }
    .field-hint.err { color: var(--err); }
    .field-hint.warn { color: var(--warn); }

    /* ── Toggle ── */
    .toggle-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 18px;
    }
    .toggle-label {
      font-family: var(--mono);
      font-size: 13px;
      color: var(--text);
      cursor: pointer;
      user-select: none;
    }
    .toggle {
      position: relative;
      width: 40px; height: 22px;
      cursor: pointer;
    }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .toggle-track {
      position: absolute; inset: 0;
      background: var(--border-hi);
      border: 1px solid var(--border);
      transition: background 0.2s;
    }
    .toggle input:checked + .toggle-track { background: var(--accent-dim); border-color: var(--accent); }
    .toggle-thumb {
      position: absolute;
      top: 3px; left: 3px;
      width: 14px; height: 14px;
      background: var(--text-dim);
      transition: transform 0.2s, background 0.2s;
    }
    .toggle input:checked ~ .toggle-thumb { transform: translateX(18px); background: var(--accent); }

    /* ── Checkbox ── */
    .check-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 10px;
      margin-bottom: 18px;
    }
    .check-row input[type=checkbox] { accent-color: var(--accent); width: 14px; height: 14px; }
    .check-row label {
      font-family: var(--mono);
      font-size: 12px;
      color: var(--text);
      cursor: pointer;
    }

    /* ── Buttons ── */
    .btn-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 24px;
    }
    .btn-primary {
      font-family: var(--mono);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--bg);
      background: var(--accent);
      border: none;
      padding: 11px 28px;
      cursor: pointer;
      transition: background 0.15s, opacity 0.15s;
      outline: none;
    }
    .btn-primary:hover:not(:disabled) { background: #00e8af; }
    .btn-primary:disabled {
      background: var(--accent-dim);
      color: var(--text-dim);
      cursor: not-allowed;
    }
    .btn-secondary {
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-dim);
      background: transparent;
      border: 1px solid var(--border);
      padding: 10px 16px;
      cursor: pointer;
      transition: border-color 0.15s, color 0.15s;
    }
    .btn-secondary:hover { border-color: var(--border-hi); color: var(--text); }
    .btn-validate {
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--accent);
      background: transparent;
      border: 1px solid var(--accent-dim);
      padding: 7px 14px;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
      margin-left: 8px;
      flex-shrink: 0;
    }
    .btn-validate:hover { background: rgba(0,200,150,0.08); border-color: var(--accent); }

    /* ── Badge ── */
    .badge {
      display: inline-block;
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 2px 7px;
      border: 1px solid;
    }
    .badge-ok   { background: var(--accent-dim); color: var(--accent);  border-color: var(--accent-dim); }
    .badge-warn { background: #2a1e00;           color: var(--warn);    border-color: #4a3500; }
    .badge-err  { background: var(--err-dim);    color: var(--err);     border-color: var(--err-dim); }

    /* ── Summary table ── */
    .summary-table { width: 100%; border-collapse: collapse; }
    .summary-table tr { border-bottom: 1px solid var(--border); }
    .summary-table tr:last-child { border-bottom: none; }
    .summary-table td {
      padding: 9px 12px;
      font-family: var(--mono);
      font-size: 12px;
      vertical-align: top;
    }
    .summary-table td:first-child {
      color: var(--text-dim);
      width: 45%;
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .summary-table td:last-child { color: var(--text-hi); word-break: break-all; }

    /* ── Terminal ── */
    .terminal-wrap { margin-top: 16px; }
    .terminal-bar {
      display: flex; align-items: center; gap: 6px;
      padding: 8px 12px;
      background: #0a0c0c;
      border: 1px solid var(--border);
      border-bottom: none;
    }
    .t-dot { width: 10px; height: 10px; border-radius: 50%; }
    .t-dot:nth-child(1) { background: #3a1515; }
    .t-dot:nth-child(2) { background: #3a3010; }
    .t-dot:nth-child(3) { background: #103a20; }
    .terminal-label { margin-left: auto; font-family: var(--mono); font-size: 10px; color: var(--text-dim); letter-spacing: 0.06em; }
    #compose-log {
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.7;
      background: #0a0c0c;
      border: 1px solid var(--border);
      padding: 14px 16px;
      height: 260px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
      color: #7fa89a;
      scroll-behavior: smooth;
    }

    /* ── Input with inline button ── */
    .input-row {
      display: flex;
      align-items: stretch;
    }
    .input-row input {
      flex: 1;
    }

    /* ── Link ── */
    .app-link {
      display: inline-block;
      margin-top: 16px;
      font-family: var(--mono);
      font-size: 14px;
      color: var(--accent);
      text-decoration: none;
      border: 1px solid var(--accent-dim);
      padding: 10px 20px;
      transition: background 0.15s, border-color 0.15s;
    }
    .app-link:hover { background: rgba(0,200,150,0.08); border-color: var(--accent); }

    /* ── Env preview ── */
    .env-preview {
      background: #0a0c0c;
      border: 1px solid var(--border);
      padding: 14px 16px;
      font-family: var(--mono);
      font-size: 12px;
      color: #7fa89a;
      white-space: pre;
      overflow-x: auto;
      margin-top: 12px;
    }

    /* ── Step wrapper ── */
    .step { display: none; }
    .step.active { display: block; }

    /* ── Footer ── */
    footer {
      margin-top: 48px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--text-dim);
      font-family: var(--mono);
      display: flex;
      justify-content: space-between;
    }

    /* ── Helpers ── */
    .mt8  { margin-top: 8px; }
    .mt12 { margin-top: 12px; }
    .mt16 { margin-top: 16px; }
    .muted { color: var(--text-dim); font-size: 12px; }
  </style>
</head>
<body>
<div class="shell">

  <!-- Header -->
  <header>
    <div class="logo">
      <div class="logo-icon">📦</div>
      <div class="logo-text">
        <h1>PAPYR.BCK · SETUP</h1>
        <p>Paperless Backup UI — Konfigurationsassistent</p>
      </div>
    </div>
  </header>

  <!-- Step bar -->
  <div class="step-bar" id="step-bar">
    <div class="step-item active" id="si-1">1 · System</div>
    <div class="step-item"       id="si-2">2 · Export</div>
    <div class="step-item"       id="si-3">3 · Backup</div>
    <div class="step-item"       id="si-4">4 · Auth</div>
    <div class="step-item"       id="si-5">5 · Port</div>
    <div class="step-item"       id="si-6">6 · Fertig</div>
  </div>

  <!-- ── Step 1: Systemprüfung ──────────────────────────────────────────── -->
  <div class="step active" id="step-1">
    <div class="panel">
      <div class="panel-head"><span>Systemprüfung</span><span id="s1-status">wird geprüft …</span></div>
      <div class="panel-body">
        <ul class="checklist" id="s1-list">
          <li id="ck-docker-inst">
            <span class="ck-icon ck-spin">↻</span>
            <span class="ck-label">Docker installiert</span>
            <span class="ck-detail" id="ck-docker-inst-d">—</span>
          </li>
          <li id="ck-docker-daemon">
            <span class="ck-icon ck-spin">↻</span>
            <span class="ck-label">Docker Daemon erreichbar</span>
            <span class="ck-detail" id="ck-docker-daemon-d">—</span>
          </li>
          <li id="ck-compose">
            <span class="ck-icon ck-spin">↻</span>
            <span class="ck-label">Docker Compose verfügbar</span>
            <span class="ck-detail" id="ck-compose-d">—</span>
          </li>
        </ul>
        <div class="mt12 stat">
          <div class="stat-label">Erkannte Docker-Socket GID</div>
          <div class="stat-value"><span id="s1-gid" style="font-family:var(--mono)">—</span></div>
        </div>
        <div id="s1-error" class="mt8 field-hint err" style="display:none"></div>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-primary" id="s1-next" disabled onclick="goTo(2)">Weiter →</button>
    </div>
  </div>

  <!-- ── Step 2: Paperless Export-Pfad ──────────────────────────────────── -->
  <div class="step" id="step-2">
    <div class="panel">
      <div class="panel-head"><span>Paperless Export-Pfad</span></div>
      <div class="panel-body">
        <p class="muted" style="margin-bottom:16px;">Pfad auf dem Host-System, den Paperless-ngx als Export-Verzeichnis nutzt.</p>
        <div class="field">
          <label>PAPERLESS_EXPORT_PATH</label>
          <div class="input-row">
            <input type="text" id="s2-path" value="./paperless/export" spellcheck="false" />
            <button class="btn-validate" onclick="validatePath(2)">Prüfen</button>
          </div>
          <div class="field-hint" id="s2-hint">Pfad eingeben, dann „Prüfen" klicken.</div>
        </div>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-secondary" onclick="goTo(1)">← Zurück</button>
      <button class="btn-primary" id="s2-next" disabled onclick="goTo(3)">Weiter →</button>
    </div>
  </div>

  <!-- ── Step 3: Backup-Verzeichnis ─────────────────────────────────────── -->
  <div class="step" id="step-3">
    <div class="panel">
      <div class="panel-head"><span>Backup-Verzeichnis</span></div>
      <div class="panel-body">
        <p class="muted" style="margin-bottom:16px;">Pfad auf dem Host-System, in dem Backup-Archive gespeichert werden.</p>
        <div class="field">
          <label>BACKUP_DIR_HOST</label>
          <div class="input-row">
            <input type="text" id="s3-path" value="/backup/paperless" spellcheck="false" />
          </div>
          <div class="field-hint" id="s3-hint">Ordner muss existieren oder wird beim Fortfahren erstellt.</div>
        </div>
        <div class="check-row">
          <input type="checkbox" id="s3-create" checked />
          <label for="s3-create">Ordner jetzt erstellen falls nicht vorhanden</label>
        </div>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-secondary" onclick="goTo(2)">← Zurück</button>
      <button class="btn-primary" onclick="step3Next()">Weiter →</button>
    </div>
  </div>

  <!-- ── Step 4: Authentifizierung ──────────────────────────────────────── -->
  <div class="step" id="step-4">
    <div class="panel">
      <div class="panel-head"><span>Authentifizierung</span></div>
      <div class="panel-body">
        <div class="toggle-row">
          <label class="toggle">
            <input type="checkbox" id="s4-toggle" onchange="toggleAuth()" />
            <div class="toggle-track"></div>
            <div class="toggle-thumb"></div>
          </label>
          <span class="toggle-label">Passwortschutz aktivieren</span>
        </div>
        <div id="s4-fields" style="display:none;">
          <div class="field">
            <label>Benutzername</label>
            <input type="text" id="s4-user" autocomplete="username" spellcheck="false" />
          </div>
          <div class="field">
            <label>Passwort</label>
            <input type="password" id="s4-pass" autocomplete="new-password" />
          </div>
          <div class="field">
            <label>Passwort bestätigen</label>
            <input type="password" id="s4-pass2" autocomplete="new-password" />
            <div class="field-hint" id="s4-hint"></div>
          </div>
        </div>
        <div id="s4-noauth" class="muted">Kein Passwortschutz — App ist ohne Login erreichbar.</div>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-secondary" onclick="goTo(3)">← Zurück</button>
      <button class="btn-primary" onclick="step4Next()">Weiter →</button>
    </div>
  </div>

  <!-- ── Step 5: Port ────────────────────────────────────────────────────── -->
  <div class="step" id="step-5">
    <div class="panel">
      <div class="panel-head"><span>Port-Konfiguration</span></div>
      <div class="panel-body">
        <p class="muted" style="margin-bottom:16px;">Host-Port, unter dem die Backup-UI erreichbar sein soll.</p>
        <div class="field">
          <label>BACKUP_PORT</label>
          <div class="input-row">
            <input type="text" id="s5-port" value="" spellcheck="false"
                   placeholder="wird automatisch ermittelt …" />
          </div>
          <div class="field-hint" id="s5-hint">Einen freien Port ab 8080 wurde automatisch vorgeschlagen.</div>
        </div>
        <div id="s5-warn" style="display:none;margin-top:8px;">
          <span class="badge badge-warn">Hinweis</span>
          <span class="muted" style="margin-left:8px;">Port ist nicht 8080. Passe ggf. Firewall-Regeln an.</span>
        </div>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-secondary" onclick="goTo(4)">← Zurück</button>
      <button class="btn-primary" onclick="step5Next()">Weiter →</button>
    </div>
  </div>

  <!-- ── Step 6: Zusammenfassung & Anwenden ─────────────────────────────── -->
  <div class="step" id="step-6">
    <div class="panel">
      <div class="panel-head"><span>Zusammenfassung</span></div>
      <div class="panel-body" style="padding:0;">
        <table class="summary-table" id="s6-table">
        </table>
      </div>
    </div>

    <div id="s6-save-section">
      <div class="btn-row">
        <button class="btn-secondary" onclick="goTo(5)">← Zurück</button>
        <button class="btn-primary" onclick="saveConfig()">Konfiguration speichern</button>
      </div>
    </div>

    <div id="s6-saved-section" style="display:none;">
      <div class="panel mt16">
        <div class="panel-head"><span>Gespeichert</span></div>
        <div class="panel-body">
          <div class="field-hint ok">✓ .env wurde erfolgreich geschrieben.</div>
          <div class="env-preview" id="s6-env-preview"></div>
          <div class="mt12 muted">Starte die App manuell mit:</div>
          <div class="env-preview" style="margin-top:6px;">docker compose up -d --build</div>
        </div>
      </div>

      <div class="btn-row" style="margin-top:8px;">
        <button class="btn-primary" id="s6-start-btn" onclick="startApp()">App jetzt starten</button>
        <span id="s6-start-msg" class="muted"></span>
      </div>

      <div id="s6-terminal-wrap" style="display:none;" class="mt16">
        <div class="terminal-wrap">
          <div class="terminal-bar">
            <span class="t-dot"></span><span class="t-dot"></span><span class="t-dot"></span>
            <span class="terminal-label">docker compose up -d --build</span>
          </div>
          <div id="compose-log"></div>
        </div>
      </div>

      <div id="s6-app-link" style="display:none;" class="mt16">
        <div class="field-hint ok" style="margin-bottom:8px;">✓ App erfolgreich gestartet.</div>
        <a class="app-link" id="s6-link" href="#" target="_blank">App öffnen →</a>
      </div>
      <div id="s6-compose-err" style="display:none;" class="mt16">
        <span class="badge badge-err">Fehler</span>
        <span class="muted" style="margin-left:8px;">docker compose fehlgeschlagen — prüfe die Log-Ausgabe oben.</span>
      </div>
    </div>
  </div>

  <footer>
    <span>papyr.bck · setup wizard</span>
    <span id="footer-step">Schritt 1 von 6</span>
  </footer>
</div><!-- .shell -->

<script>
// ── State ──────────────────────────────────────────────────────────────────
const cfg = {
  docker_gid: 999,
  export_path: "./paperless/export",
  backup_dir: "/backup/paperless",
  auth: false,
  user: "",
  pass: "",
  port: 8080,
};

let currentStep = 1;
const TOTAL = 6;

// ── Step indicator ─────────────────────────────────────────────────────────
function updateStepBar(step) {
  for (let i = 1; i <= TOTAL; i++) {
    const el = document.getElementById("si-" + i);
    el.classList.remove("active", "done");
    if (i < step) el.classList.add("done");
    else if (i === step) el.classList.add("active");
  }
  document.getElementById("footer-step").textContent =
    "Schritt " + step + " von " + TOTAL;
}

function goTo(step) {
  document.getElementById("step-" + currentStep).classList.remove("active");
  currentStep = step;
  document.getElementById("step-" + step).classList.add("active");
  updateStepBar(step);
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (step === 5) loadPort();
  if (step === 6) renderSummary();
}

// ── Step 1: System check ───────────────────────────────────────────────────
function setChecklist(id, ok, detail) {
  const li = document.getElementById(id);
  const icon = li.querySelector(".ck-icon");
  icon.textContent = ok ? "✓" : "✗";
  icon.className   = "ck-icon " + (ok ? "ck-ok" : "ck-err");
  const d = document.getElementById(id + "-d");
  if (d) d.textContent = detail || "";
}

async function runSystemCheck() {
  try {
    const r = await fetch("/api/check", { method: "POST" });
    const d = await r.json();

    cfg.docker_gid = d.docker_gid;

    setChecklist("ck-docker-inst",   d.docker_ok || d.compose_ok, "docker");
    setChecklist("ck-docker-daemon", d.docker_ok, d.docker_ok ? "erreichbar" : (d.docker_error || "nicht erreichbar"));
    setChecklist("ck-compose",       d.compose_ok, d.compose_ok ? "verfügbar" : "nicht gefunden");

    document.getElementById("s1-gid").textContent = d.docker_gid;
    document.getElementById("s1-status").textContent = d.docker_ok ? "OK" : "Fehler";

    if (!d.docker_ok && d.docker_error) {
      const errEl = document.getElementById("s1-error");
      errEl.textContent = d.docker_error;
      errEl.style.display = "block";
    }

    document.getElementById("s1-next").disabled = !d.docker_ok;
  } catch (e) {
    document.getElementById("s1-status").textContent = "Netzwerkfehler";
    ["ck-docker-inst","ck-docker-daemon","ck-compose"].forEach(id => {
      setChecklist(id, false, "Fehler");
    });
  }
}

runSystemCheck();

// ── Step 2: Validate export path ──────────────────────────────────────────
async function validatePath(step) {
  const inputId = "s" + step + "-path";
  const hintId  = "s" + step + "-hint";
  const nextId  = "s" + step + "-next";
  const pathVal = document.getElementById(inputId).value.trim();
  const create  = step === 3 ? document.getElementById("s3-create").checked : false;

  if (!pathVal) {
    setHint(hintId, "Bitte einen Pfad eingeben.", "err");
    return false;
  }

  setHint(hintId, "Prüfe …", "");

  try {
    const r = await fetch("/api/validate-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pathVal, create: create }),
    });
    const d = await r.json();

    if (d.created) {
      setHint(hintId, "✓ Ordner wurde erstellt: " + pathVal, "ok");
    } else if (d.exists) {
      setHint(hintId, "✓ Pfad existiert.", "ok");
    } else if (d.valid) {
      setHint(hintId, "Pfad existiert nicht — wird beim Backup-Start als Volume gemountet.", "warn");
    } else {
      setHint(hintId, "✗ Fehler: " + (d.error || "Ungültiger Pfad"), "err");
      if (nextId) document.getElementById(nextId).disabled = true;
      return false;
    }

    if (nextId && document.getElementById(nextId)) {
      document.getElementById(nextId).disabled = false;
    }
    return true;
  } catch (e) {
    setHint(hintId, "Netzwerkfehler beim Validieren.", "err");
    return false;
  }
}

function setHint(id, text, cls) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className   = "field-hint" + (cls ? " " + cls : "");
}

// Step 2 path input — enable next on any keystroke (validate required first)
document.getElementById("s2-path").addEventListener("input", function() {
  document.getElementById("s2-next").disabled = true;
  setHint("s2-hint", "Pfad geändert — bitte erneut prüfen.", "");
});

// ── Step 3: Backup dir ─────────────────────────────────────────────────────
async function step3Next() {
  const pathVal = document.getElementById("s3-path").value.trim();
  if (!pathVal) { setHint("s3-hint", "Bitte einen Pfad eingeben.", "err"); return; }
  const ok = await validatePath(3);
  if (ok) {
    cfg.backup_dir = pathVal;
    cfg.export_path = document.getElementById("s2-path").value.trim();
    goTo(4);
  }
}

// ── Step 4: Auth ───────────────────────────────────────────────────────────
function toggleAuth() {
  const on = document.getElementById("s4-toggle").checked;
  document.getElementById("s4-fields").style.display = on ? "block" : "none";
  document.getElementById("s4-noauth").style.display = on ? "none" : "block";
}

function step4Next() {
  const on = document.getElementById("s4-toggle").checked;
  if (!on) {
    cfg.auth = false; cfg.user = ""; cfg.pass = "";
    goTo(5);
    return;
  }
  const user  = document.getElementById("s4-user").value.trim();
  const pass  = document.getElementById("s4-pass").value;
  const pass2 = document.getElementById("s4-pass2").value;

  if (!user) { setHint("s4-hint", "Benutzername darf nicht leer sein.", "err"); return; }
  if (!pass) { setHint("s4-hint", "Passwort darf nicht leer sein.", "err"); return; }
  if (pass !== pass2) { setHint("s4-hint", "Passwörter stimmen nicht überein.", "err"); return; }

  cfg.auth = true; cfg.user = user; cfg.pass = pass;
  setHint("s4-hint", "", "");
  goTo(5);
}

// ── Step 5: Port ───────────────────────────────────────────────────────────
async function loadPort() {
  const el = document.getElementById("s5-port");
  if (el.value) return; // already set
  try {
    const r = await fetch("/api/find-port", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start: 8080 }),
    });
    const d = await r.json();
    el.value = d.port;
    checkPortWarn(d.port);
    setHint("s5-hint", "Freier Port automatisch erkannt.", "ok");
  } catch (e) {
    el.value = "8080";
    setHint("s5-hint", "Konnte keinen Port ermitteln — 8080 als Standard gesetzt.", "warn");
  }
}

function checkPortWarn(port) {
  const warn = document.getElementById("s5-warn");
  warn.style.display = (parseInt(port) !== 8080) ? "block" : "none";
}

document.getElementById("s5-port").addEventListener("input", function() {
  checkPortWarn(this.value);
});

function step5Next() {
  const raw = document.getElementById("s5-port").value.trim();
  const port = parseInt(raw, 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    setHint("s5-hint", "Ungültiger Port (1–65535).", "err");
    return;
  }
  cfg.port = port;
  goTo(6);
}

// ── Step 6: Summary ────────────────────────────────────────────────────────
function renderSummary() {
  const rows = [
    ["PAPERLESS_EXPORT_PATH", cfg.export_path || document.getElementById("s2-path").value.trim()],
    ["BACKUP_DIR_HOST",       cfg.backup_dir],
    ["BACKUP_PORT",           cfg.port],
    ["DOCKER_GID",            cfg.docker_gid],
    ["BACKUP_USER",           cfg.auth ? cfg.user : "(kein Auth)"],
    ["BACKUP_PASS",           cfg.auth ? "••••••••" : "(kein Auth)"],
  ];

  const tbody = rows.map(([k, v]) =>
    "<tr><td>" + k + "</td><td>" + escHtml(String(v)) + "</td></tr>"
  ).join("");

  document.getElementById("s6-table").innerHTML = tbody;
}

function escHtml(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

async function saveConfig() {
  const exportPath = cfg.export_path || document.getElementById("s2-path").value.trim();
  const payload = {
    export_path: exportPath,
    backup_dir:  cfg.backup_dir,
    port:        cfg.port,
    docker_gid:  cfg.docker_gid,
    user:        cfg.auth ? cfg.user : "",
    pass:        cfg.auth ? cfg.pass : "",
  };

  try {
    const r = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    if (!d.ok) { alert("Fehler beim Speichern: " + (d.error || "unbekannt")); return; }

    // Show saved section
    document.getElementById("s6-save-section").style.display = "none";
    document.getElementById("s6-saved-section").style.display = "block";

    // Build env preview
    let preview = "BACKUP_PORT=" + cfg.port + "\n";
    preview += "DOCKER_GID=" + cfg.docker_gid + "\n";
    preview += "PAPERLESS_EXPORT_PATH=" + exportPath + "\n";
    preview += "BACKUP_DIR_HOST=" + cfg.backup_dir + "\n";
    preview += "BACKUP_USER=" + (cfg.auth ? cfg.user : "") + "\n";
    preview += "BACKUP_PASS=" + (cfg.auth ? "••••••••" : "");
    document.getElementById("s6-env-preview").textContent = preview;

  } catch (e) {
    alert("Netzwerkfehler beim Speichern.");
  }
}

let pollTimer = null;
let pollOffset = 0;

async function startApp() {
  document.getElementById("s6-start-btn").disabled = true;
  document.getElementById("s6-start-msg").textContent = "Starte Docker Compose …";
  document.getElementById("s6-terminal-wrap").style.display = "block";
  document.getElementById("compose-log").textContent = "";
  pollOffset = 0;

  try {
    await fetch("/api/start", { method: "POST" });
    pollTimer = setInterval(pollCompose, 500);
  } catch (e) {
    document.getElementById("s6-start-msg").textContent = "Fehler: " + e;
  }
}

async function pollCompose() {
  try {
    const r = await fetch("/api/start-status?offset=" + pollOffset);
    const d = await r.json();
    const log = document.getElementById("compose-log");

    if (d.lines && d.lines.length) {
      d.lines.forEach(function(line) {
        log.textContent += line + "\n";
      });
      pollOffset += d.lines.length;
      log.scrollTop = log.scrollHeight;
    }

    if (d.done) {
      clearInterval(pollTimer);
      if (d.ok) {
        document.getElementById("s6-start-msg").textContent = "Erfolgreich gestartet.";
        const link = "http://localhost:" + cfg.port;
        const linkEl = document.getElementById("s6-link");
        linkEl.href = link;
        linkEl.textContent = "App öffnen → " + link;
        document.getElementById("s6-app-link").style.display = "block";
      } else {
        document.getElementById("s6-compose-err").style.display = "block";
        document.getElementById("s6-start-msg").textContent = "Fehlgeschlagen.";
      }
    }
  } catch (e) {
    // network hiccup — keep polling
  }
}
</script>
</body>
</html>
"""


# ── HTTP Request Handler ───────────────────────────────────────────────────────

class WizardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):  # suppress access logs
        pass

    # ── helpers ──────────────────────────────────────────────────────────────

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path == "/":
            body = WIZARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/start-status":
            from urllib.parse import parse_qs
            qs     = parse_qs(parsed.query)
            offset = int(qs.get("offset", ["0"])[0])

            with _compose_lock:
                lines = _compose_lines[offset:]
                done  = _compose_done
                ok    = _compose_ok

            self.send_json({"lines": lines, "done": done, "ok": ok})
            return

        self.send_response(404)
        self.end_headers()

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/check":
            result = check_docker()
            self.send_json(result)
            return

        if path == "/api/find-port":
            body  = self.read_json_body()
            start = int(body.get("start", 8080))
            try:
                port = find_free_port(start)
                self.send_json({"port": port})
            except Exception as e:
                self.send_json({"port": start, "error": str(e)})
            return

        if path == "/api/validate-path":
            body   = self.read_json_body()
            raw    = body.get("path", "").strip()
            create = bool(body.get("create", False))

            if not raw:
                self.send_json({"valid": False, "exists": False, "created": False,
                                "error": "empty path"})
                return

            p = Path(raw).expanduser()

            try:
                exists  = p.exists()
                created = False
                if create and not exists:
                    p.mkdir(parents=True, exist_ok=True)
                    created = p.exists()
                    exists  = created

                self.send_json({
                    "valid":   True,
                    "exists":  exists,
                    "created": created,
                    "error":   "",
                })
            except PermissionError as e:
                self.send_json({"valid": False, "exists": False, "created": False,
                                "error": "Keine Berechtigung: " + str(e)})
            except Exception as e:
                self.send_json({"valid": False, "exists": False, "created": False,
                                "error": str(e)})
            return

        if path == "/api/save":
            body = self.read_json_body()
            try:
                lines = [
                    "BACKUP_PORT="            + str(body.get("port", 8080)),
                    "DOCKER_GID="             + str(body.get("docker_gid", 999)),
                    "PAPERLESS_EXPORT_PATH="  + str(body.get("export_path", "./paperless/export")),
                    "BACKUP_DIR_HOST="        + str(body.get("backup_dir", "/backup/paperless")),
                    "BACKUP_USER="            + str(body.get("user", "")),
                    "BACKUP_PASS="            + str(body.get("pass", "")),
                ]
                ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
                ensure_gitignore()
                self.send_json({"ok": True, "path": str(ENV_FILE)})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)})
            return

        if path == "/api/start":
            t = threading.Thread(target=run_compose, daemon=True)
            t.start()
            self.send_json({"ok": True})
            return

        self.send_response(404)
        self.end_headers()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    wizard_port = find_free_port(8765)

    server = HTTPServer(("127.0.0.1", wizard_port), WizardHandler)
    url    = f"http://localhost:{wizard_port}"

    print(f"papyr.bck Setup läuft auf {url}")
    print("Drücke Ctrl+C zum Beenden.\n")

    def open_browser():
        webbrowser.open(url)

    threading.Timer(0.5, open_browser).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSetup-Server beendet.")
        sys.exit(0)


if __name__ == "__main__":
    main()
