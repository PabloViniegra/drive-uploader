from pathlib import Path

from src.application.use_cases.upload_file import UploadFile
from src.domain.entities.upload_job import UploadJob
from src.domain.value_objects.upload_status import UploadStatus
from src.shared.config import Settings

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
        shutdown_grace_period=5.0,
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


def test_transient_failure_then_recovers_to_done(tmp_path, monkeypatch):
    monkeypatch.setattr("src.application.use_cases.upload_file.time.sleep", lambda _: None)
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)
    upload_file = UploadFile(repo, FakeUploader(fail_times=1), _settings(retry_attempts=3))

    upload_file.execute(job)
    assert repo.jobs[job.id].status == UploadStatus.WAITING
    assert repo.jobs[job.id].error is not None

    upload_file.execute(job)
    assert repo.jobs[job.id].status == UploadStatus.DONE


def test_failed_upload_does_not_delete_local_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.application.use_cases.upload_file.time.sleep", lambda _: None)
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)

    UploadFile(repo, FakeUploader(fail_times=99), _settings(delete_after_upload=True)).execute(job)

    assert file_path.exists()


def test_backoff_grows_exponentially_with_retries(tmp_path, monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(
        "src.application.use_cases.upload_file.time.sleep", lambda secs: slept.append(secs)
    )
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)
    upload_file = UploadFile(repo, FakeUploader(fail_times=99), _settings(retry_attempts=4))

    upload_file.execute(job)
    upload_file.execute(job)
    upload_file.execute(job)

    assert slept == [2, 4, 8]


def test_permanent_failure_records_last_error(tmp_path, monkeypatch):
    monkeypatch.setattr("src.application.use_cases.upload_file.time.sleep", lambda _: None)
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    job = UploadJob(file_path=file_path, file_size=5, status=UploadStatus.UPLOADING)
    repo = InMemoryQueueRepository()
    repo.add(job)

    UploadFile(repo, FakeUploader(fail_times=99), _settings(retry_attempts=1)).execute(job)

    stored = repo.jobs[job.id]
    assert stored.status == UploadStatus.FAILED
    assert "simulated failure" in stored.error
