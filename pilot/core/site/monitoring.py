from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pilot.core.site import Site

DEFAULT_LIMIT = 10


@dataclass
class PathCount:
    path: str
    count: int


@dataclass
class SlowTransaction:
    label: str
    duration: int
    timestamp: str


@dataclass
class IpCount:
    ip: str
    count: int


class SiteMonitoring:
    """Reads this site's slice of the bench-wide monitor.json.log."""

    def __init__(self, site: "Site") -> None:
        self.site = site

    @property
    def log_file(self) -> Path:
        return self.site.bench.logs_path / "monitor.json.log"

    def top_paths(self, limit: int = DEFAULT_LIMIT) -> list[PathCount]:
        counts = Counter(entry["request"]["path"] for entry in self._entries("request"))
        return [PathCount(path, count) for path, count in counts.most_common(limit)]

    def slowest_requests(self, limit: int = DEFAULT_LIMIT) -> list[SlowTransaction]:
        return self._slowest(self._entries("request"), lambda entry: entry["request"]["path"], limit)

    def top_jobs(self, limit: int = DEFAULT_LIMIT) -> list[PathCount]:
        counts = Counter(entry["job"]["method"] for entry in self._entries("job"))
        return [PathCount(method, count) for method, count in counts.most_common(limit)]

    def slowest_jobs(self, limit: int = DEFAULT_LIMIT) -> list[SlowTransaction]:
        return self._slowest(self._entries("job"), lambda entry: entry["job"]["method"], limit)

    def top_ips(self, limit: int = DEFAULT_LIMIT) -> list[IpCount]:
        counts = Counter(entry["request"]["ip"] for entry in self._entries("request"))
        return [IpCount(ip, count) for ip, count in counts.most_common(limit)]

    def _slowest(self, entries: list[dict], label: Callable[[dict], str], limit: int) -> list[SlowTransaction]:
        ranked = sorted(entries, key=lambda entry: entry["duration"], reverse=True)
        return [
            SlowTransaction(label(entry), entry["duration"], entry["timestamp"]) for entry in ranked[:limit]
        ]

    def _entries(self, transaction_type: str) -> list[dict]:
        return [entry for entry in self._records if entry.get("transaction_type") == transaction_type]

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
