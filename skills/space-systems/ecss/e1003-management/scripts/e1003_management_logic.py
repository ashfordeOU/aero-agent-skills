"""
ECSS-E-ST-10C §4.3.1 test-campaign management logic.

Covers:
  - Responsibility assignment (customer / supplier / joint) per test type
  - Readiness-condition verification before a test is authorised
  - Campaign-phase sequencing validation
  - Campaign-plan aggregation across all test events
"""

from __future__ import annotations
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_READINESS_CONDITIONS: List[str] = [
    "configuration_baseline_locked",
    "test_procedure_approved",
    "support_equipment_calibrated",
    "personnel_qualified",
    "safety_clearance_granted",
]

CAMPAIGN_PHASE_ORDER: List[str] = [
    "planning",
    "preparation",
    "readiness_review",
    "execution",
    "reporting",
    "closeout",
]

VALID_RESPONSIBILITY_ROLES = frozenset({"customer", "supplier", "joint"})

# Maps recognised test types to their primary responsibility role.
# customer-led: customer approves procedure, witnesses, accepts results.
# supplier-led: supplier plans, conducts, controls environment.
# joint: both parties share planning and execution responsibility.
RESPONSIBILITY_RULES: Dict[str, str] = {
    "acceptance": "customer",
    "qualification_witness": "customer",
    "unit": "supplier",
    "subsystem": "supplier",
    "environmental": "supplier",
    "manufacturing": "supplier",
    "system": "joint",
    "integration": "joint",
    "combined_operations": "joint",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ManagementError(Exception):
    """Base error for e1003 management logic."""


class InvalidTestEventError(ManagementError):
    """Raised when a test event dict is missing required fields or is malformed."""


class InvalidPhaseError(ManagementError):
    """Raised when the phase list argument is not a list."""


class UnknownResponsibilityError(ManagementError):
    """Raised when an override responsibility value is not a valid role."""


# ---------------------------------------------------------------------------
# Responsibility assignment
# ---------------------------------------------------------------------------

def assign_responsibility(test_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assign primary responsibility to a test event.

    Required keys: 'test_id', 'test_type'.
    Optional key: 'override_responsibility' — must be in VALID_RESPONSIBILITY_ROLES.

    Returns a dict with keys:
      test_id        str   — echoed from input
      responsibility str   — 'customer' | 'supplier' | 'joint'
      source         str   — 'rule' | 'override'
      warnings       list  — non-fatal advisory messages
    """
    for key in ("test_id", "test_type"):
        if key not in test_event:
            raise InvalidTestEventError(
                f"test_event is missing required key '{key}'"
            )

    test_id = test_event["test_id"]
    test_type = str(test_event["test_type"]).lower().strip()

    override = test_event.get("override_responsibility")
    if override is not None:
        if override not in VALID_RESPONSIBILITY_ROLES:
            raise UnknownResponsibilityError(
                f"override_responsibility '{override}' is not a valid role; "
                f"choose from {sorted(VALID_RESPONSIBILITY_ROLES)}"
            )
        return {
            "test_id": test_id,
            "responsibility": override,
            "source": "override",
            "warnings": [],
        }

    if test_type not in RESPONSIBILITY_RULES:
        raise InvalidTestEventError(
            f"Unrecognised test_type '{test_type}'; cannot assign responsibility. "
            f"Known types: {sorted(RESPONSIBILITY_RULES)}"
        )

    return {
        "test_id": test_id,
        "responsibility": RESPONSIBILITY_RULES[test_type],
        "source": "rule",
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Readiness-condition verification
# ---------------------------------------------------------------------------

def check_readiness_conditions(test: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify all mandatory readiness conditions are met before a test is authorised.

    Required keys: 'test_id', 'conditions_met' (list[str]).

    Returns a dict with keys:
      test_id            str   — echoed from input
      status             str   — 'ready' | 'not_ready'
      satisfied          list  — canonical conditions that are confirmed
      unmet              list  — canonical conditions that are missing
      unknown_conditions list  — labels in conditions_met not on the canonical list
    """
    for key in ("test_id", "conditions_met"):
        if key not in test:
            raise InvalidTestEventError(
                f"test dict is missing required key '{key}'"
            )

    test_id = test["test_id"]
    conditions_met = set(test["conditions_met"])

    satisfied = [c for c in REQUIRED_READINESS_CONDITIONS if c in conditions_met]
    unmet = [c for c in REQUIRED_READINESS_CONDITIONS if c not in conditions_met]
    unknown = sorted(c for c in conditions_met if c not in REQUIRED_READINESS_CONDITIONS)

    status = "ready" if not unmet else "not_ready"

    return {
        "test_id": test_id,
        "status": status,
        "satisfied": satisfied,
        "unmet": unmet,
        "unknown_conditions": unknown,
    }


# ---------------------------------------------------------------------------
# Campaign-phase sequencing
# ---------------------------------------------------------------------------

def validate_campaign_phases(phases: List[str]) -> Dict[str, Any]:
    """
    Validate that a campaign phase list is well-formed.

    Rules:
      - All entries must be in CAMPAIGN_PHASE_ORDER (no unknowns).
      - No phase may appear more than once.
      - The relative order of retained phases must match CAMPAIGN_PHASE_ORDER
        (phases may be omitted/tailored out, but not reordered).

    Returns a dict with keys:
      status  str   — 'valid' | 'out_of_order' | 'unknown_phase' | 'duplicate_phase'
      issues  list  — human-readable descriptions of each problem found
    """
    if not isinstance(phases, list):
        raise InvalidPhaseError("phases must be a list of strings")

    seen: set = set()
    duplicates: List[str] = []
    unknowns: List[str] = []

    for phase in phases:
        if phase not in CAMPAIGN_PHASE_ORDER:
            unknowns.append(phase)
        if phase in seen:
            duplicates.append(phase)
        seen.add(phase)

    if unknowns:
        return {
            "status": "unknown_phase",
            "issues": [f"Unknown campaign phase: '{p}'" for p in unknowns],
        }

    if duplicates:
        return {
            "status": "duplicate_phase",
            "issues": [f"Duplicate campaign phase: '{p}'" for p in duplicates],
        }

    canonical_indices = [CAMPAIGN_PHASE_ORDER.index(p) for p in phases]
    for i in range(len(canonical_indices) - 1):
        if canonical_indices[i] >= canonical_indices[i + 1]:
            return {
                "status": "out_of_order",
                "issues": [
                    f"Phase '{phases[i]}' must precede '{phases[i + 1]}' "
                    f"in the canonical campaign sequence."
                ],
            }

    return {"status": "valid", "issues": []}


# ---------------------------------------------------------------------------
# Campaign-plan builder
# ---------------------------------------------------------------------------

def build_campaign_plan(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build and validate a full campaign plan from a list of test events.

    Each event must carry 'test_id', 'test_type', and 'conditions_met'.
    Returns a summary dict with:
      campaign_ready       bool  — True only if every event is ready
      event_count          int
      responsibility_tally dict  — count per role
      events               list  — per-event responsibility and readiness details
    """
    if not events:
        raise InvalidTestEventError("events list must not be empty")

    event_results: List[Dict[str, Any]] = []
    campaign_ready = True
    tally: Dict[str, int] = {"customer": 0, "supplier": 0, "joint": 0}

    for ev in events:
        resp = assign_responsibility(ev)
        readiness = check_readiness_conditions(ev)

        if readiness["status"] != "ready":
            campaign_ready = False

        role = resp["responsibility"]
        tally[role] = tally.get(role, 0) + 1

        event_results.append(
            {
                "test_id": ev["test_id"],
                "responsibility": role,
                "readiness_status": readiness["status"],
                "unmet_conditions": readiness["unmet"],
            }
        )

    return {
        "campaign_ready": campaign_ready,
        "event_count": len(events),
        "responsibility_tally": tally,
        "events": event_results,
    }
