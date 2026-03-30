# bus-tracer

Docker-based development environment for a small web app that crawls and displays real-time bus information.

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

## GitHub Repository

Local git is initialized already.

After authenticating GitHub CLI, create the remote repository with:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh repo create bus-tracer --private --source=. --remote=origin
```