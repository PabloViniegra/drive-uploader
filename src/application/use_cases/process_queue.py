import logging
from threading import Event

from src.domain.ports.queue_repository import QueueRepositoryPort
from src.domain.ports.upload_dispatcher import UploadDispatcherPort

logger = logging.getLogger(__name__)


class ProcessQueue:
    """Dispatcher loop: claims WAITING jobs and hands them to the upload dispatcher."""

    def __init__(
        self,
        repository: QueueRepositoryPort,
        dispatcher: UploadDispatcherPort,
        workers: int,
        poll_interval: float = 1.0,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher
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
                self._dispatcher.process(job)

    def stop(self) -> None:
        logger.info("dispatcher stop requested")
        self._stop_event.set()