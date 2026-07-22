from __future__ import annotations

import shutil
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request, send_from_directory

from admin.backend.api.responses import error_response
from admin.backend.middleware import rate_limit
from pilot.config import BenchConfig
from pilot.core.bench import Bench
from pilot.core.bench.audit_log import AuditLog
from pilot.plugins import git_ops
from pilot.plugins.manager import PluginManager
from pilot.plugins.security import PluginValidationError, confine_to_root, validate_plugin_name, validate_repo_url
from pilot.utils import installed_plugins_dir

plugins_api_bp = Blueprint("plugins_api", __name__)


@plugins_api_bp.get("")
def list_plugins():
    plugins = PluginManager.list_plugin_info()
    return jsonify({"plugins": plugins})


@plugins_api_bp.get("/<name>/assets/<path:filename>")
def get_plugin_asset(name: str, filename: str):
    """Serve a plugin's built frontend bundle (see docs/plugin-frontend.md).

    Backs the dynamic import() the Admin UI uses to load a plugin's
    Settings UI at runtime, for both bundled and installed plugins.
    """
    try:
        validate_plugin_name(name)
    except PluginValidationError as e:
        return error_response("invalid_plugin", str(e), 400)

    plugin_dir = PluginManager.plugin_dir(name)
    if plugin_dir is None:
        return error_response("not_found", f"Plugin '{name}' was not found.", 404)

    dist_dir = plugin_dir / "frontend" / "dist"
    if not dist_dir.is_dir():
        return error_response("not_found", f"Plugin '{name}' has no frontend assets.", 404)

    return send_from_directory(dist_dir, filename)


@plugins_api_bp.post("/install")
@rate_limit(5, 60)
def install_plugin():
    data = request.get_json(silent=True) or {}
    repo = (data.get("repo") or "").strip()
    branch = (data.get("branch") or "main").strip()
    name = (data.get("name") or "").strip()

    if not repo:
        return error_response("missing_repo", "Git repository URL is required.", 400)

    if not name:
        name = repo.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

    try:
        validate_plugin_name(name)
        validate_repo_url(repo)
    except PluginValidationError as e:
        return error_response("invalid_plugin", str(e), 400)

    if PluginManager.is_bundled(name):
        return error_response("reserved_name", f"'{name}' is a bundled plugin name and cannot be reused.", 409)

    bench_root = Path(current_app.config["BENCH_ROOT"])
    try:
        config = BenchConfig.read(bench_root)
        bench = Bench(config, bench_root)
    except Exception:
        return error_response("config_unavailable", "Could not read bench config.", 500)

    from pilot.tasks.install_plugin_task import InstallPluginTask

    task = InstallPluginTask.queue_submission(
        bench,
        repo=repo,
        branch=branch,
        plugin_name=name
    )

    return jsonify({
        "success": True,
        "task_id": task.task_id,
        "plugin_name": name
    })


@plugins_api_bp.post("/update")
@rate_limit(5, 60)
def update_plugin():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    plugin_dir, error = _installed_plugin_dir(name)
    if error is not None:
        return error

    res = git_ops.pull(plugin_dir)
    if res.returncode != 0:
        return error_response("git_failed", f"Failed to pull plugin changes: {res.stderr}", 500)

    try:
        PluginManager.load_installed_plugin_or_raise(name)
    except Exception as e:
        return error_response("load_failed", f"Plugin updated but failed to load: {e}", 500)

    _audit("update", name)
    return jsonify({"success": True, "output": res.stdout})


@plugins_api_bp.post("/uninstall")
@rate_limit(5, 60)
def uninstall_plugin():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    plugin_dir, error = _installed_plugin_dir(name)
    if error is not None:
        return error

    try:
        shutil.rmtree(plugin_dir)
        PluginManager.load_plugins()
    except Exception as e:
        return error_response("uninstall_failed", f"Failed to delete plugin directory: {e}", 500)

    _audit("uninstall", name)
    return jsonify({"success": True})


def _installed_plugin_dir(name: str) -> tuple[Path | None, object | None]:
    """Shared guard for /update and /uninstall: valid name, not bundled, must exist.

    Returns (plugin_dir, None) on success or (None, error_response) on failure.
    """
    if not name:
        return None, error_response("missing_name", "Plugin name is required.", 400)

    try:
        validate_plugin_name(name)
    except PluginValidationError as e:
        return None, error_response("invalid_plugin", str(e), 400)

    if PluginManager.is_bundled(name):
        return None, error_response(
            "bundled_plugin",
            f"'{name}' is a bundled plugin and is managed by Pilot core, not this endpoint.",
            403,
        )

    plugin_dir = confine_to_root(installed_plugins_dir(), name)
    if not plugin_dir.exists():
        return None, error_response("not_found", f"Plugin '{name}' is not installed.", 404)
    return plugin_dir, None


def _audit(event: str, name: str) -> None:
    bench_root = Path(current_app.config["BENCH_ROOT"])
    try:
        config = BenchConfig.read(bench_root)
        bench = Bench(config, bench_root)
        AuditLog(bench).append("plugin", {"event": event, "plugin": name})
    except Exception:
        pass
