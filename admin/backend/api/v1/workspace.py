from __future__ import annotations

import os
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request
from admin.backend.api.responses import error_response

workspace_bp = Blueprint("workspace", __name__)


def _validate_and_get_path(app_name: str, rel_path: str = "") -> Path:
    """Safely resolves path inside the requested app's directory to prevent traversal."""
    bench_root = Path(current_app.config["BENCH_ROOT"])
    app_base = (bench_root / "apps" / app_name).resolve()

    if not app_base.exists() or not app_base.is_dir():
        raise ValueError("App directory does not exist.")

    if not rel_path:
        return app_base

    target_path = (app_base / rel_path).resolve()
    # Security: Ensure target_path starts with app_base
    if not str(target_path).startswith(str(app_base)):
        raise PermissionError("Directory traversal detected.")

    return target_path


@workspace_bp.get("/apps")
def get_apps():
    bench_root = Path(current_app.config["BENCH_ROOT"])
    apps_dir = bench_root / "apps"
    if not apps_dir.exists() or not apps_dir.is_dir():
        return jsonify({"apps": []})

    apps = [d.name for d in apps_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    return jsonify({"apps": sorted(apps)})


@workspace_bp.get("/tree/<app_name>")
def get_tree(app_name: str):
    try:
        app_base = _validate_and_get_path(app_name)
    except ValueError as val_err:
        return error_response("app_not_found", str(val_err), 404)
    except PermissionError as perm_err:
        return error_response("security_error", str(perm_err), 403)

    def _build_tree(current_dir: Path, base_dir: Path) -> list[dict]:
        nodes = []
        try:
            for item in sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                if item.name.startswith((".", "__pycache__")):
                    continue
                rel_path = str(item.relative_to(base_dir))
                node = {
                    "name": item.name,
                    "path": rel_path,
                    "is_dir": item.is_dir(),
                }
                if item.is_dir():
                    node["children"] = _build_tree(item, base_dir)
                nodes.append(node)
        except Exception:
            pass
        return nodes

    return jsonify({"tree": _build_tree(app_base, app_base)})


@workspace_bp.get("/file/<app_name>")
def get_file(app_name: str):
    rel_path = request.args.get("path", "").strip()
    if not rel_path:
        return error_response("invalid_request", "File path is required.", 422)

    try:
        target_path = _validate_and_get_path(app_name, rel_path)
    except ValueError as val_err:
        return error_response("app_not_found", str(val_err), 404)
    except PermissionError as perm_err:
        return error_response("security_error", str(perm_err), 403)

    if not target_path.exists() or not target_path.is_file():
        return error_response("file_not_found", "File does not exist.", 404)

    try:
        # Avoid loading huge binary files into code editor
        if target_path.stat().st_size > 1024 * 1024 * 5:  # 5MB limit
            return error_response("file_too_large", "File size exceeds limit.", 413)

        content = target_path.read_text(encoding="utf-8", errors="replace")
        return jsonify({"content": content})
    except Exception as e:
        return error_response("read_error", f"Could not read file: {e}", 500)


@workspace_bp.post("/file/<app_name>")
def save_file(app_name: str):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("malformed_request", "Expected a JSON object.", 400)

    rel_path = (data.get("path") or "").strip()
    content = data.get("content")

    if not rel_path or content is None:
        return error_response("invalid_request", "Path and content are required.", 422)

    try:
        target_path = _validate_and_get_path(app_name, rel_path)
    except ValueError as val_err:
        return error_response("app_not_found", str(val_err), 404)
    except PermissionError as perm_err:
        return error_response("security_error", str(perm_err), 403)

    try:
        target_path.write_text(content, encoding="utf-8")
        return jsonify({"success": True})
    except Exception as e:
        return error_response("write_error", f"Could not save file: {e}", 500)
