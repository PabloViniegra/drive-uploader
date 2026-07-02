from src.application.use_cases.enqueue_file import EnqueueFile
from src.domain.value_objects.upload_status import UploadStatus

from conftest import InMemoryQueueRepository


def test_enqueue_creates_waiting_job(tmp_path):
    file_path = tmp_path / "a.txt"
    file_path.write_text("data")
    repo = InMemoryQueueRepository()

    job = EnqueueFile(repo).execute(file_path)

    assert job is not None
    assert job.status == UploadStatus.WAITING
    assert repo.jobs[job.id].file_path == file_path


def test_enqueue_skips_duplicate_active_job(tmp_path):
    file_path = tmp_path / "a.txt"
    file_path.write_text("data")
    repo = InMemoryQueueRepository()
    enqueue = EnqueueFile(repo)
    enqueue.execute(file_path)

    result = enqueue.execute(file_path)

    assert result is None
    assert len(repo.jobs) == 1
