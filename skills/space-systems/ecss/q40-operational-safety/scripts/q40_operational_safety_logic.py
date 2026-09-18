"""Operational safety for flight and ground operations.

Anchor: ECSS-Q-ST-40C clause 6.6 (operational safety: flight operations and
mission-control constraints, and hazard control over ground operations such as
transport, handling, integration and launch-site work). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the operational phases the clause covers, split into the ground set
   and the flight set, because the two carry different obligations.
2. Rank every declared control against the hazard-reduction precedence --
   eliminate by design, then an engineered safety device, then a warning
   device, then procedure and training -- and refuse to let a severe hazard
   rest on a control weaker than its severity allows.
3. Require a verification for every control, so a control that exists only on
   paper is visible as such.
4. For a flight-phase constraint, compare the reaction time the constraint
   needs with the time the operator actually has, and treat an exactly zero
   margin as a finding rather than as a pass.
5. Check that every phase the programme declared hazardous carries at least
   one operation, and report the phases left uncovered.
"""

import math

__all__ = [
    "GROUND_PHASES",
    "FLIGHT_PHASES",
    "OPERATIONAL_PHASES",
    "SEVERITY_ORDER",
    "CONTROL_PRECEDENCE",
    "MAXIMUM_CONTROL_RANK",
    "REACTION_TOLERANCE_S",
    "OPERATION_FIELDS",
    "validate_phase",
    "validate_severity",
    "validate_control_type",
    "control_rank",
    "maximum_control_rank",
    "reaction_margin_s",
    "reaction_status",
    "validate_operation",
    "assess_operation",
    "phase_coverage",
    "assess_operational_safety",
]

# Ground operations the clause puts hazard control on.
GROUND_PHASES = ("transport", "handling", "integration", "launch-site-operations")

# Flight operations and the mission-control activity that constrains them.
FLIGHT_PHASES = ("launch", "in-orbit-operations", "mission-control", "disposal")

OPERATIONAL_PHASES = GROUND_PHASES + FLIGHT_PHASES

# Severity of the consequence, most severe first.
SEVERITY_ORDER = ("catastrophic", "critical", "major", "minor")

# Hazard-reduction precedence, strongest control first.
CONTROL_PRECEDENCE = (
    "design-elimination",
    "engineered-safety-device",
    "warning-device",
    "procedure-and-training",
)

# The weakest control rank a severity may rest on.
MAXIMUM_CONTROL_RANK = {
    "catastrophic": 1,
    "critical": 2,
    "major": 3,
    "minor": 3,
}

# Reaction-time margins are differences of floats; an exactly zero margin is
# recognised through this tolerance rather than by shaving the required time.
REACTION_TOLERANCE_S = 1e-9

# The record the assessment accepts for one operation.
OPERATION_FIELDS = (
    "id",
    "phase",
    "hazard",
    "severity",
    "control_type",
    "verification",
    "available_time_s",
    "required_reaction_time_s",
    "personnel_exposed",
)


def _token(value, label, allowed):
    """Return a trimmed lowercase token drawn from allowed; raise otherwise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower()
    if token not in allowed:
        raise ValueError("%s must be one of %s, got %r" % (label, ", ".join(allowed), value))
    return token


def validate_phase(value):
    """Return a known operational phase."""
    return _token(value, "phase", OPERATIONAL_PHASES)


def validate_severity(value):
    """Return a known severity."""
    return _token(value, "severity", SEVERITY_ORDER)


def validate_control_type(value):
    """Return a known control type."""
    return _token(value, "control_type", CONTROL_PRECEDENCE)


def control_rank(control_type):
    """Return the precedence rank of a control; zero is the strongest."""
    return CONTROL_PRECEDENCE.index(validate_control_type(control_type))


def maximum_control_rank(severity):
    """Return the weakest control rank a severity is allowed to rest on."""
    return MAXIMUM_CONTROL_RANK[validate_severity(severity)]


def _positive_seconds(value, label):
    """Return a positive duration in seconds; raise on anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return seconds


def reaction_margin_s(available_time_s, required_reaction_time_s):
    """Return the seconds of slack a mission-control constraint leaves."""
    available = _positive_seconds(available_time_s, "available_time_s")
    required = _positive_seconds(required_reaction_time_s, "required_reaction_time_s")
    return available - required


def reaction_status(margin_s):
    """Return 'positive', 'exhausted' or 'negative' for a reaction margin."""
    if isinstance(margin_s, bool) or not isinstance(margin_s, (int, float)):
        raise ValueError("margin_s must be a real number, got %r" % (margin_s,))
    margin = float(margin_s)
    if not math.isfinite(margin):
        raise ValueError("margin_s must be finite")
    if math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=REACTION_TOLERANCE_S):
        return "exhausted"
    return "positive" if margin > 0.0 else "negative"


def validate_operation(operation, position=0):
    """Return one normalised operation record; raise on a malformed one."""
    if not isinstance(operation, dict):
        raise ValueError("operations[%d] must be a mapping" % position)
    unknown = sorted(key for key in operation if key not in OPERATION_FIELDS)
    if unknown:
        raise ValueError(
            "operations[%d] carries unknown keys: %s" % (position, ", ".join(unknown))
        )
    identifier = operation.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("operations[%d].id must be a non-empty string" % position)
    hazard = operation.get("hazard")
    if not isinstance(hazard, str) or not hazard.strip():
        raise ValueError("operations[%d].hazard must be a non-empty string" % position)
    control_type = operation.get("control_type")
    if control_type is not None:
        control_type = validate_control_type(control_type)
    verification = operation.get("verification")
    if verification is not None:
        if not isinstance(verification, str) or not verification.strip():
            raise ValueError(
                "operations[%d].verification must be a non-empty string when given" % position
            )
        verification = verification.strip()
    exposed = operation.get("personnel_exposed", False)
    if not isinstance(exposed, bool):
        raise ValueError("operations[%d].personnel_exposed must be a boolean" % position)
    available = operation.get("available_time_s")
    required = operation.get("required_reaction_time_s")
    if available is not None:
        available = _positive_seconds(available, "operations[%d].available_time_s" % position)
    if required is not None:
        required = _positive_seconds(
            required, "operations[%d].required_reaction_time_s" % position
        )
    return {
        "id": identifier.strip(),
        "phase": validate_phase(operation.get("phase")),
        "hazard": hazard.strip(),
        "severity": validate_severity(operation.get("severity")),
        "control_type": control_type,
        "verification": verification,
        "available_time_s": available,
        "required_reaction_time_s": required,
        "personnel_exposed": exposed,
    }


def assess_operation(operation, position=0):
    """Grade one operational hazard control against the clause's rules."""
    record = validate_operation(operation, position)
    findings = []
    rank = None
    allowed = maximum_control_rank(record["severity"])
    if record["control_type"] is None:
        findings.append(
            "%s (%s) carries no hazard control for %s"
            % (record["id"], record["phase"], record["hazard"])
        )
    else:
        rank = control_rank(record["control_type"])
        if rank > allowed:
            findings.append(
                "%s rests a %s hazard on %s, weaker than the precedence allows"
                % (record["id"], record["severity"], record["control_type"])
            )
        if record["verification"] is None:
            findings.append("%s declares a control with no verification" % record["id"])
    margin = None
    status = None
    if record["phase"] in FLIGHT_PHASES:
        if record["available_time_s"] is None or record["required_reaction_time_s"] is None:
            findings.append(
                "%s is a flight-phase constraint with no reaction-time budget declared"
                % record["id"]
            )
        else:
            margin = reaction_margin_s(
                record["available_time_s"], record["required_reaction_time_s"]
            )
            status = reaction_status(margin)
            if status != "positive":
                findings.append(
                    "%s leaves a %s reaction margin of %.3f s" % (record["id"], status, margin)
                )
    elif record["available_time_s"] is not None and record["required_reaction_time_s"] is not None:
        margin = reaction_margin_s(
            record["available_time_s"], record["required_reaction_time_s"]
        )
        status = reaction_status(margin)
        if status == "negative":
            findings.append(
                "%s needs more reaction time than the ground task leaves" % record["id"]
            )
    if (
        record["personnel_exposed"]
        and record["phase"] in GROUND_PHASES
        and (rank is None or rank >= CONTROL_PRECEDENCE.index("procedure-and-training"))
    ):
        findings.append(
            "%s exposes personnel with nothing stronger than procedure and training"
            % record["id"]
        )
    return {
        "id": record["id"],
        "phase": record["phase"],
        "phase_set": "ground" if record["phase"] in GROUND_PHASES else "flight",
        "hazard": record["hazard"],
        "severity": record["severity"],
        "control_type": record["control_type"],
        "control_rank": rank,
        "maximum_control_rank": allowed,
        "verified": record["verification"] is not None,
        "reaction_margin_s": margin,
        "reaction_status": status,
        "personnel_exposed": record["personnel_exposed"],
        "findings": findings,
    }


def phase_coverage(rows, required_phases=None):
    """Return the covered and uncovered phases for a graded operation set."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a sequence of graded operations")
    covered = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or "phase" not in row:
            raise ValueError("rows[%d] must be a graded operation" % index)
        covered.add(row["phase"])
    if required_phases is None:
        required = ()
    else:
        if not isinstance(required_phases, (list, tuple)):
            raise ValueError("required_phases must be a sequence of phase names")
        required = tuple(validate_phase(phase) for phase in required_phases)
    uncovered = tuple(phase for phase in OPERATIONAL_PHASES
                      if phase in required and phase not in covered)
    return {
        "covered": tuple(phase for phase in OPERATIONAL_PHASES if phase in covered),
        "required": tuple(phase for phase in OPERATIONAL_PHASES if phase in required),
        "uncovered": uncovered,
    }


def assess_operational_safety(spec):
    """Grade a whole operational-safety set: controls, margins and coverage.

    spec keys: operations (sequence of operation records) and optional
    required_phases (phases the programme declared hazardous).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "operations" not in spec:
        raise ValueError("spec missing required key 'operations'")
    operations = spec["operations"]
    if not isinstance(operations, (list, tuple)) or not operations:
        raise ValueError("spec['operations'] must be a non-empty sequence")
    rows = []
    seen = set()
    for position, operation in enumerate(operations):
        row = assess_operation(operation, position)
        key = row["id"].lower()
        if key in seen:
            raise ValueError("operation id %r appears twice" % row["id"])
        seen.add(key)
        rows.append(row)
    coverage = phase_coverage(rows, spec.get("required_phases"))
    findings = []
    for row in rows:
        findings.extend(row["findings"])
    for phase in coverage["uncovered"]:
        findings.append("no operation is declared for the hazardous phase %s" % phase)
    return {
        "operations": rows,
        "operation_count": len(rows),
        "ground_count": sum(1 for row in rows if row["phase_set"] == "ground"),
        "flight_count": sum(1 for row in rows if row["phase_set"] == "flight"),
        "coverage": coverage,
        "findings": findings,
        "verdict": "operations-controlled" if not findings else "operations-uncontrolled",
    }
