"""Tests for GetAppCommand.run()'s validation-skip logic — an app already
registered in apps.txt is never re-validated (or rolled back), regardless
of whether this run happened to (re-)clone it."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pilot.commands.get_app import GetAppCommand
from tests.test_commands import make_bench


def make_command(tmp_path: Path, name: str = "myapp") -> GetAppCommand:
    bench = make_bench(tmp_path)
    bench.create_directories()
    cmd = GetAppCommand(bench, f"https://github.com/frappe/{name}")
    # Skip real cloning/installing/building — only the validate-skip decision
    # in run() is under test here.
    cmd._clone = lambda: None
    cmd._normalize_folder = lambda: None
    cmd._install = lambda: None
    cmd._register = lambda: None
    cmd._build = lambda: None
    return cmd


def test_validate_runs_when_app_not_registered(tmp_path: Path) -> None:
    cmd = make_command(tmp_path)

    with patch.object(GetAppCommand, "_validate") as mock_validate:
        cmd.run()

    mock_validate.assert_called_once()


def test_validate_skipped_when_app_already_registered(tmp_path: Path) -> None:
    cmd = make_command(tmp_path)
    (cmd.bench.sites_path / "apps.txt").write_text("frappe\nmyapp\n")

    with patch.object(GetAppCommand, "_validate") as mock_validate:
        cmd.run()

    mock_validate.assert_not_called()


def test_validate_still_skipped_via_skip_validations_flag(tmp_path: Path) -> None:
    bench = make_bench(tmp_path)
    bench.create_directories()
    cmd = GetAppCommand(bench, "https://github.com/frappe/myapp", skip_validations=True)
    cmd._clone = lambda: None
    cmd._normalize_folder = lambda: None
    cmd._install = lambda: None
    cmd._register = lambda: None
    cmd._build = lambda: None

    with patch.object(GetAppCommand, "_validate") as mock_validate:
        cmd.run()

    mock_validate.assert_not_called()


def test_is_registered_reflects_apps_txt_contents(tmp_path: Path) -> None:
    cmd = make_command(tmp_path, name="erpnext")
    assert cmd._is_registered() is False

    (cmd.bench.sites_path / "apps.txt").write_text("frappe\nerpnext\n")
    assert cmd._is_registered() is True
