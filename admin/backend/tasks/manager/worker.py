from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from admin.backend.tasks.manager.task_queue import TaskQueue
from admin.backend.tasks.manager.task_state import TERMINAL_TASK_STATUSES
from admin.backend.tasks.manager.task_store import TaskStore
from admin.backend.tasks.manager.worker_state import WorkerStatus, WorkerStore


class TaskWorker:
    def __init__(self, bench_root: Path) -> None:
        self._bench_root = Path(bench_root)
        self._queue = TaskQueue(self._bench_root)
        self._tasks = TaskStore(self._bench_root)
        self._worker = WorkerStore(self._bench_root)
        self._pid = os.getpid()

    def run(self) -> int:
        lock = self._worker.try_acquire()
        if lock is None:
            return 0

        completed = 0
        with lock:
            self._worker.write_pid(self._pid)
            self._worker.write_state(WorkerStatus.STARTING, self._pid)
            try:
                while self._run_next():
                    completed += 1
                self._worker.write_state(WorkerStatus.IDLE, self._pid)
            finally:
                self._worker.write_state(WorkerStatus.STOPPED, None)
                self._worker.write_pid(None)
        return completed

    def _run_next(self) -> bool:
        task_id = self._queue.claim_next()
        if task_id is None:
            return False

        self._worker.write_state(WorkerStatus.RUNNING, self._pid, task_id)
        process = self._start_task(task_id)
        self._tasks.write_pid(task_id, process.pid)
        process.wait()
        if self._tasks.read_status(task_id) not in TERMINAL_TASK_STATUSES:
            raise RuntimeError(f"Task wrapper exited without finalizing {task_id}")
        return True

    def _start_task(self, task_id: str) -> subprocess.Popen:
        task_dir = self._tasks.task_dir(task_id)
        kwargs = {
            "start_new_session": True,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        secret_path = task_dir / "secrets.json"
        if secret_path.exists():
            kwargs["env"] = {
                **os.environ,
                "BENCH_TASK_SECRETS_FILE": str(secret_path),
            }
        return subprocess.Popen(
            [sys.executable, "-m", "admin.backend.tasks.manager.wrapper", str(task_dir)],
            **kwargs,
        )


def main() -> None:
    TaskWorker(Path(sys.argv[1])).run()


if __name__ == "__main__":
    main()
