#!/usr/bin/env python3
"""Staff CLI for the Academy Camp location-game admin API."""

import argparse
import json
import os
from urllib.request import Request, urlopen

from admin_overview import format_overview


def admin_request(path, method="GET", payload=None):
    token = os.environ["ACAMP_GAME_ADMIN_TOKEN"]
    base_url = os.environ.get("ACAMP_GAME_API_BASE_URL", "https://game-api.academy-camp.org")
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        base_url.rstrip("/") + path,
        data=body,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Academy Camp location-game staff CLI")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("overview", help="show all teams in a readable table")
    status_parser = commands.add_parser("status", help="change a game session status")
    status_parser.add_argument("--session", required=True, help="game session ID")
    status_parser.add_argument(
        "--status", required=True, choices=["test", "live", "paused", "finished"]
    )
    status_parser.add_argument("--reason", required=True, help="reason retained in the audit log")
    args = parser.parse_args()

    if args.command == "overview":
        print(format_overview(admin_request("/v1/admin/overview")))
        return

    result = admin_request(
        "/v1/admin/session/status",
        method="POST",
        payload={
            "game_session_id": args.session,
            "status": args.status,
            "reason": args.reason,
        },
    )
    print(
        "{}: 状態 = {}\n理由: {}\n記録時刻: {}".format(
            result["game_session_id"],
            result["status"],
            result["reason"],
            result["occurred_at"],
        )
    )


if __name__ == "__main__":
    main()
