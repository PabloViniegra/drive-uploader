import logging
import time

from src.domain.entities.upload_job import UploadJob
from src.domain.ports.drive_uploader import DriveUploaderPort
from src.domain.ports.queue_repository import QueueRepositoryPort
from src.domain.value_objects.upload_status import UploadStatus
from src.shared.config import Settings

logger = logging.getLogger(__name__)


class UploadFile:
    """Uploads a single job; retries with backoff, marks FAILED after max attempts."""

    def __init__(
        self,
        repository: QueueRepositoryPort,
        uploader: DriveUploaderPort,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._uploader = uploader
        self._settings = settings

    def execute(self, job: UploadJob) -> None:
        logger.info("uploading %s (attempt %d)", job.file_path, job.retries + 1)
        try:
            remote_id = self._uploader.upload(job)
        except Exception as exc:
            self._handle_failure(job, exc)
            return

        job.status = UploadStatus.DONE
        self._repository.update(job)
        logger.info("uploaded %s -> drive id %s", job.file_path, remote_id)
        if self._settings.delete_after_upload:
            job.file_path.unlink(missing_ok=True)
            logger.info("deleted local file after upload: %s", job.file_path)

    def _handle_failure(self, job: UploadJob, exc: Exception) -> None:
        job.retries += 1
        job.error = str(exc)
        if job.retries < self._settings.retry_attempts:
            backoff = 2**job.retries
            logger.warning(
                "upload failed for %s (attempt %d/%d): %s -- retrying in %ds",
                job.file_path,
                job.retries,
                self._settings.retry_attempts,
                exc,
                backoff,
            )
            time.sleep(backoff)
            job.status = UploadStatus.WAITING
        else:
            logger.error(
                "upload permanently failed for %s after %d attempts: %s",
                job.file_path,
                job.retries,
                exc,
            )
            job.status = UploadStatus.FAILED
        self._repository.update(job)
