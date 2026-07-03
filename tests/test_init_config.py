"""Tests for the first-run interactive wizard."""

from __future__ import annotations

import io
from pathlib import Path

import pytest


def test_happy_path_writes_env_file(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    input_stream = io.StringIO(f"{watch}\nfolder-xyz\n{creds}\n\n")
    output_stream = io.StringIO()
    input_stream.isatty = lambda: True  # type: ignore[method-assign]

    from src.bootstrap.init_config import run_wizard

    run_wizard(input_stream, output_stream, config_dir)

    env_file = config_dir / ".env"
    assert env_file.exists()
    contents = env_file.read_text(encoding="utf-8")
    assert f"WATCH_FOLDER={watch}" in contents
    assert "DRIVE_FOLDER_ID=folder-xyz" in contents
    assert f"GOOGLE_CREDENTIALS={creds}" in contents
    assert "DELETE_AFTER_UPLOAD" not in contents


def test_non_tty_raises_wizard_error(tmp_path: Path) -> None:
    input_stream = io.StringIO("")
    output_stream = io.StringIO()
    # StringIO.isatty() is False by default — wizard should refuse

    from src.bootstrap.init_config import WizardError, run_wizard

    with __import__("pytest").raises(WizardError):
        run_wizard(input_stream, output_stream, tmp_path)


def test_invalid_watch_folder_path_retries(tmp_path: Path) -> None:
    good_watch = tmp_path / "watch"
    good_watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    input_stream = io.StringIO(
        f"/this/path/does/not/exist\n{good_watch}\nfolder-xyz\n{creds}\n\n"
    )
    output_stream = io.StringIO()
    input_stream.isatty = lambda: True  # type: ignore[method-assign]

    from src.bootstrap.init_config import run_wizard

    run_wizard(input_stream, output_stream, config_dir)

    env_file = config_dir / ".env"
    assert f"WATCH_FOLDER={good_watch}" in env_file.read_text(encoding="utf-8")


def test_invalid_credentials_path_retries(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    good_creds = tmp_path / "creds.json"
    good_creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    input_stream = io.StringIO(
        f"{watch}\nfolder-xyz\n/nope/missing.json\n{good_creds}\n\n"
    )
    output_stream = io.StringIO()
    input_stream.isatty = lambda: True  # type: ignore[method-assign]

    from src.bootstrap.init_config import run_wizard

    run_wizard(input_stream, output_stream, config_dir)

    env_file = config_dir / ".env"
    assert f"GOOGLE_CREDENTIALS={good_creds}" in env_file.read_text(encoding="utf-8")


def test_empty_drive_folder_id_retries(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    input_stream = io.StringIO(f"{watch}\n\nfolder-xyz\n{creds}\n\n")
    output_stream = io.StringIO()
    input_stream.isatty = lambda: True  # type: ignore[method-assign]

    from src.bootstrap.init_config import run_wizard

    run_wizard(input_stream, output_stream, config_dir)

    env_file = config_dir / ".env"
    assert "DRIVE_FOLDER_ID=folder-xyz" in env_file.read_text(encoding="utf-8")


def test_wizard_creates_config_dir_if_missing(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "fresh-config"
    assert not config_dir.exists()

    input_stream = io.StringIO(f"{watch}\nfolder-xyz\n{creds}\n\n")
    output_stream = io.StringIO()
    input_stream.isatty = lambda: True  # type: ignore[method-assign]

    from src.bootstrap.init_config import run_wizard

    run_wizard(input_stream, output_stream, config_dir)

    assert config_dir.exists()
    assert (config_dir / ".env").exists()


def _make_streams(payload: str) -> tuple[io.StringIO, io.StringIO]:
    stdin = io.StringIO(payload)
    stdout = io.StringIO()
    stdin.isatty = lambda: True  # type: ignore[method-assign]
    return stdin, stdout


def test_prepare_settings_first_run_runs_wizard(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"
    stdin, stdout = _make_streams(f"{watch}\nfolder-xyz\n{creds}\n\n")

    from src.bootstrap.init_config import prepare_settings

    settings = prepare_settings(stdin, stdout, config_dir)

    assert (config_dir / ".env").exists()
    assert settings.watch_folder == watch
    assert settings.drive_folder_id == "folder-xyz"
    assert settings.credentials_path == creds
    assert settings.delete_after_upload is False


def test_prepare_settings_skips_wizard_when_env_present(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / ".env").write_text(
        "WATCH_FOLDER=/pre/watch\n"
        "DRIVE_FOLDER_ID=pre-folder\n"
        "GOOGLE_CREDENTIALS=/pre/creds.json\n",
        encoding="utf-8",
    )
    stdin, stdout = _make_streams("")

    from src.bootstrap.init_config import prepare_settings

    settings = prepare_settings(stdin, stdout, config_dir)

    assert settings.watch_folder == Path("/pre/watch")
    assert settings.drive_folder_id == "pre-folder"
    assert stdout.getvalue() == ""


def test_prepare_settings_propagates_wizard_error_on_non_tty(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    stdin = io.StringIO("")
    stdout = io.StringIO()

    from src.bootstrap.init_config import WizardError, prepare_settings

    with pytest.raises(WizardError):
        prepare_settings(stdin, stdout, config_dir)


def test_prepare_settings_creates_missing_config_dir(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "fresh"
    assert not config_dir.exists()
    stdin, stdout = _make_streams(f"{watch}\nfolder-xyz\n{creds}\n\n")

    from src.bootstrap.init_config import prepare_settings

    prepare_settings(stdin, stdout, config_dir)

    assert config_dir.is_dir()


def test_optional_delete_after_upload_yes_writes_env_var(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    stdin, stdout = _make_streams(f"{watch}\nfolder-xyz\n{creds}\nyes\n")

    from src.bootstrap.init_config import prepare_settings

    settings = prepare_settings(stdin, stdout, config_dir)

    contents = (config_dir / ".env").read_text(encoding="utf-8")
    assert "DELETE_AFTER_UPLOAD=true" in contents
    assert settings.delete_after_upload is True


def test_optional_delete_after_upload_explicit_no_skips_env_var(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    stdin, stdout = _make_streams(f"{watch}\nfolder-xyz\n{creds}\nn\n")

    from src.bootstrap.init_config import prepare_settings

    settings = prepare_settings(stdin, stdout, config_dir)

    contents = (config_dir / ".env").read_text(encoding="utf-8")
    assert "DELETE_AFTER_UPLOAD" not in contents
    assert settings.delete_after_upload is False


def test_optional_delete_after_upload_retries_on_invalid_input(tmp_path: Path) -> None:
    watch = tmp_path / "watch"
    watch.mkdir()
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    config_dir = tmp_path / "config"

    stdin, stdout = _make_streams(f"{watch}\nfolder-xyz\n{creds}\nmaybe\ny\n")

    from src.bootstrap.init_config import prepare_settings

    settings = prepare_settings(stdin, stdout, config_dir)

    contents = (config_dir / ".env").read_text(encoding="utf-8")
    assert "DELETE_AFTER_UPLOAD=true" in contents
    assert "Please answer y or n." in stdout.getvalue()
    assert settings.delete_after_upload is True