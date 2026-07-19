from __future__ import annotations

import json
from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from pilot.core.site.timeline import DEFAULT_BUCKET_SECONDS, DEFAULT_TOP, TimelinePoint, build_timeline

if TYPE_CHECKING:
    from pilot.core.site import Site


class SiteMonitoring:
    """Reads this site's slice of Frappe's monitor.json.log."""

    def __init__(self, site: "Site") -> None:
        self.site = site

    @property
    def log_file(self) -> Path:
        return self.site.bench.logs_path / "monitor.json.log"

    def top_paths(self, top: int = DEFAULT_TOP, bucket_seconds: int = DEFAULT_BUCKET_SECONDS) -> dict:
        return build_timeline(
            self._request_points(lambda e: e["request"]["path"]), top, bucket_seconds, "count"
        )

    def slowest_requests(self, top: int = DEFAULT_TOP, bucket_seconds: int = DEFAULT_BUCKET_SECONDS) -> dict:
        return build_timeline(
            self._request_points(lambda e: e["request"]["path"]), top, bucket_seconds, "duration"
        )

    def top_jobs(self, top: int = DEFAULT_TOP, bucket_seconds: int = DEFAULT_BUCKET_SECONDS) -> dict:
        return build_timeline(self._job_points(lambda e: e["job"]["method"]), top, bucket_seconds, "count")

    def slowest_jobs(self, top: int = DEFAULT_TOP, bucket_seconds: int = DEFAULT_BUCKET_SECONDS) -> dict:
        return build_timeline(self._job_points(lambda e: e["job"]["method"]), top, bucket_seconds, "duration")

    def top_ips(self, top: int = DEFAULT_TOP, bucket_seconds: int = DEFAULT_BUCKET_SECONDS) -> dict:
        return build_timeline(
            self._request_points(lambda e: e["request"]["ip"]), top, bucket_seconds, "count"
        )

    def _request_points(self, category: Callable[[dict], str]) -> list[TimelinePoint]:
        return self._points("request", category)

    def _job_points(self, category: Callable[[dict], str]) -> list[TimelinePoint]:
        return self._points("job", category)

    def _points(self, transaction_type: str, category: Callable[[dict], str]) -> list[TimelinePoint]:
        return [
            TimelinePoint(entry["timestamp"], category(entry), entry["duration"])
            for entry in self._records
            if entry.get("transaction_type") == transaction_type
        ]

    @cached_property
    def _records(self) -> list[dict]:
        if not self.log_file.exists():
            return []
        site_name = self.site.config.name
        records = []
        for line in self.log_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("site") == site_name:
                records.append(entry)
        return records
