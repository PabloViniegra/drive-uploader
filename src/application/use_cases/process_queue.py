import logging
from threading import Event

from application.use_cases.upload_file import UploadFile
from domain.ports.queue_repository import QueueRepositoryPort
from domain.ports.worker_pool import WorkerPoolPort

logger = logging.getLogger(__name__)


class ProcessQueue:
    """Dispatcher loop: claims WAITING jobs and hands them to the worker pool."""

    def __init__(
        self,
        repository: QueueRepositoryPort,
        pool: WorkerPoolPort,
        upload_file: UploadFile,
        workers: int,
        poll_interval: float = 1.0,
    ) -> None:
        self._repository = repository
        self._pool = pool
        self._upload_file = upload_file
        self._workers = workers
        self._poll_interval = poll_interval
        self._stop_event = Event()

    def run(self) -> None:
        while not self._stop_event.is_set():
            jobs = self._repository.claim(self._workers)
            if not jobs:
                self._stop_event.wait(self._poll_interval)
                continue
            logger.info("claimed %d job(s)", len(jobs))
            for job in jobs:
                self._pool.submit(self._upload_file.execute, job)

    def stop(self) -> None:
        logger.info("dispatcher stop requested")
        self._stop_event.set()
