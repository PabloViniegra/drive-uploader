from typing import Protocol

from src.domain.entities.upload_job import UploadJob


class UploadDispatcherPort(Protocol):
    def process(self, job: UploadJob) -> None:
        """Hand `job` off to the worker pool for execution."""
        ...