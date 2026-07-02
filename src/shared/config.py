import os
from dataclasses import dataclass
from pathlib import Path


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


def load_settings() -> Settings:
    watch_folder = os.environ.get("WATCH_FOLDER")
    drive_folder_id = os.environ.get("DRIVE_FOLDER_ID")
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS")
    if not watch_folder or not drive_folder_id or not credentials_path:
        raise ValueError(
            "WATCH_FOLDER, DRIVE_FOLDER_ID and GOOGLE_CREDENTIALS are required"
        )
    return Settings(
        watch_folder=Path(watch_folder),
        drive_folder_id=drive_folder_id,
        credentials_path=Path(credentials_path),
        token_path=Path(os.environ.get("GOOGLE_TOKEN_PATH", "./token.json")),
        workers=int(os.environ.get("WORKERS", "4")),
        database=Path(os.environ.get("DATABASE", "./drive_uploader.db")),
        retry_attempts=int(os.environ.get("RETRY_ATTEMPTS", "3")),
        delete_after_upload=os.environ.get("DELETE_AFTER_UPLOAD", "false").lower() == "true",
        shutdown_grace_period=float(os.environ.get("SHUTDOWN_GRACE_PERIOD", "5.0")),
    )