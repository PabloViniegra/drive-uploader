from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class WorkerPool:
    """Thin wrapper over ThreadPoolExecutor: the in-memory work queue."""

    def __init__(self, max_workers: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, fn: Callable[..., Any], *args: Any) -> None:
        self._executor.submit(fn, *args)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
