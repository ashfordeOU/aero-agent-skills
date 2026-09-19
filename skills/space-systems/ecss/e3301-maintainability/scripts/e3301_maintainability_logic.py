"""Maintenance-free mechanism design and the exceptions the customer approved.

Anchor: ECSS-E-ST-33-01 clause 4.2.4.4 -- mechanisms are designed to need no
maintenance, unless maintenance is agreed with the customer. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each declared maintenance action: the phase it falls in, whether
   it recurs, whether it opens the mechanism, and the customer approval and
   access provisions recorded against it.
2. Count how many times a recurring action actually falls inside the mission,
   because an interval longer than the mission is a design feature and an
   interval shorter than it is a servicing programme.
3. Grade every action: an approval that is absent, pending, undated or
   unreferenced leaves the action unpermitted, and an approved in-orbit action
   still owes declared access and tooling.
4. Compute the life margin of each limited-life item against the duty the
   mission accumulates, so an item that cannot reach the end of life is
   reported as a hidden maintenance demand rather than as a life figure.
5. Return one of three verdicts: maintenance-free, approved-maintenance, or
   non-compliant.
"""

import math

__all__ = [
    "MAINTENANCE_PHASES",
    "IN_ORBIT_PHASE",
    "APPROVAL_APPROVED",
    "APPROVAL_PENDING",
    "APPROVAL_ABSENT",
    "VERDICT_FREE",
    "VERDICT_APPROVED",
    "VERDICT_NON_COMPLIANT",
    "DAYS_PER_MONTH",
    "DEFAULT_LIFE_FACTOR",
    "MARGIN_TOLERANCE",
    "validate_maintenance_action",
    "occurrences_in_mission",
    "approval_state",
    "access_is_provisioned",
    "validate_life_item",
    "required_cycles",
    "life_margin_ratio",
    "assess_action",
    "assess_life_items",
    "assess_maintainability",
]

MAINTENANCE_PHASES = (
    "manufacturing",
    "ground-storage",
    "pre-launch",
    "in-orbit",
)

IN_ORBIT_PHASE = "in-orbit"

APPROVAL_APPROVED = "approved"
APPROVAL_PENDING = "pending"
APPROVAL_ABSENT = "not-submitted"

VERDICT_FREE = "maintenance-free"
VERDICT_APPROVED = "approved-maintenance"
VERDICT_NON_COMPLIANT = "non-compliant"

# Mean calendar month, so a mission stated in months converts to duty days
# the same way every time.
DAYS_PER_MONTH = 365.25 / 12.0

# Demonstrated life is expected to cover the mission duty by this factor.
DEFAULT_LIFE_FACTOR = 2.0

# Margins that should land exactly on the required factor land a few ULPs off.
MARGIN_TOLERANCE = 1.0e-9


def _require_text(value, label):
    """Return a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_real(value, label):
    """Return a finite float, refusing booleans and non-numerics."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_positive(value, label):
    """Return a strictly positive finite float."""
    number = _require_real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_bool(value, label):
    """Return a boolean, refusing anything that merely looks like one."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_maintenance_action(action):
    """Return a validated declared maintenance action.

    action keys: id, phase, requires_disassembly; optional interval_months
    (absent or None for a one-off), customer_approval, access_provision.
    """
    if not isinstance(action, dict):
        raise ValueError("maintenance action must be a mapping")
    for key in ("id", "phase", "requires_disassembly"):
        if key not in action:
            raise ValueError("maintenance action missing required key '%s'" % key)
    phase = _require_text(action["phase"], "phase")
    if phase not in MAINTENANCE_PHASES:
        raise ValueError(
            "phase %r is not one of %s" % (phase, ", ".join(MAINTENANCE_PHASES))
        )
    interval = action.get("interval_months")
    if interval is not None:
        interval = _require_positive(interval, "interval_months")
    approval = action.get("customer_approval")
    if approval is not None and not isinstance(approval, dict):
        raise ValueError("'customer_approval' must be a mapping when present")
    access = action.get("access_provision")
    if access is not None and not isinstance(access, dict):
        raise ValueError("'access_provision' must be a mapping when present")
    return {
        "id": _require_text(action["id"], "action id"),
        "phase": phase,
        "interval_months": interval,
        "requires_disassembly": _require_bool(
            action["requires_disassembly"], "requires_disassembly"
        ),
        "customer_approval": approval,
        "access_provision": access,
    }


def occurrences_in_mission(action, mission_duration_months):
    """Return how many times a declared action falls inside the mission."""
    record = validate_maintenance_action(action)
    duration = _require_positive(mission_duration_months, "mission_duration_months")
    if record["interval_months"] is None:
        return 1
    return int(math.floor(duration / record["interval_months"]))


def approval_state(action):
    """Return the state of the customer approval recorded against an action."""
    record = validate_maintenance_action(action)
    approval = record["customer_approval"]
    if not approval:
        return APPROVAL_ABSENT
    status = approval.get("status")
    if not isinstance(status, str) or status.strip().lower() != APPROVAL_APPROVED:
        return APPROVAL_PENDING
    _require_text(approval.get("reference", ""), "approval reference")
    _require_text(approval.get("date", ""), "approval date")
    return APPROVAL_APPROVED


def access_is_provisioned(action):
    """Return True when an action declares both an access route and its tooling."""
    record = validate_maintenance_action(action)
    access = record["access_provision"]
    if not access:
        return False
    route = access.get("route")
    tooling = access.get("tooling")
    if not isinstance(route, str) or not route.strip():
        return False
    if not isinstance(tooling, str) or not tooling.strip():
        return False
    return True


def validate_life_item(item):
    """Return a validated limited-life item record.

    item keys: id, qualified_cycles, duty_cycles_per_day.
    """
    if not isinstance(item, dict):
        raise ValueError("life item must be a mapping")
    for key in ("id", "qualified_cycles", "duty_cycles_per_day"):
        if key not in item:
            raise ValueError("life item missing required key '%s'" % key)
    return {
        "id": _require_text(item["id"], "life item id"),
        "qualified_cycles": _require_positive(item["qualified_cycles"], "qualified_cycles"),
        "duty_cycles_per_day": _require_positive(
            item["duty_cycles_per_day"], "duty_cycles_per_day"
        ),
    }


def required_cycles(duty_cycles_per_day, mission_duration_months):
    """Return the cycles a mission accumulates at a given daily duty."""
    per_day = _require_positive(duty_cycles_per_day, "duty_cycles_per_day")
    duration = _require_positive(mission_duration_months, "mission_duration_months")
    return per_day * duration * DAYS_PER_MONTH


def life_margin_ratio(item, mission_duration_months):
    """Return demonstrated life divided by the life the mission demands."""
    record = validate_life_item(item)
    demanded = required_cycles(record["duty_cycles_per_day"], mission_duration_months)
    return record["qualified_cycles"] / demanded


def assess_action(action, mission_duration_months):
    """Assess one declared maintenance action."""
    record = validate_maintenance_action(action)
    occurrences = occurrences_in_mission(action, mission_duration_months)
    state = approval_state(action)
    provisioned = access_is_provisioned(action)
    findings = []
    if state != APPROVAL_APPROVED:
        findings.append(
            "action %s is declared but not approved by the customer (%s)"
            % (record["id"], state)
        )
    if record["phase"] == IN_ORBIT_PHASE:
        if not provisioned:
            findings.append(
                "in-orbit action %s declares no access route and tooling" % record["id"]
            )
        if record["requires_disassembly"]:
            findings.append(
                "in-orbit action %s opens the mechanism, which no flight "
                "configuration supports" % record["id"]
            )
    if record["interval_months"] is not None and occurrences == 0:
        findings.append(
            "action %s recurs every %g months, longer than the mission; it is "
            "not a maintenance demand at all"
            % (record["id"], record["interval_months"])
        )
    return {
        "id": record["id"],
        "phase": record["phase"],
        "interval_months": record["interval_months"],
        "occurrences": occurrences,
        "approval_state": state,
        "access_provisioned": provisioned,
        "requires_disassembly": record["requires_disassembly"],
        "permitted": state == APPROVAL_APPROVED and not findings,
        "findings": findings,
    }


def assess_life_items(items, mission_duration_months, life_factor=DEFAULT_LIFE_FACTOR):
    """Assess the limited-life items against the duty the mission accumulates."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("life items must be a sequence")
    factor = _require_positive(life_factor, "life_factor")
    records = []
    findings = []
    for item in items:
        record = validate_life_item(item)
        ratio = life_margin_ratio(item, mission_duration_months)
        sufficient = ratio > factor or math.isclose(
            ratio, factor, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
        )
        if not sufficient:
            findings.append(
                "item %s demonstrates %.3f times the mission duty, under the "
                "required %.3f; the shortfall is an unstated maintenance demand"
                % (record["id"], ratio, factor)
            )
        records.append({
            "id": record["id"],
            "qualified_cycles": record["qualified_cycles"],
            "required_cycles": required_cycles(
                record["duty_cycles_per_day"], mission_duration_months
            ),
            "margin_ratio": ratio,
            "sufficient": sufficient,
        })
    return {"records": records, "findings": findings}


def assess_maintainability(spec):
    """Assess a mechanism design against the maintenance-free intent.

    spec keys: mission_duration_months; optional maintenance_actions,
    life_items and life_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "mission_duration_months" not in spec:
        raise ValueError("spec missing required key 'mission_duration_months'")
    duration = _require_positive(
        spec["mission_duration_months"], "mission_duration_months"
    )
    actions = spec.get("maintenance_actions", [])
    if not isinstance(actions, (list, tuple)):
        raise ValueError("'maintenance_actions' must be a sequence")
    identifiers = [validate_maintenance_action(action)["id"] for action in actions]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("the maintenance action list repeats an identifier")
    action_records = [assess_action(action, duration) for action in actions]
    life = assess_life_items(
        spec.get("life_items", []), duration, spec.get("life_factor", DEFAULT_LIFE_FACTOR)
    )
    findings = []
    for record in action_records:
        findings.extend(record["findings"])
    findings.extend(life["findings"])

    permitted = [record for record in action_records if record["permitted"]]
    if findings:
        verdict = VERDICT_NON_COMPLIANT
    elif action_records:
        verdict = VERDICT_APPROVED
    else:
        verdict = VERDICT_FREE
    return {
        "verdict": verdict,
        "actions": action_records,
        "permitted_action_count": len(permitted),
        "declared_action_count": len(action_records),
        "life_items": life["records"],
        "findings": findings,
        "maintenance_free": verdict == VERDICT_FREE,
        "compliant": verdict in (VERDICT_FREE, VERDICT_APPROVED),
    }
