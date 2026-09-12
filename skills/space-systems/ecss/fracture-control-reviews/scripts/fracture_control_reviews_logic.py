"""
Fracture-control review gate logic — ECSS-E-ST-32C §5.3.

Implements review-milestone readiness checks for fracture-control inputs
submitted at safety and project reviews (SRR → AR).  Deterministic,
offline, stdlib only.
"""

# Canonical milestone sequence
REVIEW_ORDER = ("SRR", "PDR", "CDR", "QR", "AR")

# FCI list maturity level required at each milestone (in ascending order)
FCI_MATURITY_LEVELS = ("preliminary", "draft", "final", "verified", "accepted")

FCI_MATURITY_REQUIRED = {
    "SRR": "preliminary",
    "PDR": "draft",
    "CDR": "final",
    "QR":  "verified",
    "AR":  "accepted",
}

# Required fracture-control input items at each milestone
REQUIRED_INPUTS = {
    "SRR": frozenset({
        "fracture_control_plan_draft",
        "fci_list_preliminary",
        "fracture_criteria_draft",
    }),
    "PDR": frozenset({
        "fracture_control_plan_baselined",
        "fci_list_draft",
        "fracture_analysis_preliminary",
        "fracture_criteria_baselined",
    }),
    "CDR": frozenset({
        "fracture_control_plan_approved",
        "fci_list_final",
        "fracture_analysis_final",
        "nde_procedures_draft",
        "fracture_test_plan",
        "previous_review_actions_closed",
    }),
    "QR": frozenset({
        "fci_list_verified",
        "fracture_analysis_final",
        "nde_results",
        "fracture_test_results",
        "test_analysis_correlation",
        "previous_review_actions_closed",
    }),
    "AR": frozenset({
        "fci_list_accepted",
        "fracture_summary_report",
        "nde_acceptance_records",
        "waivers_dispositioned",
        "previous_review_actions_closed",
    }),
}


def _validate_milestone(milestone: str) -> None:
    if milestone not in REVIEW_ORDER:
        raise ValueError(
            f"Unknown review milestone: {milestone!r}. "
            f"Must be one of {REVIEW_ORDER}."
        )


def _validate_maturity(maturity: str) -> None:
    if maturity not in FCI_MATURITY_LEVELS:
        raise ValueError(
            f"Unknown FCI maturity level: {maturity!r}. "
            f"Must be one of {FCI_MATURITY_LEVELS}."
        )


def required_inputs(milestone: str) -> frozenset:
    """Return the frozenset of required fracture-control inputs for a milestone."""
    _validate_milestone(milestone)
    return REQUIRED_INPUTS[milestone]


def fci_maturity_required(milestone: str) -> str:
    """Return the FCI list maturity level required at a given milestone."""
    _validate_milestone(milestone)
    return FCI_MATURITY_REQUIRED[milestone]


def check_fci_maturity(milestone: str, current_maturity: str) -> dict:
    """
    Check whether the current FCI list maturity meets the milestone requirement.

    Returns:
        dict with keys:
          meets_requirement (bool)
          required_maturity (str)
          current_maturity  (str)
          shortfall         (int) — 0 if requirement met, >0 if behind
    """
    _validate_milestone(milestone)
    _validate_maturity(current_maturity)
    required = FCI_MATURITY_REQUIRED[milestone]
    req_idx = FCI_MATURITY_LEVELS.index(required)
    cur_idx = FCI_MATURITY_LEVELS.index(current_maturity)
    shortfall = max(0, req_idx - cur_idx)
    return {
        "meets_requirement": cur_idx >= req_idx,
        "required_maturity": required,
        "current_maturity": current_maturity,
        "shortfall": shortfall,
    }


def check_review_readiness(milestone: str, available_inputs: set) -> dict:
    """
    Check whether fracture-control review inputs are ready for a milestone.

    Args:
        milestone:        one of REVIEW_ORDER
        available_inputs: set of input item identifiers currently available

    Returns:
        dict with keys:
          ready   (bool)         — True only when missing is empty
          missing (frozenset)    — required items not in available_inputs
          present (frozenset)    — required items found in available_inputs
    """
    _validate_milestone(milestone)
    required = REQUIRED_INPUTS[milestone]
    available = frozenset(available_inputs)
    missing = required - available
    present = required & available
    return {
        "ready": len(missing) == 0,
        "missing": missing,
        "present": present,
    }


def milestone_index(milestone: str) -> int:
    """Return the 0-based sequential index of a review milestone."""
    _validate_milestone(milestone)
    return REVIEW_ORDER.index(milestone)


def previous_milestone(milestone: str):
    """Return the milestone that precedes the given one, or None for SRR."""
    idx = milestone_index(milestone)
    if idx == 0:
        return None
    return REVIEW_ORDER[idx - 1]


def next_milestone(milestone: str):
    """Return the milestone that follows the given one, or None for AR."""
    idx = milestone_index(milestone)
    if idx == len(REVIEW_ORDER) - 1:
        return None
    return REVIEW_ORDER[idx + 1]
