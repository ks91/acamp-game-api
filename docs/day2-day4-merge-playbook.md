# Day 2–4 location-game merge playbook

## Day 2: make a testable prototype, not a complete game

Each team works in its own `scenarios/prototypes/<team>/scenario.json` and Discord thread. By the end of the day, write one prototype card:

```text
Team:
Player experience we want:
One core loop:
One location-based action:
What players receive or learn:
What we observed in the Olympic Center test:
What failed or remains unknown:
What must exist for Day 4:
What can be omitted:
```

A prototype may use staff-facilitated or paper steps for mechanics not yet in the shared app. Mark those clearly as `proposal`, not implemented behavior.

## Day 3: curate one coherent common game

Do not merge all features. Choose one shared player loop and admit team ideas only when they strengthen it.

1. Freeze Day 2 prototype files as evidence.
2. Compare cards using: player clarity, safety, Metro-time feasibility, observability, and compatibility with a shared score/state model.
3. Select one common world, a small number of action types, and a common win condition.
4. Give each team contribution a role: faction, route, information source, quest, item, or finale.
5. Implement and test only the selected common mechanics.
6. Create one shared Day 4 scenario and map every team to its common `game_session_id`.

## Day 4: freeze, play, observe

Before departure, set the shared scenario to `live`, verify each Cellular iPad's session/device config, and verify admin overview. Do not change rules casually during play. Use the admin CLI to pause when safety, weather, or transport requires it; record the reason. Every team has its own exploration device, but teams need not co-locate for the game to progress.

## Shared-session registry shape

For Day 4, all teams point to one session and one scenario; team IDs still keep scores and claims separate.

```json
{
  "green": {"game_session_id": "day4-tokyo-1", "status": "live", "scenario_path": "tokyo-day4-1.json", "play_device_id": "green-ipad"},
  "blue": {"game_session_id": "day4-tokyo-1", "status": "live", "scenario_path": "tokyo-day4-1.json", "play_device_id": "blue-ipad"}
}
```

Use the same pattern for every team. Create a separate Day 5/Day 22 replay session instead of rewriting Day 4 history.
