# Six-team prototype workflow

## Source layout

Keep shared platform code on `main`. Give each team a separate scenario file:

```text
scenarios/prototypes/<team-id>/scenario.json
```

A team proposes changes in its Discord thread. The thread's PAT/Hermes helps turn the idea into a small scenario change and a field-test record. A staff integrator reviews and merges changes to `main`; the AWS VM only pulls `main` and never receives direct edits.

Separate files avoid six teams editing the same JSON. Use one `game_session_id` per prototype, for example `prototype-green-2026-09-20`, so scores and claims cannot mix between teams.

## Shared-world integration

Before a common game, copy or combine the tested ideas into one versioned shared scenario, such as `scenarios/tokyo-full-v1.json`. Staff freeze that scenario at game start. Any live change is recorded with time, reason, and the applicable rule version.

## Session status

`ACAMP_GAME_STATUS` controls whether claims are accepted:

```text
test      field trial; claims accepted
live      common play; claims accepted
paused    claims rejected
finished  claims rejected
```

Set the value in `/etc/acamp-game-api.env` and restart `acamp-game-api`. Location samples may still be accepted while claims are paused, so staff can diagnose connectivity without changing scores.
