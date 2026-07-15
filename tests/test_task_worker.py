from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import admin.backend.tasks.manager.worker as worker_module
from admin.backend.tasks.manager.task_state import TaskStatus
from admin.backend.tasks.manager.task_store import TaskStore
from admin.backend.tasks.manager.worker import TaskWorker
from admin.backend.tasks.manager.worker_state import WorkerStatus, WorkerStore


def enqueue(store: TaskStore, task_id: str, sequence: int) -> None:
    store.create_queued(
        {
            "task_id": task_id,
            "command": "build",
            "args": {},
            "command_argv": ["bench", "build"],
            "queue_sequence": sequence,
            "queued_at": "2026-07-15T12:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
        }
    )


def test_worker_runs_fifo_tasks_one_at_a_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaskStore(tmp_path)
    first = "20260715-120000-111111"
    second = "20260715-120000-222222"
    enqueue(store, first, 1)
    enqueue(store, second, 2)
    events: list[tuple[str, str]] = []

    class Process:
        def __init__(self, task_id: str, pid: int) -> None:
            self.task_id = task_id
            self.pid = pid

        def wait(self) -> int:
            events.append(("wait", self.task_id))
            store.transition(self.task_id, TaskStatus.RUNNING, TaskStatus.SUCCESS)
            return 0

    def start_process(argv, **kwargs):
        task_id = Path(argv[-1]).name
        if task_id == second:
            assert events == [("start", first), ("wait", first)]
        assert kwargs["start_new_session"] is True
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        events.append(("start", task_id))
        return Process(task_id, 4000 + len(events))

    monkeypatch.setattr(worker_module.subprocess, "Popen", start_process)

    completed = TaskWorker(tmp_path).run()

    assert completed == 2
    assert events == [
        ("start", first),
        ("wait", first),
        ("start", second),
        ("wait", second),
    ]
    assert store.read_status(first) == TaskStatus.SUCCESS
    assert store.read_status(second) == TaskStatus.SUCCESS
    assert WorkerStore(tmp_path).read_pid() is None
    assert WorkerStore(tmp_path).read_state().status == WorkerStatus.STOPPED


def test_worker_passes_private_secrets_to_task_wrapper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaskStore(tmp_path)
    task_id = "20260715-120000-111111"
    enqueue(store, task_id, 1)
    secret_path = store.task_dir(task_id) / "secrets.json"
    secret_path.write_text('{"admin_password":"secret"}')
    captured = {}

    class Process:
        pid = 4321

        def wait(self) -> int:
            store.transition(task_id, TaskStatus.RUNNING, TaskStatus.SUCCESS)
            return 0

    def start_process(argv, **kwargs):
        captured.update(kwargs)
        return Process()

    monkeypatch.setattr(worker_module.subprocess, "Popen", start_process)

    TaskWorker(tmp_path).run()

    assert captured["env"] == {
        **os.environ,
        "BENCH_TASK_SECRETS_FILE": str(secret_path),
    }


def test_second_worker_cannot_claim_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueue(TaskStore(tmp_path), "20260715-120000-111111", 1)
    lock = WorkerStore(tmp_path).try_acquire()
    assert lock is not None
    monkeypatch.setattr(
        worker_module.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("task process was started"),
    )

    try:
        assert TaskWorker(tmp_path).run() == 0
    finally:
        lock.release()

    assert TaskStore(tmp_path).read_status("20260715-120000-111111") == TaskStatus.QUEUED
