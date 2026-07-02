import logging
import signal
from threading import Thread

from application.use_cases.enqueue_file import EnqueueFile
from application.use_cases.process_queue import ProcessQueue
from application.use_cases.upload_file import UploadFile
from infrastructure.drive.google_drive_adapter import GoogleDriveAdapter
from infrastructure.filesystem.watchdog_adapter import FolderWatcher
from infrastructure.persistence.sqlite_repository import SqliteQueueRepository
from infrastructure.threading.worker_pool import WorkerPool
from shared.config import Settings

logger = logging.getLogger(__name__)


class DependencyContainer:
    """Wires adapters to use cases and owns the service lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = SqliteQueueRepository(settings.database)
        self._uploader = GoogleDriveAdapter(
            str(settings.credentials_path), str(settings.token_path), settings.drive_folder_id
        )
        self._pool = WorkerPool(settings.workers)
        self._enqueue_file = EnqueueFile(self._repository)
        self._upload_file = UploadFile(self._repository, self._uploader, settings)
        self._process_queue = ProcessQueue(
            self._repository, self._pool, self._upload_file, settings.workers
        )
        self._watcher = FolderWatcher(settings.watch_folder, self._enqueue_file)
        self._dispatcher_thread = Thread(target=self._process_queue.run, daemon=True)

    def start(self) -> None:
        self._settings.watch_folder.mkdir(parents=True, exist_ok=True)
        self._repository.reset_in_progress()
        self._watcher.scan_existing()
        self._watcher.start()
        self._dispatcher_thread.start()
        logger.info("drive-uploader started: watching %s", self._settings.watch_folder)

        signal.signal(signal.SIGINT, lambda *_: self.stop())
        signal.signal(signal.SIGTERM, lambda *_: self.stop())
        self._dispatcher_thread.join()

    def stop(self) -> None:
        logger.info("drive-uploader shutting down")
        self._watcher.stop()
        self._process_queue.stop()
        self._pool.shutdown(wait=True)
