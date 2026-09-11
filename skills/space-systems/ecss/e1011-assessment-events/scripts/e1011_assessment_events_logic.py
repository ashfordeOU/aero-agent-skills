"""
ECSS-E-ST-10-11C §4.10.2 assessment event logic.

Implements review type validation, milestone coverage checking,
finding lifecycle management, and gate readiness verification for
crew hardware assessment events (usability, design, crew-station).

All functions are pure and return new objects; no mutation of inputs.
"""

REVIEW_TYPES = frozenset({"usability", "design", "crew-station"})

MILESTONE_ORDER = ["PDR", "CDR", "QR", "AR", "ORR"]

REQUIRED_REVIEWS_BY_MILESTONE = {
    "PDR": frozenset({"design"}),
    "CDR": frozenset({"design", "usability", "crew-station"}),
    "QR":  frozenset({"usability", "crew-station"}),
    "AR":  frozenset({"crew-station"}),
    "ORR": frozenset({"usability"}),
}

HARDWARE_CATEGORIES = frozenset({
    "interface", "display", "control", "seat", "tool", "suit", "habitat",
})

HARDWARE_REVIEW_MAP = {
    "interface": frozenset({"usability", "design"}),
    "display":   frozenset({"usability", "design"}),
    "control":   frozenset({"usability", "design", "crew-station"}),
    "seat":      frozenset({"crew-station", "design"}),
    "tool":      frozenset({"usability", "design"}),
    "suit":      frozenset({"crew-station", "design"}),
    "habitat":   frozenset({"usability", "design", "crew-station"}),
}

FINDING_SEVERITY_LEVELS = frozenset({"critical", "major", "minor", "observation"})


class ValidationError(ValueError):
    """Raised when a supplied value fails a domain constraint."""


def validate_review_type(review_type: str) -> str:
    """Return review_type unchanged if valid; raise ValidationError otherwise."""
    if review_type not in REVIEW_TYPES:
        raise ValidationError(
            f"Unknown review type '{review_type}'. "
            f"Expected one of: {sorted(REVIEW_TYPES)}"
        )
    return review_type


def validate_milestone(milestone: str) -> str:
    """Return milestone unchanged if valid; raise ValidationError otherwise."""
    if milestone not in MILESTONE_ORDER:
        raise ValidationError(
            f"Unknown milestone '{milestone}'. "
            f"Expected one of: {MILESTONE_ORDER}"
        )
    return milestone


def validate_hardware_category(category: str) -> str:
    """Return category unchanged if valid; raise ValidationError otherwise."""
    if category not in HARDWARE_CATEGORIES:
        raise ValidationError(
            f"Unknown hardware category '{category}'. "
            f"Expected one of: {sorted(HARDWARE_CATEGORIES)}"
        )
    return category


def reviews_for_hardware(category: str) -> frozenset:
    """Return the set of review types applicable to a given hardware category."""
    validate_hardware_category(category)
    return HARDWARE_REVIEW_MAP[category]


def required_reviews_for_milestone(milestone: str) -> frozenset:
    """Return the set of review types required at the given programme milestone."""
    validate_milestone(milestone)
    return REQUIRED_REVIEWS_BY_MILESTONE.get(milestone, frozenset())


def check_milestone_coverage(scheduled: dict) -> list:
    """
    Verify that every required review type is scheduled at each milestone.

    :param scheduled: mapping of milestone -> iterable of scheduled review types
    :return: list of gap dicts {'milestone': str, 'missing': list}; empty = compliant
    """
    gaps = []
    for milestone in MILESTONE_ORDER:
        required = REQUIRED_REVIEWS_BY_MILESTONE.get(milestone, frozenset())
        if not required:
            continue
        actual = frozenset(scheduled.get(milestone, []))
        missing = required - actual
        if missing:
            gaps.append({"milestone": milestone, "missing": sorted(missing)})
    return gaps


def reviews_due_before_gate(milestone: str, scheduled: dict) -> list:
    """
    Return coverage gaps at every milestone up to and including the given gate.

    :param milestone: the gate milestone to check readiness for
    :param scheduled: mapping of milestone -> iterable of scheduled review types
    :return: list of gap dicts {'milestone': str, 'missing': list}
    """
    validate_milestone(milestone)
    gate_idx = MILESTONE_ORDER.index(milestone)
    scoped = MILESTONE_ORDER[: gate_idx + 1]
    # check_milestone_coverage() audits every milestone in MILESTONE_ORDER, so
    # scope its result to the milestones up to and including this gate —
    # otherwise a PDR gate reports gaps at QR/AR/ORR that are not due yet.
    return [g for g in check_milestone_coverage(scheduled) if g["milestone"] in scoped]


def add_finding(findings: dict, finding_id: str, description: str, severity: str) -> dict:
    """
    Register a new finding from a review event.

    Returns a new findings dict with the entry added; does not mutate the input.
    """
    if finding_id in findings:
        raise ValidationError(f"Finding '{finding_id}' already exists.")
    if severity not in FINDING_SEVERITY_LEVELS:
        raise ValidationError(
            f"Unknown severity '{severity}'. "
            f"Expected one of: {sorted(FINDING_SEVERITY_LEVELS)}"
        )
    if not description.strip():
        raise ValidationError("Finding description must not be empty.")
    return {
        **findings,
        finding_id: {
            "description": description,
            "severity": severity,
            "status": "open",
            "resolution": None,
        },
    }


def close_finding(findings: dict, finding_id: str, resolution: str) -> dict:
    """
    Mark an existing finding as closed with a resolution note.

    Returns a new findings dict; does not mutate the input.
    """
    if finding_id not in findings:
        raise ValidationError(f"Finding '{finding_id}' does not exist.")
    if findings[finding_id]["status"] == "closed":
        raise ValidationError(f"Finding '{finding_id}' is already closed.")
    if not resolution.strip():
        raise ValidationError("Resolution note must not be empty.")
    updated = {k: dict(v) for k, v in findings.items()}
    updated[finding_id]["status"] = "closed"
    updated[finding_id]["resolution"] = resolution
    return updated


def waive_finding(findings: dict, finding_id: str, rationale: str) -> dict:
    """
    Mark an existing finding as waived with a formal rationale.

    Returns a new findings dict; does not mutate the input.
    """
    if finding_id not in findings:
        raise ValidationError(f"Finding '{finding_id}' does not exist.")
    if findings[finding_id]["status"] == "waived":
        raise ValidationError(f"Finding '{finding_id}' is already waived.")
    if not rationale.strip():
        raise ValidationError("Waiver rationale must not be empty.")
    updated = {k: dict(v) for k, v in findings.items()}
    updated[finding_id]["status"] = "waived"
    updated[finding_id]["resolution"] = rationale
    return updated


def verify_gate_readiness(findings: dict) -> tuple:
    """
    Check whether all findings are closed or waived.

    :return: (ready: bool, open_ids: list) — ready is True when open_ids is empty
    """
    open_ids = sorted(fid for fid, f in findings.items() if f["status"] == "open")
    return (len(open_ids) == 0, open_ids)


def milestone_index(milestone: str) -> int:
    """Return the ordinal position of a milestone in the programme sequence."""
    validate_milestone(milestone)
    return MILESTONE_ORDER.index(milestone)
