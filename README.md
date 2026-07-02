<div align="center">

# Drive Uploader

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-managed-FFD43B?style=flat&logo=uv&logoColor=black)](https://github.com/astral-sh/uv)
[![Google Drive](https://img.shields.io/badge/Google%20Drive-API-4285F4?style=flat&logo=googledrive&logoColor=white)](https://developers.google.com/drive)
[![SQLite](https://img.shields.io/badge/SQLite-queue-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Ruff](https://img.shields.io/badge/Ruff-linted-D7FF64?style=flat&logo=ruff&logoColor=black)](https://github.com/astral-sh/ruff)
[![pytest](https://img.shields.io/badge/pytest-tested-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](./LICENSE)

A durable, fault-tolerant Google Drive uploader. Watches a local folder, syncs new files to Drive, survives crashes without losing or duplicating work.

</div>

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Project Layout](#project-layout)
- [Testing](#testing)
- [License](#license)

## Overview

`drive-uploader` is a monolithic Python service that watches a local folder and uploads new files to a configured Google Drive folder. A SQLite-backed durable queue plus a thread-pool worker pool make uploads concurrent and crash-safe: no file is lost, and no file is ever uploaded twice.

## Features

- **Durable queue.** SQLite is the single source of truth. Jobs persist across restarts; a job is never dispatched twice.
- **Concurrent uploads.** Configurable worker pool for parallel transfers.
- **Resumable uploads.** Large files use Google Drive's resumable upload protocol.
- **Crash recovery.** Jobs left in `UPLOADING` from a prior crash are reset to `WAITING` on startup.
- **Stable-file detection.** A new file is only enqueued after its size stops changing, so partially-written files are skipped.
- **Exponential backoff.** Failed uploads retry with a `2 ** retries` delay, up to `RETRY_ATTEMPTS` before being marked `FAILED`.
- **Hexagonal architecture.** The `domain` layer has no outward dependencies; `application` only knows about `Protocol` ports.

## Architecture

The project follows a hexagonal (ports & adapters) layout under `src/`:

```
domain/           entities, value objects, ports (Protocols). Zero outward imports.
application/      use cases: EnqueueFile, UploadFile, ProcessQueue.
infrastructure/   adapters: SQLite repository, Google Drive, watchdog, worker pool.
bootstrap/        composition root, dependency wiring, lifecycle (SIGINT/SIGTERM).
shared/           configuration loader.
```

Dependency direction: `infrastructure` and `bootstrap` -> `application` -> `domain`. There are no `__init__.py` files: the layout uses PEP 420 implicit namespace packages, with `pythonpath = ["src"]` configured in `pyproject.toml`.

### Data flow

1. `watchdog` detects a new file in the watch folder and waits for its size to stabilise.
2. `EnqueueFile` persists the path as `WAITING` (deduplicated against any active job on the same path).
3. `ProcessQueue` atomically claims a batch of `WAITING` jobs, transitioning them to `UPLOADING`.
4. `WorkerPool` threads run `UploadFile` against the Drive adapter.
5. Outcome: `DONE`, or back to `WAITING` with backoff, or `FAILED` once retries are exhausted.

## Requirements

- Python 3.11 or newer
- [`uv`](https://github.com/astral-sh/uv) as the package manager
- A Google Cloud Service Account with the Drive API enabled, plus its JSON credentials file
- A target Google Drive folder (you need its folder ID)

## Installation

```bash
git clone <your-fork-url> drive-uploader
cd drive-uploader
make install
```

`make install` runs `uv sync`, which creates the virtual environment and installs runtime and development dependencies.

## Configuration

All settings come from environment variables. Copy `.env.example` to `.env` and edit the values:

```env
WATCH_FOLDER=/absolute/path/to/watch
DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_CREDENTIALS=/absolute/path/to/service-account.json
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `WATCH_FOLDER` | yes | — | Folder to monitor for new files. |
| `DRIVE_FOLDER_ID` | yes | — | ID of the target Google Drive folder. |
| `GOOGLE_CREDENTIALS` | yes | — | Path to a Service Account JSON file. |
| `WORKERS` | no | `4` | Thread-pool size for parallel uploads. |
| `DATABASE` | no | `./drive_uploader.db` | Path to the SQLite queue file. |
| `RETRY_ATTEMPTS` | no | `3` | Maximum retry attempts per job before marking it `FAILED`. |
| `DELETE_AFTER_UPLOAD` | no | `false` | Delete the local file after a successful upload. |

## Usage

```bash
make run
```

On start the service:

1. Recovers any jobs left in `UPLOADING` from a previous run (resets them to `WAITING`).
2. Scans the watch folder and enqueues files already present.
3. Starts the filesystem watcher and the dispatcher loop.

Stop with `Ctrl+C`. SIGINT and SIGTERM are handled gracefully.

## Development

```bash
make install   # uv sync
make lint      # ruff check
make test      # pytest -q
make clean     # remove __pycache__ directories and the local SQLite file
```

## Project Layout

```
src/
  application/use_cases/    EnqueueFile, UploadFile, ProcessQueue
  bootstrap/                dependency_container, main entrypoint
  domain/
    entities/               UploadJob
    value_objects/          UploadStatus
    ports/                  DriveUploaderPort, QueueRepositoryPort, WorkerPoolPort
  infrastructure/
    drive/                  GoogleDriveAdapter
    filesystem/             FolderWatcher (watchdog)
    persistence/            SqliteQueueRepository
    threading/              WorkerPool
  shared/                   configuration loader

tests/
  conftest.py               InMemoryQueueRepository, FakeUploader
  test_enqueue_file.py
  test_sqlite_repository.py
  test_upload_file.py
```

## Testing

Tests use hand-written in-memory fakes defined in `tests/conftest.py`; there is no mocking library. The SQLite repository tests run against a real SQLite file in a `tmp_path` fixture and include a sequential double-`claim()` test that proves a job is never dispatched twice.

## License

Released under the [MIT License](./LICENSE).