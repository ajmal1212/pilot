from __future__ import annotations

from pathlib import Path

from admin.backend.api_contract import (
    API_ROOT_PREFIX,
    API_V1_PREFIX,
    accepted_response,
    created_response,
    no_content_response,
)
from admin.backend.app import create_app


def test_api_prefixes_define_one_version_boundary() -> None:
    assert API_ROOT_PREFIX == "/api"
    assert API_V1_PREFIX == "/api/v1"


def test_resource_response_helpers_define_creation_and_deletion_contracts(
    tmp_path: Path,
) -> None:
    app = create_app(tmp_path)
    with app.test_request_context():
        created = created_response({"id": "one"}, "/api/v1/resources/one")
        accepted = accepted_response({"id": "task-one"}, "/api/v1/tasks/task-one")
        deleted = no_content_response()

    assert (created.status_code, created.headers["Location"], created.get_json()) == (
        201,
        "/api/v1/resources/one",
        {"id": "one"},
    )
    assert (accepted.status_code, accepted.headers["Location"], accepted.get_json()) == (
        202,
        "/api/v1/tasks/task-one",
        {"id": "task-one"},
    )
    assert deleted.status_code == 204
    assert deleted.get_data() == b""


def test_health_is_an_open_liveness_check(tmp_path: Path) -> None:
    response = create_app(tmp_path).test_client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["Access-Control-Allow-Origin"] == "*"


def test_unknown_api_route_returns_json_404(tmp_path: Path) -> None:
    response = create_app(tmp_path).test_client().get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "error": {
            "code": "not_found",
            "message": "API route not found.",
            "details": {},
        }
    }


def test_wrong_api_method_returns_json_405(tmp_path: Path) -> None:
    response = create_app(tmp_path).test_client().post("/api/v1/health")

    assert response.status_code == 405
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "error": {
            "code": "method_not_allowed",
            "message": "Method not allowed.",
            "details": {},
        }
    }


def test_unversioned_product_route_is_not_an_alias(tmp_path: Path) -> None:
    response = create_app(tmp_path).test_client().get("/api/bootstrap")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
