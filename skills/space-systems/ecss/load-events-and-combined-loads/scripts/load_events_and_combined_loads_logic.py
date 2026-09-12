"""
Load events and load combination rules for space structures.
Implements the enumeration and combination procedure of ECSS-E-ST-32C
clauses 4.2.5 (load events) and 4.2.6 (combined loads and interaction rules).
"""

VALID_PHASES = {
    "ground_handling",
    "transportation",
    "launch",
    "ascent",
    "separation",
    "on_orbit",
    "re_entry",
    "landing",
}

VALID_LOAD_TYPES = {
    "quasi_static",
    "dynamic",
    "thermal",
    "pressure",
    "acoustic",
    "shock",
    "random_vibration",
}

# Minimum required load types per mission phase (ECSS-E-ST-32C clause 4.2.5).
REQUIRED_LOAD_TYPES_BY_PHASE = {
    "ground_handling": {"quasi_static", "thermal"},
    "transportation": {"quasi_static", "dynamic", "shock"},
    "launch": {"quasi_static", "acoustic", "random_vibration", "thermal"},
    "ascent": {"quasi_static", "acoustic", "random_vibration", "thermal"},
    "separation": {"quasi_static", "shock"},
    "on_orbit": {"quasi_static", "thermal"},
    "re_entry": {"quasi_static", "thermal", "pressure"},
    "landing": {"quasi_static", "shock", "dynamic"},
}

# All phases that must appear at least once in a complete load event set.
REQUIRED_PHASES = set(VALID_PHASES)

# Default ultimate factor for metallic isotropic structures (ECSS-E-ST-32C).
DEFAULT_ULTIMATE_FACTOR = 1.5


def validate_load_event(event: dict) -> dict:
    """
    Validate a load event dict.

    Returns the validated dict.
    Raises ValueError for any constraint violation.
    """
    name = event.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("Load event must have a non-empty string 'name'.")

    phase = event.get("phase")
    if phase not in VALID_PHASES:
        raise ValueError(
            f"Unknown mission phase '{phase}'. "
            f"Expected one of: {sorted(VALID_PHASES)}."
        )

    load_types = event.get("load_types")
    if not load_types or not isinstance(load_types, (list, set)):
        raise ValueError("Load event must have a non-empty 'load_types' list.")

    unknown = set(load_types) - VALID_LOAD_TYPES
    if unknown:
        raise ValueError(
            f"Unknown load types: {sorted(unknown)}. "
            f"Expected a subset of: {sorted(VALID_LOAD_TYPES)}."
        )

    limit_load = event.get("limit_load")
    if limit_load is None or not isinstance(limit_load, (int, float)):
        raise ValueError("Load event must have a numeric 'limit_load'.")
    if limit_load < 0:
        raise ValueError("'limit_load' must be non-negative.")

    return event


def categorize_load_event(event: dict) -> str:
    """Return the mission phase for a validated load event."""
    validate_load_event(event)
    return event["phase"]


def get_required_load_types(phase: str) -> set:
    """Return the minimum required load types for a given mission phase."""
    if phase not in VALID_PHASES:
        raise ValueError(
            f"Unknown mission phase '{phase}'. "
            f"Expected one of: {sorted(VALID_PHASES)}."
        )
    return set(REQUIRED_LOAD_TYPES_BY_PHASE[phase])


def check_load_type_coverage(event: dict) -> list:
    """
    Compare a load event's load types against the minimum required for its phase.

    Returns a sorted list of missing load type names; empty list means compliant.
    """
    validate_load_event(event)
    required = REQUIRED_LOAD_TYPES_BY_PHASE[event["phase"]]
    actual = set(event["load_types"])
    return sorted(required - actual)


def compute_design_load(loads: list, combination_factors: dict) -> float:
    """
    Compute a combined design load by applying combination factors to each
    load component and summing the contributions.

    loads: list of {"load_type": str, "value": float}
    combination_factors: dict mapping load_type to a numeric factor;
        load types absent from the dict receive a factor of 0.0.

    Returns the combined scalar design load value.
    Raises ValueError if loads is empty or any item is malformed.
    """
    if not loads:
        raise ValueError("'loads' must not be empty.")

    total = 0.0
    for item in loads:
        lt = item.get("load_type")
        val = item.get("value")
        if lt is None or val is None:
            raise ValueError(
                "Each load item must have 'load_type' (str) and 'value' (float)."
            )
        factor = combination_factors.get(lt, 0.0)
        total += factor * float(val)

    return total


def apply_ultimate_factor(
    limit_load: float, ultimate_factor: float = DEFAULT_ULTIMATE_FACTOR
) -> float:
    """
    Scale a limit load to ultimate load.

    Returns limit_load * ultimate_factor.
    Raises ValueError for a non-positive ultimate factor or negative limit load.
    """
    if limit_load < 0:
        raise ValueError("'limit_load' must be non-negative.")
    if ultimate_factor <= 0:
        raise ValueError("'ultimate_factor' must be positive.")
    return limit_load * ultimate_factor


def check_event_coverage(
    events: list, required_phases: set = None
) -> tuple:
    """
    Verify that all required mission phases appear in the events list.

    Returns (covered: bool, missing_phases: sorted list).
    """
    if required_phases is None:
        required_phases = REQUIRED_PHASES

    present_phases = set()
    for event in events:
        validate_load_event(event)
        present_phases.add(event["phase"])

    missing = sorted(required_phases - present_phases)
    return (len(missing) == 0, missing)


def find_governing_load_case(combinations: list) -> dict:
    """
    Return the combination dict with the highest 'design_load' value.

    Each item must have 'name' (str) and 'design_load' (float).
    Raises ValueError if combinations is empty.
    """
    if not combinations:
        raise ValueError("'combinations' must not be empty.")
    return max(combinations, key=lambda c: c["design_load"])
