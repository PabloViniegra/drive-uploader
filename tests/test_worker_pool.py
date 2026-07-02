from pathlib import Path

from src.domain.entities.upload_job import UploadJob
from src.domain.value_objects.upload_status import UploadStatus
from src.infrastructure.threading.worker_pool import WorkerPool


def test_submitted_job_reaches_the_handler():
    handled: list[UploadJob] = []
    pool = WorkerPool(max_workers=2, job_handler=handled.append)
    job = UploadJob(file_path=Path("/tmp/x.txt"), file_size=1, status=UploadStatus.UPLOADING)

    pool.process(job)
    pool.shutdown(wait=True)

    assert handled == [job]


def test_processes_multiple_jobs_concurrently():
    handled: list[UploadJob] = []
    pool = WorkerPool(max_workers=4, job_handler=handled.append)
    jobs = [
        UploadJob(file_path=Path(f"/tmp/{i}.txt"), file_size=1, status=UploadStatus.UPLOADING)
        for i in range(10)
    ]

    for job in jobs:
        pool.process(job)
    pool.shutdown(wait=True)

    assert {j.id for j in handled} == {j.id for j in jobs}
