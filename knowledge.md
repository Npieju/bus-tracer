# Bus Tracer Knowledge

## Product Goal

- Publish a lightweight web app on GitHub Pages.
- Show the Kanachu real-time approach information for the fixed route 伊勢山（平塚市） -> 大野農協前（平塚市）.
- Refresh the published data every 5 minutes.

## Fixed Route Definition

- Boarding stop: 伊勢山（平塚市）
- Boarding stop ID: `16240`
- Alighting stop: 大野農協前（平塚市）
- Alighting stop ID: `16244`

## Architecture Decisions

- The site is static and served from `docs/` via GitHub Pages.
- Live data is not fetched directly from the browser because the upstream site does not provide a permissive CORS path suitable for this app.
- Data is fetched server-side inside GitHub Actions on a 5-minute schedule.
- The scraper writes a normalized JSON snapshot to `docs/data/status.json`.
- The frontend reads `status.json` and refreshes it in the browser every 5 minutes.

## Key Files

- `scripts/fetch_bus_data.py`: upstream fetch + parse + JSON generation.
- `docs/index.html`: static UI shell.
- `docs/app.js`: JSON fetch, timer, and rendering logic.
- `docs/styles.css`: visual design.
- `.github/workflows/pages.yml`: scheduled fetch and GitHub Pages deploy.
- `docs/.nojekyll`: disables Jekyll processing on Pages.

## Deployment Assumptions

- The default branch is `main`.
- GitHub Pages is configured to use `GitHub Actions` as the source.
- The first deployment must be triggered after the initial push.
- If the repository remains private, the GitHub plan must support private GitHub Pages.

## Data Contract

`docs/data/status.json` should always contain these keys:

- `status`: `ok` or `error`
- `fetchedAt`: UTC timestamp in ISO 8601 format
- `message`: top-level human-readable fetch result
- `hasLiveData`: boolean
- `route.fromStop.id`: `16240`
- `route.toStop.id`: `16244`
- `source.url`: upstream result URL
- `details`: flattened text extracted from the source page

## Operational Risks

- Upstream HTML may change without notice and break parsing.
- GitHub Actions cron is not exact real-time scheduling; runs can drift.
- Scheduled workflows only run on the default branch.
- GitHub Pages may remain unpublished until the first successful deploy completes.
- At off-hours there may be no active bus approach data, so a successful fetch can still show `該当する情報は現在ありません。`.

## Verification Commands

Generate the snapshot locally:

```bash
python3 scripts/fetch_bus_data.py --output docs/data/status.json
```

Preview the site locally:

```bash
python3 -m http.server 8000 --directory docs
```

Inspect Pages configuration after first deployment:

```bash
gh api repos/Npieju/bus-tracer/pages
```