"""Tests for the minimal .env file parser."""

from __future__ import annotations

from pathlib import Path


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    from src.shared.env import parse_env_file

    assert parse_env_file(tmp_path / "missing.env") == {}


def test_basic_key_value(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar", "BAZ": "qux"}


def test_comments_and_blank_lines_ignored(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text(
        "# this is a comment\n"
        "\n"
        "FOO=bar\n"
        "   \n"
        "# another comment\n"
        "BAZ=qux\n",
        encoding="utf-8",
    )

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar", "BAZ": "qux"}


def test_single_quoted_value(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("FOO='bar baz'\n", encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar baz"}


def test_double_quoted_value(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text('FOO="bar baz"\n', encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar baz"}


def test_export_prefix_tolerated(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("export FOO=bar\n", encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar"}


def test_partial_file_returns_what_was_parsed(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("FOO=bar\n", encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar"}


def test_malformed_lines_ignored(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("FOO=bar\nTHIS_IS_NOT_VALID\nBAZ=qux\n", encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"FOO": "bar", "BAZ": "qux"}


def test_value_with_equals_sign(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("URL=https://example.com?a=1&b=2\n", encoding="utf-8")

    from src.shared.env import parse_env_file

    assert parse_env_file(p) == {"URL": "https://example.com?a=1&b=2"}