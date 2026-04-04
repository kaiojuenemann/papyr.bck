# External Integrations

**Analysis Date:** 2026-04-04

## Docker API (Primary Integration)

**SDK:** `docker==7.1.0` (Python Docker SDK)
**Connection:** Unix socket `/var/run/docker.sock` mounted at runtime

### How it's used

```python
docker_client = docker.from_env()   # connects via DOCKER_HOST or /var/run/docker.sock
docker_client.ping()                # validated at startup
```

**Operations performed:**
- `docker_client.containers.list()` — enumerate all running containers
- `docker_client.api.exec_create(container_id, cmd, ...)` — create exec inside Paperless container
- `docker_client.api.exec_start(exec_id, stream=True)` — stream command output
- `docker_client.api.exec_inspect(exec_id)` — read exit code after exec
- `docker_client.api.exec_resize(exec_id, ...)` — set pseudo-TTY size

**Container detection logic (`/status` endpoint):**
1. Lists all running containers
2. Matches by `PAPERLESS_CONTAINER_NAME` (if set) OR by image name containing `PAPERLESS_IMAGE_NAME`
3. Extracts Docker Compose labels (`com.docker.compose.project`, `com.docker.compose.service`) to determine mode
4. Returns `mode: "compose"` or `mode: "run"` — affects how backup command is constructed

**Failure handling:** If `docker_client` is None (socket unavailable), all protected endpoints return 503.

---

## Paperless-ngx Container (Target Integration)

**Type:** In-process Docker exec (no HTTP calls to Paperless)
**Requirement:** Paperless-ngx must be running as a Docker container on the same Docker host

### Backup command executed inside container

```
python manage.py document_exporter {EXPORT_PATH_IN_CONTAINER}
```

- **Working dir inside container:** `MANAGE_PY_WORKDIR` (default: `/usr/src/paperless/src`)
- **Output path inside container:** `EXPORT_PATH_IN_CONTAINER` (default: `/usr/src/paperless/export`)
- The export path must be a shared volume accessible to the backup-ui container

### Post-export archival (on host)
After export completes, the backup-ui containers zips the export into a timestamped `.tar.gz` in `BACKUP_DIR`, then prunes old archives (keeps `BACKUP_KEEP_LAST`).

---

## Local Filesystem

**Volumes mounted at runtime:**
| Host path | Container path | Purpose |
|-----------|---------------|---------|
| `/var/run/docker.sock` | `/var/run/docker.sock` | Docker API access |
| (configurable) | `/backup/paperless` | Backup archive storage |
| (shared with Paperless) | `/usr/src/paperless/export` | Export output from Paperless |

**File operations:**
- Archive creation via `tar` CLI (system binary, not Python tarfile)
- Archive listing/download via Flask `send_file`
- Old archive deletion via `pathlib.Path.unlink`

---

## HTTP Basic Auth (Optional)

**Type:** Built-in, custom implementation using `hmac.compare_digest`
**Activation:** Set both `BACKUP_USER` and `BACKUP_PASS` environment variables

```python
@require_auth   # decorator applied to all non-health routes
def require_auth(f):
    if not auth or auth.username != BACKUP_USER or not hmac.compare_digest(auth.password, BACKUP_PASS):
        return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Backup"'})
```

**Misconfiguration guard:** If `BACKUP_USER` is set but `BACKUP_PASS` is empty, all protected endpoints return 503 and log a CRITICAL warning.

---

## Docker Socket Proxy (Optional Secure Variant)

**File:** `docker-compose.secure.yml`
**Purpose:** Limits Docker socket exposure — only specific API paths are proxied (read-only container listing, exec endpoints)
**Pattern:** `tecnativa/docker-socket-proxy` or similar in the compose file

---

## No External Services

This application has **zero external HTTP dependencies** at runtime:
- No cloud storage
- No external APIs (Paperless API is not used — exec is used instead)
- No telemetry or analytics
- No external auth providers (OIDC, OAuth, etc.)
- No message queues or databases

---

## API Endpoints Exposed

| Route | Auth | Method | Purpose |
|-------|------|--------|---------|
| `/` | ✓ | GET | Serve web UI |
| `/health` | ✗ | GET | Health check (used by Docker) |
| `/status` | ✓ | GET | Container detection + backup state |
| `/backup/stream` | ✓ | GET | SSE stream — run backup, stream output |
| `/backup/abort` | ✓ | POST | Signal abort of running backup |
| `/backup/download/<filename>` | ✓ | GET | Download a backup archive |

---

*Integrations analysis: 2026-04-04*
