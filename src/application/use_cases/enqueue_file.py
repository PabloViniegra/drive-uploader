import logging
from pathlib import Path

from domain.entities.upload_job import UploadJob
from domain.ports.queue_repository import QueueRepositoryPort
from domain.value_objects.upload_status import UploadStatus

logger = logging.getLogger(__name__)


class EnqueueFile:
    def __init__(self, repository: QueueRepositoryPort) -> None:
        self._repository = repository

    def execute(self, file_path: Path) -> UploadJob | None:
        if self._repository.exists_active(file_path):
            logger.info("skip enqueue, already active: %s", file_path)
            return None
        job = UploadJob(
            file_path=file_path,
            file_size=file_path.stat().st_size,
            status=UploadStatus.WAITING,
        )
        self._repository.add(job)
        logger.info("enqueued %s (%d bytes)", file_path, job.file_size)
        return job
