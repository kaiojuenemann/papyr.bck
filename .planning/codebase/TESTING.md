# Testing

**Analysis Date:** 2026-04-04

## Framework

**Status: No automated tests exist.**

No test files, no pytest/unittest configuration, no CI pipeline, no `pyproject.toml`, no `setup.cfg`. This is a solo-developed utility with zero test infrastructure at this time.

---

## Manual Testing Approach

The application is currently validated manually:

1. **Run the container** via `docker-compose up --build`
2. **Open browser** at `http://localhost:8080`
3. **Click "Start Backup"** — observe SSE stream output in the UI
4. **Verify archive** appears in the configured `BACKUP_DIR`
5. **Test abort** — click Abort during a running backup

---

## What Would Need Testing (If Added)

### Unit-testable units

| Module | Testable behaviors |
|--------|------------------|
| `app.py` — container detection | `docker_client.containers.list()` mock → correct mode/container detected |
| `app.py` — auth decorator | Missing/wrong credentials → 401; correct → pass-through |
| `app.py` — auth misconfiguration | `BACKUP_USER` set + empty `BACKUP_PASS` → 503 on all protected routes |
| `app.py` — backup retention | `BACKUP_KEEP_LAST=3` with 5 archives → oldest 2 deleted |
| `app.py` — `/health` endpoint | `docker_client=None` → 503; ping ok → 200 |

### Integration test scenarios

| Scenario | What to test |
|----------|-------------|
| Full backup flow | Exec created in Paperless container → output streamed via SSE → archive created |
| Concurrent backup lock | Second `/backup/stream` request while one is running → rejected |
| Abort flow | `POST /backup/abort` during stream → exec terminates, SSE closes |
| Docker socket unavailable | `docker_client=None` on startup → all endpoints return meaningful error |
| Archive download | `GET /backup/download/<filename>` → correct file served |

### Frontend (manual/browser)

- SSE connection opens and streams output lines
- Progress indicator updates
- Abort button disables correctly after click
- UI recovers if SSE connection drops

---

## Key Testing Gaps

- **No regression protection** — any refactor could silently break backup flow
- **SSE streaming** is inherently hard to unit-test (requires real HTTP streaming or mocking `stream_with_context`)
- **Docker exec** requires a real Docker daemon or a well-mocked Docker SDK client
- **Thread safety** of `_backup_lock` and `_abort_requested` is not tested under concurrency

---

## Recommended Test Stack (If Adding Tests)

```
pytest                  # test runner
pytest-flask            # Flask test client fixture
pytest-mock / unittest.mock  # mock Docker SDK
responses               # if any HTTP calls added later
```

Minimal `conftest.py` would need:
- Fixture that patches `docker.from_env()` to return a mock client
- Flask test app with env vars set for auth/no-auth modes

---

*Testing analysis: 2026-04-04*
