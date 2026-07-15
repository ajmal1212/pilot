from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path


def main() -> None:
    payload_path = Path(sys.argv[1])
    try:
        payload = json.loads(payload_path.read_text())
    finally:
        payload_path.unlink(missing_ok=True)

    module = payload["module"]
    sys.argv = [module, *payload["args"]]
    runpy.run_module(module, run_name="__main__")


if __name__ == "__main__":
    main()
