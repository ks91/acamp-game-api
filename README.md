# acamp-game-api

Academy Camp 2026 position-game API and game-state service.

## Initial contract

- `GET /health` returns the service health status.
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

## Repository safety

Never commit production tokens, private keys, `.env` files, or game databases/position logs.
