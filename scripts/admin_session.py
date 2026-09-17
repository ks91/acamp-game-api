#!/usr/bin/env python3
"""Change a location-game session status through the protected admin API."""

import argparse
import json
import os
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description="Change one game session's status")
    parser.add_argument("--session", required=True, help="game session ID")
    parser.add_argument(
        "--status", required=True, choices=["test", "live", "paused", "finished"]
    )
    parser.add_argument("--reason", required=True, help="reason recorded in the audit log")
    args = parser.parse_args()

    token = os.environ["ACAMP_GAME_ADMIN_TOKEN"]
    base_url = os.environ.get("ACAMP_GAME_API_BASE_URL", "https://game-api.academy-camp.org")
    body = json.dumps(
        {"game_session_id": args.session, "status": args.status, "reason": args.reason}
    ).encode("utf-8")
    request = Request(
        base_url.rstrip("/") + "/v1/admin/session/status",
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
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
