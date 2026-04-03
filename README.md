# papyr.bck

Web UI for triggering and monitoring Paperless-ngx backups — auto-detects Docker containers, streams live progress, and manages retention.

**Repository:** https://github.com/kaiojuenemann/papyr.bck

---

## Verzeichnisstruktur

```
papyr.bck/
├── Dockerfile
├── requirements.txt
├── app.py
├── docker-compose.yml          ← kompletter Stack inkl. Paperless
├── docker-compose.secure.yml   ← Socket-Proxy Overlay (empfohlen für Produktion)
├── favicon.svg
└── templates/
    └── index.html
```

## Schnellstart

### 1. Socket-GID ermitteln

```bash
stat -c '%g' /var/run/docker.sock
# z.B. 999
```

Wenn abweichend: `group_add` in `docker-compose.yml` anpassen.

### 2. Volumes anpassen

In `docker-compose.yml`:
- `./paperless/export` → dein tatsächlicher Export-Pfad
- `/backup/paperless`  → dein Backup-Zielverzeichnis (muss existieren)

```bash
mkdir -p /backup/paperless
```

### 3. Auth aktivieren (empfohlen!)

```yaml
environment:
  BACKUP_USER: "admin"
  BACKUP_PASS: "dein-sicheres-passwort"
```

> **Hinweis:** Wenn `BACKUP_USER` gesetzt ist, muss auch `BACKUP_PASS` gesetzt sein.
> Fehlt `BACKUP_PASS`, werden alle geschützten Endpunkte mit HTTP 503 beantwortet.

### 4. Starten

```bash
docker compose up -d --build
```

Öffne: http://localhost:8080

### 5. Produktiv: Socket-Proxy aktivieren (empfohlen)

Für Produktions-Setups schränkt `docker-compose.secure.yml` den Socket-Zugriff
auf das nötige Minimum ein (Container auflisten + exec – kein Zugriff auf Images,
Volumes, Netzwerke o.Ä.):

```bash
docker compose -f docker-compose.yml -f docker-compose.secure.yml up -d --build
```

---

## Umgebungsvariablen

| Variable                   | Standard                        | Beschreibung |
|----------------------------|---------------------------------|--------------|
| `PAPERLESS_IMAGE_NAME`     | `paperless-ngx`                 | Image-Tag-Suche |
| `PAPERLESS_CONTAINER_NAME` | *(leer)*                        | Exakter Container-Name (Override) |
| `EXPORT_PATH_IN_CONTAINER` | `/usr/src/paperless/export`     | Export-Pfad im Paperless-Container |
| `MANAGE_PY_WORKDIR`        | `/usr/src/paperless/src`        | Arbeitsverzeichnis für manage.py |
| `BACKUP_DIR`               | `/backup/paperless`             | Backup-Ziel im Backup-Container |
| `BACKUP_KEEP_LAST`         | `7`                             | Anzahl Archive, die behalten werden |
| `BACKUP_USER`              | *(leer = kein Auth)*            | HTTP Basic Auth Benutzername |
| `BACKUP_PASS`              | *(leer)*                        | HTTP Basic Auth Passwort (Pflicht wenn BACKUP_USER gesetzt) |

---

## Sicherheitshinweise

- **HTTP Basic Auth** immer aktivieren, wenn das Interface öffentlich erreichbar ist.
- **Docker Socket Proxy** für Produktions-Setups: `docker-compose.secure.yml` als
  Overlay verwenden (siehe Schnellstart Schritt 5). Schränkt den Socket-Zugriff auf
  `CONTAINERS` und `EXEC` ein.
- **Netzwerk:** Das Interface sollte nur im internen Netz oder hinter einem Reverse Proxy
  (nginx, Traefik) mit TLS erreichbar sein.

---

## Architektur

```
Browser
  │  SSE-Stream (/backup/stream)
  ▼
Flask (gunicorn, 1 Worker, 4 Threads)
  │  docker Python SDK (low-level API: exec_create / exec_start / exec_inspect)
  ▼
Docker Engine (via /var/run/docker.sock oder Socket-Proxy)
  │  exec in Container
  ▼
Paperless-ngx Container
  └─ python manage.py document_exporter /usr/src/paperless/export

Flask
  └─ subprocess: tar -czf /backup/paperless/papyr.bck_TIMESTAMP.tar.gz
```
