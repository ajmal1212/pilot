from __future__ import annotations

from pathlib import Path

from flask import current_app, jsonify, request

from admin.backend.api.v1.sites import sites_bp
from admin.backend.api.v1.sites.shared import internal_error, site_name, site_not_found
from admin.backend.middleware import require_scope
from pilot.core.bench import Bench
from pilot.internal.site_paths import site_exists

_DEFAULT_TOP = 5
_DEFAULT_BUCKET_SECONDS = 600


@sites_bp.get("/<name>/monitoring")
@require_scope(site_name)
def get_monitoring(name: str):
    bench_root = Path(current_app.config["BENCH_ROOT"])
    if not site_exists(bench_root, name):
        return site_not_found()
    top = request.args.get("top", _DEFAULT_TOP, type=int)
    bucket_seconds = request.args.get("bucket_seconds", _DEFAULT_BUCKET_SECONDS, type=int)
    try:
        monitoring = Bench(bench_root).site(name).monitoring
        return jsonify(
            {
                "top_paths": monitoring.top_paths(top, bucket_seconds),
                "slowest_requests": monitoring.slowest_requests(top, bucket_seconds),
                "top_jobs": monitoring.top_jobs(top, bucket_seconds),
                "slowest_jobs": monitoring.slowest_jobs(top, bucket_seconds),
                "top_ips": monitoring.top_ips(top, bucket_seconds),
            }
        )
    except Exception:
        return internal_error("Could not read site monitoring data.")
