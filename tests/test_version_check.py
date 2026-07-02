"""Tests for the best-effort new-version one-liner."""

from __future__ import annotations

import socket
from urllib.error import URLError


def test_newer_version_returns_one_liner() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return "v9.9.9"

    assert (
        check_for_new_version("0.1.0", fetcher=fetcher)
        == "new version available: 9.9.9 "
        "(re-download from https://github.com/PabloViniegra/drive-uploader/releases/latest)"
    )


def test_same_version_returns_none() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return "0.1.0"

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_older_version_returns_none() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return "0.0.5"

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_fetcher_returns_none_silently() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return None

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_fetcher_raises_silently() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        raise URLError("network down")

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_fetcher_raises_socket_timeout_silently() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        raise socket.timeout()

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_fetcher_returns_non_numeric_tag_returns_none() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return "not-a-version"

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_fetcher_returns_empty_string_returns_none() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return ""

    assert check_for_new_version("0.1.0", fetcher=fetcher) is None


def test_malformed_current_version_does_not_crash() -> None:
    from src.bootstrap.version_check import check_for_new_version

    def fetcher() -> str | None:
        return "9.9.9"

    assert check_for_new_version("garbage", fetcher=fetcher) is None


def test_announce_prints_one_liner(capsys) -> None:
    from src.bootstrap.version_check import announce_new_version_if_any

    def fetcher() -> str | None:
        return "v9.9.9"

    announce_new_version_if_any("0.1.0", fetcher=fetcher)

    captured = capsys.readouterr()
    assert "new version available: 9.9.9" in captured.out


def test_announce_silent_when_no_new_version(capsys) -> None:
    from src.bootstrap.version_check import announce_new_version_if_any

    def fetcher() -> str | None:
        return None

    announce_new_version_if_any("0.1.0", fetcher=fetcher)

    captured = capsys.readouterr()
    assert captured.out == ""


def test_is_newer_compares_semver_correctly() -> None:
    from src.bootstrap.version_check import is_newer

    assert is_newer("1.2.3", "1.2.2") is True
    assert is_newer("1.2.2", "1.2.3") is False
    assert is_newer("1.2.3", "1.2.3") is False
    assert is_newer("1.10.0", "1.2.0") is True
    assert is_newer("2.0.0", "1.9.9") is True
    assert is_newer("v1.2.3", "v1.2.2") is True