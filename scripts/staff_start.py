#!/usr/bin/env python3
"""Reset one team/mode and declare the new round live for staff."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from admin import admin_request


MODE_LABELS = {"center_test": "センター棟テスト", "tokyo": "東京版"}
TEAM_LABELS = {
    "green": "グリーン", "blue": "ブルー", "red": "レッド",
    "yellow": "イエロー", "purple": "パープル", "pink": "ピンク",
}


def start_team_mode(registry, team_id, mode, reason, request=admin_request):
    try:
        session_id = registry[team_id]["modes"][mode]["game_session_id"]
    except KeyError as error:
        raise ValueError("unknown team or mode") from error
    request(
        "/v1/admin/session/reset",
        method="POST",
        payload={"game_session_id": session_id, "reason": reason},
    )
    request(
        "/v1/admin/session/status",
        method="POST",
        payload={"game_session_id": session_id, "status": "live", "reason": reason},
    )
    return "【{}・{}】を最初から開始しました。".format(
        TEAM_LABELS.get(team_id, team_id), MODE_LABELS.get(mode, mode)
    )


def start_team_modes(registry, team_ids, mode, reason, request=admin_request):
    missing = ["{}:{}".format(team_id, mode) for team_id in team_ids if mode not in registry.get(team_id, {}).get("modes", {})]
    if missing:
        raise ValueError("missing registered mode(s): " + ", ".join(missing))
    return [start_team_mode(registry, team_id, mode, reason, request=request) for team_id in team_ids]


def main():
    parser = argparse.ArgumentParser(description="Start a fresh team game round")
    parser.add_argument("--team", required=True, choices=sorted(TEAM_LABELS), nargs="+")
    parser.add_argument("--mode", required=True, choices=sorted(MODE_LABELS))
    parser.add_argument("--reason", default="スタッフが新しいラウンドを開始")
    args = parser.parse_args()
    registry_path = os.environ["ACAMP_GAME_TEAM_SESSIONS_PATH"]
    with Path(registry_path).open(encoding="utf-8") as source:
        registry = json.load(source)
    for message in start_team_modes(registry, args.team, args.mode, args.reason):
        print(message)


if __name__ == "__main__":
    main()
