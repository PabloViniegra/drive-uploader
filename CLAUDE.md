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
- Run: `PYTHONPATH=src uv run python -m bootstrap.main` (requires env vars, see Architecture)
- Lint: `uv run ruff check .`
- Test: `uv run pytest -q`

## Architecture

Hexagonal, monolithic, `src/` layout with **no `__init__.py` files** — packages are PEP 420
implicit namespace packages; `pythonpath = ["src"]` in `pyproject.toml` makes `domain.*`,
`application.*`, etc. importable as-is. Do not add `__init__.py` back "for consistency" —
namespace packages already work here and were removed deliberately.

Dependency direction: `infrastructure`/`bootstrap` → `application` → `domain`. `domain` has
zero outward imports. `application` never imports `infrastructure.*` directly, only the
`Protocol` ports in `domain/ports/`.

- `domain/`: `entities/upload_job.py` (`UploadJob`), `value_objects/upload_status.py`
  (`UploadStatus`: NEW/WAITING/UPLOADING/DONE/FAILED), `ports/` (`DriveUploaderPort`,
  `QueueRepositoryPort`, `WorkerPoolPort` — all `typing.Protocol`, not ABCs).
- `application/use_cases/`: `EnqueueFile` (dedup via `exists_active` + persist as WAITING),
  `UploadFile` (upload; on failure: `retries += 1`, backoff `sleep(2**retries)`, back to
  WAITING or FAILED past `retry_attempts`), `ProcessQueue` (dispatcher loop: atomically
  `claim()`s a batch of WAITING jobs, submits each to the worker pool).
- `infrastructure/persistence/sqlite_repository.py`: `SqliteQueueRepository` — one shared
  connection (`check_same_thread=False`) guarded by a single `threading.Lock`, WAL mode.
  `claim()` does UPDATE-then-SELECT under the lock so no two dispatcher passes can grab the
  same job. Table has a partial UNIQUE index on `file_path` for WAITING/UPLOADING/DONE (lets
  a FAILED job's path be re-enqueued).
- `infrastructure/drive/google_drive_adapter.py`: `GoogleDriveAdapter` — Service Account
  credentials, resumable `MediaFileUpload`. One Drive `service` object per thread via
  `threading.local` (the client isn't safe to share across threads).
- `infrastructure/filesystem/watchdog_adapter.py`: `FolderWatcher` — `watchdog.Observer` +
  handler that waits for a file's size to stop changing (polls every second) before calling
  `EnqueueFile`, so partially-written files aren't picked up mid-copy. `scan_existing()`
  enqueues files already present at startup.
- `infrastructure/threading/worker_pool.py`: `WorkerPool` — thin wrapper over
  `ThreadPoolExecutor`; this *is* the in-memory work queue, no separate `queue.Queue`.
- `bootstrap/dependency_container.py`: composition root; wires every adapter to its port and
  owns the lifecycle (`start()`/`stop()`, SIGINT/SIGTERM). On `start()`: creates
  `watch_folder`, calls `reset_in_progress()` (recovers jobs stuck in UPLOADING from a prior
  crash), `scan_existing()`, then starts the watcher and the dispatcher thread.
  `bootstrap/main.py` is the entrypoint.

Flow: watchdog detects a stable file → `EnqueueFile` → SQLite (source of truth, WAITING) →
`ProcessQueue` claims a batch atomically (WAITING→UPLOADING) → `WorkerPool` threads run
`UploadFile` → DONE, or WAITING with backoff, or FAILED after `retry_attempts`.

Config: `shared/config.py::load_settings()` reads env vars. Required: `WATCH_FOLDER`,
`DRIVE_FOLDER_ID`, `GOOGLE_CREDENTIALS` (Service Account JSON path). Optional: `WORKERS`
(4), `DATABASE` (`./drive_uploader.db`), `RETRY_ATTEMPTS` (3), `DELETE_AFTER_UPLOAD`
(false).

## Code Style

- Ruff, line-length 100, default rule set — no extra linter plugins enabled.
- Import submodules directly, e.g. `from domain.value_objects.upload_status import
  UploadStatus`, not package-level re-exports — there is no `__init__.py` to hold them.
- `# ponytail:` comments mark a deliberate simplification and name its upgrade trigger (e.g.
  the single global SQLite write lock, one Drive `service` per thread). Read the comment
  before "fixing" what it already accounts for.

## Others

- Tests use hand-written in-memory fakes (`tests/conftest.py`: `InMemoryQueueRepository`,
  `FakeUploader`), no mocking library. `test_sqlite_repository.py` runs against the real
  SQLite adapter via `tmp_path`, including a sequential double-`claim()` test proving no job
  is dispatched twice.
