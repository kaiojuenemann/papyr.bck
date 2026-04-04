# Codebase Structure

**Analysis Date:** 2026-04-04

## Directory Layout

```
/Users/kaijunemann/backup-ui/
├── app.py                          # Flask application (core logic)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container image specification
├── docker-compose.yml              # Multi-container orchestration
├── docker-compose.secure.yml       # Optional socket proxy overlay
├── setup.sh                        # Bash setup wizard (interactive)
├── setup_web.py                    # Web-based setup wizard (stdlib-only)
├── README.md                       # User documentation
├── LICENSE                         # Apache 2.0
├── templates/
│   └── index.html                  # Single-page application (SSE client)
├── .planning/
│   └── codebase/                   # GSD documentation (this directory)
├── .env                            # Runtime configuration (gitignored, auto-generated)
└── .gitignore                      # Git exclusions
```

## Directory Purposes

**Root (Project Root):**
- Purpose: Application source, configuration, and Docker runtime
- Contains: Flask app, templates, deployment manifests
- Key files: `app.py`, `requirements.txt`, `docker-compose.yml`

**templates/ (Frontend Assets):**
- Purpose: HTML/CSS/JS for browser UI
- Contains: Single-file SPA (Single-Page Application)
- Key files: `index.html` (21KB, embedded inline styles and scripts)

**.planning/codebase/ (Documentation):**
- Purpose: GSD (Generative Software Development) analysis documents
- Contains: Architecture, structure, conventions, concerns analysis
- Auto-generated: Yes (by GSD orchestrator)

## Key File Locations

**Entry Points:**

| File | Purpose |
|------|---------|
| `app.py` | Flask WSGI application (loaded by gunicorn in container) |
| `setup.sh` | Interactive shell setup (run once on host before docker compose up) |
| `setup_web.py` | Web-based wizard setup (Python stdlib only, no dependencies) |
| `templates/index.html` | Browser SPA (loaded by Flask GET /) |

**Configuration:**

| File | Purpose | Sensitive |
|------|---------|-----------|
| `requirements.txt` | Python package versions | No |
| `Dockerfile` | Container image build spec | No |
| `docker-compose.yml` | Multi-container deployment manifest | No (env vars interpolated) |
| `docker-compose.secure.yml` | Optional socket proxy for hardened deployments | No |
| `.env` | Runtime environment variables (auto-generated) | **Yes** - never committed |

**Core Logic:**

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 407 | Flask application with all routes and backup orchestration |
| `app.py` lines 33-42 | Config | Environment variable parsing |
| `app.py` lines 52-56 | State | Global Flask app, locks, container reference |
| `app.py` lines 69-88 | Auth | `require_auth()` decorator |
| `app.py` lines 91-145 | Detection | `detect_paperless_container()` function |
| `app.py` lines 148-162 | Retention | `apply_retention()` generator |
| `app.py` lines 165-273 | Orchestration | `run_backup_generator()` main backup flow |
| `app.py` lines 276-402 | Routes | All HTTP endpoints |

**Testing:**

- Test files: None detected
- Test framework: Not configured

## Naming Conventions

**Files:**

- Python modules: lowercase with underscores (`app.py`, `setup.sh`, `setup_web.py`)
- Templates: lowercase with underscores (`index.html`)
- Configuration: dotfiles (`.env`, `.gitignore`) or compound (docker-compose.yml)
- Archives: `paperless-ngx_YYYY-MM-DD_HH-MM-SS.tar.gz` (time-based, sortable)

**Directories:**

- Functional grouping: `templates/`, `.planning/codebase/`
- Lowercase, hyphens not typically used (follows Python convention)

**Functions & Methods:**

- Helpers: snake_case with descriptive verbs (`detect_paperless_container`, `apply_retention`, `run_backup_generator`)
- Route handlers: snake_case matching HTTP semantics (`backup_stream`, `backup_abort`, `backup_download`)
- Internal functions: leading underscore for truly private (`_auth_misconfigured`, `_backup_lock`, `_abort_requested`)

**Variables:**

- Configuration: SCREAMING_SNAKE_CASE for env-backed constants (`PAPERLESS_IMAGE_NAME`, `BACKUP_DIR`, `BACKUP_KEEP_LAST`)
- Flags/locks: snake_case with `_` prefix (`_backup_lock`, `_abort_requested`, `_current_container`)

**Types:**

- No TypeScript/type hints (Python only, untyped)
- Flask decorators: `@app.route()`, `@require_auth`, `@wraps()`

## Where to Add New Code

**New Feature (Backup-related):**

- Primary code: Add function to `app.py` above routes section (before line 276)
- If blocking backup: Integrate into `run_backup_generator()` (lines 165-273)
- If async status: Add state variable near line 54-56, check in `/status` route
- Streaming updates: Yield SSE events from generator

**New Route/Endpoint:**

- Implementation: Add `@app.route()` decorated function in routes section (lines 276-402)
- If sensitive: Apply `@require_auth` decorator (line 279, 292, 328, 355, 384)
- If protected: Check auth status first (line 78)
- Response format: JSON via `jsonify()` or streaming via generator

**Utility/Helper Function:**

- Shared helpers: Add in "Hilfsfunktionen" section (lines 67-162)
- Keep standalone, no Flask dependencies if possible
- Use snake_case naming

**Frontend Changes:**

- All UI code: `templates/index.html` (embedded within single file)
- Structure: Inline `<style>` block (CSS), inline `<script>` block (JavaScript)
- EventSource client: JavaScript event listeners for SSE stream
- Keep logic simple (vanilla JS, no framework)

**Configuration/Deployment:**

- Docker: Modify `Dockerfile` (Alpine/slim Python image, system deps line 7-10)
- Compose: Modify `docker-compose.yml` (volumes, env vars, ports)
- Shell setup: Modify `setup.sh` (interactive prompts, .env generation)
- Web setup: Modify `setup_web.py` (embedded HTML wizard, API endpoints)

## Special Directories

**`templates/`:**
- Purpose: Flask template serving directory
- Generated: No
- Committed: Yes
- Contains: Single `index.html` SPA file (21.6KB)
- Modification: Edit HTML directly in index.html

**`.planning/codebase/`:**
- Purpose: GSD orchestrator documentation
- Generated: Yes (by Claude agent via `/gsd:map-codebase`)
- Committed: Yes (for team reference)
- Files: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md
- Modification: Do not edit manually (auto-generated)

**`.env`:**
- Purpose: Runtime configuration (secrets, deployment-specific values)
- Generated: Yes (by `setup.sh` or `setup_web.py`)
- Committed: No (in .gitignore)
- Contains: BACKUP_USER, BACKUP_PASS, BACKUP_PORT, DOCKER_GID, PAPERLESS_EXPORT_PATH, BACKUP_DIR_HOST
- Modification: Generated by setup wizard or manual editing

## File Relationships

**Request → Response Flow:**

```
Browser Request
    ↓
Flask Route Handler (@app.route + @require_auth)
    ↓
Business Logic (detect_paperless_container, run_backup_generator, etc.)
    ↓
Docker SDK / Subprocess
    ↓
Paperless Container / Filesystem
    ↓
Response (HTML, JSON, SSE Stream, File Download)
    ↓
Browser Rendering / JavaScript Handler
```

**Initialization Sequence (Container Startup):**

1. Dockerfile: `USER backup` (line 24) drops root privileges
2. Dockerfile: CMD executes gunicorn (line 31-36)
3. Gunicorn: Imports `app:app` (app.py Flask instance)
4. app.py: Initializes logger, parses env vars (lines 27-42)
5. app.py: Creates Flask app instance (line 53)
6. app.py: Attempts Docker client connection (lines 58-64)
7. app.py: Registers routes (lines 276-402)
8. Flask: Serving on 0.0.0.0:8080

**Configuration Propagation:**

```
.env (host)
    ↓
docker-compose.yml (interpolates $VAR)
    ↓
Docker environment (passed to container)
    ↓
app.py: os.environ.get() (lines 34-42)
    ↓
Module-level constants (PAPERLESS_IMAGE_NAME, BACKUP_DIR, etc.)
    ↓
Routes and business logic consume constants
```

## Dependency Graph

**External (pip):**
- `flask==3.1.0` → Flask web framework
- `docker==7.1.0` → Docker SDK for Python
- `gunicorn==23.0.0` → WSGI application server

**Standard Library (no import needed):**
- `hmac` → Secure password comparison
- `os` → Environment variables
- `subprocess` → Run tar command
- `threading` → Locks and events
- `logging` → Application logs
- `functools` → @wraps decorator
- `pathlib` → File path operations
- `datetime` → Timestamps

**System Dependencies (Docker):**
- `tar` (line 9 in Dockerfile) → Archive creation
- `curl` (line 9) → Health check
- `python:3.12-slim` base image

---

*Structure analysis: 2026-04-04*
