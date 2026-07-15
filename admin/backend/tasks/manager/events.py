from __future__ import annotations

import json
from typing import Literal, TypedDict


class OutputEvent(TypedDict):
    type: Literal["line", "overwrite"]
    line: str


class DoneEvent(TypedDict):
    type: Literal["done"]
    exit_code: int | None


TaskStreamEvent = OutputEvent | DoneEvent


def output_event(line: str, *, overwrite: bool = False) -> OutputEvent:
    return {"type": "overwrite" if overwrite else "line", "line": line}


def done_event(exit_code: int | None) -> DoneEvent:
    return {"type": "done", "exit_code": exit_code}


def sse_message(event: TaskStreamEvent, event_id: int | None = None) -> str:
    prefix = f"id: {event_id}\n" if event_id is not None else ""
    payload = json.dumps(event, separators=(",", ":"))
    return f"{prefix}data: {payload}\n\n"
