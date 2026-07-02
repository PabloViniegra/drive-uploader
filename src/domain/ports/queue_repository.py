from pathlib import Path
from typing import Protocol

from src.domain.entities.upload_job import UploadJob


class QueueRepositoryPort(Protocol):
    def add(self, job: UploadJob) -> None:
        ...

    def claim(self, limit: int) -> list[UploadJob]:
        """Atomically move up to `limit` WAITING jobs to UPLOADING and return them."""
        ...

    def update(self, job: UploadJob) -> None:
        ...

    def exists_active(self, file_path: Path) -> bool:
        """True if file_path has a job that is WAITING, UPLOADING or DONE."""
        ...

    def reset_in_progress(self) -> None:
        """Move any UPLOADING job back to WAITING (crash recovery)."""
        ...
