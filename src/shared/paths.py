from __future__ import annotations

import os
from pathlib import Path


class ConfigDirError(RuntimeError):
    """Raised when the platform config directory cannot be resolved."""


def config_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "DriveUploader"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "drive-uploader"

    home = os.environ.get("HOME")
    if home:
        return Path(home) / ".config" / "drive-uploader"

    raise ConfigDirError(
        "Cannot resolve config directory: set APPDATA (Windows) "
        "or XDG_CONFIG_HOME / HOME (Linux)."
    )