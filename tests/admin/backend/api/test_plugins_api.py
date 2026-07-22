from __future__ import annotations

from pathlib import Path
from tests.admin.backend.api.test_apps_view import _client


def test_list_plugins(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)

    client = _client(bench_root)
    response = client.get("/api/v1/plugins")

    assert response.status_code == 200
    data = response.get_json()
    assert "plugins" in data
    assert isinstance(data["plugins"], list)
