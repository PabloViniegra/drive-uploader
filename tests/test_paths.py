"""Tests for the platform-aware config directory resolver."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_linux_with_xdg_config_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", "/should/not/be/used")

    from src.shared.paths import config_dir

    assert config_dir() == tmp_path / "drive-uploader"


def test_linux_with_home_only(monkeypatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", "/home/alice")

    from src.shared.paths import config_dir

    assert config_dir() == Path("/home/alice/.config/drive-uploader")


def test_linux_without_home_raises(monkeypatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    from src.shared.paths import ConfigDirError, config_dir

    with pytest.raises(ConfigDirError):
        config_dir()


def test_windows_with_appdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))

    from src.shared.paths import config_dir

    assert config_dir() == tmp_path / "DriveUploader"


def test_windows_without_appdata_raises(monkeypatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)

    from src.shared.paths import ConfigDirError, config_dir

    with pytest.raises(ConfigDirError):
        config_dir()