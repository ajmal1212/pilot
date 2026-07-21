"""Tests for the terminal PTY session APIs."""

from __future__ import annotations

import time
from pathlib import Path
from tests.admin.backend.api.test_apps_view import _client


def test_terminal_session_lifecycle(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)

    client = _client(bench_root)
    
    # 1. Create a session
    response = client.post("/api/v1/terminal/session")
    assert response.status_code == 200
    data = response.get_json()
    assert "session_id" in data
    session_id = data["session_id"]

    # 2. Resize terminal
    resize_resp = client.post(f"/api/v1/terminal/resize/{session_id}", json={
        "cols": 80,
        "rows": 24
    })
    assert resize_resp.status_code == 200
    assert resize_resp.get_json()["success"] is True

    # 3. Send keyboard input (hex encoded for "ls\n")
    input_resp = client.post(f"/api/v1/terminal/input/{session_id}", json={
        "data": "6c730a"  # hex bytes for 'ls\n'
    })
    assert input_resp.status_code == 200
    assert input_resp.get_json()["success"] is True
