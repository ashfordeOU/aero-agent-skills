"""
HFE parameter characterization logic.
ECSS-E-ST-10-11C §4.2.1.1–4.2.1.2: characterize human-machine systems via
interrelated HFE parameters and the standard parameter set.
"""

# Standard HFE parameter categories per ECSS-E-ST-10-11C §4.2.1.2
STANDARD_PARAM_CATEGORIES = {
    "performance",
    "workload",
    "situation_awareness",
    "human_error",
    "training",
    "environment",
    "interface",
    "communication",
}

# Required categories: a parameter set is incomplete if any are absent.
REQUIRED_CATEGORIES = frozenset({
    "performance",
    "workload",
    "situation_awareness",
    "human_error",
})

# Recognized synonyms mapped to their canonical category.
_ALIASES = {
    "task_performance": "performance",
    "accuracy": "performance",
    "speed": "performance",
    "throughput": "performance",
    "mental_workload": "workload",
    "physical_workload": "workload",
    "sa": "situation_awareness",
    "awareness": "situation_awareness",
    "error_probability": "human_error",
    "error_rate": "human_error",
    "error_type": "human_error",
    "training_requirement": "training",
    "lighting": "environment",
    "noise": "environment",
    "vibration": "environment",
    "thermal": "environment",
    "hmi": "interface",
    "display": "interface",
    "control": "interface",
    "controls": "interface",
    "comms": "communication",
    "voice": "communication",
    "data_link": "communication",
}

# Pairwise interrelationships per §4.2.1.1 — stored as frozensets so order
# of the pair does not matter during lookup.
_INTERRELATED_PAIRS = [
    frozenset({"workload", "performance"}),
    frozenset({"workload", "human_error"}),
    frozenset({"situation_awareness", "human_error"}),
    frozenset({"situation_awareness", "performance"}),
    frozenset({"environment", "workload"}),
    frozenset({"interface", "workload"}),
    frozenset({"training", "human_error"}),
    frozenset({"training", "performance"}),
    frozenset({"communication", "situation_awareness"}),
]


def categorize_parameter(param_type):
    """
    Map a raw parameter type string to a standard HFE category name.

    Returns the canonical category string.
    Raises ValueError for unrecognized types.
    Raises TypeError if param_type is not a string.
    """
    if not isinstance(param_type, str):
        raise TypeError(
            f"param_type must be a str, got {type(param_type).__name__}"
        )
    normalized = param_type.strip().lower()
    if normalized in STANDARD_PARAM_CATEGORIES:
        return normalized
    if normalized in _ALIASES:
        return _ALIASES[normalized]
    raise ValueError(
        f"Unrecognized HFE parameter type: '{param_type}'"
    )


def check_parameter_set_completeness(params):
    """
    Check that a parameter set covers all required HFE categories.

    params: list of dicts, each with at minimum a "type" key (str).

    Returns a dict:
        covered  — set of category strings present in the parameter set
        missing  — set of required category strings absent from the set
        findings — list of finding strings (empty means no issues)

    Raises TypeError if params is not a list or an element is not a dict.
    Raises ValueError if any dict is missing the "type" key.
    """
    if not isinstance(params, list):
        raise TypeError(
            f"params must be a list, got {type(params).__name__}"
        )

    covered = set()
    findings = []

    for p in params:
        if not isinstance(p, dict):
            raise TypeError(
                f"Each parameter must be a dict, got {type(p).__name__}"
            )
        if "type" not in p:
            raise ValueError(
                f"Parameter missing required 'type' field: {p!r}"
            )
        try:
            category = categorize_parameter(p["type"])
            covered.add(category)
        except ValueError as exc:
            findings.append(f"FINDING: {exc}")

    missing = set(REQUIRED_CATEGORIES) - covered
    for cat in sorted(missing):
        findings.append(
            f"FINDING: Required HFE category '{cat}' not represented in parameter set"
        )

    return {"covered": covered, "missing": missing, "findings": findings}


def map_parameter_interrelationships(params):
    """
    Map pairwise interrelationships among the HFE categories present.

    params: list of dicts with a "type" key.
    Unrecognized types are silently ignored for this mapping (they will
    have been caught by check_parameter_set_completeness).

    Returns a dict:
        pairs    — list of (category_a, category_b) tuples that are both
                   present AND interrelated per §4.2.1.1
        isolated — sorted list of categories present but with no active
                   interrelationship partner in the set
    """
    present = set()
    for p in params:
        try:
            cat = categorize_parameter(p.get("type", ""))
            present.add(cat)
        except (ValueError, TypeError):
            pass

    active_pairs = []
    for pair_set in _INTERRELATED_PAIRS:
        a, b = tuple(sorted(pair_set))
        if a in present and b in present:
            active_pairs.append((a, b))

    connected = set()
    for a, b in active_pairs:
        connected.add(a)
        connected.add(b)

    isolated = sorted(c for c in present if c not in connected)

    return {"pairs": active_pairs, "isolated": isolated}


def assess_parameter_coverage(params, system_phases):
    """
    Verify that every defined system phase has at least one parameter.

    params: list of dicts, each with "name" (str) and "phase" (str) keys.
    system_phases: list of phase name strings that must be covered.

    Returns a dict:
        phase_coverage  — dict mapping phase -> list of parameter names
        uncovered_phases — list of phases with no parameter assignment
        findings        — list of finding strings
    """
    if not isinstance(system_phases, list):
        raise TypeError(
            f"system_phases must be a list, got {type(system_phases).__name__}"
        )

    phase_coverage = {ph: [] for ph in system_phases}
    findings = []

    for p in params:
        name = p.get("name", "?")
        phase = p.get("phase")
        if phase is None:
            findings.append(
                f"FINDING: Parameter '{name}' has no phase assignment"
            )
            continue
        if phase not in phase_coverage:
            findings.append(
                f"FINDING: Parameter '{name}' references unknown phase '{phase}'"
            )
            continue
        phase_coverage[phase].append(name)

    uncovered = [ph for ph in system_phases if not phase_coverage[ph]]
    for ph in uncovered:
        findings.append(
            f"FINDING: System phase '{ph}' has no HFE parameters assigned"
        )

    return {
        "phase_coverage": phase_coverage,
        "uncovered_phases": uncovered,
        "findings": findings,
    }
