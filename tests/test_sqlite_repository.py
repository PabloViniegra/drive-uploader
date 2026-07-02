from pathlib import Path

from domain.entities.upload_job import UploadJob
from domain.value_objects.upload_status import UploadStatus
from infrastructure.persistence.sqlite_repository import SqliteQueueRepository


def _job(path: Path) -> UploadJob:
    return UploadJob(file_path=path, file_size=1, status=UploadStatus.WAITING)


def test_add_and_claim_round_trip(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    job = _job(tmp_path / "f.txt")
    repo.add(job)

    claimed = repo.claim(10)

    assert len(claimed) == 1
    assert claimed[0].id == job.id
    assert claimed[0].status == UploadStatus.UPLOADING


def test_claim_does_not_double_dispatch(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    repo.add(_job(tmp_path / "f.txt"))

    first = repo.claim(10)
    second = repo.claim(10)

    assert len(first) == 1
    assert second == []


def test_update_persists_status(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    job = _job(tmp_path / "f.txt")
    repo.add(job)
    job.status = UploadStatus.DONE
    repo.update(job)

    assert repo.exists_active(job.file_path) is True


def test_reset_in_progress_requeues_uploading_jobs(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    job = _job(tmp_path / "f.txt")
    repo.add(job)
    repo.claim(10)  # -> UPLOADING

    repo.reset_in_progress()
    claimable = repo.claim(10)

    assert len(claimable) == 1
    assert claimable[0].status == UploadStatus.UPLOADING


def test_exists_active_respects_status(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    path = tmp_path / "f.txt"
    job = _job(path)
    repo.add(job)

    assert repo.exists_active(path) is True

    job.status = UploadStatus.FAILED
    repo.update(job)

    assert repo.exists_active(path) is False
