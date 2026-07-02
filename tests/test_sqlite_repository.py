from pathlib import Path

from src.domain.entities.upload_job import UploadJob
from src.domain.value_objects.upload_status import UploadStatus
from src.infrastructure.persistence.sqlite_repository import SqliteQueueRepository


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


def test_claim_respects_batch_limit(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    for i in range(3):
        repo.add(_job(tmp_path / f"f{i}.txt"))

    first = repo.claim(2)
    second = repo.claim(2)

    assert len(first) == 2
    assert len(second) == 1


def test_claim_is_fifo_by_created_at(tmp_path):
    from datetime import datetime, timezone

    repo = SqliteQueueRepository(tmp_path / "queue.db")
    newer = UploadJob(
        file_path=tmp_path / "new.txt",
        file_size=1,
        status=UploadStatus.WAITING,
        created_at=datetime(2020, 1, 2, tzinfo=timezone.utc),
    )
    older = UploadJob(
        file_path=tmp_path / "old.txt",
        file_size=1,
        status=UploadStatus.WAITING,
        created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    repo.add(newer)
    repo.add(older)

    first = repo.claim(1)
    second = repo.claim(1)

    assert first[0].file_path.name == "old.txt"
    assert second[0].file_path.name == "new.txt"


def test_retries_and_error_survive_round_trip(tmp_path):
    repo = SqliteQueueRepository(tmp_path / "queue.db")
    job = _job(tmp_path / "f.txt")
    job.retries = 2
    job.error = "boom"
    repo.add(job)

    claimed = repo.claim(10)[0]

    assert claimed.retries == 2
    assert claimed.error == "boom"


def test_unique_index_blocks_duplicate_active_path(tmp_path):
    import sqlite3

    import pytest

    repo = SqliteQueueRepository(tmp_path / "queue.db")
    path = tmp_path / "dup.txt"
    repo.add(_job(path))

    with pytest.raises(sqlite3.IntegrityError):
        repo.add(_job(path))
