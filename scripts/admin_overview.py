#!/usr/bin/env python3
"""Print the token-protected admin overview as a staff-readable table."""

import json
import os
from urllib.request import Request, urlopen


def format_overview(payload):
    lines = ["班 | 状態 | 得点 | 獲得 | 位置送信 | 最終送信 | GPS精度"]
    lines.append("---|---|---:|---|---:|---|---")
    for team in payload["teams"]:
        places = ", ".join(team["claimed_places"]) or "—"
        last_time = team["latest_location_time"] or "—"
        accuracy = team["latest_location_accuracy_m"]
        accuracy_text = "—" if accuracy is None else "{:.1f}m".format(accuracy)
        lines.append(
            "{team_id} | {status} | {score} | {places} | {location_event_count} | {last_time} | {accuracy}".format(
                places=places, last_time=last_time, accuracy=accuracy_text, **team
            )
        )
    return "\n".join(lines)


def main():
    token = os.environ["ACAMP_GAME_ADMIN_TOKEN"]
    base_url = os.environ.get("ACAMP_GAME_API_BASE_URL", "https://game-api.academy-camp.org")
    request = Request(
        base_url.rstrip("/") + "/v1/admin/overview",
        headers={"Authorization": "Bearer " + token},
    )
    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    print(format_overview(payload))


if __name__ == "__main__":
    main()
