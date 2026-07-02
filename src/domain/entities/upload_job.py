import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from domain.value_objects.upload_status import UploadStatus


@dataclass
class UploadJob:
    file_path: Path
    file_size: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: UploadStatus = UploadStatus.NEW
    retries: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
