from __future__ import annotations

import os
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 120


def clone(repo: str, branch: str, dest: Path) -> subprocess.CompletedProcess:
    """Shallow-clone `repo` into `dest` with hooks and prompts disabled.

    `--` before `repo` stops a repo value that starts with `-` from being
    parsed as a git option. Hooks are disabled because a cloned repo can
    ship a post-checkout/post-merge hook that runs on clone/pull.
    """
    cmd = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "clone",
        "--depth",
        "1",
        "-b",
        branch,
        "--",
        repo,
        str(dest),
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=_git_env(),
        timeout=GIT_TIMEOUT_SECONDS,
    )


def pull(dest: Path) -> subprocess.CompletedProcess:
    cmd = ["git", "-c", "core.hooksPath=/dev/null", "pull", "--ff-only"]
    return subprocess.run(
        cmd,
        cwd=dest,
        capture_output=True,
        text=True,
        env=_git_env(),
        timeout=GIT_TIMEOUT_SECONDS,
    )


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env
