from __future__ import annotations

from pathlib import Path
from admin.backend.app import create_app


def test_cloudflare_action_invalid_action(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    client = app.test_client()

    res = client.post("/api/v1/cloudflare/action", json={"action": "invalid"})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "invalid_action"


def test_cloudflare_zones_missing_token(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    client = app.test_client()

    res = client.post("/api/v1/cloudflare/zones", json={})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "missing_token"


def test_cloudflare_create_missing_domain(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    client = app.test_client()

    res = client.post("/api/v1/cloudflare/create", json={})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "missing_parameters"


def test_cloudflare_toggle_expose_invalid_site_name(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    client = app.test_client()

    res = client.post("/api/v1/cloudflare/sites/invalid;site/expose", json={"expose": True, "domain": "example.com"})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "invalid_site_name"
