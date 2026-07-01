#!/usr/bin/env python3
"""
Find targets in registry/apps_v2.json whose code reference changed between
two revisions, so only those need a fresh scan — not the whole registry.

A target is changed if the app is new, its repo changed, the target is new,
or the target's ref (branch/tag/commit) changed. Pure metadata edits do not
trigger a re-scan.

Output: JSON list of {name, repo, target_type, target} items.

Run:
    python3 scripts/diff_marketplace_apps.py <old-apps.json> <new-apps.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_apps(path: Path) -> dict[str, dict]:
    apps = json.loads(path.read_text())
    return {app["name"]: app for app in apps}


def targets_by_version(app: dict) -> dict[str, dict]:
    return {t["version"]: t for t in app.get("targets", [])}


def find_changed_targets(old_apps: dict[str, dict], new_apps: dict[str, dict]) -> list[dict]:
    changed = []
    for name, app in new_apps.items():
        old_app = old_apps.get(name)
        repo_changed = old_app is None or old_app.get("repo") != app.get("repo")
        old_targets = targets_by_version(old_app) if old_app else {}

        for version, target in targets_by_version(app).items():
            old_target = old_targets.get(version)
            target_changed = old_target is None or old_target.get("target") != target.get("target")
            if repo_changed or target_changed:
                changed.append({"name": name, "repo": app["repo"], **target})

    return changed


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: diff_marketplace_apps.py <old-apps.json> <new-apps.json>", file=sys.stderr)
        sys.exit(1)

    old_apps = load_apps(Path(sys.argv[1]))
    new_apps = load_apps(Path(sys.argv[2]))
    changed = find_changed_targets(old_apps, new_apps)

    print(json.dumps(changed, indent=2))


if __name__ == "__main__":
    main()
