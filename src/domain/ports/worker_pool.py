from collections.abc import Callable
from typing import Any, Protocol


class WorkerPoolPort(Protocol):
    def submit(self, fn: Callable[..., Any], *args: Any) -> None:
        ...
