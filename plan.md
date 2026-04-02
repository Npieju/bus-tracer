# Bus Tracer Plan

## Current State

- Static GitHub Pages app is implemented.
- Scheduled GitHub Actions deployment is implemented.
- Scraper validation is implemented.
- Local snapshot generation works.
- First production deploy has not been validated yet.
- Real bus-running-hours validation has not been performed yet.

## Immediate Goal

Get the repository into a state where the first production deploy can be triggered without additional setup work inside the codebase.

## Release Steps

1. Commit the current workspace changes.
2. Push `main` to `origin`.
3. In GitHub repository settings, confirm `Pages -> Source = GitHub Actions`.
4. Run the `Deploy GitHub Pages` workflow manually once.
5. Confirm the published site and `data/status.json` are reachable.

## Production Validation Plan

1. Wait until buses are actually operating on the tracked route.
2. Open the published page and the upstream Kanachu page side by side.
3. Confirm the route labels are correct.
4. Confirm the status message and details match the upstream page.
5. Leave the page open long enough to confirm the browser-side 5-minute refresh.
6. Check the latest GitHub Actions run summary for fetch status.

## Open TODOs

- Verify the first GitHub Pages deployment succeeds on GitHub.
- Confirm whether the repository will stay private or become public.
- Decide whether historical snapshots should be preserved or whether latest-state-only is enough.
- Optionally add a health badge or status note once the public URL is known.
- Optionally add tests around parser extraction if upstream instability becomes a recurring issue.

## Decision Log

- No dedicated deployment branch is needed.
- No commit/push hook is required for periodic updates.
- Scheduled GitHub Actions is the authoritative update mechanism.
- The route is intentionally fixed for now.