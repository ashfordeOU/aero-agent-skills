"""Purchasing-duty assessment for class 1 commercial EEE part procurement.

Anchor: ECSS-Q-ST-60-13C clause 4.3.1 (the purchasing duties that make a
delivered commercial part meet the highest assurance expectations).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared supply channel. The channel is not a label: it
   decides which duties the register has to carry, because a part bought away
   from the manufacturer or its franchised network pulls in traceability and
   counterfeit-avoidance duties that a direct purchase does not.
2. Build the duty register for that channel: the duties every class 1 purchase
   carries, plus the extra duties the channel adds.
3. Validate each assignment: the duty named has to be in the register, the
   responsible party has to be one of the permitted roles, and the assignment
   has to cite an evidence reference.
4. Grade each duty as discharged, or open with the reason it is open:
   unassigned, assigned to no permitted role, or assigned with no evidence
   cited. An assigned but unevidenced duty stays open.
5. Take the discharged share of the register against the declared coverage
   floor under a named tolerance, and return every finding.
"""

import math

__all__ = [
    "BASE_DUTIES",
    "CHANNEL_EXTRA_DUTIES",
    "PERMITTED_ROLES",
    "COVERAGE_TOLERANCE",
    "validate_supply_channel",
    "required_duties",
    "validate_assignment",
    "grade_duty",
    "build_duty_register",
    "duty_coverage",
    "assess_procurement_overview",
]

# Duties every class 1 commercial part purchase carries, whatever the channel.
BASE_DUTIES = (
    "specify-part-requirements",
    "flow-down-to-supplier",
    "verify-supplier-approval",
    "verify-delivered-conformance",
    "record-traceability",
)

# Duties a channel adds on top of the base register. A purchase made away from
# the manufacturer or its franchised network has to rebuild the traceability
# that the direct route supplies for free.
CHANNEL_EXTRA_DUTIES = {
    "manufacturer-direct": (),
    "franchised-distributor": (),
    "independent-distributor": (
        "establish-manufacturer-traceability",
        "counterfeit-avoidance-screening",
    ),
    "open-market": (
        "establish-manufacturer-traceability",
        "counterfeit-avoidance-screening",
    ),
}

# Parties a duty may be assigned to. A duty assigned to anyone else is not
# assigned: nobody in the arrangement is answerable for it.
PERMITTED_ROLES = (
    "customer",
    "supplier",
    "procurement-authority",
    "component-engineering",
)

# Coverage is a ratio of small integers. An exactly-met floor can land a few
# units in the last place low; absorb that here rather than lowering the floor.
COVERAGE_TOLERANCE = 1e-9


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def validate_supply_channel(channel):
    """Return the validated supply channel the parts are bought through."""
    if channel is None:
        raise ValueError("supply_channel must be declared, not left undeclared")
    token = _normalize_token(channel, "supply_channel")
    if token not in CHANNEL_EXTRA_DUTIES:
        raise ValueError(
            "supply_channel '%s' is not a recognized channel; expected one of %s"
            % (token, ", ".join(sorted(CHANNEL_EXTRA_DUTIES)))
        )
    return token


def required_duties(channel):
    """Return the ordered duty register the channel has to discharge."""
    token = validate_supply_channel(channel)
    return tuple(BASE_DUTIES) + tuple(CHANNEL_EXTRA_DUTIES[token])


def validate_assignment(assignment):
    """Return one validated duty assignment record."""
    if not isinstance(assignment, dict):
        raise ValueError("each assignment must be a mapping")
    if "duty" not in assignment:
        raise ValueError("assignment missing required key 'duty'")
    duty = _normalize_token(assignment["duty"], "duty")
    owner_raw = assignment.get("owner")
    owner = None
    if owner_raw is not None:
        owner = _normalize_token(owner_raw, "owner")
    evidence_raw = assignment.get("evidence", "")
    if evidence_raw is None:
        evidence_raw = ""
    if not isinstance(evidence_raw, str):
        raise ValueError("evidence for duty '%s' must be a string" % duty)
    evidence = evidence_raw.strip()
    return {"duty": duty, "owner": owner, "evidence": evidence}


def grade_duty(duty, assignment):
    """Return the state of one register duty: discharged, or open with a reason."""
    duty_token = _normalize_token(duty, "duty")
    if assignment is None:
        return {
            "duty": duty_token,
            "owner": None,
            "evidence": "",
            "state": "open",
            "reason": "no responsible party is assigned",
        }
    record = validate_assignment(assignment)
    if record["duty"] != duty_token:
        raise ValueError(
            "assignment for duty '%s' was graded against duty '%s'"
            % (record["duty"], duty_token)
        )
    if record["owner"] is None:
        reason = "no responsible party is assigned"
    elif record["owner"] not in PERMITTED_ROLES:
        reason = "responsible party '%s' is not a permitted role" % record["owner"]
    elif not record["evidence"]:
        reason = "assigned to '%s' but no evidence is cited" % record["owner"]
    else:
        reason = ""
    record["state"] = "discharged" if not reason else "open"
    record["reason"] = reason
    return record


def build_duty_register(channel, assignments):
    """Return the graded duty register plus the assignments outside it."""
    register = required_duties(channel)
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("assignments must be a sequence of assignment mappings")
    by_duty = {}
    for assignment in assignments:
        record = validate_assignment(assignment)
        if record["duty"] in by_duty:
            raise ValueError("duty '%s' is assigned twice" % record["duty"])
        by_duty[record["duty"]] = assignment
    graded = [grade_duty(duty, by_duty.get(duty)) for duty in register]
    extraneous = [duty for duty in sorted(by_duty) if duty not in register]
    return {"register": register, "duties": graded, "extraneous": extraneous}


def duty_coverage(graded):
    """Return the discharged share of a graded duty register."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of duty records")
    discharged = 0
    for record in graded:
        if not isinstance(record, dict) or "state" not in record:
            raise ValueError("each duty record must be a mapping carrying 'state'")
        if record["state"] == "discharged":
            discharged += 1
    return discharged / float(len(graded))


def assess_procurement_overview(spec):
    """Run the full clause 4.3.1 purchasing-duty assessment.

    spec keys: supply_channel, assignments, coverage_floor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("supply_channel", "assignments", "coverage_floor"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    floor = spec["coverage_floor"]
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        raise ValueError("coverage_floor must be a real number")
    floor = float(floor)
    if not math.isfinite(floor) or floor < 0.0 or floor > 1.0:
        raise ValueError("coverage_floor must lie in [0, 1], got %r" % (spec["coverage_floor"],))

    channel = validate_supply_channel(spec["supply_channel"])
    built = build_duty_register(channel, spec["assignments"])
    graded = built["duties"]
    coverage = duty_coverage(graded)

    findings = []
    for record in graded:
        if record["state"] == "open":
            findings.append("duty '%s' is open: %s" % (record["duty"], record["reason"]))
    for duty in built["extraneous"]:
        findings.append(
            "assignment names duty '%s', which the register for a %s purchase does not carry"
            % (duty, channel)
        )

    coverage_met = coverage > floor or math.isclose(
        coverage, floor, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if not coverage_met:
        findings.append(
            "duty coverage %.3f is below the declared floor of %.3f" % (coverage, floor)
        )

    return {
        "supply_channel": channel,
        "register": list(built["register"]),
        "duties": graded,
        "extraneous": built["extraneous"],
        "open_duties": [r["duty"] for r in graded if r["state"] == "open"],
        "coverage": coverage,
        "coverage_floor": floor,
        "coverage_met": coverage_met,
        "acceptable": not findings,
        "findings": findings,
    }
