from __future__ import annotations

from pathlib import Path
from typing import Callable, TextIO

from src.shared.config import Settings, load_settings


class WizardError(RuntimeError):
    """Raised when the wizard cannot run (e.g. stdin is not a TTY)."""


def _prompt_until_valid(
    label: str,
    read_line: Callable[[], str],
    write: Callable[[str], None],
    is_valid: Callable[[str], bool],
    error_msg: str,
) -> str:
    while True:
        write(f"{label}: ")
        value = read_line().strip()
        if is_valid(value):
            return value
        write(f"  {error_msg}\n")


def run_wizard(
    input_stream: TextIO,
    output_stream: TextIO,
    config_dir_path: Path,
) -> None:
    if not input_stream.isatty():
        raise WizardError(
            "Interactive setup requires a terminal. "
            "Create the .env file manually in the config directory."
        )

    config_dir_path.mkdir(parents=True, exist_ok=True)

    def write(message: str) -> None:
        output_stream.write(message)
        output_stream.flush()

    def read_line() -> str:
        return input_stream.readline().rstrip("\n")

    write("First-run setup. Enter the required settings:\n")

    watch_folder = _prompt_until_valid(
        "Watch folder path",
        read_line,
        write,
        lambda v: bool(v) and Path(v).is_dir(),
        "Path does not exist or is not a folder. Try again.",
    )

    drive_folder_id = _prompt_until_valid(
        "Drive folder ID",
        read_line,
        write,
        lambda v: bool(v),
        "Drive folder ID cannot be empty. Try again.",
    )

    credentials_path = _prompt_until_valid(
        "Google credentials file path",
        read_line,
        write,
        lambda v: bool(v) and Path(v).is_file(),
        "Path does not exist or is not a file. Try again.",
    )

    env_content = (
        f"WATCH_FOLDER={watch_folder}\n"
        f"DRIVE_FOLDER_ID={drive_folder_id}\n"
        f"GOOGLE_CREDENTIALS={credentials_path}\n"
    )
    env_file = config_dir_path / ".env"
    env_file.write_text(env_content, encoding="utf-8")
    write(f"Wrote {env_file}\n")


def prepare_settings(
    stdin: TextIO,
    stdout: TextIO,
    config_dir_path: Path,
) -> Settings:
    config_dir_path.mkdir(parents=True, exist_ok=True)
    env_file = config_dir_path / ".env"
    if not env_file.exists():
        run_wizard(stdin, stdout, config_dir_path)
    return load_settings(env_file=env_file)