#!/usr/bin/env python3
"""Validate one location-game scenario JSON file before deployment."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scenario_validation import validate_scenario


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 scripts/validate_scenario.py <scenario.json>")
    with open(sys.argv[1], encoding="utf-8") as handle:
        errors = validate_scenario(json.load(handle))
    if errors:
        print("INVALID")
        for error in errors:
            print("- " + error)
        raise SystemExit(1)
    print("OK: " + sys.argv[1])


if __name__ == "__main__":
    main()
