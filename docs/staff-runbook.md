# Staff runbook: Academy Camp location game

Use the staff CLI on the AWS VM after loading `/etc/acamp-game-api.env`. Never put tokens in GitHub, an iPad, or Discord.

```bash
sudo -i
set -a
. /etc/acamp-game-api.env
set +a
python3 /var/www/acamp-game-api/scripts/admin.py overview
```

## Stop or resume a session

```bash
python3 /var/www/acamp-game-api/scripts/admin.py status \
  --session <session-id> --status paused --reason "<concrete reason>"
```

Confirm with `overview`. Resume a prototype with `--status test`; resume an approved common game with `--status live`. `finished` ends claims; use it only when the game is over.

## GPS is unavailable or too inaccurate

Do not tell a team to retry while crossing roads or riding transit. Ask them to stop at a safe outdoor point, open `game_app.py`, and press **現在地を更新**. A place claim requires a location received within five minutes and with accuracy no worse than the place radius.

## Connectivity failure

`game_app.py` saves an unsent location event locally and retries it on the next location update. Do not manually edit `pending-events.json`. If the team needs to play before connectivity returns, use an agreed narrative/offline rule; do not award server scores manually without an explicit recorded staff decision.

## iPad app fails after an update

1. Fully quit Pythonista.
2. Pull the whole repository in Working Copy.
3. Relaunch Pythonista from the linked repository folder.
4. Run `game_app.py`.

Never copy only `app.py` or edit a cached Pythonista copy.

## API is unavailable

Pause affected sessions first if the service is still reachable. Then check:

```bash
sudo systemctl status acamp-game-api --no-pager
sudo systemctl status apache2 --no-pager
```

For a code update, stop the service, pull only `main` with `git pull --ff-only`, then start it. Do not edit source files directly on the VM.

## Weather, transport, or safety change

Pause the affected session. Move to the prepared smaller-area or indoor scenario only after staff agree on the replacement session and record the reason through the admin CLI. Safety decisions override scoring and schedules.

## After any incident

Record: session ID, time, observed issue, action taken, result, and the next rule or software improvement to test. This is the evidence for the 22nd improvement round.
