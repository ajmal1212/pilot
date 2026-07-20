from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from admin.backend.providers.timeline import TimelinePoint, build_timeline

WINDOW_SECONDS = {"30m": 1800, "1h": 3600, "6h": 21600, "12h": 43200, "24h": 86400, "1w": 604800}
_MAX_BUCKETS = 48
_TOP_LIMIT = 5


class SiteMonitoringProvider:
    """Aggregates one site's slice of Frappe's monitor.json.log for one time window."""

    def __init__(self, bench_root: Path, site_name: str, window: str) -> None:
        self._log_path = bench_root / "logs" / "monitor.json.log"
        self._site_name = site_name
        self._window = window if window in WINDOW_SECONDS else "1h"
        self._cutoff = datetime.now(UTC) - timedelta(seconds=WINDOW_SECONDS[self._window])
        self._bucket_seconds = max(60, WINDOW_SECONDS[self._window] // _MAX_BUCKETS)

    def get_analytics(self) -> dict:
        entries = list(self._entries_in_window())
        return {
            "window": self._window,
            "window_seconds": WINDOW_SECONDS[self._window],
            "now": int(datetime.now(UTC).timestamp() * 1000),
            "top_paths": self._timeline(entries, "request", self._request_path, "count"),
            "slowest_requests": self._timeline(entries, "request", self._request_path, "duration"),
            "top_jobs": self._timeline(entries, "job", self._job_method, "count"),
            "slowest_jobs": self._timeline(entries, "job", self._job_method, "duration"),
            "top_ips": self._timeline(entries, "request", self._request_ip, "count"),
        }

    def _timeline(self, entries: list[dict], transaction_type: str, category, by: str) -> dict:
        points = self._points(entries, transaction_type, category)
        return build_timeline(points, _TOP_LIMIT, self._bucket_seconds, by)

    def _points(self, entries: list[dict], transaction_type: str, category) -> list[TimelinePoint]:
        points = []
        for entry in entries:
            if entry.get("transaction_type") != transaction_type:
                continue
            duration = entry.get("duration")
            name = category(entry)
            when = self._get_time(entry.get("timestamp"))
            if when is None or not isinstance(duration, (int, float)) or not name:
                continue
            points.append(TimelinePoint(self.to_epoch_ms(when), name, duration))
        return points

    @staticmethod
    def _request_path(entry: dict) -> str | None:
        return (entry.get("request") or {}).get("path")

    @staticmethod
    def _request_ip(entry: dict) -> str | None:
        return (entry.get("request") or {}).get("ip")

    @staticmethod
    def _job_method(entry: dict) -> str | None:
        return (entry.get("job") or {}).get("method")

    def _entries_in_window(self):
        # Records are appended in time order, so read newest-first and stop at
        # the first one older than the window - a short window never scans the whole file.
        for record in self._iter_records_reversed(self._log_path):
            if not isinstance(record, dict) or record.get("site") != self._site_name:
                continue
            when = self._get_time(record.get("timestamp"))
            if when is None:
                continue
            if when < self._cutoff:
                break
            yield record

    @staticmethod
    def _get_time(value: object) -> datetime | None:
        """Older lines carry naive server-local time; astimezone() normalizes it to UTC."""
        if not isinstance(value, str):
            return None
        try:
            when = datetime.fromisoformat(value)
        except ValueError:
            return None
        return when if when.tzinfo else when.astimezone(UTC)

    @staticmethod
    def to_epoch_ms(when: datetime) -> int:
        return int(when.timestamp() * 1000)

    @staticmethod
    def _iter_records_reversed(path: Path, block_size: int = 65536):
        """Yields records newest-first, in blocks from the end, so a short window
        never touches the whole file."""
        if not path.exists():
            return
        with path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            remainder = b""
            while position > 0:
                size = min(block_size, position)
                position -= size
                handle.seek(position)
                lines = (handle.read(size) + remainder).split(b"\n")
                remainder = lines[0]
                for line in reversed(lines[1:]):
                    record = _safe_json(line)
                    if record is not None:
                        yield record
            record = _safe_json(remainder)
            if record is not None:
                yield record


def _safe_json(line: bytes):
    if not line.strip():
        return None
    try:
        return json.loads(line)
    except ValueError:
        return None
