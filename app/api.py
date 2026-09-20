import json
import math
import os
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request

from app.game_store import PersistentGameStore
from app.location_store import LocationSample, LocationStore
from app.session_store import SessionStore


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


def _place_scores_from_environment() -> dict[str, int]:
    prefix = "ACAMP_GAME_PLACE_SCORE_"
    scores = {}
    for key, value in os.environ.items():
        if key.startswith(prefix) and value:
            place_id = key.removeprefix(prefix).lower().replace("_", "-")
            scores[place_id] = int(value)
    return scores


def _scenario_from_environment() -> dict:
    scenario_path = os.environ.get("ACAMP_GAME_SCENARIO_PATH")
    if not scenario_path:
        return {"id": None, "name": None, "places": []}
    with open(scenario_path, "r", encoding="utf-8") as scenario_file:
        return json.load(scenario_file)


def _place_definitions_from_environment() -> dict:
    scenario_path = os.environ.get("ACAMP_GAME_SCENARIO_PATH")
    if not scenario_path:
        return {}
    with open(scenario_path, "r", encoding="utf-8") as scenario_file:
        scenario = json.load(scenario_file)
    return {place["id"]: place for place in scenario.get("places", [])}


def _team_sessions_from_environment() -> dict:
    path = os.environ.get("ACAMP_GAME_TEAM_SESSIONS_PATH")
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as session_file:
        sessions = json.load(session_file)
    directory = os.path.dirname(path)
    for session in sessions.values():
        scenario_path = session.get("scenario_path")
        if scenario_path:
            with open(os.path.join(directory, scenario_path), "r", encoding="utf-8") as scenario_file:
                session["scenario"] = json.load(scenario_file)
    return sessions


def _team_session(app: Flask, team_id: str) -> dict:
    assigned = app.config["TEAM_SESSIONS"].get(team_id)
    if assigned is not None:
        return assigned
    return {
        "game_session_id": app.config["GAME_SESSION_ID"],
        "status": app.config["GAME_STATUS"],
        "scenario": app.config["SCENARIO"],
    }
def _resolved_team_session(app: Flask, team_id: str) -> dict:
    session = dict(_team_session(app, team_id))
    session["status"] = SessionStore(app.config["DATABASE_PATH"]).status_for(
        session["game_session_id"], session["status"]
    )
    return session


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_PATH=os.environ.get(
            "ACAMP_GAME_DATABASE_PATH", "/var/lib/acamp-game-api/game.sqlite3"
        ),
        TEAM_TOKENS=_team_tokens_from_environment(),
        PLACE_SCORES=_place_scores_from_environment(),
        PLACE_DEFINITIONS=_place_definitions_from_environment(),
        SCENARIO=_scenario_from_environment(),
        GAME_SESSION_ID=os.environ.get("ACAMP_GAME_SESSION_ID"),
        GAME_STATUS=os.environ.get("ACAMP_GAME_STATUS", "test"),
        TEAM_SESSIONS=_team_sessions_from_environment(),
        ADMIN_TOKEN=os.environ.get("ACAMP_GAME_ADMIN_TOKEN"),
        MAX_LOCATION_AGE_SECONDS=int(os.environ.get("ACAMP_GAME_MAX_LOCATION_AGE_SECONDS", "300")),
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

    @app.get("/v1/game/definition")
    def game_definition():
        token = _bearer_token(request.headers.get("Authorization"))
        team_id = app.config["TEAM_TOKENS"].get(token)
        if team_id is None:
            return jsonify(error="invalid team token"), 401
        return jsonify(_team_session(app, team_id)["scenario"])

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

    @app.post("/v1/actions")
    def create_action():
        token = _bearer_token(request.headers.get("Authorization"))
        team_id = app.config["TEAM_TOKENS"].get(token)
        if team_id is None:
            return jsonify(error="invalid team token"), 401
        session = _resolved_team_session(app, team_id)
        if session["status"] == "paused":
            return jsonify(error="game session is paused"), 409
        if session["status"] == "finished":
            return jsonify(error="game session is finished"), 409
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get("type") != "claim_place":
            return jsonify(error="unsupported action"), 400
        requested_device_id = payload.get("device_id")
        play_device_id = session.get("play_device_id")
        if play_device_id and requested_device_id != play_device_id:
            return jsonify(error="device is not allowed to claim"), 403
        place_id = payload.get("place_id")
        if not isinstance(place_id, str):
            return jsonify(error="unknown place_id"), 404
        session_places = {
            place["id"]: place for place in session["scenario"].get("places", [])
        }
        place_definition = session_places.get(place_id) or app.config["PLACE_DEFINITIONS"].get(place_id)
        if place_definition is not None:
            score = place_definition["points"]
            latest_location = LocationStore(app.config["DATABASE_PATH"]).team_state(
                team_id, requested_device_id
            )["latest_location"]
            if latest_location is None:
                return jsonify(error="location sample required before claim"), 409
            received_at = datetime.fromisoformat(latest_location["received_at"]).replace(
                tzinfo=timezone.utc
            )
            age_seconds = (datetime.now(timezone.utc) - received_at).total_seconds()
            if age_seconds > app.config["MAX_LOCATION_AGE_SECONDS"]:
                return jsonify(error="location sample is too old"), 409
            distance_m = _distance_m(
                latest_location["latitude"],
                latest_location["longitude"],
                place_definition["latitude"],
                place_definition["longitude"],
            )
            if latest_location["accuracy_m"] > place_definition["radius_m"]:
                return jsonify(error="location accuracy is too low"), 409
            if distance_m > place_definition["radius_m"]:
                return jsonify(error="team is outside place radius", distance_m=round(distance_m)), 409
        elif isinstance(place_id, str) and place_id in app.config["PLACE_SCORES"]:
            score = app.config["PLACE_SCORES"][place_id]
        else:
            return jsonify(error="unknown place_id"), 404
        try:
            requested_session_id = str(payload["game_session_id"])
            action_id = str(payload["action_id"])
        except KeyError:
            return jsonify(error="invalid action"), 400
        game_session_id = session["game_session_id"] or requested_session_id
        if session["game_session_id"] and requested_session_id != game_session_id:
            return jsonify(error="game session does not match team assignment"), 403

        game_store = PersistentGameStore(app.config["DATABASE_PATH"])
        configured_home = session.get("home_place_id")
        if configured_home:
            game_store.set_home_if_missing(game_session_id, team_id, configured_home)
        result = game_store.claim_place(
            game_session_id=game_session_id,
            team_id=team_id,
            place_id=place_id,
            score=score,
            action_id=action_id,
        )
        response = {
            "action_id": action_id,
            "claimed": result.claimed,
            "place_id": place_id,
            "score_delta": result.score_delta,
            "team_score": result.team_score,
            "transferred": result.transferred,
            "home_place_id": result.home_place_id,
        }
        return jsonify(response), 201 if result.claimed else 200

    @app.post("/v1/admin/session/status")
    def set_session_status():
        token = _bearer_token(request.headers.get("Authorization"))
        if not app.config["ADMIN_TOKEN"] or token != app.config["ADMIN_TOKEN"]:
            return jsonify(error="invalid admin token"), 401
        payload = request.get_json(silent=True) or {}
        status = payload.get("status")
        session_id = payload.get("game_session_id")
        reason = payload.get("reason")
        if status not in {"test", "live", "paused", "finished"} or not isinstance(session_id, str) or not isinstance(reason, str) or not reason:
            return jsonify(error="invalid session status change"), 400
        return jsonify(SessionStore(app.config["DATABASE_PATH"]).set_status(session_id, status, reason))

    @app.get("/v1/admin/overview")
    def admin_overview():
        token = _bearer_token(request.headers.get("Authorization"))
        if not app.config["ADMIN_TOKEN"] or token != app.config["ADMIN_TOKEN"]:
            return jsonify(error="invalid admin token"), 401

        teams = []
        for team_id in sorted(set(app.config["TEAM_TOKENS"].values())):
            session = _resolved_team_session(app, team_id)
            location_state = LocationStore(app.config["DATABASE_PATH"]).team_state(team_id)
            game_state = PersistentGameStore(app.config["DATABASE_PATH"]).team_summary(
                session["game_session_id"], team_id
            )
            latest_location = location_state["latest_location"]
            teams.append(
                {
                    "team_id": team_id,
                    "game_session_id": session["game_session_id"],
                    "status": session["status"],
                    "score": game_state["score"],
                    "claimed_places": game_state["claimed_places"],
                    "location_event_count": location_state["location_event_count"],
                    "latest_location_time": (
                        latest_location["client_time"] if latest_location else None
                    ),
                    "latest_location_accuracy_m": (
                        latest_location["accuracy_m"] if latest_location else None
                    ),
                }
            )
        return jsonify(teams=teams)

    @app.get("/v1/team/state")
    def team_state():
        token = _bearer_token(request.headers.get("Authorization"))
        team_id = app.config["TEAM_TOKENS"].get(token)
        if team_id is None:
            return jsonify(error="invalid team token"), 401
        location_state = LocationStore(app.config["DATABASE_PATH"]).team_state(team_id)
        if location_state["latest_location"]:
            location_state["latest_location"].pop("received_at")
        game_state = PersistentGameStore(app.config["DATABASE_PATH"]).team_summary(
            _resolved_team_session(app, team_id)["game_session_id"], team_id
        )
        location_state.update(game_state)
        return jsonify(location_state)

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
def _distance_m(latitude_a, longitude_a, latitude_b, longitude_b) -> float:
    earth_radius_m = 6_371_000
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(math.radians(latitude_a))
        * math.cos(math.radians(latitude_b))
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(math.sqrt(haversine))


app = create_app()
