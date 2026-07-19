from __future__ import annotations

import hmac
import json
import time
from pathlib import Path

from admin.backend.app import create_app


def _make_app(tmp_path: Path):
    """Create a Flask test app with a valid bench.toml and admin enabled."""
    (tmp_path / "bench.toml").write_text(
        '[bench]\nname = "test"\npython = "3.14"\n'
        "[admin]\nport = 8000\nenabled = true\n"
        'password = "test"\njwt_secret = "testsecret"\n'
        "allow_bench_management = true\n"
        "[production]\nenabled = false\n",
        encoding="utf-8",
    )
    return create_app(tmp_path)


def _auth_header() -> dict[str, str]:
    """Generate a valid Bearer token for the test JWT secret."""
    import base64

    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"scope": "bench", "exp": int(time.time()) + 3600}).encode()
    ).rstrip(b"=").decode()
    signing_input = f"{header}.{payload}".encode()
    sig = base64.urlsafe_b64encode(
        hmac.new(b"testsecret", signing_input, "sha256").digest()
    ).rstrip(b"=").decode()
    token = f"{header}.{payload}.{sig}"
    return {"Authorization": f"Bearer {token}"}


def test_setup_production_invalid_bench_name(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    res = client.post(
        "/api/v1/benches/invalid;bench/actions/setup-production",
        json={"admin_domain": "pilot.example.com"},
        headers=_auth_header(),
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "invalid_bench_name"


def test_setup_production_invalid_domain(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    bench_dir = tmp_path.parent / "testbench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "bench.toml").write_text("[admin]\nport = 8000\n[production]\nenabled = false\n", encoding="utf-8")

    res = client.post(
        "/api/v1/benches/testbench/actions/setup-production",
        json={"admin_domain": "invalid_domain;script"},
        headers=_auth_header(),
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "invalid_admin_domain"


def test_setup_production_invalid_process_manager(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    bench_dir = tmp_path.parent / "testbench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "bench.toml").write_text("[admin]\nport = 8000\n[production]\nenabled = false\n", encoding="utf-8")

    res = client.post(
        "/api/v1/benches/testbench/actions/setup-production",
        json={"admin_domain": "pilot.example.com", "process_manager": "invalid_pm"},
        headers=_auth_header(),
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "invalid_process_manager"


def test_setup_production_domain_conflict(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    bench1_dir = tmp_path.parent / "bench1"
    bench1_dir.mkdir(parents=True, exist_ok=True)
    (bench1_dir / "bench.toml").write_text(
        '[bench]\nname = "bench1"\npython = "3.14"\n[admin]\nport = 8000\ndomain = "admin.example.com"\n[production]\nenabled = true\n', encoding="utf-8"
    )

    bench2_dir = tmp_path.parent / "bench2"
    bench2_dir.mkdir(parents=True, exist_ok=True)
    (bench2_dir / "bench.toml").write_text(
        '[bench]\nname = "bench2"\npython = "3.14"\n[admin]\nport = 8002\n[production]\nenabled = false\n', encoding="utf-8"
    )

    res = client.post(
        "/api/v1/benches/bench2/actions/setup-production",
        json={"admin_domain": "admin.example.com"},
        headers=_auth_header(),
    )
    assert res.status_code == 409
    assert res.get_json()["error"]["code"] == "admin_domain_conflict"


def test_setup_production_invalid_tls(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    bench_dir = tmp_path.parent / "testbench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "bench.toml").write_text("[admin]\nport = 8000\n[production]\nenabled = false\n", encoding="utf-8")

    res = client.post(
        "/api/v1/benches/testbench/actions/setup-production",
        json={"admin_domain": "pilot.example.com", "tls": "false"},
        headers=_auth_header(),
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "invalid_tls"


def test_setup_production_missing_letsencrypt_email(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    bench_dir = tmp_path.parent / "testbench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "bench.toml").write_text("[admin]\nport = 8000\n[production]\nenabled = false\n", encoding="utf-8")

    res = client.post(
        "/api/v1/benches/testbench/actions/setup-production",
        json={"admin_domain": "pilot.example.com", "tls": True},
        headers=_auth_header(),
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "letsencrypt_email_required"


def test_setup_production_domain_same_as_bench_name(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    client = app.test_client()

    bench_dir = tmp_path.parent / "testbench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    (bench_dir / "bench.toml").write_text("[admin]\nport = 8000\n[production]\nenabled = false\n", encoding="utf-8")

    res = client.post(
        "/api/v1/benches/testbench/actions/setup-production",
        json={"admin_domain": "testbench"},
        headers=_auth_header(),
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "invalid_admin_domain"
