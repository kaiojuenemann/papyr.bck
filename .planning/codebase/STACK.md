# Technology Stack

**Analysis Date:** 2026-04-04

## Languages

**Primary:**
- Python 3.12 - Backend application logic, Docker entry point, HTTP server
- HTML5 - Frontend UI template (`templates/index.html`)
- JavaScript (vanilla) - Client-side event streaming, status polling, DOM management
- Bash - Setup automation (`setup.sh`), container shell commands within Docker

**Secondary:**
- YAML - Docker Compose configuration files

## Runtime

**Environment:**
- Python 3.12-slim - Official Python Docker base image
- Docker - Container orchestration and execution
- Docker Compose - Multi-container orchestration

**Package Manager:**
- pip - Python package manager
- Lockfile: `requirements.txt` (present, pinned versions)

## Frameworks

**Core:**
- Flask 3.1.0 - HTTP web framework, routing, request handling, template rendering
  - Location: `app.py`
  - Purpose: RESTful API endpoints, SSE stream handling, static file serving

**Build/Dev:**
- Gunicorn 23.0.0 - WSGI HTTP server for production deployment
  - Configuration: 1 worker, 4 threads, 3600s timeout (for long-running backups)
  - Bind: 0.0.0.0:8080
- Docker 7.1.0 - Python Docker SDK for runtime container introspection and management
  - Purpose: Query running containers, detect Paperless-ngx, execute commands via Docker API

## Key Dependencies

**Critical:**
- Flask 3.1.0 - HTTP request/response handling, template rendering
- docker 7.1.0 - Docker SDK Python client, enables container detection and command execution
- gunicorn 23.0.0 - Production WSGI server, handles concurrent requests with threading
- (Python standard library: `subprocess`, `threading`, `logging`, `pathlib`, `hmac`, `json`, etc.)

**Infrastructure:**
- tar - System binary used for archive creation (installed via apt in Dockerfile)
- curl - System binary used for health checks (installed via apt in Dockerfile)

## Configuration

**Environment Variables:**
The application is entirely configured via environment variables (no .env file reading in app.py):

- `PAPERLESS_IMAGE_NAME` - Docker image tag to search for (default: "paperless-ngx")
- `PAPERLESS_CONTAINER_NAME` - Explicit container name override (optional, default: empty)
- `EXPORT_PATH_IN_CONTAINER` - Path where document_exporter writes in Paperless container (default: "/usr/src/paperless/export")
- `MANAGE_PY_WORKDIR` - Working directory for manage.py commands in Paperless (default: "/usr/src/paperless/src")
- `BACKUP_DIR` - Host-side backup storage directory (default: "/backup/paperless")
- `BACKUP_KEEP_LAST` - Number of archives to retain before deletion (default: 7)
- `BACKUP_USER` - Optional HTTP Basic Auth username (empty = no auth)
- `BACKUP_PASS` - Optional HTTP Basic Auth password (must be set if BACKUP_USER is set)

**Build Configuration:**
- `Dockerfile` - Containerization spec, installs Python 3.12-slim, pip packages, system tools
  - Security: Non-root user "backup" with group membership for Docker socket access
  - Healthcheck: HTTP GET /health endpoint with 30s interval
- `docker-compose.yml` - Multi-container orchestration
  - Services: paperless-ngx (external), paperless-backup-ui (built from .), socket-proxy (optional)
  - Networks: bridge network "paperless_net" for inter-container communication
  - Volumes: Docker socket, export path, backup directory

**Setup Configuration:**
- `setup.sh` - Interactive shell script for first-time setup
  - No pip/system dependencies (stdlib only in Python)
  - Detects free port automatically
  - Queries Docker GID and creates .env file
  - Offers optional `docker compose up -d --build`
- `setup_web.py` - Alternative web-based setup wizard
  - HTTP server for GUI configuration
  - Auto-generates .env file
  - Standalone (stdlib-only, no pip installs required)

## Platform Requirements

**Development:**
- Docker & Docker Compose installed on host
- Python 3 (for running setup scripts locally)
- Bash shell
- Git (for cloning repository)

**Production:**
- Docker 20.10+ (for Docker Compose v2 support)
- Docker Compose 2.0+
- Linux kernel (tested on Docker Desktop for Mac/Windows via VM)
- Mounted Docker socket (`/var/run/docker.sock`) with appropriate group permissions
- 500MB+ free disk space (for backup archives)

**Deployment Target:**
- Docker containers on Docker Engine
- Typical deployment: docker-compose up -d on same host as Paperless-ngx
- Alternative secure deployment: docker-compose with socket-proxy overlay (docker-compose.secure.yml)

---

*Stack analysis: 2026-04-04*
