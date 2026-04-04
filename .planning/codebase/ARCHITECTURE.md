# Architecture

**Analysis Date:** 2026-04-04

## Pattern Overview

**Overall:** Monolithic Flask microservice with streaming SSE (Server-Sent Events) for long-running backup operations.

**Key Characteristics:**
- Single-container Flask application with tight Docker integration
- Streaming output pattern for real-time progress feedback
- Thread-safe operation with locking mechanism for concurrent backup attempts
- Docker-first deployment with gunicorn WSGI server
- Event-driven abort mechanism for graceful process termination

## Layers

**Frontend (Browser):**
- Purpose: Real-time UI rendering and event stream consumption
- Location: `templates/index.html`
- Contains: HTML5, CSS (dark theme), vanilla JavaScript
- Depends on: Flask routes, EventSource API
- Used by: End users via web browsers

**API Layer (Flask Routes):**
- Purpose: HTTP endpoints for status, backup control, and downloads
- Location: `app.py` (routes section starting line 276)
- Contains: `@app.route` decorated functions with `@require_auth` decorator
- Depends on: Docker SDK, filesystem operations
- Used by: Frontend UI, health monitoring systems

**Business Logic (Generators & Helpers):**
- Purpose: Orchestration of multi-step backup process
- Location: `app.py` (generator functions starting line 165)
- Contains: `run_backup_generator()`, `apply_retention()`, container detection
- Depends on: Docker API, subprocess, filesystem
- Used by: `/backup/stream` route

**Infrastructure (Docker & System):**
- Purpose: Container management and file operations
- Location: `app.py` (initialization section starting line 58)
- Contains: Docker client connection, logging setup, configuration
- Depends on: Docker daemon, environment variables
- Used by: All layers above

## Data Flow

**Backup Initiation:**

1. User clicks "Start Backup" button in `templates/index.html`
2. JavaScript opens EventSource to `/backup/stream` route
3. Flask checks `_backup_lock` (line 331) - returns error if already running
4. Acquires lock and yields from `run_backup_generator()`

**Backup Execution (Generator-driven Streaming):**

1. **Detection Phase** (line 177-188):
   - `detect_paperless_container()` queries Docker API via SDK
   - Returns container object and metadata (compose mode vs docker-run mode)
   - Streams: "Container gefunden: ..."

2. **Export Phase** (line 193-236):
   - Uses Docker low-level API `exec_create()` + `exec_start()` (line 197-202)
   - Executes `python manage.py document_exporter` inside Paperless container
   - Streams output line-by-line as SSE events
   - Checks exit code after completion

3. **Archive Phase** (line 238-265):
   - Subprocess runs `tar -czf` to compress exported data
   - Creates timestamped archive: `paperless-ngx_YYYY-MM-DD_HH-MM-SS.tar.gz`
   - Computes file size in MB
   - Streams: archive name and size

4. **Retention Phase** (line 267-269):
   - `apply_retention()` deletes archives older than `BACKUP_KEEP_LAST` (default: 7)
   - Removes files by modification time, newest first
   - Streams deletion events

5. **Completion** (line 271-273):
   - Yields `__DONE_OK__` or `__DONE_ERROR__` sentinel
   - Releases `_backup_lock` in finally block

**State Management:**

- **`_backup_lock`** (threading.Lock, line 54): Ensures only one backup runs at a time
- **`_abort_requested`** (threading.Event, line 55): Set when user clicks abort, checked after export completes
- **`_current_container`** (global, line 56): Holds container reference for abort signal delivery
- **Thread safety:** Lock acquired before generator execution, released in finally block (line 345)

**Status Query Flow:**

1. Frontend polls `/status` endpoint (no auth required if BACKUP_USER not set)
2. Returns:
   - Backup running status (via `_backup_lock.locked()`)
   - List of existing archives with size/timestamp
   - Paperless container detection status
   - Docker availability

## Key Abstractions

**Container Detection Logic:**

- Purpose: Auto-discover Paperless container across docker-compose and docker-run deployments
- Location: `detect_paperless_container()` function (lines 91-145)
- Pattern: Multi-criteria matching (explicit name > image tag > container name substring)
- Return value: Dict with mode, container reference, compose metadata (if applicable)

**Streaming Response Pattern:**

- Purpose: HTTP response with infinite streaming via SSE
- Location: `/backup/stream` route (lines 327-351)
- Pattern: Generator function yielding `data: <msg>\n\n` formatted strings
- Headers: `text/event-stream` mimetype, `X-Accel-Buffering: no` (disable proxy buffering)

**Authentication Decorator:**

- Purpose: Optional HTTP Basic Auth for sensitive endpoints
- Location: `require_auth()` decorator (lines 69-88)
- Pattern: Checks BACKUP_USER/BACKUP_PASS env vars, compares with constant-time HMAC digest
- Applied to: `/`, `/status`, `/backup/stream`, `/backup/abort`, `/backup/download/<filename>`

**Retention Policy:**

- Purpose: Automatic cleanup of old backups
- Location: `apply_retention()` function (lines 148-162)
- Pattern: Glob + sort by mtime, delete oldest beyond threshold
- Generator yields: SSE events for each deletion

## Entry Points

**HTTP Server:**

- Location: `app.py` line 405-406
- Triggers: Container startup (see Dockerfile CMD line 31-36)
- Responsibilities: Bind to 0.0.0.0:8080, serve Flask app via gunicorn
- Configuration: 1 worker, 4 threads, 3600s timeout (for long-running backups)

**Routes:**

| Route | Auth | Purpose |
|-------|------|---------|
| `GET /` | Optional | Render main UI (index.html) |
| `GET /health` | None | Liveness probe (no auth to allow monitoring) |
| `GET /status` | Optional | JSON status snapshot (backup running, archives, container info) |
| `GET /backup/stream` | Optional | SSE stream of backup progress |
| `POST /backup/abort` | Optional | Signal abort to running backup |
| `GET /backup/download/<filename>` | Optional | Download archive file |

## Error Handling

**Strategy:** Fail-fast with streaming error messages to client. Lock released in all paths.

**Patterns:**

- **Auth misconfiguration:** 503 response (lines 46-50, 74-76)
- **Docker unavailable:** Health endpoint returns 503, backup detects as None (lines 62-64)
- **Container not found:** SSE error message + `__DONE_ERROR__` sentinel (lines 180-182)
- **Exec command failure:** Try/except wraps exec_create (line 203), streams error, releases lock (line 345)
- **Path traversal in downloads:** Validates filename, rejects "/" or "\" (line 388)
- **Concurrent backup attempt:** Early return with error message, lock never acquired (line 331-339)

## Cross-Cutting Concerns

**Logging:**
- Framework: Python stdlib `logging` (configured line 27-31)
- Pattern: INFO for checkpoint messages, ERROR for failures, WARNING for degraded states
- Destination: Docker container logs (captured by docker compose)

**Validation:**
- Container detection uses multi-criteria matching (robustness)
- Archive filenames validated for path traversal (security)
- Auth tokens checked with HMAC constant-time comparison (prevents timing attacks)
- Exit codes checked after long-running process (reliability)

**Authentication:**
- HTTP Basic Auth (RFC 7617)
- Optional: Only enforced if both BACKUP_USER and BACKUP_PASS are set (line 78)
- Secure password comparison: `hmac.compare_digest()` (line 81)
- Missing BACKUP_PASS triggers security warning (line 46-50)

**Concurrency:**
- Lock model: Single global `threading.Lock()` for backup execution
- Abort mechanism: `threading.Event()` checked after export completes (line 224)
- Thread-safe: Generator runs within lock context (line 341-345)

---

*Architecture analysis: 2026-04-04*
