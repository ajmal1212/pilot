from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from tests.admin.backend.api.test_apps_view import _client


@contextmanager
def _bundled_plugin(tmp_path: Path, slug: str = "sample-bundled"):
    """Fake a bundled plugin so bundled-plugin behavior is testable without
    depending on any specific plugin (e.g. cloudflare) actually being bundled.
    """
    bundled_root = tmp_path / "bundled"
    (bundled_root / slug).mkdir(parents=True)
    (bundled_root / slug / "plugin.py").write_text("")
    with patch("pilot.plugins.manager._BUNDLED_ROOT", bundled_root):
        yield slug


def test_list_plugins(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        response = client.get("/api/v1/plugins")

    assert response.status_code == 200
    data = response.get_json()
    assert "plugins" in data
    assert isinstance(data["plugins"], list)
    bundled = next(p for p in data["plugins"] if p["name"] == slug)
    assert bundled["bundled"] is True


def _patched_plugins_dir(plugins_root: Path):
    return (
        patch("admin.backend.api.v1.plugins_api.installed_plugins_dir", return_value=plugins_root),
        patch("pilot.plugins.scaffold.installed_plugins_dir", return_value=plugins_root),
    )


def test_scaffold_creates_a_new_plugin(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    plugins_root = tmp_path / "plugins-data"
    client = _client(bench_root)

    p1, p2 = _patched_plugins_dir(plugins_root)
    with p1, p2:
        response = client.post("/api/v1/plugins/scaffold", json={"name": "my-plugin"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["name"] == "my-plugin"
    assert (plugins_root / "my-plugin" / "plugin.py").is_file()
    assert (plugins_root / "my-plugin" / "frontend" / "src" / "index.js").is_file()


def test_scaffold_rejects_invalid_name(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.post("/api/v1/plugins/scaffold", json={"name": "../../etc"})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_plugin"


def test_scaffold_rejects_bundled_plugin_name(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        response = client.post("/api/v1/plugins/scaffold", json={"name": slug})

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "reserved_name"


def test_scaffold_rejects_an_existing_plugin_dir(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    plugins_root = tmp_path / "plugins-data"
    (plugins_root / "my-plugin").mkdir(parents=True)
    client = _client(bench_root)

    p1, p2 = _patched_plugins_dir(plugins_root)
    with p1, p2:
        response = client.post("/api/v1/plugins/scaffold", json={"name": "my-plugin"})

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "already_exists"


def test_scaffold_missing_name_is_rejected(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.post("/api/v1/plugins/scaffold", json={})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "missing_name"


def test_install_rejects_invalid_plugin_name(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.post(
        "/api/v1/plugins/install",
        json={"repo": "https://github.com/frappe/example-plugin", "name": "../../etc"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_plugin"


def test_install_rejects_non_https_repo(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.post(
        "/api/v1/plugins/install",
        json={"repo": "file:///etc/passwd", "name": "demo"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_plugin"


def test_install_rejects_bundled_plugin_name(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        response = client.post(
            "/api/v1/plugins/install",
            json={"repo": "https://github.com/frappe/example-plugin", "name": slug},
        )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "reserved_name"


def test_install_queues_task_for_a_valid_request(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with patch("pilot.internal.tasks.runner.task_workers.wake", return_value=False):
        response = client.post(
            "/api/v1/plugins/install",
            json={"repo": "https://github.com/frappe/example-plugin", "branch": "main"},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["plugin_name"] == "example-plugin"


def test_update_rejects_bundled_plugin(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        response = client.post("/api/v1/plugins/update", json={"name": slug})

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "bundled_plugin"


def test_uninstall_rejects_bundled_plugin(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        response = client.post("/api/v1/plugins/uninstall", json={"name": slug})

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "bundled_plugin"


def test_uninstall_rejects_path_traversal_name(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.post("/api/v1/plugins/uninstall", json={"name": "../../pilot"})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_plugin"


def test_uninstall_unknown_installed_plugin_is_not_found(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with patch(
        "admin.backend.api.v1.plugins_api.installed_plugins_dir", return_value=tmp_path / "plugins-data"
    ):
        response = client.post("/api/v1/plugins/uninstall", json={"name": "does-not-exist"})

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_get_plugin_asset_serves_a_bundled_plugin_bundle(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        dist_dir = tmp_path / "bundled" / slug / "frontend" / "dist"
        dist_dir.mkdir(parents=True)
        (dist_dir / "index.js").write_text("export function init() {}")

        response = client.get(f"/api/v1/plugins/{slug}/assets/index.js")

    assert response.status_code == 200
    assert b"export function init" in response.data


def test_get_plugin_asset_rejects_invalid_name(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.get("/api/v1/plugins/../assets/index.js")

    assert response.status_code in (400, 404)


def test_get_plugin_asset_404_when_plugin_unknown(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    response = client.get("/api/v1/plugins/does-not-exist/assets/index.js")

    assert response.status_code == 404


def test_get_plugin_asset_404_when_no_frontend_built(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)

    with _bundled_plugin(tmp_path) as slug:
        response = client.get(f"/api/v1/plugins/{slug}/assets/index.js")

    assert response.status_code == 404


def test_get_plugin_asset_rejects_filename_traversal(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    client = _client(bench_root)
    secret = tmp_path / "secret.txt"
    secret.write_text("do-not-serve-me")

    with _bundled_plugin(tmp_path) as slug:
        dist_dir = tmp_path / "bundled" / slug / "frontend" / "dist"
        dist_dir.mkdir(parents=True)
        (dist_dir / "index.js").write_text("export function init() {}")

        response = client.get(f"/api/v1/plugins/{slug}/assets/../../../../secret.txt")

    assert response.status_code == 404


def test_uninstall_removes_an_installed_plugin(tmp_path: Path) -> None:
    bench_root = tmp_path / "benches" / "current"
    bench_root.mkdir(parents=True)
    plugins_root = tmp_path / "plugins-data"
    plugin_dir = plugins_root / "demo"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.py").write_text("")

    client = _client(bench_root)

    with patch("admin.backend.api.v1.plugins_api.installed_plugins_dir", return_value=plugins_root):
        response = client.post("/api/v1/plugins/uninstall", json={"name": "demo"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert not plugin_dir.exists()
