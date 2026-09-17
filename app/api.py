import json
import os
from typing import Any

from flask import Flask, jsonify, request

from app.location_store import LocationSample, LocationStore


def _team_tokens_from_environment() -> dict[str, str]:
    """Return the internal token-to-team mapping from deployment configuration.

    Individual variables such as ACAMP_GAME_TEAM_TOKEN_GREEN avoid quoting JSON
    in a systemd EnvironmentFile and take precedence over the legacy JSON map.
    """
    individual_tokens = {
        value: key.removeprefix("ACAMP_GAME_TEAM_TOKEN_").lower()
        for key, value in os.environ.items()
        if key.startswith("ACAMP_GAME_TEAM_TOKEN_") and value
    }
    if individual_tokens:
        return individual_tokens

    configured = os.environ.get("ACAMP_GAME_TEAM_TOKENS_JSON", "{}")
    try:
        team_to_token = json.loads(configured)
    except json.JSONDecodeError:
        return {}
    if not isinstance(team_to_token, dict):
        return {}
    return {str(token): str(team_id) for team_id, token in team_to_token.items()}


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_PATH=os.environ.get(
            "ACAMP_GAME_DATABASE_PATH", "/var/lib/acamp-game-api/game.sqlite3"
        ),
        TEAM_TOKENS=_team_tokens_from_environment(),
    )
    if config:
        app.config.update(config)

    @app.get("/health")
    def health():
        return jsonify(
            api_version="v1",
            service="acamp-game-api",
            status="ok",
        )

    @app.post("/v1/location-samples")
    def create_location_sample():
        token = _bearer_token(request.headers.get("Authorization"))
        team_id = app.config["TEAM_TOKENS"].get(token)
        if team_id is None:
            return jsonify(error="invalid team token"), 401

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="JSON object body is required"), 400
        if payload.get("team_id") != team_id:
            return jsonify(error="team token does not match team_id"), 403

        try:
            sample = _location_sample_from(payload)
        except (KeyError, TypeError, ValueError):
            return jsonify(error="invalid location sample"), 400

        result = LocationStore(app.config["DATABASE_PATH"]).add(sample)
        if result.duplicate:
            return jsonify(accepted=True, duplicate=True, event_id=result.event_id)
        return jsonify(accepted=True, event_id=result.event_id), 201

    @app.get("/v1/team/state")
    def team_state():
        token = _bearer_token(request.headers.get("Authorization"))
        team_id = app.config["TEAM_TOKENS"].get(token)
        if team_id is None:
            return jsonify(error="invalid team token"), 401
        return jsonify(LocationStore(app.config["DATABASE_PATH"]).team_state(team_id))

    return app


def _bearer_token(header: str | None) -> str | None:
    prefix = "Bearer "
    if header is None or not header.startswith(prefix):
        return None
    return header[len(prefix) :]


def _location_sample_from(payload: dict[str, Any]) -> LocationSample:
    latitude = float(payload["latitude"])
    longitude = float(payload["longitude"])
    accuracy_m = float(payload["accuracy_m"])
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or accuracy_m < 0:
        raise ValueError("coordinates or accuracy are out of range")
    return LocationSample(
        sample_id=str(payload["sample_id"]),
        team_id=str(payload["team_id"]),
        device_id=str(payload["device_id"]),
        client_time=str(payload["client_time"]),
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
    )


app = create_app()
