from pathlib import Path

import pytest

from src.shared.config import load_settings

_REQUIRED = {
    "WATCH_FOLDER": "/data/watch",
    "DRIVE_FOLDER_ID": "folder-123",
    "GOOGLE_CREDENTIALS": "/secrets/creds.json",
}

_ENV_KEYS = (
    "WATCH_FOLDER",
    "DRIVE_FOLDER_ID",
    "GOOGLE_CREDENTIALS",
    "GOOGLE_TOKEN_PATH",
    "WORKERS",
    "DATABASE",
    "RETRY_ATTEMPTS",
    "DELETE_AFTER_UPLOAD",
    "SHUTDOWN_GRACE_PERIOD",
)


def _clear_env(monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _isolate_config_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))


@pytest.mark.parametrize("missing", ["WATCH_FOLDER", "DRIVE_FOLDER_ID", "GOOGLE_CREDENTIALS"])
def test_missing_required_var_raises(monkeypatch, missing):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        if key != missing:
            monkeypatch.setenv(key, value)

    with pytest.raises(ValueError):
        load_settings()


def test_required_vars_are_parsed(monkeypatch):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)

    settings = load_settings()

    assert settings.watch_folder == Path("/data/watch")
    assert settings.drive_folder_id == "folder-123"
    assert settings.credentials_path == Path("/secrets/creds.json")


def test_defaults_point_to_config_dir(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _isolate_config_dir(monkeypatch, tmp_path)
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)

    settings = load_settings()

    expected_dir = tmp_path / ".config" / "drive-uploader"
    assert settings.database == expected_dir / "drive_uploader.db"
    assert settings.token_path == expected_dir / "token.json"
    assert settings.workers == 4
    assert settings.retry_attempts == 3
    assert settings.delete_after_upload is False
    assert settings.shutdown_grace_period == 5.0


def test_optional_vars_coerced_to_types(monkeypatch):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("WORKERS", "8")
    monkeypatch.setenv("RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("SHUTDOWN_GRACE_PERIOD", "12.5")
    monkeypatch.setenv("DATABASE", "/var/db.sqlite")
    monkeypatch.setenv("GOOGLE_TOKEN_PATH", "/var/token.json")

    settings = load_settings()

    assert settings.workers == 8
    assert settings.retry_attempts == 5
    assert settings.shutdown_grace_period == 12.5
    assert settings.database == Path("/var/db.sqlite")
    assert settings.token_path == Path("/var/token.json")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("True", True), ("TRUE", True), ("false", False), ("", False), ("yes", False)],
)
def test_delete_after_upload_is_case_insensitive_bool(monkeypatch, raw, expected):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DELETE_AFTER_UPLOAD", raw)

    assert load_settings().delete_after_upload is expected


def test_env_file_value_used_when_env_var_unset(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE=/from/file.sqlite\n", encoding="utf-8")

    settings = load_settings(env_file=env_file)

    assert settings.database == Path("/from/file.sqlite")


def test_explicit_env_var_wins_over_env_file(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DATABASE", "/explicit/path.sqlite")
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE=/from/file.sqlite\n", encoding="utf-8")

    settings = load_settings(env_file=env_file)

    assert settings.database == Path("/explicit/path.sqlite")


def test_env_file_supplies_required_var(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    for key, value in _REQUIRED.items():
        if key != "WATCH_FOLDER":
            monkeypatch.setenv(key, value)
    env_file = tmp_path / ".env"
    env_file.write_text("WATCH_FOLDER=/from/file/watch\n", encoding="utf-8")

    settings = load_settings(env_file=env_file)

    assert settings.watch_folder == Path("/from/file/watch")
