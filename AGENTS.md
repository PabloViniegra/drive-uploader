## Overview

drive-uploader is a monolithic service that watches a local folder and uploads new files to
Google Drive. It uses a SQLite-backed durable queue plus a thread-pool worker pool so uploads
run concurrently and survive crashes without losing or double-uploading files.

## Technology

- Python >=3.11, managed with `uv`.
- Runtime deps: `google-api-python-client`, `google-auth` (Service Account auth), `watchdog`
  (filesystem events).
- Concurrency/persistence are stdlib only: `sqlite3`, `threading`,
  `concurrent.futures.ThreadPoolExecutor`. No external queue/task library.
- Dev: `pytest`, `ruff`.

## Commands

- Install: `uv sync`
- Run: `PYTHONPATH=src uv run python -m src.bootstrap.main` (requires env vars, see Architecture)
- Lint: `uv run ruff check .`
- Imports: `PYTHONPATH=src uv run lint-imports` (enforces the hexagonal layering rules — `core-knows-no-adapters`, `adapters-dont-reach-into-each-other`)
- Test: `uv run pytest -q`

## Architecture

**Pattern:** Hexagonal / Ports & Adapters
**Decision date:** 2026-07-02
**Status:** Accepted
**ADR:** /adr/001-hexagonal-ports-and-adapters.md

### Guiding principles

- `domain/` is the innermost layer: it imports nothing outside stdlib and sibling `domain/` modules. All ports live there as `typing.Protocol` (not `abc.ABC`).
- `application/use_cases/` orchestrates business behaviour using `domain/` ports. It does not know about Drive, SQLite, watchdog or the worker pool.
- `infrastructure/` holds adapters — driving (watchdog) plus driven (sqlite, google_drive, worker_pool). Each driven adapter implements exactly one `domain/` port.
- `bootstrap/dependency_container.py` is the **only** place where core and adapters are wired together. It owns lifecycle (`start()` / `stop()`, SIGINT/SIGTERM).
- `shared/config.py` is the only allowed non-hexagonal top-level package; it carries env-driven `Settings` and is treated as cross-cutting.

### Layout

`src/` is a PEP 420 implicit-namespace layout: there are **no `__init__.py`** files. Source code imports everything via the `src.` prefix (e.g. `from src.domain.foo import Bar`), which lets `import-linter` (root_package = `src`) build a real dependency graph. Do not re-add `__init__.py` "for consistency", and keep the `src.` prefix in every import.

```
src/
├── domain/                       # entities, value_objects, ports (Protocol)
├── application/use_cases/        # EnqueueFile, UploadFile, ProcessQueue
├── infrastructure/
│   ├── filesystem/               # driving: watchdog_adapter
│   ├── persistence/              # driven:  sqlite_repository
│   ├── drive/                    # driven:  google_drive_adapter
│   └── threading/                # driven:  worker_pool
├── shared/                       # config (cross-cutting Settings)
└── bootstrap/                    # composition root + entrypoint only
```

### Rules for contributors (enforceable)

1. `domain/` may import only stdlib + sibling `domain/` modules.
2. `application/` may import `domain/` and `shared/`, plus stdlib / external libs. Never `infrastructure/` or `bootstrap/`.
3. `infrastructure/` may import `domain/`, `shared/`, stdlib and external libs. Adapters do not import one another.
4. `bootstrap/` is the only package that may import from every other top-level package.
5. New top-level packages under `src/` require an ADR update before merge.
6. Use cases receive dependencies via constructor injection (verified via `tests/conftest.py`).

Linter wiring (done; see ADR-001 M6): `import-linter` with contracts `core-knows-no-adapters` and `adapters-dont-reach-into-each-other`. The contracts are real (grimp reports 30 resolved dependencies); they caught a violation while being wired (the rejected `application-knows-no-shared` contract conflicted with the CLAUDE.md rule that allows `shared/` as cross-cutting — that contract was dropped).

### Flow

watchdog detects a stable file (size stops changing for `STABLE_CHECK_INTERVAL` seconds) → `EnqueueFile` dedups via `exists_active` and persists the job as WAITING → `ProcessQueue` atomically `claim()`s a batch (WAITING→UPLOADING) → worker-pool threads run `UploadFile` → DONE (and optionally delete the local file), or back to WAITING with `sleep(2**retries)` backoff, or FAILED past `retry_attempts`.

`scan_existing()` is called once at `start()` so files already on disk when the watcher comes up are also enqueued.

### Config

`shared/config.py::load_settings()` reads env vars. Required: `WATCH_FOLDER`, `DRIVE_FOLDER_ID`, `GOOGLE_CREDENTIALS`. Optional: `WORKERS` (4), `DATABASE` (`./drive_uploader.db`), `RETRY_ATTEMPTS` (3), `DELETE_AFTER_UPLOAD` (false), `GOOGLE_TOKEN_PATH` (`./token.json`).

> **Drift to resolve (ADR-001 M3):** the current `GoogleDriveAdapter._credentials` uses OAuth `InstalledAppFlow` (interactive consent on first run + token refresh), but the line in `## Technology` still says "Service Account". Don't assume Service Account auth until M3 is closed — either update `CLAUDE.md` or rewrite the adapter.

### Why we chose this

The de-facto layout already separates `domain`, `application`, `infrastructure` and `bootstrap`; the 2026-07-02 audit (ADR-001) confirmed the hexagon is being followed in the large. This section prescribes it so the rules are enforceable, and so the seams that still need repair (`WorkerPoolPort`, signal-handler ordering, idempotency ordering, the auth drift above) have an ordered migration plan in the ADR rather than slipping in one at a time.

## Code Style

- Ruff, line-length 100, default rule set — no extra linter plugins enabled.
- Import submodules directly with the `src.` prefix, e.g. `from
  src.domain.value_objects.upload_status import UploadStatus`, not package-level re-exports —
  there is no `__init__.py` to hold them.
- `# ponytail:` comments mark a deliberate simplification and name its upgrade trigger (e.g.
  the single global SQLite write lock, one Drive `service` per thread). Read the comment
  before "fixing" what it already accounts for.

## Others

- Tests use hand-written in-memory fakes (`tests/conftest.py`: `InMemoryQueueRepository`,
  `FakeUploader`), no mocking library. `test_sqlite_repository.py` runs against the real
  SQLite adapter via `tmp_path`, including a sequential double-`claim()` test proving no job
  is dispatched twice.

## Agent skills

### Issue tracker

GitHub Issues via the `gh` CLI. External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` and `adr/` at the repo root. See `docs/agents/domain.md`.
