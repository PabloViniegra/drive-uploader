from pathlib import Path

from domain.entities.upload_job import UploadJob
from domain.value_objects.upload_status import UploadStatus


class InMemoryQueueRepository:
    def __init__(self) -> None:
        self.jobs: dict = {}

    def add(self, job: UploadJob) -> None:
        self.jobs[job.id] = job

    def claim(self, limit: int) -> list[UploadJob]:
        waiting = [j for j in self.jobs.values() if j.status == UploadStatus.WAITING]
        claimed = waiting[:limit]
        for job in claimed:
            job.status = UploadStatus.UPLOADING
        return claimed

    def update(self, job: UploadJob) -> None:
        self.jobs[job.id] = job

    def exists_active(self, file_path: Path) -> bool:
        active = {UploadStatus.WAITING, UploadStatus.UPLOADING, UploadStatus.DONE}
        return any(
            j.file_path == file_path and j.status in active for j in self.jobs.values()
        )

    def reset_in_progress(self) -> None:
        for job in self.jobs.values():
            if job.status == UploadStatus.UPLOADING:
                job.status = UploadStatus.WAITING


class FakeUploader:
    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls = 0
        self.uploaded: list[UploadJob] = []

    def upload(self, job: UploadJob) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("simulated failure")
        self.uploaded.append(job)
        return "fake-remote-id"
