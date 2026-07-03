from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Callable


CURRENT_VERSION = "0.1.2"

_RELEASES_URL = "https://api.github.com/repos/PabloViniegra/drive-uploader/releases/latest"
_DOWNLOAD_URL = "https://github.com/PabloViniegra/drive-uploader/releases/latest"
_TIMEOUT_SECONDS = 2.0


def _parse_version(v: str) -> tuple[int, ...] | None:
    parts = v.lstrip("v").split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def is_newer(latest: str, current: str) -> bool:
    latest_v = _parse_version(latest)
    current_v = _parse_version(current)
    if latest_v is None or current_v is None:
        return False
    return latest_v > current_v


def fetch_latest_version(
    url: str = _RELEASES_URL,
    timeout: float = _TIMEOUT_SECONDS,
) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (
        urllib.error.URLError,
        socket.timeout,
        TimeoutError,
        ValueError,
        OSError,
    ):
        return None
    tag = data.get("tag_name")
    if not isinstance(tag, str) or not tag:
        return None
    return tag.lstrip("v")


def build_one_liner(latest: str, url: str = _DOWNLOAD_URL) -> str:
    return f"new version available: {latest.lstrip('v')} (re-download from {url})"


def check_for_new_version(
    current_version: str,
    fetcher: Callable[[], str | None] = fetch_latest_version,
) -> str | None:
    try:
        latest = fetcher()
    except Exception:
        return None
    if latest is None:
        return None
    if not is_newer(latest, current_version):
        return None
    return build_one_liner(latest)


def announce_new_version_if_any(
    current_version: str,
    fetcher: Callable[[], str | None] = fetch_latest_version,
) -> None:
    one_liner = check_for_new_version(current_version, fetcher=fetcher)
    if one_liner:
        print(one_liner)