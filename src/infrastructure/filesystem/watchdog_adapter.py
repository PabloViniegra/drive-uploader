import logging
import time
from pathlib import Path
from threading import Thread

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from application.use_cases.enqueue_file import EnqueueFile

logger = logging.getLogger(__name__)

_STABLE_CHECK_INTERVAL = 1.0


class _StableFileHandler(FileSystemEventHandler):
    """Waits for a file's size to stop changing before enqueueing it.

    Guards against picking up a file that's still being written/copied.
    """

    def __init__(self, enqueue_file: EnqueueFile) -> None:
        self._enqueue_file = enqueue_file

    def on_created(self, event):
        if not event.is_directory:
            self._handle(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._handle(Path(event.dest_path))

    def _handle(self, path: Path) -> None:
        logger.info("detected new file: %s", path)
        Thread(target=self._wait_and_enqueue, args=(path,), daemon=True).start()

    def _wait_and_enqueue(self, path: Path) -> None:
        last_size = -1
        while path.exists():
            size = path.stat().st_size
            if size == last_size:
                break
            last_size = size
            time.sleep(_STABLE_CHECK_INTERVAL)
        if path.exists():
            logger.info("file stable, enqueueing: %s", path)
            self._enqueue_file.execute(path)
        else:
            logger.warning("file disappeared before stabilizing: %s", path)


class FolderWatcher:
    """Watches a folder and enqueues new files for upload."""

    def __init__(self, watch_folder: Path, enqueue_file: EnqueueFile) -> None:
        self._watch_folder = watch_folder
        self._enqueue_file = enqueue_file
        self._observer = Observer()

    def scan_existing(self) -> None:
        found = [path for path in self._watch_folder.iterdir() if path.is_file()]
        logger.info("startup scan: found %d existing file(s) in %s", len(found), self._watch_folder)
        for path in found:
            self._enqueue_file.execute(path)

    def start(self) -> None:
        handler = _StableFileHandler(self._enqueue_file)
        self._observer.schedule(handler, str(self._watch_folder), recursive=False)
        self._observer.start()
        logger.info("watcher started on %s", self._watch_folder)

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        logger.info("watcher stopped")
