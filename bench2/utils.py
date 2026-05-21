import subprocess
from pathlib import Path

from bench2.exceptions import CommandError


def run_command(
    argv: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    stream_output: bool = False,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=not stream_output,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode() if not stream_output and result.stderr else ""
        raise CommandError(
            f"Command {argv[0]!r} failed with exit code {result.returncode}.\n{stderr}".strip(),
            returncode=result.returncode,
        )
    return result
