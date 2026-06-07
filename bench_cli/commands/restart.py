from __future__ import annotations

from bench_cli.core.bench import Bench
from bench_cli.exceptions import BenchError


class RestartCommand:
    def __init__(self, bench: Bench) -> None:
        self.bench = bench

    def run(self) -> None:
        manager = self._detect_manager()
        manager.generate_config()
        manager.reload()
        manager.restart()

    def _detect_manager(self):
        from bench_cli.managers.supervisor_process_manager import SupervisorProcessManager
        from bench_cli.managers.systemd_process_manager import SystemdProcessManager

        supervisor = SupervisorProcessManager(self.bench)
        if supervisor.supervisor_conf_path.exists():
            return supervisor

        systemd = SystemdProcessManager(self.bench)
        if systemd.is_configured():
            return systemd

        raise BenchError(
            "No production process manager found. Run 'bench setup production' first."
        )
