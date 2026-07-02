import time
from threading import Thread

from src.application.use_cases.process_queue import ProcessQueue
from src.domain.entities.upload_job import UploadJob
from src.domain.value_objects.upload_status import UploadStatus

from conftest import FakeDispatcher, InMemoryQueueRepository


def _run_in_background(process_queue: ProcessQueue) -> Thread:
    thread = Thread(target=process_queue.run, daemon=True)
    thread.start()
    return thread


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)


def _waiting_job(path: str) -> UploadJob:
    from pathlib import Path

    return UploadJob(file_path=Path(path), file_size=1, status=UploadStatus.WAITING)


def test_dispatches_every_claimed_job():
    repo = InMemoryQueueRepository()
    jobs = [_waiting_job(f"/tmp/f{i}.txt") for i in range(3)]
    for job in jobs:
        repo.add(job)
    dispatcher = FakeDispatcher()
    process_queue = ProcessQueue(repo, dispatcher, workers=2, poll_interval=0.01)

    thread = _run_in_background(process_queue)
    _wait_until(lambda: len(dispatcher.processed) == 3)
    process_queue.stop()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert {j.id for j in dispatcher.processed} == {j.id for j in jobs}


def test_stop_breaks_the_loop_even_when_idle():
    repo = InMemoryQueueRepository()
    dispatcher = FakeDispatcher()
    process_queue = ProcessQueue(repo, dispatcher, workers=4, poll_interval=0.01)

    thread = _run_in_background(process_queue)
    process_queue.stop()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert dispatcher.processed == []


def test_does_not_redispatch_already_claimed_jobs():
    repo = InMemoryQueueRepository()
    repo.add(_waiting_job("/tmp/only.txt"))
    dispatcher = FakeDispatcher()
    process_queue = ProcessQueue(repo, dispatcher, workers=4, poll_interval=0.01)

    thread = _run_in_background(process_queue)
    _wait_until(lambda: len(dispatcher.processed) == 1)
    time.sleep(0.05)
    process_queue.stop()
    thread.join(timeout=2)

    assert len(dispatcher.processed) == 1
