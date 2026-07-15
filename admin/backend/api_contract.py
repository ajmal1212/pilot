from __future__ import annotations

from flask import current_app, jsonify

API_ROOT_PREFIX = "/api"
API_V1_PREFIX = f"{API_ROOT_PREFIX}/v1"


def is_api_path(path: str) -> bool:
    return path == API_ROOT_PREFIX or path.startswith(f"{API_ROOT_PREFIX}/")


def error_response(
    code: str,
    message: str,
    status: int,
    details: dict | None = None,
):
    return (
        jsonify(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                }
            }
        ),
        status,
    )


def created_response(resource: dict, location: str):
    return _resource_response(resource, 201, location)


def accepted_response(resource: dict, location: str):
    return _resource_response(resource, 202, location)


def no_content_response():
    return current_app.response_class(status=204)


def _resource_response(resource: dict, status: int, location: str):
    response = jsonify(resource)
    response.status_code = status
    response.headers["Location"] = location
    return response
