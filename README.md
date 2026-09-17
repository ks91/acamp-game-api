# acamp-game-api

Academy Camp 2026 position-game API and game-state service.

## Initial contract

- `GET /health` returns the service health status.
- `POST /v1/location-samples` accepts an authenticated team-device location sample and records it as an event.
- `POST /v1/actions` supports a server-scored `claim_place` action; claims are idempotent per team, place, and game session.
- `GET /v1/team/state` returns the authenticated team's latest location state.
- A spot claim is idempotent for `(game_session_id, team_id, place_id)`.
- The game server, not the iPad, is the authority for a successful claim and its score.

## Local development

The production VM is expected to use Python 3.10.12. Create an isolated environment and install pinned dependencies:

```bash
uv venv --python 3.10.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/gunicorn --bind 127.0.0.1:8000 'app.api:app'
```

Then request `http://127.0.0.1:8000/health`.

## Deployment target

The AWS VM checkout target is `/var/www/acamp-game-api`. Runtime configuration and all credentials stay outside this repository.

To permit team-device check-ins, set a root-owned environment file such as `/etc/acamp-game-api.env` and reference it from the systemd service with `EnvironmentFile=/etc/acamp-game-api.env`:

```bash
ACAMP_GAME_DATABASE_PATH=/var/lib/acamp-game-api/game.sqlite3
ACAMP_GAME_TEAM_TOKEN_GREEN=replace-with-a-long-random-token
ACAMP_GAME_SCENARIO_PATH=/var/www/acamp-game-api/scenarios/fujisawa-test-1.json
ACAMP_GAME_SESSION_ID=fujisawa-test-1
ACAMP_GAME_STATUS=test
ACAMP_GAME_ADMIN_TOKEN=replace-with-a-separate-long-random-token
```

Use one `ACAMP_GAME_TEAM_TOKEN_<TEAM_ID>` variable per team. This avoids JSON quoting in systemd environment files. Never commit this file or copy its values into Discord.

## Admin overview

`GET /v1/admin/overview` requires `Authorization: Bearer <ACAMP_GAME_ADMIN_TOKEN>`. It returns each team's session ID, operational status, score, claimed place IDs, location-event count, and latest sample time/accuracy. It intentionally omits raw coordinates; use a separate, explicitly designed staff-only diagnostic endpoint if coordinates become operationally necessary.

## Scenario places

Set `ACAMP_GAME_SCENARIO_PATH` to a Git-managed scenario JSON file. Coordinates use **WGS 84 decimal degrees**: JSON numbers, no `°` symbols, no degrees/minutes/seconds. Latitude is north-positive; longitude is east-positive. Five decimal places are roughly metre-level precision, so `35.33870` and `139.48880` are suitable inputs; the gameplay radius, not excess decimal digits, determines practical precision.

Each place uses a circle centered on `latitude` / `longitude`; the server compares it to the team's latest submitted location before allowing a claim.

```json
{
  "id": "time-site",
  "name": "時間の結節点",
  "latitude": 35.3387,
  "longitude": 139.4888,
  "radius_m": 40,
  "points": 120
}
```

## Repository safety

Never commit production tokens, private keys, `.env` files, or game databases/position logs.
