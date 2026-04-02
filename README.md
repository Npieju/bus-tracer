# bus-tracer

GitHub Pages app that tracks the real-time Kanachu bus approach status for 伊勢山（平塚市） -> 大野農協前（平塚市） and refreshes the published data every 5 minutes.

## Included Packages

- FastAPI
- Uvicorn
- HTTPX
- Beautiful Soup 4
- selectolax
- lxml
- pandas
- SQLAlchemy
- Alembic
- Jinja2
- aiofiles
- orjson
- pydantic-settings
- python-dotenv
- tenacity
- pytest
- Ruff

## Development

Use the dev container or run the compose service for a shell-only environment.

```bash
docker compose up -d --build
docker compose exec app bash
```

If you change the dev container setup, rebuild it from VS Code with `Dev Containers: Rebuild and Reopen in Container`.

## GitHub CLI In Container

The dev container includes `gh`.

It also mounts these host files into the container in read-only mode so authentication and git settings are shared:

- `~/.config/gh`
- `~/.gitconfig`
- `~/.ssh`

This means a `gh auth login` done on the host can be reused inside the container after rebuild.

## App Structure

- `scripts/fetch_bus_data.py`: Fetches and parses the Kanachu approach page and writes `docs/data/status.json`.
- `docs/`: Static site published to GitHub Pages.
- `.github/workflows/pages.yml`: Runs the scraper every 5 minutes and deploys the updated site.

## Local Preview

Generate the current data snapshot:

```bash
python3 scripts/fetch_bus_data.py --output docs/data/status.json
```

Preview the static site locally:

```bash
python3 -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`.

## GitHub Pages Deployment

1. Push this repository to GitHub.
2. In GitHub, enable Pages with `GitHub Actions` as the source.
3. The workflow will deploy on push, on manual dispatch, and on a 5-minute cron schedule.

## Pre-Production Checklist

1. Push the local `main` branch to `origin/main` at least once. Until the first push, the remote repository has no default branch and Pages cannot start.
2. If you are on a GitHub plan that does not support private Pages, switch the repository to public before expecting the site to open.
3. In GitHub `Settings -> Pages`, confirm the source is `GitHub Actions`.
4. In GitHub `Actions`, run `Deploy GitHub Pages` manually once to force the first deployment instead of waiting for cron.
5. After that first run, verify both the site root and `docs/data/status.json` are reachable from the published URL.
6. When buses are running, compare the published page against the source site once to confirm the parser still matches the live layout.

## Troubleshooting

- `gh api repos/Npieju/bus-tracer/pages` returning `404` before the first successful deployment is expected.
- Scheduled workflows only run on the default branch and may be paused automatically on inactive repositories.
- If the upstream HTML layout changes, the workflow summary will still show the last fetch result, and `status.json` will fall back to an error payload instead of silently publishing broken data.

Notes:

- GitHub Actions cron supports 5-minute intervals, but the actual run time can drift slightly.
- The app itself also re-fetches `status.json` in the browser every 5 minutes so an already-open tab updates after a new deployment lands.

## GitHub Repository

Local git is initialized already.

After authenticating GitHub CLI, create the remote repository with:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh repo create bus-tracer --private --source=. --remote=origin
```