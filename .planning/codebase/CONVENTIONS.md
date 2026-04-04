# Coding Conventions

**Analysis Date:** 2026-04-04

## Naming Patterns

**Files:**
- Python: `snake_case.py` (e.g., `app.py`, `setup_web.py`)
- HTML/Templates: `lowercase.html` (e.g., `index.html`)
- SVG assets: `lowercase.svg` (e.g., `favicon.svg`, `idee1.svg`)

**Functions:**
- Python functions: `snake_case` (e.g., `detect_paperless_container()`, `apply_retention()`, `refreshStatus()`)
- Python decorators: `snake_case` (e.g., `require_auth`)
- JavaScript functions: `camelCase` (e.g., `updateClock()`, `refreshStatus()`, `startBackup()`, `finishBackup()`)
- JavaScript async functions: `camelCase` (e.g., `abortBackup()`)

**Variables:**
- Python module-level constants: `UPPER_SNAKE_CASE` (e.g., `PAPERLESS_IMAGE_NAME`, `BACKUP_DIR`, `BACKUP_KEEP_LAST`)
- Python module-level "private" variables: `_snake_case` prefix (e.g., `_backup_lock`, `_abort_requested`, `_current_container`, `_auth_misconfigured`)
- Python local variables: `snake_case` (e.g., `archive_name`, `docker_client`, `result`)
- JavaScript module-level state: `camelCase` (e.g., `evtSource`, `isRunning`)
- JavaScript local variables: `camelCase` (e.g., `logEl`, `btnBackup`, `el`, `data`)

**Types/Classes:**
- Python class names: `PascalCase` (not observed in main code, but Flask convention)
- HTTP request handlers: `PascalCase` (e.g., `WizardHandler` in `setup_web.py`)

## Code Style

**Formatting:**
- No linting or formatting tools configured (.eslintrc, .prettierrc, etc.)
- Python style follows PEP 8 conventions implicitly
- 2-space indentation in HTML/CSS (inline styles)
- 4-space indentation in Python code
- Line length appears unconstrained (lines exceed 80 characters throughout)

**Comment Style:**
- Section dividers: `# ── Section Name ───────────────────────────────────` (Python, `setup.sh`)
- Module docstrings: Triple-quoted at top of file (e.g., `app.py` line 1-12)
- Function docstrings: Triple-quoted with description and parameters where used
- Inline comments: Sparse, used for non-obvious logic (e.g., `# Low-Level API: exec_create + exec_start...` in app.py:191)

## Import Organization

**Order in Python:**
1. Standard library imports (`import hmac`, `import os`, `import subprocess`, etc.)
2. Third-party imports (`import docker`, `from flask import ...`)

**Example from `app.py`:**
```python
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
```

**Path Aliases:**
- No aliases used (all imports use full paths or relative imports)

## Error Handling

**Patterns:**
- Broad `try/except` blocks with `Exception` catching (e.g., `setup_web.py:39-42`)
- Exception logging: Use `logging` module with `log.error()`, `log.warning()`, `log.critical()` (e.g., `app.py:64`)
- HTTP error responses: Return `Response()` or `jsonify()` with status codes (e.g., `app.py:74-86`)
- Path validation: Check file operations before execution (e.g., `app.py:388-389` path traversal prevention)
- Graceful degradation: Docker client optional, app runs with reduced functionality if unavailable (e.g., `app.py:58-64`)

**Error Context:**
- Include relevant context in error messages: `log.error("Docker containers.list() fehlgeschlagen: %s", exc)` (app.py:106)
- User-facing errors: Plain English/German, no stack traces (e.g., `"Authentifizierung erforderlich."`)
- Debug errors: Include exception details for troubleshooting (e.g., `log.error("pkill fehlgeschlagen: %s", exc)`)

## Logging

**Framework:** Python `logging` module with `basicConfig()`

**Configuration:**
```python
# app.py lines 27-31
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)
```

**Patterns:**
- Info logs: Progress and state changes (e.g., `log.info("Docker-Socket verbunden.")`)
- Warning logs: Degraded states (e.g., `log.warning("exec_inspect fehlgeschlagen: %s", exc)`)
- Critical logs: Configuration errors that affect operation (e.g., `log.critical("SICHERHEITSWARNUNG: ...")`)
- Error logs: Failures that need investigation (e.g., `log.error("Docker-Socket nicht erreichbar: %s", exc)`)

**Frontend Logging (JavaScript):**
- Uses custom `logAppend(text, cls)` function to append to HTML log element
- Classes applied: `log-err`, `log-warn`, `log-ok`, `log-hi`, `log-dim` for styling
- Line classification via regex: `classifyLine(line)` checks content for keywords (`FEHLER`, `ERROR`, `warn`, `erfolgreich`)

## Comments

**When to Comment:**
- Algorithm explanation: When logic is non-obvious (e.g., `app.py:191-192` Docker exec API usage)
- Warning comments: Security or configuration concerns (e.g., `app.py:387` path traversal warning)
- Section dividers: Logical groupings within files (e.g., `# ─── Routes ────` in `app.py`)
- Not applied to: Simple function definitions, obvious control flow

**DocStrings/Comments:**
- Module-level docstrings: Present in `app.py` and `setup_web.py` with German language
- Function docstrings: Short, present in utility functions (e.g., `require_auth`, `detect_paperless_container`)
- JSDoc: Not used in JavaScript; inline documentation minimal

**Example:**
```python
def require_auth(f):
    """Optionale HTTP Basic Auth – aktiv wenn BACKUP_USER *und* BACKUP_PASS gesetzt."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # ... implementation
```

## Function Design

**Size:** Functions are compact to moderate length (15-50 lines typical)
- `require_auth()`: 17 lines (decorator pattern)
- `detect_paperless_container()`: 46 lines (complex container detection)
- `run_backup_generator()`: 107 lines (streaming generator, longest function)

**Parameters:**
- Explicit over implicit: All parameters named (no excessive use of *args, **kwargs except in decorators)
- Type hints: Used sparingly (e.g., `def apply_retention(backup_dir: str, keep_last: int)`)
- Default values: Environment variables as runtime defaults (e.g., `os.environ.get("BACKUP_USER", "")`)

**Return Values:**
- Generator functions use `yield` (e.g., `apply_retention()` yields SSE data chunks)
- Dict returns for structured data (e.g., `detect_paperless_container()` returns detection info dict)
- Tuple unpacking not heavily used
- None implicit for void functions

## Module Design

**Exports:**
- Python modules: No explicit `__all__` defined
- Flask app: Global `app` instance used as entry point (line 53: `app = Flask(__name__)`)
- No barrel files or re-exports

**Global State:**
- Module-level state variables for Flask app coordination:
  - `_backup_lock`: `threading.Lock()` for synchronization
  - `_abort_requested`: `threading.Event()` for cancellation
  - `_current_container`: Container reference for abort operations
  - `_auth_misconfigured`: Boolean flag for configuration errors

**Flask Routes:**
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

---

*Convention analysis: 2026-04-04*
