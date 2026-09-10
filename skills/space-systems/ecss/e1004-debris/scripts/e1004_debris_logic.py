"""Deterministic logic for ECSS-E-ST-10-04C 10.2.2.1 debris flux model selection.

Offline, stdlib-only module backing the e1004-debris skill leaf: checking a
mission's orbit/epoch envelope, selecting a debris flux model (MASTER-class
or ORDEM-class) whose declared validity envelope covers that mission
envelope, building a complete model run request, and flagging when a prior
result needs re-assessment due to epoch drift or an orbit change.
"""

MODEL_FAMILIES = frozenset({"MASTER", "ORDEM"})

ENVELOPE_FIELDS = ("altitude_km", "inclination_deg", "epoch_year", "diameter_mm")


def validate_envelope(envelope: dict) -> list:
    """Check a mission or model envelope dict for completeness and sanity.

    Each of ENVELOPE_FIELDS must map to a (low, high) pair with low <= high.
    Returns a list of human-readable issue strings; an empty list means the
    envelope is fit to use in a coverage check.
    """
    issues = []
    for field in ENVELOPE_FIELDS:
        value = envelope.get(field)
        if value is None:
            issues.append(f"missing envelope field '{field}'")
            continue
        low, high = value
        if low > high:
            issues.append(
                f"envelope field '{field}' has min {low} greater than max {high}"
            )
    return issues


def envelope_covers(model_envelope: dict, mission_envelope: dict) -> list:
    """Check whether model_envelope fully contains mission_envelope.

    For every field in ENVELOPE_FIELDS, the mission's (low, high) range must
    fall entirely within the model's declared (low, high) range. Returns a
    list of gap descriptions; an empty list means full coverage.
    """
    gaps = []
    for field in ENVELOPE_FIELDS:
        model_low, model_high = model_envelope[field]
        mission_low, mission_high = mission_envelope[field]
        if mission_low < model_low or mission_high > model_high:
            gaps.append(
                f"'{field}' mission range ({mission_low}, {mission_high}) "
                f"exceeds model declared range ({model_low}, {model_high})"
            )
    return gaps


def select_model(candidates: list, mission_envelope: dict, mandated_family=None):
    """Select a debris flux model whose envelope covers the mission envelope.

    candidates: list of {"name": str, "family": "MASTER"|"ORDEM",
    "envelope": {...ENVELOPE_FIELDS...}}. Only a candidate from a
    recognised family whose declared envelope fully covers the mission
    envelope is eligible. If mandated_family is given, eligibility is
    further restricted to that family. Among eligible candidates, the
    selection is deterministic: alphabetically first by name, since either
    family is equally acceptable per the clause when both cover the
    envelope. Returns (selected_name, issues); selected_name is None when
    issues is non-empty.
    """
    issues = validate_envelope(mission_envelope)
    if issues:
        return None, issues

    covering = []
    for candidate in candidates:
        if candidate.get("family") not in MODEL_FAMILIES:
            continue
        if envelope_covers(candidate["envelope"], mission_envelope):
            continue
        covering.append(candidate)

    if mandated_family is not None:
        covering = [c for c in covering if c["family"] == mandated_family]

    if not covering:
        reason = "no candidate model's declared envelope covers the mission envelope"
        if mandated_family is not None:
            reason += f" within the mandated family '{mandated_family}'"
        return None, [reason]

    covering.sort(key=lambda c: c["name"])
    return covering[0]["name"], []


def build_run_request(diameter_thresholds_mm, exposure_days, surface_id):
    """Build a complete debris flux model run request, or report issues.

    diameter_thresholds_mm must be a non-empty, strictly ascending sequence
    of strictly positive values. exposure_days must be > 0. surface_id must
    be non-empty. Returns (request_dict_or_None, issues); request_dict is
    None when issues is non-empty.
    """
    issues = []
    if not diameter_thresholds_mm:
        issues.append("diameter_thresholds_mm must list at least one threshold")
    else:
        if any(d <= 0 for d in diameter_thresholds_mm):
            issues.append("diameter thresholds must be strictly positive")
        if list(diameter_thresholds_mm) != sorted(diameter_thresholds_mm):
            issues.append("diameter thresholds must be given in ascending order")

    if exposure_days <= 0:
        issues.append("exposure_days must be > 0")

    if not surface_id:
        issues.append("surface_id must be provided")

    if issues:
        return None, issues

    return (
        {
            "diameter_thresholds_mm": list(diameter_thresholds_mm),
            "exposure_days": exposure_days,
            "surface_id": surface_id,
        },
        [],
    )


def needs_reassessment(
    model_epoch_max_year: int, mission_end_year: int, orbit_changed: bool
) -> bool:
    """Flag when a prior debris-flux result must be re-assessed.

    Re-assessment is required if the mission's analysis end-year now
    exceeds the selected model's declared epoch validity, or if the orbit
    regime changed (e.g. a maneuver) after the result was produced.
    """
    return mission_end_year > model_epoch_max_year or orbit_changed
