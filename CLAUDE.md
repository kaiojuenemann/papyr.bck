<!-- GSD:project-start source:PROJECT.md -->
## Project

**papyr.bck — Paperless-ngx Backup UI**

papyr.bck ist eine Web-UI für Paperless-ngx-Backups. Die App läuft als Docker-Container auf demselben Host wie Paperless-ngx, führt den `document_exporter` per Docker-Exec im Paperless-Container aus und streamt den Output live per Server-Sent Events in den Browser. Zielgruppe: Einzelnutzer im Homelab-Umfeld.

**Core Value:** Die App darf niemals die Paperless-ngx-Instanz gefährden — Korrektheit und Sicherheit haben Vorrang vor allem anderen.

### Constraints

- **Tech Stack:** Python 3.12, Flask 3.1.0, Docker SDK 7.1.0, Gunicorn — keine Änderung des Stacks
- **Sicherheit:** Änderungen dürfen die Paperless-Instanz unter keinen Umständen gefährden
- **Vorgehen:** Audit-Ergebnisse werden erst als Liste präsentiert, dann nach Freigabe behoben
- **Deployment:** Muss als Docker-Container laufen, Docker-Socket-Zugriff erforderlich
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - Backend application logic, Docker entry point, HTTP server
- HTML5 - Frontend UI template (`templates/index.html`)
- JavaScript (vanilla) - Client-side event streaming, status polling, DOM management
- Bash - Setup automation (`setup.sh`), container shell commands within Docker
- YAML - Docker Compose configuration files
## Runtime
- Python 3.12-slim - Official Python Docker base image
- Docker - Container orchestration and execution
- Docker Compose - Multi-container orchestration
- pip - Python package manager
- Lockfile: `requirements.txt` (present, pinned versions)
## Frameworks
- Flask 3.1.0 - HTTP web framework, routing, request handling, template rendering
- Gunicorn 23.0.0 - WSGI HTTP server for production deployment
- Docker 7.1.0 - Python Docker SDK for runtime container introspection and management
## Key Dependencies
- Flask 3.1.0 - HTTP request/response handling, template rendering
- docker 7.1.0 - Docker SDK Python client, enables container detection and command execution
- gunicorn 23.0.0 - Production WSGI server, handles concurrent requests with threading
- (Python standard library: `subprocess`, `threading`, `logging`, `pathlib`, `hmac`, `json`, etc.)
- tar - System binary used for archive creation (installed via apt in Dockerfile)
- curl - System binary used for health checks (installed via apt in Dockerfile)
## Configuration
- `PAPERLESS_IMAGE_NAME` - Docker image tag to search for (default: "paperless-ngx")
- `PAPERLESS_CONTAINER_NAME` - Explicit container name override (optional, default: empty)
- `EXPORT_PATH_IN_CONTAINER` - Path where document_exporter writes in Paperless container (default: "/usr/src/paperless/export")
- `MANAGE_PY_WORKDIR` - Working directory for manage.py commands in Paperless (default: "/usr/src/paperless/src")
- `BACKUP_DIR` - Host-side backup storage directory (default: "/backup/paperless")
- `BACKUP_KEEP_LAST` - Number of archives to retain before deletion (default: 7)
- `BACKUP_USER` - Optional HTTP Basic Auth username (empty = no auth)
- `BACKUP_PASS` - Optional HTTP Basic Auth password (must be set if BACKUP_USER is set)
- `Dockerfile` - Containerization spec, installs Python 3.12-slim, pip packages, system tools
- `docker-compose.yml` - Multi-container orchestration
- `setup.sh` - Interactive shell script for first-time setup
- `setup_web.py` - Alternative web-based setup wizard
## Platform Requirements
- Docker & Docker Compose installed on host
- Python 3 (for running setup scripts locally)
- Bash shell
- Git (for cloning repository)
- Docker 20.10+ (for Docker Compose v2 support)
- Docker Compose 2.0+
- Linux kernel (tested on Docker Desktop for Mac/Windows via VM)
- Mounted Docker socket (`/var/run/docker.sock`) with appropriate group permissions
- 500MB+ free disk space (for backup archives)
- Docker containers on Docker Engine
- Typical deployment: docker-compose up -d on same host as Paperless-ngx
- Alternative secure deployment: docker-compose with socket-proxy overlay (docker-compose.secure.yml)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python: `snake_case.py` (e.g., `app.py`, `setup_web.py`)
- HTML/Templates: `lowercase.html` (e.g., `index.html`)
- SVG assets: `lowercase.svg` (e.g., `favicon.svg`, `idee1.svg`)
- Python functions: `snake_case` (e.g., `detect_paperless_container()`, `apply_retention()`, `refreshStatus()`)
- Python decorators: `snake_case` (e.g., `require_auth`)
- JavaScript functions: `camelCase` (e.g., `updateClock()`, `refreshStatus()`, `startBackup()`, `finishBackup()`)
- JavaScript async functions: `camelCase` (e.g., `abortBackup()`)
- Python module-level constants: `UPPER_SNAKE_CASE` (e.g., `PAPERLESS_IMAGE_NAME`, `BACKUP_DIR`, `BACKUP_KEEP_LAST`)
- Python module-level "private" variables: `_snake_case` prefix (e.g., `_backup_lock`, `_abort_requested`, `_current_container`, `_auth_misconfigured`)
- Python local variables: `snake_case` (e.g., `archive_name`, `docker_client`, `result`)
- JavaScript module-level state: `camelCase` (e.g., `evtSource`, `isRunning`)
- JavaScript local variables: `camelCase` (e.g., `logEl`, `btnBackup`, `el`, `data`)
- Python class names: `PascalCase` (not observed in main code, but Flask convention)
- HTTP request handlers: `PascalCase` (e.g., `WizardHandler` in `setup_web.py`)
## Code Style
- No linting or formatting tools configured (.eslintrc, .prettierrc, etc.)
- Python style follows PEP 8 conventions implicitly
- 2-space indentation in HTML/CSS (inline styles)
- 4-space indentation in Python code
- Line length appears unconstrained (lines exceed 80 characters throughout)
- Section dividers: `# ── Section Name ───────────────────────────────────` (Python, `setup.sh`)
- Module docstrings: Triple-quoted at top of file (e.g., `app.py` line 1-12)
- Function docstrings: Triple-quoted with description and parameters where used
- Inline comments: Sparse, used for non-obvious logic (e.g., `# Low-Level API: exec_create + exec_start...` in app.py:191)
## Import Organization
- No aliases used (all imports use full paths or relative imports)
## Error Handling
- Broad `try/except` blocks with `Exception` catching (e.g., `setup_web.py:39-42`)
- Exception logging: Use `logging` module with `log.error()`, `log.warning()`, `log.critical()` (e.g., `app.py:64`)
- HTTP error responses: Return `Response()` or `jsonify()` with status codes (e.g., `app.py:74-86`)
- Path validation: Check file operations before execution (e.g., `app.py:388-389` path traversal prevention)
- Graceful degradation: Docker client optional, app runs with reduced functionality if unavailable (e.g., `app.py:58-64`)
- Include relevant context in error messages: `log.error("Docker containers.list() fehlgeschlagen: %s", exc)` (app.py:106)
- User-facing errors: Plain English/German, no stack traces (e.g., `"Authentifizierung erforderlich."`)
- Debug errors: Include exception details for troubleshooting (e.g., `log.error("pkill fehlgeschlagen: %s", exc)`)
## Logging
- Info logs: Progress and state changes (e.g., `log.info("Docker-Socket verbunden.")`)
- Warning logs: Degraded states (e.g., `log.warning("exec_inspect fehlgeschlagen: %s", exc)`)
- Critical logs: Configuration errors that affect operation (e.g., `log.critical("SICHERHEITSWARNUNG: ...")`)
- Error logs: Failures that need investigation (e.g., `log.error("Docker-Socket nicht erreichbar: %s", exc)`)
- Uses custom `logAppend(text, cls)` function to append to HTML log element
- Classes applied: `log-err`, `log-warn`, `log-ok`, `log-hi`, `log-dim` for styling
- Line classification via regex: `classifyLine(line)` checks content for keywords (`FEHLER`, `ERROR`, `warn`, `erfolgreich`)
## Comments
- Algorithm explanation: When logic is non-obvious (e.g., `app.py:191-192` Docker exec API usage)
- Warning comments: Security or configuration concerns (e.g., `app.py:387` path traversal warning)
- Section dividers: Logical groupings within files (e.g., `# ─── Routes ────` in `app.py`)
- Not applied to: Simple function definitions, obvious control flow
- Module-level docstrings: Present in `app.py` and `setup_web.py` with German language
- Function docstrings: Short, present in utility functions (e.g., `require_auth`, `detect_paperless_container`)
- JSDoc: Not used in JavaScript; inline documentation minimal
## Function Design
- `require_auth()`: 17 lines (decorator pattern)
- `detect_paperless_container()`: 46 lines (complex container detection)
- `run_backup_generator()`: 107 lines (streaming generator, longest function)
- Explicit over implicit: All parameters named (no excessive use of *args, **kwargs except in decorators)
- Type hints: Used sparingly (e.g., `def apply_retention(backup_dir: str, keep_last: int)`)
- Default values: Environment variables as runtime defaults (e.g., `os.environ.get("BACKUP_USER", "")`)
- Generator functions use `yield` (e.g., `apply_retention()` yields SSE data chunks)
- Dict returns for structured data (e.g., `detect_paperless_container()` returns detection info dict)
- Tuple unpacking not heavily used
- None implicit for void functions
## Module Design
- Python modules: No explicit `__all__` defined
- Flask app: Global `app` instance used as entry point (line 53: `app = Flask(__name__)`)
- No barrel files or re-exports
- Module-level state variables for Flask app coordination:
- All routes decorated with `@app.route()` and optionally `@require_auth`
- Routes grouped logically: health/status endpoints first, then backup operations
- No blueprint organization (single monolithic app.py)
## Naming Conventions Summary
| Item | Convention | Example |
|------|-----------|---------|
| Python files | snake_case | app.py, setup_web.py |
| Python functions | snake_case | detect_paperless_container() |
| Python constants | UPPER_SNAKE_CASE | BACKUP_USER, BACKUP_KEEP_LAST |
| Python private | _snake_case | _backup_lock, _abort_requested |
| JavaScript functions | camelCase | startBackup(), refreshStatus() |
| JavaScript state | camelCase | evtSource, isRunning |
| HTML classes | kebab-case | panel-head, status-grid, log-err |
| CSS custom properties | kebab-case | --bg, --accent, --text-dim |
| HTML IDs | kebab-case | dot-docker, btn-backup, progress-bar |
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Single-container Flask application with tight Docker integration
- Streaming output pattern for real-time progress feedback
- Thread-safe operation with locking mechanism for concurrent backup attempts
- Docker-first deployment with gunicorn WSGI server
- Event-driven abort mechanism for graceful process termination
## Layers
- Purpose: Real-time UI rendering and event stream consumption
- Location: `templates/index.html`
- Contains: HTML5, CSS (dark theme), vanilla JavaScript
- Depends on: Flask routes, EventSource API
- Used by: End users via web browsers
- Purpose: HTTP endpoints for status, backup control, and downloads
- Location: `app.py` (routes section starting line 276)
- Contains: `@app.route` decorated functions with `@require_auth` decorator
- Depends on: Docker SDK, filesystem operations
- Used by: Frontend UI, health monitoring systems
- Purpose: Orchestration of multi-step backup process
- Location: `app.py` (generator functions starting line 165)
- Contains: `run_backup_generator()`, `apply_retention()`, container detection
- Depends on: Docker API, subprocess, filesystem
- Used by: `/backup/stream` route
- Purpose: Container management and file operations
- Location: `app.py` (initialization section starting line 58)
- Contains: Docker client connection, logging setup, configuration
- Depends on: Docker daemon, environment variables
- Used by: All layers above
## Data Flow
- **`_backup_lock`** (threading.Lock, line 54): Ensures only one backup runs at a time
- **`_abort_requested`** (threading.Event, line 55): Set when user clicks abort, checked after export completes
- **`_current_container`** (global, line 56): Holds container reference for abort signal delivery
- **Thread safety:** Lock acquired before generator execution, released in finally block (line 345)
## Key Abstractions
- Purpose: Auto-discover Paperless container across docker-compose and docker-run deployments
- Location: `detect_paperless_container()` function (lines 91-145)
- Pattern: Multi-criteria matching (explicit name > image tag > container name substring)
- Return value: Dict with mode, container reference, compose metadata (if applicable)
- Purpose: HTTP response with infinite streaming via SSE
- Location: `/backup/stream` route (lines 327-351)
- Pattern: Generator function yielding `data: <msg>\n\n` formatted strings
- Headers: `text/event-stream` mimetype, `X-Accel-Buffering: no` (disable proxy buffering)
- Purpose: Optional HTTP Basic Auth for sensitive endpoints
- Location: `require_auth()` decorator (lines 69-88)
- Pattern: Checks BACKUP_USER/BACKUP_PASS env vars, compares with constant-time HMAC digest
- Applied to: `/`, `/status`, `/backup/stream`, `/backup/abort`, `/backup/download/<filename>`
- Purpose: Automatic cleanup of old backups
- Location: `apply_retention()` function (lines 148-162)
- Pattern: Glob + sort by mtime, delete oldest beyond threshold
- Generator yields: SSE events for each deletion
## Entry Points
- Location: `app.py` line 405-406
- Triggers: Container startup (see Dockerfile CMD line 31-36)
- Responsibilities: Bind to 0.0.0.0:8080, serve Flask app via gunicorn
- Configuration: 1 worker, 4 threads, 3600s timeout (for long-running backups)
| Route | Auth | Purpose |
|-------|------|---------|
| `GET /` | Optional | Render main UI (index.html) |
| `GET /health` | None | Liveness probe (no auth to allow monitoring) |
| `GET /status` | Optional | JSON status snapshot (backup running, archives, container info) |
| `GET /backup/stream` | Optional | SSE stream of backup progress |
| `POST /backup/abort` | Optional | Signal abort to running backup |
| `GET /backup/download/<filename>` | Optional | Download archive file |
## Error Handling
- **Auth misconfiguration:** 503 response (lines 46-50, 74-76)
- **Docker unavailable:** Health endpoint returns 503, backup detects as None (lines 62-64)
- **Container not found:** SSE error message + `__DONE_ERROR__` sentinel (lines 180-182)
- **Exec command failure:** Try/except wraps exec_create (line 203), streams error, releases lock (line 345)
- **Path traversal in downloads:** Validates filename, rejects "/" or "\" (line 388)
- **Concurrent backup attempt:** Early return with error message, lock never acquired (line 331-339)
## Cross-Cutting Concerns
- Framework: Python stdlib `logging` (configured line 27-31)
- Pattern: INFO for checkpoint messages, ERROR for failures, WARNING for degraded states
- Destination: Docker container logs (captured by docker compose)
- Container detection uses multi-criteria matching (robustness)
- Archive filenames validated for path traversal (security)
- Auth tokens checked with HMAC constant-time comparison (prevents timing attacks)
- Exit codes checked after long-running process (reliability)
- HTTP Basic Auth (RFC 7617)
- Optional: Only enforced if both BACKUP_USER and BACKUP_PASS are set (line 78)
- Secure password comparison: `hmac.compare_digest()` (line 81)
- Missing BACKUP_PASS triggers security warning (line 46-50)
- Lock model: Single global `threading.Lock()` for backup execution
- Abort mechanism: `threading.Event()` checked after export completes (line 224)
- Thread-safe: Generator runs within lock context (line 341-345)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
