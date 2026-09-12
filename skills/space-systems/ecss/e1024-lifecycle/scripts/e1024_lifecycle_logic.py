"""
ECSS-E-ST-10C §4.3 — Interface management life cycle logic.

Implements deterministic, offline checks for the four interface lifecycle
streams: generic, space_launch, space_ground, and ots.  No third-party
dependencies; stdlib only.
"""

from __future__ import annotations

INTERFACE_TYPES: tuple[str, ...] = (
    "generic",
    "space_launch",
    "space_ground",
    "ots",
)

PROJECT_PHASES: tuple[str, ...] = ("0", "A", "B", "C", "D", "E", "F")

MATURITY_LEVELS: dict[str, str] = {
    "0": "preliminary_definition",
    "A": "preliminary_definition",
    "B": "initial_icd_baseline",
    "C": "frozen_icd",
    "D": "verified_icd",
    "E": "verified_icd",
    "F": "closed_out",
}

# Required activities per (phase, interface_type).
# Each activity is an opaque string key the caller records as completed.
# For non-generic types these are the stream-specific activities only;
# generic activities must be fetched separately and combined.
_ACTIVITIES: dict[tuple[str, str], list[str]] = {
    # Generic — baseline stream applicable to every interface.
    ("0", "generic"):  ["identify_interfaces", "assign_responsibilities"],
    ("A", "generic"):  ["draft_interface_requirements", "prepare_icd_template"],
    ("B", "generic"):  ["baseline_icd", "issue_interface_requirement_document"],
    ("C", "generic"):  ["detail_icd", "verify_subsystem_compliance"],
    ("D", "generic"):  ["freeze_icd", "perform_interface_verification_test"],
    ("E", "generic"):  ["maintain_icd", "process_change_requests"],
    ("F", "generic"):  ["close_out_icd"],
    # Space element – launch segment.
    ("A", "space_launch"): ["preliminary_mechanical_envelope_definition"],
    ("B", "space_launch"): ["preliminary_launch_icd_issue"],
    ("C", "space_launch"): ["launch_service_agreement_execution", "launch_icd_freeze"],
    ("D", "space_launch"): ["interface_verification_testing_with_launcher"],
    ("E", "space_launch"): [],
    ("F", "space_launch"): ["archive_launch_icd"],
    # Space – ground segment.
    ("A", "space_ground"): ["preliminary_tmtc_interface_definition"],
    ("B", "space_ground"): ["ground_segment_icd_baseline"],
    ("C", "space_ground"): ["ground_segment_interface_freeze"],
    ("D", "space_ground"): ["operations_readiness_validation"],
    ("E", "space_ground"): ["maintain_ground_icd", "process_operations_changes"],
    ("F", "space_ground"): ["close_out_ground_icd"],
    # OTS-product involvement (stream-specific only; generic is also required).
    ("A", "ots"): ["identify_ots_product_interfaces"],
    ("B", "ots"): ["preliminary_ots_technical_agreement"],
    ("C", "ots"): ["formal_ots_technical_agreement"],
    ("D", "ots"): ["ots_acceptance_and_integration"],
    ("E", "ots"): [],
    ("F", "ots"): [],
}

# Required OTS agreements that must be in place cumulatively by each phase.
_OTS_AGREEMENTS_BY_PHASE: dict[str, list[str]] = {
    "0": [],
    "A": [],
    "B": ["preliminary_technical_interface_agreement"],
    "C": [
        "preliminary_technical_interface_agreement",
        "formal_technical_interface_agreement",
    ],
    "D": [
        "preliminary_technical_interface_agreement",
        "formal_technical_interface_agreement",
        "acceptance_agreement",
    ],
    "E": [
        "preliminary_technical_interface_agreement",
        "formal_technical_interface_agreement",
        "acceptance_agreement",
    ],
    "F": [
        "preliminary_technical_interface_agreement",
        "formal_technical_interface_agreement",
        "acceptance_agreement",
    ],
}

# Phase at which each interface type's ICD is considered frozen.
_FREEZE_PHASE: dict[str, str] = {
    "generic":      "D",
    "space_launch": "C",
    "space_ground": "C",
    "ots":          "C",
}


def _validate_phase(phase: str) -> None:
    if phase not in PROJECT_PHASES:
        raise ValueError(
            f"Unknown phase {phase!r}. Valid phases: {PROJECT_PHASES}"
        )


def _validate_interface_type(interface_type: str) -> None:
    if interface_type not in INTERFACE_TYPES:
        raise ValueError(
            f"Unknown interface type {interface_type!r}. "
            f"Valid types: {INTERFACE_TYPES}"
        )


def get_phase_activities(phase: str, interface_type: str) -> list[str]:
    """Return the stream-specific required activities for *interface_type* at *phase*.

    For ots and other non-generic stream types the generic activities are NOT
    included here — use get_all_phase_activities to obtain the combined list.
    Returns an empty list if no stream-specific activities apply at that phase.
    """
    _validate_phase(phase)
    _validate_interface_type(interface_type)
    return list(_ACTIVITIES.get((phase, interface_type), []))


def get_all_phase_activities(phase: str, interface_type: str) -> list[str]:
    """Return the full combined activity list for *interface_type* at *phase*.

    For non-generic types this is the union of the generic activities and the
    stream-specific activities for that phase.
    """
    _validate_phase(phase)
    _validate_interface_type(interface_type)
    combined = get_phase_activities(phase, "generic")
    if interface_type != "generic":
        combined = combined + get_phase_activities(phase, interface_type)
    return combined


def check_lifecycle_compliance(
    phase: str,
    interface_type: str,
    completed: list[str],
) -> list[str]:
    """Return required activities for *interface_type* at *phase* absent from *completed*.

    An empty return list means the phase gate is met for that stream.
    """
    _validate_phase(phase)
    _validate_interface_type(interface_type)
    required = get_all_phase_activities(phase, interface_type)
    completed_set = set(completed)
    return [a for a in required if a not in completed_set]


def get_ots_agreements(phase: str) -> list[str]:
    """Return the cumulative list of OTS agreements that must be in place by *phase*."""
    _validate_phase(phase)
    return list(_OTS_AGREEMENTS_BY_PHASE[phase])


def check_ots_compliance(phase: str, signed_agreements: list[str]) -> list[str]:
    """Return OTS agreements required by *phase* that are absent from *signed_agreements*."""
    _validate_phase(phase)
    required = get_ots_agreements(phase)
    signed_set = set(signed_agreements)
    return [a for a in required if a not in signed_set]


def determine_maturity_level(phase: str) -> str:
    """Return the expected ICD maturity level for *phase*."""
    _validate_phase(phase)
    return MATURITY_LEVELS[phase]


def validate_phase_sequence(phases_done: list[str]) -> list[str]:
    """Return project phases missing from *phases_done* given the latest done phase.

    A phase is missing if it precedes the latest completed phase in the ordered
    sequence and is not present in *phases_done*.  Returns an empty list if the
    sequence is complete up to the latest phase or if *phases_done* is empty.
    """
    if not phases_done:
        return []
    for p in phases_done:
        _validate_phase(p)
    phase_index = {p: i for i, p in enumerate(PROJECT_PHASES)}
    latest_idx = max(phase_index[p] for p in phases_done)
    done_set = set(phases_done)
    return [
        PROJECT_PHASES[i]
        for i in range(latest_idx)
        if PROJECT_PHASES[i] not in done_set
    ]


def check_interface_freeze(phase: str, interface_type: str) -> bool:
    """Return True if the interface is expected to be frozen at or before *phase*."""
    _validate_phase(phase)
    _validate_interface_type(interface_type)
    freeze_phase = _FREEZE_PHASE[interface_type]
    phase_index = {p: i for i, p in enumerate(PROJECT_PHASES)}
    return phase_index[phase] >= phase_index[freeze_phase]
