"""
paperless-backup-ui · app.py
────────────────────────────
Flask-Backend für das Paperless-ngx Backup-Interface.

Funktionen:
  - Auto-Erkennung: Docker-Compose-Mode vs. Docker-run-Mode
  - Streaming-Backup via Server-Sent Events (SSE)
  - Lock gegen parallele Backup-Läufe
  - Optional: HTTP Basic Auth (BACKUP_USER / BACKUP_PASS)
  - Backup-Retention: automatisches Löschen alter Archive
"""

import hmac
import os
import subprocess
import threading
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path

import docker
from flask import Flask, Response, render_template, jsonify, request, stream_with_context, send_file

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ─── Konfiguration (via Umgebungsvariablen) ────────────────────────────────────
PAPERLESS_IMAGE_NAME  = os.environ.get("PAPERLESS_IMAGE_NAME", "paperless-ngx")
PAPERLESS_CONTAINER_NAME = os.environ.get("PAPERLESS_CONTAINER_NAME", "")   # optionaler Override
EXPORT_PATH_IN_CONTAINER = os.environ.get("EXPORT_PATH_IN_CONTAINER", "/usr/src/paperless/export")
MANAGE_PY_WORKDIR     = os.environ.get("MANAGE_PY_WORKDIR", "/usr/src/paperless/src")
BACKUP_DIR            = os.environ.get("BACKUP_DIR", "/backup/paperless")
BACKUP_KEEP_LAST      = int(os.environ.get("BACKUP_KEEP_LAST", "7"))          # Anzahl Archive behalten

BACKUP_USER           = os.environ.get("BACKUP_USER", "")                    # leer = kein Auth
BACKUP_PASS           = os.environ.get("BACKUP_PASS", "")

# Fehlkonfiguration: Benutzername ohne Passwort gesetzt
_auth_misconfigured = bool(BACKUP_USER and not BACKUP_PASS)
if _auth_misconfigured:
    log.critical(
        "SICHERHEITSWARNUNG: BACKUP_USER ist gesetzt, BACKUP_PASS ist leer! "
        "Alle geschützten Endpunkte werden mit 503 beantwortet bis BACKUP_PASS konfiguriert ist."
    )

# ─── App & Lock ────────────────────────────────────────────────────────────────
app = Flask(__name__)
_backup_lock     = threading.Lock()
_abort_requested = threading.Event()   # gesetzt wenn Nutzer Abbruch anfordert
_current_container = None              # Container des laufenden Exports (für Abort)

try:
    docker_client = docker.from_env()
    docker_client.ping()
    log.info("Docker-Socket verbunden.")
except Exception as exc:
    docker_client = None
    log.error("Docker-Socket nicht erreichbar: %s", exc)


# ─── Hilfsfunktionen ───────────────────────────────────────────────────────────

def require_auth(f):
    """Optionale HTTP Basic Auth – aktiv wenn BACKUP_USER *und* BACKUP_PASS gesetzt."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _auth_misconfigured:
            return Response(
                "Auth-Fehlkonfiguration: BACKUP_USER ohne BACKUP_PASS. Bitte BACKUP_PASS setzen.",
                503,
            )
        if not BACKUP_USER:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or auth.username != BACKUP_USER or not hmac.compare_digest(auth.password, BACKUP_PASS):
            return Response(
                "Authentifizierung erforderlich.",
                401,
                {"WWW-Authenticate": 'Basic realm="Paperless Backup"'},
            )
        return f(*args, **kwargs)
    return decorated


def detect_paperless_container():
    """
    Sucht den laufenden Paperless-ngx Container.
    Prüft (in dieser Reihenfolge):
      1. Expliziter Container-Name via PAPERLESS_CONTAINER_NAME
      2. Image-Tag enthält PAPERLESS_IMAGE_NAME
      3. Container-Name enthält "paperless"
    Gibt ein Dict zurück oder None.
    """
    if not docker_client:
        return None

    try:
        containers = docker_client.containers.list()
    except Exception as exc:
        log.error("Docker containers.list() fehlgeschlagen: %s", exc)
        return None

    for container in containers:
        # Prüfung 1: expliziter Name-Override
        if PAPERLESS_CONTAINER_NAME and container.name != PAPERLESS_CONTAINER_NAME:
            continue

        # Prüfung 2+3: Image-Tag oder Container-Name
        try:
            tags = container.image.tags or []
        except Exception:
            tags = []

        image_match = any(PAPERLESS_IMAGE_NAME.lower() in t.lower() for t in tags)
        name_match  = "paperless" in container.name.lower()

        if not (image_match or name_match or PAPERLESS_CONTAINER_NAME):
            continue

        labels = container.attrs.get("Config", {}).get("Labels") or {}
        project = labels.get("com.docker.compose.project")

        if project:
            return {
                "mode":         "compose",
                "container":    container,
                "container_id": container.short_id,
                "service":      labels.get("com.docker.compose.service", "webserver"),
                "project":      project,
            }
        else:
            return {
                "mode":         "run",
                "container":    container,
                "container_id": container.short_id,
                "container_name": container.name,
            }

    return None


def apply_retention(backup_dir: str, keep_last: int):
    """Löscht ältere Archive, behält die <keep_last> neuesten."""
    archives = sorted(
        Path(backup_dir).glob("paperless-ngx_*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    to_delete = archives[keep_last:]
    for old in to_delete:
        try:
            old.unlink()
            log.info("Altes Backup gelöscht: %s", old.name)
            yield f"data: [Retention] Gelöscht: {old.name}\n\n"
        except Exception as exc:
            yield f"data: [Retention] Fehler beim Löschen von {old.name}: {exc}\n\n"


def run_backup_generator():
    """
    Generator für den SSE-Stream.
    Führt folgende Schritte durch:
      1. Container-Erkennung
      2. document_exporter via Docker SDK exec_run (streaming)
      3. tar-Archivierung
      4. Retention-Policy
    """
    global _current_container
    _abort_requested.clear()

    # ── Schritt 1: Container finden ──────────────────────────────────────────
    yield "data: [1/4] Suche Paperless-ngx Container...\n\n"
    info = detect_paperless_container()
    if not info:
        yield "data: FEHLER: Kein laufender Paperless-ngx Container gefunden.\n\n"
        yield "data: __DONE_ERROR__\n\n"
        return

    container = info["container"]
    _current_container = container
    mode_label = "docker-compose" if info["mode"] == "compose" else "docker-run"
    yield f"data: Container gefunden: {container.name} ({container.short_id}) · Modus: {mode_label}\n\n"

    # ── Schritt 2: document_exporter ausführen ───────────────────────────────
    # Low-Level API: exec_create + exec_start liefern nach Stream-Ende per
    # exec_inspect den echten Exit-Code, den exec_run(stream=True) nicht bietet.
    yield "data: [2/4] Starte document_exporter...\n\n"
    log.info("exec_create auf Container %s", container.name)

    try:
        exec_id = docker_client.api.exec_create(
            container.id,
            cmd=["python", "manage.py", "document_exporter", EXPORT_PATH_IN_CONTAINER],
            workdir=MANAGE_PY_WORKDIR,
        )["Id"]
        output_stream = docker_client.api.exec_start(exec_id, stream=True)
    except Exception as exc:
        _current_container = None
        yield f"data: FEHLER beim Starten des Exporters: {exc}\n\n"
        yield "data: __DONE_ERROR__\n\n"
        return

    # Streaming-Output vom Exporter
    for chunk in output_stream:
        if chunk:
            text = chunk.decode("utf-8", errors="replace").rstrip()
            for line in text.splitlines():
                yield f"data: {line}\n\n"

    # Jetzt ist der Prozess beendet – Exit-Code per exec_inspect auslesen
    _current_container = None
    try:
        exec_exit_code = docker_client.api.exec_inspect(exec_id).get("ExitCode")
    except Exception as exc:
        exec_exit_code = None
        log.warning("exec_inspect fehlgeschlagen: %s", exc)

    if _abort_requested.is_set():
        yield "data: Backup wurde abgebrochen.\n\n"
        yield "data: __DONE_ERROR__\n\n"
        return

    if exec_exit_code is None:
        yield "data: WARNUNG: Exit-Code nicht ermittelbar – Backup wird trotzdem fortgesetzt.\n\n"
    elif exec_exit_code != 0:
        yield f"data: FEHLER: document_exporter beendet mit Exit-Code {exec_exit_code}.\n\n"
        yield "data: __DONE_ERROR__\n\n"
        return

    yield "data: document_exporter abgeschlossen.\n\n"

    # ── Schritt 3: tar-Archivierung ──────────────────────────────────────────
    timestamp   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_name = f"paperless-ngx_{timestamp}.tar.gz"
    archive_path = str(Path(BACKUP_DIR) / archive_name)

    yield f"data: [3/4] Erstelle Archiv: {archive_name}...\n\n"
    log.info("Erstelle Archiv: %s", archive_path)

    # Export-Verzeichnis innerhalb des Backup-Volumes
    # Das Volume-Mapping ist: /backup/paperless (Host) → /backup/paperless (Container)
    # EXPORT_PATH_IN_CONTAINER → /backup/paperless/export (via eigenem Volume-Mount)
    result = subprocess.run(
        ["tar", "-czf", archive_path, "-C", EXPORT_PATH_IN_CONTAINER, "."],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        yield f"data: FEHLER bei tar: {result.stderr}\n\n"
        yield "data: __DONE_ERROR__\n\n"
        return

    # Dateigröße ermitteln
    try:
        size_mb = Path(archive_path).stat().st_size / (1024 * 1024)
        yield f"data: Archiv erstellt: {archive_name} ({size_mb:.1f} MB)\n\n"
    except Exception:
        yield f"data: Archiv erstellt: {archive_name}\n\n"

    # ── Schritt 4: Retention ─────────────────────────────────────────────────
    yield f"data: [4/4] Retention-Policy: behalte die letzten {BACKUP_KEEP_LAST} Archive...\n\n"
    yield from apply_retention(BACKUP_DIR, BACKUP_KEEP_LAST)

    yield "data: Backup erfolgreich abgeschlossen.\n\n"
    yield "data: __DONE_OK__\n\n"
    log.info("Backup abgeschlossen: %s", archive_name)


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
@require_auth
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    """Healthcheck-Endpoint (kein Auth erforderlich)."""
    docker_ok = docker_client is not None
    return jsonify({"status": "ok", "docker": docker_ok}), 200 if docker_ok else 503


@app.route("/status")
@require_auth
def status():
    """Gibt Container-Info und Backup-Status zurück."""
    info = detect_paperless_container()
    archives = []

    backup_path = Path(BACKUP_DIR)
    if backup_path.exists():
        for arc in sorted(backup_path.glob("paperless-ngx_*.tar.gz"),
                          key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                stat = arc.stat()
                archives.append({
                    "name":     arc.name,
                    "size_mb":  round(stat.st_size / (1024 * 1024), 1),
                    "created":  datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
            except Exception:
                continue

    return jsonify({
        "backup_running": _backup_lock.locked(),
        "docker_available": docker_client is not None,
        "paperless": {
            "found":     info is not None,
            "mode":      info.get("mode") if info else None,
            "container": info.get("container_id") if info else None,
            "name":      info["container"].name if info else None,
        } if info else {"found": False},
        "archives":      archives,
        "keep_last":     BACKUP_KEEP_LAST,
        "backup_dir":    BACKUP_DIR,
    })


@app.route("/backup/stream")
@require_auth
def backup_stream():
    """SSE-Endpoint: startet Backup und streamt Fortschritt."""
    if not _backup_lock.acquire(blocking=False):
        def already_running():
            yield "data: Ein Backup läuft bereits. Bitte warten.\n\n"
            yield "data: __DONE_ERROR__\n\n"
        return Response(
            stream_with_context(already_running()),
            mimetype="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    def generate():
        try:
            yield from run_backup_generator()
        finally:
            _backup_lock.release()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/backup/abort", methods=["POST"])
@require_auth
def backup_abort():
    """Bricht einen laufenden Backup-Export ab."""
    if not _backup_lock.locked():
        return jsonify({"error": "Kein Backup läuft."}), 400

    container = _current_container
    if not container:
        # Export bereits abgeschlossen, tar oder Retention läuft noch
        return jsonify({"error": "Export-Phase bereits beendet, Abbruch nicht möglich."}), 400

    _abort_requested.set()

    try:
        # pkill -TERM -f document_exporter im Paperless-Container
        # (pkill ist in der Paperless-ngx Standard-Image verfügbar)
        container.exec_run(
            ["pkill", "-TERM", "-f", "document_exporter"],
            detach=True,
        )
        log.info("Abort-Signal an Container %s gesendet.", container.name)
    except Exception as exc:
        log.error("pkill fehlgeschlagen: %s", exc)
        return jsonify({"error": f"Signal konnte nicht gesendet werden: {exc}"}), 500

    return jsonify({"status": "Abort-Signal gesendet."})


@app.route("/backup/download/<path:filename>")
@require_auth
def backup_download(filename):
    """Lädt ein einzelnes Backup-Archiv herunter."""
    # Path-Traversal verhindern: nur einfacher Dateiname erlaubt
    if "/" in filename or "\\" in filename or filename != Path(filename).name:
        return jsonify({"error": "Ungültiger Dateiname."}), 400

    archive_path = Path(BACKUP_DIR) / filename

    # Nur bekannte Archive ausliefern
    if not archive_path.exists() or not archive_path.name.startswith("paperless-ngx_"):
        return jsonify({"error": "Archiv nicht gefunden."}), 404

    return send_file(
        archive_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/gzip",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
