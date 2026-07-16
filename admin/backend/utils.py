from __future__ import annotations

from pathlib import Path


def read_tail_text(path: Path, min_lines: int, block_size: int = 65536) -> str:
    """Read only as much of the file's end as needed for at least min_lines
    newlines, doubling the window each attempt so a bounded tail read never
    touches a large file's full size."""
    size = path.stat().st_size
    read_size = min(block_size, size)
    with path.open("rb") as handle:
        while True:
            handle.seek(size - read_size)
            chunk = handle.read(read_size)
            if read_size >= size or chunk.count(b"\n") >= min_lines:
                return chunk.decode(errors="replace")
            read_size = min(read_size * 2, size)


def format_duration(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
