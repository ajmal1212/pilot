# Agent Guide

This repo is a Python CLI plus FastAPI Admin backend for managing Frappe benches. Prefer small, direct changes that keep the object model easy to use.

## Main Rules

- Put real behavior in `pilot.core`, managers, or tasks.
- Keep CLI commands and API routes thin.
- Use `Server`, `Bench`, `Site`, and `App` as the main entry points.
- Group related files in folders instead of adding many same-prefix modules.
- Avoid lazy re-exports in package `__init__.py` when autocomplete matters.
- Keep comments short. Remove comments that restate the code.
- Do not create refactor planning markdown files.

## Useful Entry Points

- `pilot/core/server/__init__.py`: host-level operations.
- `pilot/core/bench/__init__.py`: bench object and bench-level operations.
- `pilot/core/site/__init__.py`: site object and site-level operations.
- `pilot/core/app/__init__.py`: app object and repository operations.
- `pilot/tasks/__init__.py`: public task API and task exports.
- `pilot/internal/cli`: argparse and command dispatch internals.
- `admin/backend/api/v1`: Admin API route groups.

## Design Expectations

Use object-owned syntax when adding features:

```python
bench = Server().bench("main")
site = bench.site("site.local")
InstallAppTask.queue(bench, site="site.local", apps=["erpnext"])
```

Avoid new APIs that pass a bench and site into unrelated helper objects when the operation can live under `bench`, `site`, `app`, or `server`.

## Working Rules

- Do not touch unrelated dirty files.
- Do not delete data directories.
- The top-level `benches/` directory is local data and must stay ignored.
- Use `apply_patch` for manual edits.
- Run `uv run ruff check admin pilot tests` after Python changes.
- Run targeted tests for narrow behavior changes and `uv run pytest` before committing broad refactors.

## Docs

Keep docs concise and current. Human readers should find the workflow quickly. LLMs should find the source of truth, object boundaries, and safe edit locations without scanning long prose.
