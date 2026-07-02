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
- [Installing the binary](#installing-the-binary)
- [Installing from source](#installing-from-source)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Project Layout](#project-layout)
- [Testing](#testing)
- [Out of scope](#out-of-scope)
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

End-user install (binary):

- A Google Cloud Service Account with the Drive API enabled, plus its JSON credentials file
- A target Google Drive folder (you need its folder ID)
- Windows 10/11 or a modern Linux distribution

Developer install (from source): see [Installing from source](#installing-from-source).

## Installing the binary

Download the latest release for your operating system from the
[GitHub Releases page](https://github.com/PabloViniegra/drive-uploader/releases/latest).
Each release attaches two binaries plus a `SHA256SUMS` checksum file:

| Asset | Platform |
|---|---|
| `drive-uploader-vX.Y.Z-linux-amd64` | Linux (x86_64) |
| `drive-uploader-vX.Y.Z-windows-amd64.exe` | Windows (x86_64) |
| `SHA256SUMS` | both |

### Verify the download

```bash
# Linux
sha256sum -c SHA256SUMS

# Windows (PowerShell)
Get-FileHash .\drive-uploader-vX.Y.Z-windows-amd64.exe -Algorithm SHA256
```

Compare the printed digest against the one in `SHA256SUMS` for your
asset. Abort if they do not match.

### Run it

**Windows.** Double-click the `.exe`. Windows SmartScreen may show a
"Windows protected your PC" warning because the binary is not
code-signed — click **More info**, then **Run anyway**. This warning
is expected for v1; see [Out of scope](#out-of-scope) below.

**Linux.** From a terminal:

```bash
chmod +x drive-uploader-vX.Y.Z-linux-amd64
./drive-uploader-vX.Y.Z-linux-amd64
```

### First-run setup

The first time you run the binary it detects an empty config directory
and walks you through an interactive wizard that asks for:

1. The **watch folder** path (must exist; the wizard retries on bad input)
2. The **Drive folder ID** (non-empty string)
3. The **Google credentials file** path (must exist)

Settings are persisted to a `.env` file in a per-user config directory:

| OS | Config directory |
|---|---|
| Windows | `%APPDATA%\DriveUploader\` |
| Linux | `$XDG_CONFIG_HOME/drive-uploader/` (falls back to `~/.config/drive-uploader/`) |

The same directory holds `token.json` (OAuth token, managed by the
auth library) and `drive_uploader.db` (SQLite queue).

Subsequent runs skip the wizard and start the service directly. If
stdin is not a terminal (e.g. you launched the binary from a
shortcut or a script), the wizard refuses with a friendly error
explaining how to create `.env` by hand — set the three required
variables (`WATCH_FOLDER`, `DRIVE_FOLDER_ID`, `GOOGLE_CREDENTIALS`)
and run the binary again.

The service runs in the foreground; logs print to the console. Stop
with `Ctrl+C`. SIGINT and SIGTERM are handled gracefully.

A best-effort check for newer releases prints a one-liner on startup
when a newer tag exists. It never blocks startup and never fails
loudly.

### Updating

Re-download the newer binary from the Releases page and replace the
old file. There is no auto-update in v1.

## Installing from source

For development or to run the service without a pre-built binary:

```bash
git clone <your-fork-url> drive-uploader
cd drive-uploader
make install
```

`make install` runs `uv sync`, which creates the virtual environment
and installs runtime and development dependencies. You will need
Python 3.11 or newer and [`uv`](https://github.com/astral-sh/uv)
on your machine.

## Configuration

All settings come from environment variables. Copy `.env.example` to
`.env` and edit the values, or use the first-run wizard described
above.

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
| `DATABASE` | no | `<config-dir>/drive_uploader.db` | Path to the SQLite queue file. |
| `GOOGLE_TOKEN_PATH` | no | `<config-dir>/token.json` | Path to the OAuth token file. |
| `RETRY_ATTEMPTS` | no | `3` | Maximum retry attempts per job before marking it `FAILED`. |
| `DELETE_AFTER_UPLOAD` | no | `false` | Delete the local file after a successful upload. |
| `SHUTDOWN_GRACE_PERIOD` | no | `5.0` | Seconds the dispatcher waits for in-flight jobs on shutdown. |

When running from source, defaults resolve to `./drive_uploader.db`
and `./token.json` relative to the current working directory.
When running from the binary, defaults resolve to the per-user
config directory.

## Out of scope

The following are deferred from the v1 binary distribution:

- **Code signing.** Windows SmartScreen will warn on first launch.
  See the [Run it](#run-it) section for the workaround.
- **Package-manager distribution** (winget, scoop, apt). v1 ships
  via GitHub Releases only.
- **Auto-update.** Re-download from the Releases page to upgrade.
- **GUI / system tray icon / auto-start on login.** The binary is a
  foreground terminal process started manually.

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