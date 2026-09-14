"""Quality assurance duties for a highest-assurance commercial EEE programme.

Anchor: ECSS-Q-ST-60-13C clause 4.5.1 (the frame of quality assurance duties
that applies to a commercial component programme run at the highest assurance
level). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate each duty assignment: the duty named, who owns it, which
   organisation that owner sits in, the state of the assignment and the state
   of its evidence.
2. Map the assignments onto the duty set a class 1 programme owes, keeping an
   unassigned duty, a duty deferred on an approved authorisation and a duty
   with no evidence apart.
3. Test the owner of every duty that has to be judged independently against
   the organisation that executes the work it assures.
4. Weight the duties that are genuinely covered into a programme coverage
   score, comparing it with the required score through a named tolerance.
5. Rank the findings and return one readiness verdict: ready,
   ready-with-actions, or not-ready.
"""

import math

__all__ = [
    "SCORE_TOLERANCE",
    "DUTY_WEIGHTS",
    "INDEPENDENCE_REQUIRED",
    "OWNER_ORGANISATIONS",
    "ASSIGNMENT_STATES",
    "EVIDENCE_STATES",
    "SEVERITY_ORDER",
    "duty_weight",
    "validate_duty_assignment",
    "owner_is_independent",
    "duty_is_covered",
    "coverage_score",
    "duty_findings",
    "readiness_verdict",
    "assess_quality_assurance_duties",
]

# The coverage score is a weighted quotient; a programme that covers exactly
# the required fraction can land a few ULP below it. Absorb the representation
# error here instead of lowering the required score.
SCORE_TOLERANCE = 1e-9

# The duties a class 1 commercial component programme owes, with the weight
# each carries in the coverage score. The heavier duties are the ones whose
# absence cannot be recovered later in the programme.
DUTY_WEIGHTS = {
    "procurement-specification-approval": 3.0,
    "manufacturer-capability-assessment": 3.0,
    "lot-acceptance-review": 3.0,
    "delivered-data-package-review": 2.0,
    "nonconformance-disposition": 3.0,
    "alert-and-advisory-handling": 2.0,
    "lot-traceability-maintenance": 2.0,
    "parts-control-board-reporting": 1.0,
}

# Duties whose owner has to sit outside the organisation executing the work
# being assured; an owner inside it is grading its own output.
INDEPENDENCE_REQUIRED = (
    "lot-acceptance-review",
    "delivered-data-package-review",
    "nonconformance-disposition",
)

OWNER_ORGANISATIONS = (
    "quality-assurance",
    "design-authority",
    "procurement",
    "supplier",
    "project-management",
)

ASSIGNMENT_STATES = ("assigned", "unassigned", "deferred")

EVIDENCE_STATES = ("recorded", "planned", "absent")

SEVERITY_ORDER = ("critical", "major", "minor")


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def duty_weight(duty, weights=None):
    """Return the coverage weight of a duty, or raise on an unknown one."""
    table = DUTY_WEIGHTS if weights is None else weights
    if not isinstance(table, dict) or not table:
        raise ValueError("duty weight table must be a non-empty mapping")
    key = _require_text(duty, "duty")
    if key not in table:
        raise ValueError("duty %r is not one of %r" % (duty, sorted(table)))
    weight = table[key]
    if not isinstance(weight, (int, float)) or isinstance(weight, bool):
        raise ValueError("weight of duty %r must be a real number" % duty)
    weight = float(weight)
    if not math.isfinite(weight) or weight <= 0.0:
        raise ValueError("weight of duty %r must be positive and finite" % duty)
    return weight


def validate_duty_assignment(assignment, weights=None):
    """Return a normalised duty assignment or raise on a malformed one."""
    if not isinstance(assignment, dict):
        raise ValueError("assignment must be a mapping, got %r" % (assignment,))
    duty = _require_text(assignment.get("duty"), "duty")
    duty_weight(duty, weights)
    state = assignment.get("state", "assigned")
    if state not in ASSIGNMENT_STATES:
        raise ValueError("assignment state %r is not one of %r" % (state, ASSIGNMENT_STATES))
    evidence = assignment.get("evidence", "absent")
    if evidence not in EVIDENCE_STATES:
        raise ValueError("evidence state %r is not one of %r" % (evidence, EVIDENCE_STATES))
    record = {
        "duty": duty,
        "state": state,
        "evidence": evidence,
        "owner": None,
        "owner_organisation": None,
        "authorisation_reference": None,
    }
    if state == "deferred":
        record["authorisation_reference"] = _require_text(
            assignment.get("authorisation_reference"),
            "authorisation reference for a deferred duty",
        )
        return record
    if state == "unassigned":
        return record
    record["owner"] = _require_text(assignment.get("owner"), "duty owner")
    organisation = _require_text(
        assignment.get("owner_organisation"), "owner organisation"
    ).lower()
    if organisation not in OWNER_ORGANISATIONS:
        raise ValueError(
            "owner organisation %r is not one of %r"
            % (organisation, OWNER_ORGANISATIONS)
        )
    record["owner_organisation"] = organisation
    return record


def owner_is_independent(duty, owner_organisation, executing_organisation):
    """Return True when a duty owner sits outside the executing organisation."""
    key = _require_text(duty, "duty")
    if key not in INDEPENDENCE_REQUIRED:
        return True
    owner = _require_text(owner_organisation, "owner organisation").lower()
    executor = _require_text(executing_organisation, "executing organisation").lower()
    for label, value in (("owner", owner), ("executor", executor)):
        if value not in OWNER_ORGANISATIONS:
            raise ValueError(
                "%s organisation %r is not one of %r" % (label, value, OWNER_ORGANISATIONS)
            )
    return owner != executor


def duty_is_covered(record, executing_organisation):
    """Return True when a duty counts towards the coverage score."""
    if not isinstance(record, dict) or "duty" not in record:
        raise ValueError("record must be a normalised duty assignment")
    if record["state"] != "assigned":
        return False
    if record["evidence"] == "absent":
        return False
    return owner_is_independent(
        record["duty"], record["owner_organisation"], executing_organisation
    )


def coverage_score(records, executing_organisation, weights=None):
    """Return the weighted fraction of the owed duties actually covered."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of normalised assignments")
    table = DUTY_WEIGHTS if weights is None else weights
    if not isinstance(table, dict) or not table:
        raise ValueError("duty weight table must be a non-empty mapping")
    total = sum(duty_weight(duty, table) for duty in table)
    seen = set()
    earned = 0.0
    for record in records:
        if not isinstance(record, dict) or "duty" not in record:
            raise ValueError("each record must be a normalised duty assignment")
        duty = record["duty"]
        if duty in seen:
            continue
        seen.add(duty)
        if duty not in table:
            continue
        if duty_is_covered(record, executing_organisation):
            earned += duty_weight(duty, table)
    return earned / total


def _finding(severity, duty, message):
    if severity not in SEVERITY_ORDER:
        raise ValueError("severity %r is not one of %r" % (severity, SEVERITY_ORDER))
    return {"severity": severity, "duty": duty, "message": message}


def duty_findings(record, executing_organisation):
    """Return the findings one normalised duty assignment raises."""
    if not isinstance(record, dict) or "duty" not in record:
        raise ValueError("record must be a normalised duty assignment")
    duty = record["duty"]
    findings = []
    if record["state"] == "unassigned":
        findings.append(_finding("critical", duty, "%s carries no named owner" % duty))
        return findings
    if record["state"] == "deferred":
        findings.append(
            _finding(
                "minor",
                duty,
                "%s is deferred on authorisation %s"
                % (duty, record["authorisation_reference"]),
            )
        )
        return findings
    if not owner_is_independent(
        duty, record["owner_organisation"], executing_organisation
    ):
        findings.append(
            _finding(
                "critical",
                duty,
                "%s is owned inside %s, the organisation executing the work it assures"
                % (duty, record["owner_organisation"]),
            )
        )
    if record["evidence"] == "absent":
        findings.append(
            _finding("major", duty, "%s has an owner but no evidence of execution" % duty)
        )
    elif record["evidence"] == "planned":
        findings.append(
            _finding("minor", duty, "%s is planned and not yet recorded" % duty)
        )
    return findings


def readiness_verdict(score, findings, required_score):
    """Return the programme readiness verdict."""
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("score must be a real number")
    score = float(score)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("score must sit in [0, 1], got %r" % (score,))
    if not isinstance(required_score, (int, float)) or isinstance(required_score, bool):
        raise ValueError("required_score must be a real number")
    required = float(required_score)
    if not math.isfinite(required) or not 0.0 < required <= 1.0:
        raise ValueError("required_score must sit in (0, 1], got %r" % (required_score,))
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding:
            raise ValueError("each finding must carry a severity")
        severities.add(finding["severity"])
    meets_score = score > required or math.isclose(
        score, required, rel_tol=0.0, abs_tol=SCORE_TOLERANCE
    )
    if "critical" in severities or not meets_score:
        return "not-ready"
    if severities:
        return "ready-with-actions"
    return "ready"


def assess_quality_assurance_duties(programme):
    """Grade the duty allocation of a class 1 programme against clause 4.5.1.

    programme keys: assignments (sequence), executing_organisation, optional
    required_score and duty_weights.
    """
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping")
    for key in ("assignments", "executing_organisation"):
        if key not in programme:
            raise ValueError("programme missing required key '%s'" % key)
    assignments = programme["assignments"]
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("programme['assignments'] must be a sequence")
    executor = _require_text(
        programme["executing_organisation"], "executing organisation"
    ).lower()
    if executor not in OWNER_ORGANISATIONS:
        raise ValueError(
            "executing organisation %r is not one of %r" % (executor, OWNER_ORGANISATIONS)
        )
    weights = programme.get("duty_weights", DUTY_WEIGHTS)
    required_score = programme.get("required_score", 1.0)

    records = [validate_duty_assignment(item, weights) for item in assignments]
    seen = {}
    for record in records:
        seen.setdefault(record["duty"], record)
    findings = []
    for duty in sorted(weights):
        record = seen.get(duty)
        if record is None:
            findings.append(
                _finding("critical", duty, "%s appears nowhere in the duty matrix" % duty)
            )
            continue
        findings.extend(duty_findings(record, executor))
    score = coverage_score(records, executor, weights)
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["duty"]))
    verdict = readiness_verdict(score, findings, required_score)
    return {
        "records": records,
        "coverage_score": score,
        "required_score": float(required_score),
        "findings": findings,
        "verdict": verdict,
        "ready": verdict == "ready",
    }
