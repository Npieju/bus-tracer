#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib import error, request


API_BASE = "https://api.github.com"
ACCEPT_HEADER = "application/vnd.github+json"


@dataclass
class WorkflowRun:
    id: int
    name: str
    status: str
    conclusion: str | None
    created_at: datetime
    html_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a repository_dispatch refresh event and optionally wait for the workflow run.",
    )
    parser.add_argument("--owner", default="Npieju", help="GitHub repository owner")
    parser.add_argument("--repo", default="bus-tracer", help="GitHub repository name")
    parser.add_argument("--event-type", default="external-refresh", help="repository_dispatch event type")
    parser.add_argument("--token", help="GitHub token. Falls back to GITHUB_TOKEN or GH_TOKEN.")
    parser.add_argument("--api-base", default=API_BASE, help="GitHub API base URL")
    parser.add_argument("--wait", action="store_true", help="Wait for the repository_dispatch workflow run")
    parser.add_argument("--timeout", type=int, default=180, help="Seconds to wait for the run to appear or finish")
    parser.add_argument("--poll-interval", type=int, default=5, help="Polling interval in seconds while waiting")
    return parser.parse_args()


def get_token(explicit_token: str | None) -> str:
    token = explicit_token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token
    raise SystemExit("GitHub token is required. Use --token or set GITHUB_TOKEN / GH_TOKEN.")


def parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def api_request(
    url: str,
    token: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[int, bytes]:
    data = None
    headers = {
        "Accept": ACCEPT_HEADER,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bus-tracer-dispatch-check",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            return response.status, response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API request failed: {exc.code} {exc.reason}\n{detail}") from exc
    except error.URLError as exc:
        raise SystemExit(f"GitHub API request failed: {exc.reason}") from exc


def send_dispatch(args: argparse.Namespace, token: str, requested_at: datetime) -> None:
    url = f"{args.api_base}/repos/{args.owner}/{args.repo}/dispatches"
    payload = {
        "event_type": args.event_type,
        "client_payload": {
            "source": "manual-check",
            "requestedAt": requested_at.isoformat().replace("+00:00", "Z"),
        },
    }
    status, _ = api_request(url, token, method="POST", payload=payload)
    if status != 204:
        raise SystemExit(f"Dispatch was not accepted. Unexpected status: {status}")


def list_repository_dispatch_runs(args: argparse.Namespace, token: str) -> list[WorkflowRun]:
    url = (
        f"{args.api_base}/repos/{args.owner}/{args.repo}/actions/runs"
        "?event=repository_dispatch&per_page=10"
    )
    _, body = api_request(url, token)
    data = json.loads(body.decode("utf-8"))
    runs: list[WorkflowRun] = []
    for item in data.get("workflow_runs", []):
        runs.append(
            WorkflowRun(
                id=item["id"],
                name=item.get("display_title") or item.get("name") or "(unknown)",
                status=item["status"],
                conclusion=item.get("conclusion"),
                created_at=parse_datetime(item["created_at"]),
                html_url=item["html_url"],
            )
        )
    return runs


def wait_for_run(args: argparse.Namespace, token: str, requested_at: datetime) -> WorkflowRun:
    deadline = time.monotonic() + args.timeout
    earliest_match = requested_at - timedelta(seconds=10)
    matched_run: WorkflowRun | None = None
    announced_run = False

    while time.monotonic() < deadline:
        runs = list_repository_dispatch_runs(args, token)
        candidates = [run for run in runs if run.created_at >= earliest_match]
        if candidates:
            matched_run = max(candidates, key=lambda run: run.created_at)
            if not announced_run:
                print(f"workflow run detected: {matched_run.id} ({matched_run.name})")
                print(f"run url: {matched_run.html_url}")
                announced_run = True
            if matched_run.status == "completed":
                return matched_run
        time.sleep(args.poll_interval)

    if matched_run is not None:
        raise SystemExit(
            "Timed out while waiting for workflow completion. "
            f"Latest run status: {matched_run.status} ({matched_run.html_url})"
        )
    raise SystemExit("Timed out while waiting for a repository_dispatch workflow run to appear.")


def main() -> int:
    args = parse_args()
    token = get_token(args.token)
    requested_at = datetime.now(timezone.utc)

    send_dispatch(args, token, requested_at)
    print(
        f"repository_dispatch accepted for {args.owner}/{args.repo} "
        f"with event type '{args.event_type}'."
    )

    if not args.wait:
        print("Use --wait to poll the GitHub Actions run until it completes.")
        return 0

    run = wait_for_run(args, token, requested_at)
    print(f"workflow status: {run.status}")
    print(f"workflow conclusion: {run.conclusion}")
    return 0 if run.conclusion == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
