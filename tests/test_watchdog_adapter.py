from pathlib import Path

from src.infrastructure.filesystem.watchdog_adapter import FolderWatcher, _StableFileHandler

from conftest import RecordingOnFileDetected


def test_stable_file_is_enqueued(tmp_path, monkeypatch):
    monkeypatch.setattr("src.infrastructure.filesystem.watchdog_adapter.time.sleep", lambda _: None)
    file_path = tmp_path / "done.txt"
    file_path.write_text("payload")
    sink = RecordingOnFileDetected()

    _StableFileHandler(sink)._wait_and_enqueue(file_path)

    assert sink.paths == [file_path]


def test_waits_until_size_stops_growing(tmp_path, monkeypatch):
    file_path = tmp_path / "growing.txt"
    file_path.write_text("ab")
    grew = {"done": False}

    def grow_once(_):
        if not grew["done"]:
            file_path.write_text("abcdef")
            grew["done"] = True

    monkeypatch.setattr("src.infrastructure.filesystem.watchdog_adapter.time.sleep", grow_once)
    sink = RecordingOnFileDetected()

    _StableFileHandler(sink)._wait_and_enqueue(file_path)

    assert sink.paths == [file_path]
    assert grew["done"] is True


def test_file_that_disappears_is_not_enqueued(tmp_path, monkeypatch):
    file_path = tmp_path / "vanishing.txt"
    file_path.write_text("partial")

    monkeypatch.setattr(
        "src.infrastructure.filesystem.watchdog_adapter.time.sleep",
        lambda _: file_path.unlink(),
    )
    sink = RecordingOnFileDetected()

    _StableFileHandler(sink)._wait_and_enqueue(file_path)

    assert sink.paths == []


def test_scan_existing_enqueues_files_but_not_directories(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    (tmp_path / "subdir").mkdir()
    sink = RecordingOnFileDetected()

    FolderWatcher(tmp_path, sink).scan_existing()

    assert {Path(p).name for p in sink.paths} == {"a.txt", "b.txt"}
