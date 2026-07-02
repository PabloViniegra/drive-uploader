from pathlib import Path
from typing import Protocol

from src.domain.entities.upload_job import UploadJob


class OnFileDetectedPort(Protocol):
    def execute(self, file_path: Path) -> UploadJob | None:
        """Handle a newly-detected stable file."""
        ...