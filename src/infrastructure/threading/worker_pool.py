from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from src.domain.entities.upload_job import UploadJob


class WorkerPool:
    """ThreadPoolExecutor-backed implementation of UploadDispatcherPort."""

    def __init__(self, max_workers: int, job_handler: Callable[[UploadJob], None]) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._job_handler = job_handler

    def process(self, job: UploadJob) -> None:
        self._executor.submit(self._job_handler, job)

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)