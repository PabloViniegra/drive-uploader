import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock

from src.domain.entities.upload_job import UploadJob
from src.domain.value_objects.upload_status import UploadStatus

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS upload_jobs (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    status TEXT NOT NULL,
    retries INTEGER NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_upload_jobs_active_path
ON upload_jobs(file_path)
WHERE status IN ('WAITING', 'UPLOADING', 'DONE');
CREATE INDEX IF NOT EXISTS ix_upload_jobs_status
ON upload_jobs(status, created_at);
"""


class SqliteQueueRepository:
    """SQLite-backed durable queue. One shared connection guarded by a lock.

    # ponytail: single global write lock; the network upload dominates over
    # DB I/O, so this never becomes the bottleneck. Upgrade: per-shard
    # connections if that stops being true.
    """

    def __init__(self, database_path: Path) -> None:
        self._lock = Lock()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(database_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA busy_timeout=5000")
            self._connection.executescript(_SCHEMA)
            self._connection.commit()

    def add(self, job: UploadJob) -> None:
        with self._lock:
            self._connection.execute(
                """INSERT INTO upload_jobs
                   (id, file_path, file_size, status, retries, error, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                self._to_row(job),
            )
            self._connection.commit()

    def update(self, job: UploadJob) -> None:
        with self._lock:
            self._connection.execute(
                """UPDATE upload_jobs
                   SET status = ?, retries = ?, error = ?
                   WHERE id = ?""",
                (job.status.value, job.retries, job.error, str(job.id)),
            )
            self._connection.commit()

    def claim(self, limit: int) -> list[UploadJob]:
        with self._lock:
            cursor = self._connection.execute(
                """SELECT id FROM upload_jobs
                   WHERE status = ?
                   ORDER BY created_at
                   LIMIT ?""",
                (UploadStatus.WAITING.value, limit),
            )
            ids = [row["id"] for row in cursor.fetchall()]
            if not ids:
                return []
            placeholders = ",".join("?" * len(ids))
            self._connection.execute(
                f"UPDATE upload_jobs SET status = ? WHERE id IN ({placeholders})",
                (UploadStatus.UPLOADING.value, *ids),
            )
            rows = self._connection.execute(
                f"SELECT * FROM upload_jobs WHERE id IN ({placeholders})", ids
            ).fetchall()
            self._connection.commit()
            return [self._to_job(row) for row in rows]

    def exists_active(self, file_path: Path) -> bool:
        with self._lock:
            cursor = self._connection.execute(
                """SELECT 1 FROM upload_jobs
                   WHERE file_path = ? AND status IN ('WAITING', 'UPLOADING', 'DONE')
                   LIMIT 1""",
                (str(file_path),),
            )
            return cursor.fetchone() is not None

    def reset_in_progress(self) -> None:
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE upload_jobs SET status = ? WHERE status = ?",
                (UploadStatus.WAITING.value, UploadStatus.UPLOADING.value),
            )
            self._connection.commit()
            if cursor.rowcount:
                logger.info(
                    "recovered %d job(s) stuck in UPLOADING from a prior crash", cursor.rowcount
                )

    @staticmethod
    def _to_row(job: UploadJob) -> tuple:
        return (
            str(job.id),
            str(job.file_path),
            job.file_size,
            job.status.value,
            job.retries,
            job.error,
            job.created_at.isoformat(),
        )

    @staticmethod
    def _to_job(row: sqlite3.Row) -> UploadJob:
        return UploadJob(
            id=uuid.UUID(row["id"]),
            file_path=Path(row["file_path"]),
            file_size=row["file_size"],
            status=UploadStatus(row["status"]),
            retries=row["retries"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
