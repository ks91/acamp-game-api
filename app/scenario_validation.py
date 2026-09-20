def validate_scenario(scenario):
    errors = []
    if not isinstance(scenario, dict):
        return ["scenario must be an object"]
    if not isinstance(scenario.get("id"), str) or not scenario["id"].strip():
        errors.append("scenario id is required")
    if not isinstance(scenario.get("name"), str) or not scenario["name"].strip():
        errors.append("scenario name is required")
    if "intro" in scenario and not isinstance(scenario["intro"], str):
        errors.append("intro must be text")
    places = scenario.get("places")
    if not isinstance(places, list):
        return errors + ["places must be a list"]
    place_ids = set()
    for place in places:
        label = place.get("id", "<missing>") if isinstance(place, dict) else "<invalid>"
        if not isinstance(place, dict):
            errors.append("place must be an object")
            continue
        place_id = place.get("id")
        if not isinstance(place_id, str) or not place_id.strip():
            errors.append("place id is required")
        elif place_id in place_ids:
            errors.append("duplicate place id: {}".format(place_id))
        else:
            place_ids.add(place_id)
        if not isinstance(place.get("name"), str) or not place["name"].strip():
            errors.append("{}: name is required".format(label))
        for field in ("description", "hint", "claim_message"):
            if field in place and not isinstance(place[field], str):
                errors.append("{}: {} must be text".format(label, field))
        latitude = place.get("latitude")
        longitude = place.get("longitude")
        if not isinstance(latitude, (int, float)) or not -90 <= latitude <= 90:
            errors.append("{}: latitude must be between -90 and 90".format(label))
        if not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180:
            errors.append("{}: longitude must be between -180 and 180".format(label))
        if not isinstance(place.get("radius_m"), (int, float)) or place["radius_m"] <= 0:
            errors.append("{}: radius_m must be positive".format(label))
        if not isinstance(place.get("points"), int) or place["points"] <= 0:
            errors.append("{}: points must be positive".format(label))
    return errors
