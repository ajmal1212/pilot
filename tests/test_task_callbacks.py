from __future__ import annotations

import json
from pathlib import Path

import pytest

from admin.backend.tasks import callbacks


def test_remove_failed_site_operation_uses_json_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_path = tmp_path / "sites" / "new.localhost"
    site_path.mkdir(parents=True)
    monkeypatch.setattr(callbacks, "_remove_from_hosts", lambda site: None)

    callbacks.run_callback(
        {"operation": "remove-failed-site", "args": {"site": "new.localhost"}},
        {"bench_root": str(tmp_path)},
    )

    assert not site_path.exists()


def test_disable_site_ssl_operation_uses_json_args(tmp_path: Path) -> None:
    config_path = tmp_path / "sites" / "secure.localhost" / "site_config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"ssl": True, "db_name": "site"}))

    callbacks.run_callback(
        {"operation": "disable-site-ssl", "args": {"site": "secure.localhost"}},
        {"bench_root": str(tmp_path)},
    )

    assert json.loads(config_path.read_text()) == {"ssl": False, "db_name": "site"}


def test_callback_args_must_be_json_serializable(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="JSON serializable"):
        callbacks.validate_callback(
            {"operation": "remove-failed-site", "args": {"path": tmp_path}}
        )
