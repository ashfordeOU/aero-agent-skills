"""Coverage of the two ways a faulted start up can be triggered.

Anchor: ECSS-E-ST-20C clause 5.2.7.6.1 (the faulted start-up behaviour
required of a current limiter holds for a commanded turn on and equally for a
turn on produced by the bus voltage rising, so the verification evidence has
to reach both). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared fault conditions and the verification case records.
2. Fold each case's trigger onto one of the two routes the clause names: a
   commanded turn on, or a rise of the main bus voltage. A trigger that folds
   onto neither is refused rather than guessed at.
3. Build the required matrix as every declared fault condition against both
   routes, and place each case in its cell.
4. Count a cell as covered only by a case that actually ran and passed. A
   planned case and a failed case are both recorded, and neither covers.
5. Report the uncovered cells in the terms of the clause: a condition
   exercised on one route only is the failure the clause exists to prevent.
6. Report cases naming a condition that was never declared, and a route with
   no case anywhere in the set, as findings of their own.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "TRIGGER_ROUTES",
    "CASE_OUTCOMES",
    "normalise_trigger",
    "normalise_condition",
    "normalise_outcome",
    "validate_case",
    "validate_case_set",
    "validate_conditions",
    "required_cells",
    "build_matrix",
    "uncovered_cells",
    "coverage_fraction",
    "assess_trigger_coverage",
]

# The coverage fraction is a ratio of small counts, but the required fraction
# is declared project data and can be written as a decimal that does not
# represent exactly. Absorb that here rather than by rounding the ratio.
FRACTION_TOLERANCE = 1e-12

TRIGGER_ROUTES = ("commanded-turn-on", "rising-bus-voltage")
CASE_OUTCOMES = ("pass", "fail", "not-run")

_TRIGGER_ALIASES = {
    "commanded-turn-on": "commanded-turn-on",
    "commanded": "commanded-turn-on",
    "command": "commanded-turn-on",
    "turn-on-command": "commanded-turn-on",
    "on-command": "commanded-turn-on",
    "switch-on-command": "commanded-turn-on",
    "telecommand": "commanded-turn-on",
    "rising-bus-voltage": "rising-bus-voltage",
    "bus-voltage-rise": "rising-bus-voltage",
    "bus-voltage-ramp": "rising-bus-voltage",
    "rising-bus": "rising-bus-voltage",
    "bus-power-up": "rising-bus-voltage",
    "main-bus-rise": "rising-bus-voltage",
    "power-up": "rising-bus-voltage",
}

_OUTCOME_ALIASES = {
    "pass": "pass",
    "passed": "pass",
    "ok": "pass",
    "fail": "fail",
    "failed": "fail",
    "not-run": "not-run",
    "notrun": "not-run",
    "planned": "not-run",
    "pending": "not-run",
    "open": "not-run",
}


def _token(value, label):
    """Return a lowercase hyphenated token for a declared name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def normalise_trigger(value, label="trigger"):
    """Return the clause route a declared trigger belongs to."""
    token = _token(value, label)
    if token not in _TRIGGER_ALIASES:
        raise ValueError(
            "%s %r folds onto neither %s nor %s; name the route explicitly"
            % (label, value, TRIGGER_ROUTES[0], TRIGGER_ROUTES[1])
        )
    return _TRIGGER_ALIASES[token]


def normalise_condition(value, label="fault_condition"):
    """Return the normalised name of a declared downstream fault condition."""
    return _token(value, label)


def normalise_outcome(value, label="outcome"):
    """Return the normalised outcome of a verification case."""
    token = _token(value, label)
    if token not in _OUTCOME_ALIASES:
        raise ValueError(
            "%s must name one of %s, got %r" % (label, CASE_OUTCOMES, value)
        )
    return _OUTCOME_ALIASES[token]


def validate_conditions(conditions):
    """Return the validated, de-duplicated fault condition set."""
    if not isinstance(conditions, (list, tuple)) or not conditions:
        raise ValueError("fault_conditions must be a non-empty sequence")
    seen = []
    for i, item in enumerate(conditions):
        token = normalise_condition(item, "fault_conditions[%d]" % i)
        if token in seen:
            raise ValueError("fault condition %r is declared twice" % (token,))
        seen.append(token)
    return seen


def validate_case(case, index):
    """Return one validated verification case record."""
    if not isinstance(case, dict):
        raise ValueError("case[%d] must be a mapping" % index)
    for key in ("trigger", "fault_condition", "outcome"):
        if key not in case:
            raise ValueError("case[%d] missing required key '%s'" % (index, key))
    return {
        "id": str(case.get("id", "case-%d" % index)),
        "trigger": normalise_trigger(case["trigger"], "case[%d].trigger" % index),
        "declared_trigger": str(case["trigger"]),
        "fault_condition": normalise_condition(
            case["fault_condition"], "case[%d].fault_condition" % index
        ),
        "outcome": normalise_outcome(case["outcome"], "case[%d].outcome" % index),
    }


def validate_case_set(cases):
    """Return the validated case set, refusing repeated case identifiers."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")
    records = [validate_case(c, i) for i, c in enumerate(cases)]
    ids = [r["id"] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError("case ids must be unique, got %r" % (ids,))
    return records


def required_cells(conditions):
    """Return every declared fault condition against both clause routes."""
    tokens = validate_conditions(conditions)
    return [(condition, route) for condition in tokens for route in TRIGGER_ROUTES]


def build_matrix(cases, conditions):
    """Return the coverage matrix and the cases that fall outside it."""
    tokens = validate_conditions(conditions)
    records = validate_case_set(cases)
    matrix = {}
    for cell in required_cells(tokens):
        matrix[cell] = {"pass": [], "fail": [], "not-run": []}
    undeclared = []
    for record in records:
        cell = (record["fault_condition"], record["trigger"])
        if cell not in matrix:
            undeclared.append(record)
            continue
        matrix[cell][record["outcome"]].append(record["id"])
    return {"matrix": matrix, "undeclared": undeclared, "cases": records}


def uncovered_cells(matrix):
    """Return the cells carrying no case that ran and passed."""
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping of cells")
    out = []
    for cell in sorted(matrix):
        if not matrix[cell]["pass"]:
            out.append(cell)
    return out


def coverage_fraction(matrix):
    """Return the share of required cells carrying a passing case."""
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping of cells")
    covered = sum(1 for cell in matrix if matrix[cell]["pass"])
    return covered / float(len(matrix))


def _other_route(route):
    return TRIGGER_ROUTES[1] if route == TRIGGER_ROUTES[0] else TRIGGER_ROUTES[0]


def assess_trigger_coverage(spec):
    """Run the full clause 5.2.7.6.1 trigger coverage assessment.

    spec keys: fault_conditions, cases, optional required_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("fault_conditions", "cases"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = spec.get("required_fraction", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_fraction must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_fraction must sit in [0, 1], got %r" % (required,))

    built = build_matrix(spec["cases"], spec["fault_conditions"])
    matrix = built["matrix"]
    uncovered = uncovered_cells(matrix)
    fraction = coverage_fraction(matrix)

    findings = []
    for condition, route in uncovered:
        twin = (condition, _other_route(route))
        if matrix[twin]["pass"]:
            findings.append(
                "fault condition %s is evidenced on the %s route only; the clause "
                "carries the same behaviour onto the %s route"
                % (condition, _other_route(route), route)
            )
        else:
            findings.append(
                "fault condition %s has no passing case on the %s route"
                % (condition, route)
            )
    for record in built["cases"]:
        if record["outcome"] == "fail":
            findings.append(
                "case %s failed on %s against %s"
                % (record["id"], record["trigger"], record["fault_condition"])
            )
        elif record["outcome"] == "not-run":
            findings.append(
                "case %s is still open on %s against %s and covers nothing yet"
                % (record["id"], record["trigger"], record["fault_condition"])
            )
    for record in built["undeclared"]:
        findings.append(
            "case %s names fault condition %s, which is not in the declared set"
            % (record["id"], record["fault_condition"])
        )
    for route in TRIGGER_ROUTES:
        if not any(r["trigger"] == route for r in built["cases"]):
            findings.append(
                "no case anywhere in the set is triggered by %s" % route
            )

    meets_fraction = fraction > required or math.isclose(
        fraction, required, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    return {
        "matrix": matrix,
        "cases": built["cases"],
        "undeclared": built["undeclared"],
        "uncovered_cells": uncovered,
        "coverage_fraction": fraction,
        "required_fraction": required,
        "meets_required_fraction": meets_fraction,
        "findings": findings,
        "compliant": meets_fraction and not findings,
    }
