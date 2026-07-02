from typing import Protocol

from domain.entities.upload_job import UploadJob


class DriveUploaderPort(Protocol):
    def upload(self, job: UploadJob) -> str:
        """Upload the job's file to Drive; return the remote file id."""
        ...
