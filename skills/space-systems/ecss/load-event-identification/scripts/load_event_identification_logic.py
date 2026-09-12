"""
Load event identification logic — ECSS-E-ST-32C clause 7.2.1.

Enumerates and validates load events across all mission phases:
assembly, test, flight, and ground operations.
"""

VALID_PHASES = frozenset({"assembly", "test", "flight", "ground_ops"})

REQUIRED_PHASES = frozenset({"assembly", "test", "flight", "ground_ops"})

VALID_LOAD_TYPES = frozenset({
    "quasi_static",
    "dynamic",
    "thermal",
    "pressure",
    "acoustic",
    "shock",
})

MANDATORY_FLIGHT_SUBTYPES = frozenset({"launch", "ascent", "on_orbit", "separation"})


def validate_event(event):
    """
    Validate a single load event dict.

    Required keys: name (str), phase (str in VALID_PHASES),
    load_types (non-empty list drawn from VALID_LOAD_TYPES).

    Returns a list of error strings; empty list means the event is valid.
    """
    if not isinstance(event, dict):
        return ["event must be a dict"]

    errors = []
    required_keys = {"name", "phase", "load_types"}
    missing_keys = required_keys - set(event.keys())
    if missing_keys:
        errors.append("missing required keys: " + ", ".join(sorted(missing_keys)))

    if "name" in event and not isinstance(event["name"], str):
        errors.append("name must be a string")
    if "name" in event and isinstance(event["name"], str) and not event["name"].strip():
        errors.append("name must not be blank")

    if "phase" in event:
        if event["phase"] not in VALID_PHASES:
            errors.append(
                "unknown phase '{}'; must be one of: {}".format(
                    event["phase"], ", ".join(sorted(VALID_PHASES))
                )
            )

    if "load_types" in event:
        lt = event["load_types"]
        if not isinstance(lt, list) or len(lt) == 0:
            errors.append("load_types must be a non-empty list")
        else:
            unknown = sorted(set(lt) - VALID_LOAD_TYPES)
            if unknown:
                errors.append(
                    "unknown load types: " + ", ".join(unknown)
                )

    return errors


def categorize_events_by_phase(events):
    """
    Group a list of load event dicts by their phase field.

    Only events whose phase is in VALID_PHASES are included.
    Returns a dict mapping each valid phase to a (possibly empty) list of events.
    """
    result = {phase: [] for phase in VALID_PHASES}
    for event in events:
        phase = event.get("phase")
        if phase in VALID_PHASES:
            result[phase].append(event)
    return result


def find_missing_phases(events):
    """
    Return the set of required phases that have no valid event.

    Considers only events whose phase is in REQUIRED_PHASES.
    """
    covered = {event.get("phase") for event in events} & REQUIRED_PHASES
    return REQUIRED_PHASES - covered


def find_missing_flight_subtypes(events):
    """
    Check that flight events collectively cover all mandatory flight subtypes.

    A subtype is considered covered when its keyword appears in the event name
    (case-insensitive substring match).

    Returns the set of mandatory flight subtypes not found.
    """
    flight_events = [e for e in events if e.get("phase") == "flight"]
    found = set()
    for event in flight_events:
        name_lower = event.get("name", "").lower()
        for subtype in MANDATORY_FLIGHT_SUBTYPES:
            if subtype in name_lower:
                found.add(subtype)
    return MANDATORY_FLIGHT_SUBTYPES - found


def identify_load_events(events):
    """
    Main entry point for load event identification.

    Accepts a list of load event dicts. Each dict must contain:
      - name      : str  — unique human-readable label
      - phase     : str  — one of VALID_PHASES
      - load_types: list — non-empty subset of VALID_LOAD_TYPES

    Returns a result dict:
      valid                  : bool — True only when all events pass validation
                                      and all required phases are covered
      events_by_phase        : dict — valid events grouped by phase
      missing_phases         : set  — required phases with no valid event
      missing_flight_subtypes: set  — mandatory flight subtypes not represented
      validation_errors      : list — [(index, [error_str, ...]), ...]
      total_events           : int
      valid_event_count      : int
    """
    if not isinstance(events, list):
        raise TypeError("events must be a list, got: " + type(events).__name__)

    validation_errors = []
    invalid_indices = set()
    for i, event in enumerate(events):
        errs = validate_event(event)
        if errs:
            validation_errors.append((i, errs))
            invalid_indices.add(i)

    valid_events = [e for i, e in enumerate(events) if i not in invalid_indices]

    events_by_phase = categorize_events_by_phase(valid_events)
    missing_phases = find_missing_phases(valid_events)
    missing_flight_subtypes = find_missing_flight_subtypes(valid_events)

    overall_valid = (len(validation_errors) == 0 and len(missing_phases) == 0)

    return {
        "valid": overall_valid,
        "events_by_phase": events_by_phase,
        "missing_phases": missing_phases,
        "missing_flight_subtypes": missing_flight_subtypes,
        "validation_errors": validation_errors,
        "total_events": len(events),
        "valid_event_count": len(valid_events),
    }
