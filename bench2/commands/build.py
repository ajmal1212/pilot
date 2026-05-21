from __future__ import annotations

import click

from bench2.core.bench import Bench
from bench2.utils import run_command


class BuildCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        for app in self.bench.apps():
            click.echo(f"Building assets for {app.config.name}...")
            app.build_assets()

        click.echo("Collecting assets into sites/assets/...")
        bench_binary = self.bench.env_path / "bin" / "bench"
        run_command(
            [str(bench_binary), "build", "--make-copy"],
            cwd=self.bench.path,
        )
