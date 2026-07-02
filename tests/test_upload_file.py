from pathlib import Path

from application.use_cases.upload_file import UploadFile
from domain.entities.upload_job import UploadJob
from domain.value_objects.upload_status import UploadStatus
from shared.config import Settings

from conftest import FakeUploader, InMemoryQueueRepository


def _settings(**overrides) -> Settings:
    base = dict(
        watch_folder=Path("/tmp/watch"),
        drive_folder_id="folder-id",
        credentials_path=Path("/tmp/creds.json"),
        token_path=Path("/tmp/token.json"),
        workers=2,
        database=Path("/tmp/db.sqlite"),
        retry_attempts=3,
        delete_after_upload=False,
    )
    base.update(overrides)
    return Settings(**base)


def test_upload_success_marks_job_done(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)

    UploadFile(repo, FakeUploader(), _settings()).execute(job)

    assert repo.jobs[job.id].status == UploadStatus.DONE


def test_upload_failure_retries_then_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("application.use_cases.upload_file.time.sleep", lambda _: None)
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)
    uploader = FakeUploader(fail_times=99)
    upload_file = UploadFile(repo, uploader, _settings(retry_attempts=2))

    upload_file.execute(job)
    assert repo.jobs[job.id].status == UploadStatus.WAITING
    assert repo.jobs[job.id].retries == 1

    upload_file.execute(job)
    assert repo.jobs[job.id].status == UploadStatus.FAILED
    assert repo.jobs[job.id].retries == 2


def test_delete_after_upload_removes_file(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)

    UploadFile(repo, FakeUploader(), _settings(delete_after_upload=True)).execute(job)

    assert not file_path.exists()
