from __future__ import annotations

import subprocess
from pathlib import Path

from pilot.plugins import git_ops


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "test"], check=True)
    (path / "plugin.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)


def test_clone_then_pull_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _init_repo(source)
    dest = tmp_path / "dest"

    clone_result = git_ops.clone(f"file://{source}", "main", dest)

    assert clone_result.returncode == 0
    assert (dest / "plugin.py").read_text() == "VALUE = 1\n"

    (source / "plugin.py").write_text("VALUE = 2\n")
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-q", "-m", "update"], check=True)

    pull_result = git_ops.pull(dest)

    assert pull_result.returncode == 0
    assert (dest / "plugin.py").read_text() == "VALUE = 2\n"


def test_clone_disables_hooks(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _init_repo(source)
    hooks_dir = source / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    marker = tmp_path / "hook-ran"
    (hooks_dir / "post-checkout").write_text(f"#!/bin/sh\ntouch {marker}\n")
    (hooks_dir / "post-checkout").chmod(0o755)
    dest = tmp_path / "dest"

    git_ops.clone(f"file://{source}", "main", dest)

    assert not marker.exists()
