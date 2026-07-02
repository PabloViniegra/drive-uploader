from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.shared.env import parse_env_file
from src.shared.paths import ConfigDirError, config_dir


@dataclass(frozen=True)
class Settings:
    watch_folder: Path
    drive_folder_id: str
    credentials_path: Path
    token_path: Path
    workers: int
    database: Path
    retry_attempts: int
    delete_after_upload: bool
    shutdown_grace_period: float


def _resolve_defaults() -> tuple[Path, Path]:
    try:
        cfg = config_dir()
    except ConfigDirError:
        return Path("./drive_uploader.db"), Path("./token.json")
    return cfg / "drive_uploader.db", cfg / "token.json"


def load_settings(env_file: Path | None = None) -> Settings:
    if env_file is None:
        try:
            env_file = config_dir() / ".env"
        except ConfigDirError:
            env_file = None

    file_values = parse_env_file(env_file) if env_file is not None else {}

    def get(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, file_values.get(key, default))

    default_db, default_token = _resolve_defaults()

    watch_folder = get("WATCH_FOLDER")
    drive_folder_id = get("DRIVE_FOLDER_ID")
    credentials_path = get("GOOGLE_CREDENTIALS")
    if not watch_folder or not drive_folder_id or not credentials_path:
        raise ValueError(
            "WATCH_FOLDER, DRIVE_FOLDER_ID and GOOGLE_CREDENTIALS are required"
        )
    return Settings(
        watch_folder=Path(watch_folder),
        drive_folder_id=drive_folder_id,
        credentials_path=Path(credentials_path),
        token_path=Path(get("GOOGLE_TOKEN_PATH") or str(default_token)),
        workers=int(get("WORKERS", "4")),
        database=Path(get("DATABASE") or str(default_db)),
        retry_attempts=int(get("RETRY_ATTEMPTS", "3")),
        delete_after_upload=get("DELETE_AFTER_UPLOAD", "false").lower() == "true",
        shutdown_grace_period=float(get("SHUTDOWN_GRACE_PERIOD", "5.0")),
    )