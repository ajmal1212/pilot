from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from flask import Blueprint, current_app, jsonify, request

from admin.backend.api.responses import error_response
from pilot.config import BenchConfig
from pilot.core.bench import Bench
from pilot.plugins.manager import PluginManager

plugins_api_bp = Blueprint("plugins_api", __name__)


@plugins_api_bp.get("")
def list_plugins():
    plugins = PluginManager.list_plugin_info()
    return jsonify({"plugins": plugins})


@plugins_api_bp.post("/install")
def install_plugin():
    data = request.get_json(silent=True) or {}
    repo = (data.get("repo") or "").strip()
    branch = (data.get("branch") or "main").strip()
    name = (data.get("name") or "").strip()

    if not repo:
        return error_response("missing_repo", "Git repository URL is required.", 400)

    # Derive plugin name from repo URL if not supplied
    if not name:
        name = repo.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

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
        "task_id": task.id,
        "plugin_name": name
    })


@plugins_api_bp.post("/update")
def update_plugin():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    if not name:
        return error_response("missing_name", "Plugin name is required.", 400)

    plugin_dir = Path(__file__).parents[3] / "pilot" / "plugins" / name
    if not plugin_dir.exists():
        return error_response("not_found", f"Plugin '{name}' is not installed.", 404)

    try:
        res = subprocess.run(["git", "pull"], cwd=plugin_dir, capture_output=True, text=True)
        if res.returncode != 0:
            return error_response("git_failed", f"Failed to pull plugin changes: {res.stderr}", 500)
    except Exception as e:
        return error_response("update_failed", f"Failed to update plugin: {e}", 500)

    PluginManager.load_plugins()
    return jsonify({"success": True, "output": res.stdout})


@plugins_api_bp.post("/uninstall")
def uninstall_plugin():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    if not name:
        return error_response("missing_name", "Plugin name is required.", 400)

    plugin_dir = Path(__file__).parents[3] / "pilot" / "plugins" / name
    if not plugin_dir.exists():
        return error_response("not_found", f"Plugin '{name}' is not installed.", 404)

    try:
        shutil.rmtree(plugin_dir)
        PluginManager.load_plugins()
    except Exception as e:
        return error_response("uninstall_failed", f"Failed to delete plugin directory: {e}", 500)

    return jsonify({"success": True})
