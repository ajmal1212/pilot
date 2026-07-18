# Admin UI

The Admin UI is the browser surface for benches, sites, apps, tasks, logs, and settings. It should expose operations without reimplementing backend rules.

## Layout

The React app lives under `admin/frontend`. Backend API routes live under `admin/backend/api/v1`.

Keep UI code organized by feature area when it grows: benches, sites, apps, tasks, logs, settings, setup, and shared API/client utilities.

## Data Flow

- Fetch state from the Admin API.
- Start long operations through task endpoints.
- Subscribe to task status, steps, and logs.
- Refresh affected data after task callbacks or final task states.

The UI should treat task ids as the handle for long work.

## Settings

Settings screens edit `bench.toml` through the backend. The frontend should not know how to rewrite TOML or infer production side effects.

Post-save changes such as restarts, firewall sync, WAF sync, or S3 credential sync belong in backend/core code.

## UX Expectations

- Show the current bench and site context clearly.
- Prefer dense operational screens over marketing-style pages.
- Keep destructive actions explicit and reversible where possible.
- Show task progress and logs near the operation that started them.
- Do not hide backend errors behind generic failure messages.

## Local Work

Use the repo scripts and package metadata for exact frontend commands. After API shape changes, update the API client and run the relevant frontend checks.
