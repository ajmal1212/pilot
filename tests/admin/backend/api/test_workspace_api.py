"""Tests for the workspace API endpoints."""

from __future__ import annotations

from pathlib import Path
from tests.admin.backend.api.test_apps_view import _client


def test_get_apps_lists_directories_in_apps(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    apps_dir = bench_root / "apps"
    apps_dir.mkdir(parents=True)
    
    # Create two dummy app directories
    (apps_dir / "my_custom_app").mkdir()
    (apps_dir / "another_app").mkdir()
    # A hidden directory (should be ignored)
    (apps_dir / ".hidden_dir").mkdir()

    client = _client(bench_root)
    response = client.get("/api/v1/workspace/apps")
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["apps"] == ["another_app", "my_custom_app"]


def test_get_tree_returns_correct_hierarchy(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    app_dir = bench_root / "apps" / "my_app"
    app_dir.mkdir(parents=True)
    
    # Create files and directories
    (app_dir / "file1.py").write_text("print('hello')")
    sub_dir = app_dir / "utils"
    sub_dir.mkdir()
    (sub_dir / "file2.js").write_text("console.log('hello')")

    client = _client(bench_root)
    response = client.get("/api/v1/workspace/tree/my_app")
    
    assert response.status_code == 200
    data = response.get_json()
    tree = data["tree"]
    
    assert len(tree) == 2
    # First item should be utils dir (directories first in sorted keys)
    assert tree[0]["name"] == "utils"
    assert tree[0]["path"] == "utils"
    assert tree[0]["is_dir"] is True
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "file2.js"
    assert tree[0]["children"][0]["path"] == "utils/file2.js"
    
    # Second should be file1.py
    assert tree[1]["name"] == "file1.py"
    assert tree[1]["path"] == "file1.py"
    assert tree[1]["is_dir"] is False


def test_get_tree_app_not_found(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    client = _client(bench_root)
    
    response = client.get("/api/v1/workspace/tree/non_existent")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "app_not_found"


def test_get_file_reads_content(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    app_dir = bench_root / "apps" / "my_app"
    app_dir.mkdir(parents=True)
    file_path = app_dir / "config.json"
    file_path.write_text('{"key": "value"}')

    client = _client(bench_root)
    response = client.get("/api/v1/workspace/file/my_app?path=config.json")
    
    assert response.status_code == 200
    assert response.get_json()["content"] == '{"key": "value"}'


def test_get_file_traversal_blocked(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    app_dir = bench_root / "apps" / "my_app"
    app_dir.mkdir(parents=True)
    
    # Write sensitive file outside app directory
    sensitive_file = bench_root / "sensitive.txt"
    sensitive_file.write_text("secret_token")

    client = _client(bench_root)
    response = client.get("/api/v1/workspace/file/my_app?path=../sensitive.txt")
    
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "security_error"


def test_save_file_writes_content(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    app_dir = bench_root / "apps" / "my_app"
    app_dir.mkdir(parents=True)
    file_path = app_dir / "code.py"
    file_path.write_text("x = 10")

    client = _client(bench_root)
    response = client.post("/api/v1/workspace/file/my_app", json={
        "path": "code.py",
        "content": "x = 20\ny = 30"
    })
    
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert file_path.read_text() == "x = 20\ny = 30"
