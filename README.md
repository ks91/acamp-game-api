# acamp-game-api

Academy Camp 2026 position-game API and game-state service.

## Initial contract

- `GET /health` returns the service health status.
- `POST /v1/location-samples` accepts an authenticated team-device location sample and records it as an event.
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
```

Use one `ACAMP_GAME_TEAM_TOKEN_<TEAM_ID>` variable per team. This avoids JSON quoting in systemd environment files. Never commit this file or copy its values into Discord.

## Repository safety

Never commit production tokens, private keys, `.env` files, or game databases/position logs.
