import logging
import threading
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from domain.entities.upload_job import UploadJob

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveAdapter:
    """Uploads files to a Drive folder using OAuth user credentials.

    # ponytail: one `service` instance per thread via threading.local —
    # googleapiclient's http objects aren't safe to share across threads.
    # ponytail: single lock around token load/refresh/write — token.json is
    # shared mutable state across threads, unlike the old per-thread-only
    # service-account read. Per-account locks if this becomes a bottleneck.
    """

    def __init__(self, client_secret_path: str, token_path: str, folder_id: str) -> None:
        self._client_secret_path = client_secret_path
        self._token_path = Path(token_path)
        self._folder_id = folder_id
        self._local = threading.local()
        self._auth_lock = threading.Lock()

    def upload(self, job: UploadJob) -> str:
        media = MediaFileUpload(str(job.file_path), resumable=True)
        metadata = {"name": job.file_path.name, "parents": [self._folder_id]}
        request = self._service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        )
        response = request.execute()
        return response["id"]

    @property
    def _service(self):
        if not hasattr(self._local, "service"):
            self._local.service = build("drive", "v3", credentials=self._credentials())
        return self._local.service

    def _credentials(self) -> Credentials:
        with self._auth_lock:
            creds = None
            if self._token_path.exists():
                creds = Credentials.from_authorized_user_file(str(self._token_path), _SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("OAuth token expired, refreshing")
                    creds.refresh(Request())
                else:
                    logger.info("no valid OAuth token, launching interactive consent flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self._client_secret_path, _SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                self._token_path.write_text(creds.to_json())
                logger.info("OAuth token saved to %s", self._token_path)
            return creds
