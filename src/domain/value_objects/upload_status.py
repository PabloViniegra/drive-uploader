from enum import Enum


class UploadStatus(Enum):
    WAITING = "WAITING"
    UPLOADING = "UPLOADING"
    DONE = "DONE"
    FAILED = "FAILED"