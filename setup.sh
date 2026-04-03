#!/usr/bin/env bash
# setup.sh – Interaktiver Setup-Assistent für papyr.bck
# Führe dieses Skript einmal aus – danach ist alles konfiguriert.

set -uo pipefail

# ── Farben ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC}  $*"; }
info() { echo -e "${BLUE}ℹ${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
fail() { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }
hr()   { echo "──────────────────────────────────────────────"; }

# ── Port-Prüfung ────────────────────────────────────────────────────────────
is_port_free() {
    local port=$1
    if command -v python3 &>/dev/null; then
        python3 -c \
          "import socket; s=socket.socket(); s.settimeout(0.5); r=s.connect_ex(('127.0.0.1',${port})); s.close(); exit(0 if r!=0 else 1)" \
          2>/dev/null
        return $?
    elif command -v nc &>/dev/null; then
        ! nc -z 127.0.0.1 "$port" 2>/dev/null
        return $?
    else
        ! (bash -c "(echo >/dev/tcp/127.0.0.1/${port})" 2>/dev/null)
        return $?
    fi
}

find_free_port() {
    local port=${1:-8080}
    while ! is_port_free "$port"; do
        ((port++))
    done
    echo "$port"
}

# ── Willkommen ──────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${BOLD}  papyr.bck – Setup-Assistent${NC}"
echo -e "  Beantworte ein paar Fragen – den Rest erledigt das Skript."
echo ""
hr
echo ""

# ── Voraussetzungen prüfen ──────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    fail "Docker wurde nicht gefunden. Bitte installiere Docker zuerst:\n  https://docs.docker.com/get-docker/"
fi
ok "Docker gefunden ($(docker --version | head -1))"

if ! docker compose version &>/dev/null 2>&1; then
    fail "Docker Compose (v2) wurde nicht gefunden.\n  Stelle sicher, dass du Docker Desktop oder 'docker-compose-plugin' installiert hast."
fi
ok "Docker Compose gefunden"

if ! docker info &>/dev/null 2>&1; then
    fail "Docker läuft nicht oder du hast keine Berechtigung.\n  Starte Docker und versuche es erneut, oder führe das Skript mit 'sudo' aus."
fi
ok "Docker-Daemon erreichbar"

echo ""

# ── Docker-Socket-GID ───────────────────────────────────────────────────────
if [ -S /var/run/docker.sock ]; then
    # macOS: stat -f '%g' | Linux: stat -c '%g'
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null \
              || stat -f '%g' /var/run/docker.sock 2>/dev/null \
              || echo "999")
    ok "Docker-Socket-GID automatisch ermittelt: ${BOLD}${DOCKER_GID}${NC}"
else
    warn "Docker-Socket nicht unter /var/run/docker.sock gefunden. Verwende GID 999."
    DOCKER_GID="999"
fi

echo ""
hr
echo ""

# ── Schritt 1: Paperless Export-Pfad ────────────────────────────────────────
echo -e "${BOLD}Schritt 1/4 – Paperless Export-Verzeichnis${NC}"
echo ""
echo "  Das ist der Ordner auf deinem Server, in den Paperless"
echo "  seine Dokumente exportiert."
echo "  (Oft: /opt/paperless/export  oder  ./paperless/export)"
echo ""
read -rp "  Export-Pfad [./paperless/export]: " INPUT_EXPORT
PAPERLESS_EXPORT_PATH="${INPUT_EXPORT:-./paperless/export}"
ok "Export-Pfad: ${PAPERLESS_EXPORT_PATH}"

echo ""
hr
echo ""

# ── Schritt 2: Backup-Zielordner ─────────────────────────────────────────────
echo -e "${BOLD}Schritt 2/4 – Backup-Zielordner${NC}"
echo ""
echo "  Hier werden die fertigen Backup-Dateien (.tar.gz) gespeichert."
echo ""
read -rp "  Backup-Zielordner [/backup/paperless]: " INPUT_BACKUP
BACKUP_DIR_HOST="${INPUT_BACKUP:-/backup/paperless}"

if [ ! -d "$BACKUP_DIR_HOST" ]; then
    echo ""
    warn "Ordner '${BACKUP_DIR_HOST}' existiert noch nicht."
    read -rp "  Jetzt erstellen? [J/n]: " INPUT_MKDIR
    if [[ "${INPUT_MKDIR:-J}" =~ ^[JjYy]$ ]] || [ -z "${INPUT_MKDIR:-}" ]; then
        if mkdir -p "$BACKUP_DIR_HOST" 2>/dev/null; then
            ok "Ordner erstellt: ${BACKUP_DIR_HOST}"
        else
            warn "Konnte Ordner nicht erstellen (fehlende Rechte?). Versuche es mit sudo ..."
            sudo mkdir -p "$BACKUP_DIR_HOST" && ok "Ordner erstellt (mit sudo): ${BACKUP_DIR_HOST}"
        fi
    else
        warn "Ordner nicht erstellt. Du musst ihn vor dem Start manuell anlegen."
    fi
else
    ok "Ordner existiert bereits: ${BACKUP_DIR_HOST}"
fi

echo ""
hr
echo ""

# ── Schritt 3: Passwortschutz ─────────────────────────────────────────────────
echo -e "${BOLD}Schritt 3/4 – Passwortschutz (empfohlen)${NC}"
echo ""
echo "  Schütze die Web-App mit Benutzername + Passwort, damit nicht jeder"
echo "  im Netzwerk einen Backup starten kann."
echo "  Drücke einfach Enter, um keinen Schutz einzurichten."
echo ""
read -rp "  Benutzername (leer = kein Schutz): " BACKUP_USER

if [ -n "${BACKUP_USER}" ]; then
    while true; do
        read -rsp "  Passwort: " BACKUP_PASS
        echo ""
        if [ -z "${BACKUP_PASS}" ]; then
            warn "Passwort darf nicht leer sein, wenn ein Benutzername gesetzt ist."
        else
            read -rsp "  Passwort bestätigen: " BACKUP_PASS_CONFIRM
            echo ""
            if [ "${BACKUP_PASS}" = "${BACKUP_PASS_CONFIRM}" ]; then
                ok "Passwortschutz aktiviert (Benutzer: ${BACKUP_USER})"
                break
            else
                warn "Passwörter stimmen nicht überein. Bitte erneut eingeben."
            fi
        fi
    done
else
    warn "Kein Passwortschutz gesetzt. Die App ist ohne Login erreichbar!"
    BACKUP_PASS=""
fi

echo ""
hr
echo ""

# ── Schritt 4: Port ─────────────────────────────────────────────────────────
echo -e "${BOLD}Schritt 4/4 – Port${NC}"
echo ""

DESIRED_PORT=8080
if is_port_free "$DESIRED_PORT"; then
    BACKUP_PORT="$DESIRED_PORT"
    ok "Port ${BOLD}${BACKUP_PORT}${NC} ist frei."
else
    warn "Port ${DESIRED_PORT} ist bereits belegt."
    BACKUP_PORT=$(find_free_port $((DESIRED_PORT + 1)))
    ok "Freier Port gefunden: ${BOLD}${BACKUP_PORT}${NC}"
fi

echo ""
hr
echo ""

# ── .env schreiben ────────────────────────────────────────────────────────────
cat > .env <<EOF
# papyr.bck – Konfiguration (generiert von setup.sh)
# Um die Einstellungen zu ändern, führe setup.sh erneut aus.

BACKUP_PORT=${BACKUP_PORT}
DOCKER_GID=${DOCKER_GID}
PAPERLESS_EXPORT_PATH=${PAPERLESS_EXPORT_PATH}
BACKUP_DIR_HOST=${BACKUP_DIR_HOST}
BACKUP_USER=${BACKUP_USER}
BACKUP_PASS=${BACKUP_PASS}
EOF

ok ".env-Datei gespeichert"

# .env aus git-Tracking ausschließen (Passwort!)
if [ -f .gitignore ]; then
    if ! grep -qxF '.env' .gitignore; then
        echo '.env' >> .gitignore
        ok ".env zu .gitignore hinzugefügt (Passwort wird nicht ins Repository eingecheckt)"
    fi
else
    echo '.env' > .gitignore
    ok ".gitignore angelegt und .env eingetragen"
fi

echo ""
hr
echo ""

# ── Zusammenfassung ───────────────────────────────────────────────────────────
echo -e "${BOLD}  Zusammenfassung${NC}"
echo ""
echo "  Export-Pfad:    ${PAPERLESS_EXPORT_PATH}"
echo "  Backup-Ordner:  ${BACKUP_DIR_HOST}"
if [ -n "${BACKUP_USER}" ]; then
    echo "  Passwortschutz: Ja  (Benutzer: ${BACKUP_USER})"
else
    echo -e "  Passwortschutz: ${YELLOW}Nein${NC}"
fi
echo "  Port:           ${BACKUP_PORT}"
echo ""

if [ "${BACKUP_PORT}" -ne 8080 ]; then
    warn "Port 8080 war belegt – die App startet auf Port ${BOLD}${BACKUP_PORT}${NC}."
    echo ""
fi

echo -e "  Deine App-URL: ${BOLD}http://localhost:${BACKUP_PORT}${NC}"
echo ""
hr
echo ""

# ── Starten? ──────────────────────────────────────────────────────────────────
read -rp "  App jetzt starten? [J/n]: " INPUT_START
if [[ "${INPUT_START:-J}" =~ ^[JjYy]$ ]] || [ -z "${INPUT_START:-}" ]; then
    echo ""
    info "Baue und starte papyr.bck ... (kann beim ersten Mal eine Minute dauern)"
    echo ""
    docker compose up -d --build
    echo ""
    ok "App läuft!"
    echo ""
    echo -e "  Öffne im Browser: ${BOLD}http://localhost:${BACKUP_PORT}${NC}"
    echo ""
    if [ "${BACKUP_PORT}" -ne 8080 ]; then
        warn "Merke dir Port ${BACKUP_PORT} – 8080 war bereits belegt."
    fi
else
    echo ""
    info "Alles vorbereitet. Starte die App später mit:"
    echo ""
    echo "    docker compose up -d --build"
    echo ""
    echo -e "  Danach erreichbar unter: ${BOLD}http://localhost:${BACKUP_PORT}${NC}"
    echo ""
fi
