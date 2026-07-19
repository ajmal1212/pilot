from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

DEFAULT_TOP = 5
DEFAULT_BUCKET_SECONDS = 600


@dataclass
class TimelinePoint:
    """One timestamped event, normalized from any log source."""

    timestamp: str
    category: str
    duration: int


def build_timeline(
    points: list[TimelinePoint],
    top: int = DEFAULT_TOP,
    bucket_seconds: int = DEFAULT_BUCKET_SECONDS,
    by: str = "count",
) -> dict:
    """Bucket points into a per-category time series for the top N categories,
    ranked by request count (by="count") or worst duration (by="duration")."""
    categories = [name for name, _ in _rank(points, top, by)]
    buckets: dict[int, dict[str, float]] = {}
    for point in points:
        if point.category not in categories:
            continue
        row = buckets.setdefault(_bucket_epoch_ms(point.timestamp, bucket_seconds), {})
        if by == "count":
            row[point.category] = row.get(point.category, 0) + 1
        else:
            row[point.category] = max(row.get(point.category, 0), round(point.duration / 1000))
    return {
        "categories": categories,
        "points": [{"time": time, **values} for time, values in sorted(buckets.items())],
    }


def _rank(points: list[TimelinePoint], top: int, by: str) -> list[tuple[str, float]]:
    if by == "count":
        return Counter(point.category for point in points).most_common(top)
    slowest: dict[str, int] = {}
    for point in points:
        slowest[point.category] = max(slowest.get(point.category, 0), point.duration)
    return sorted(slowest.items(), key=lambda item: item[1], reverse=True)[:top]


def _bucket_epoch_ms(timestamp: str, bucket_seconds: int) -> int:
    epoch = datetime.fromisoformat(timestamp).timestamp()
    return int(epoch // bucket_seconds) * bucket_seconds * 1000
