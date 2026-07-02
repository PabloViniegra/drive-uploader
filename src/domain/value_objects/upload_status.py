from enum import Enum

class UploadStatus(Enum):
    NEW = "NEW"
    WAITING = "WAITING"
    UPLOADING = "UPLOADING"
    DONE = "DONE"
    FAILED = "FAILED"