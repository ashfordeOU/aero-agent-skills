"""Required contents of the device validation plan.

Anchor: ECSS-E-ST-20-40C Annex D (device validation plan data item -- the
validation approach, the use cases the device is validated against and the
pass criteria applied to each validation activity). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the supplied section list against the required contents of the plan.
2. Validate every use case (identifier, positive criticality weight, explicit
   safety-driving flag) and every validation activity (identifier, recognized
   approach, non-empty covered-use-case list, pass criterion).
3. Build the use-case-to-activity coverage matrix and compute the
   criticality-weighted coverage fraction.
4. Detect approach shortfalls: a safety-driving use case covered only by
   arguing approaches (analysis, similarity, review-of-design) and never by an
   observing approach (test, demonstration).
5. Grade each pass criterion for measurability (comparator, finite bound,
   real unit, tolerance behind an equality) and evaluate a measured value
   against a criterion when one is supplied.
6. Report the coverage fraction against the required threshold together with
   the uncovered use cases, unmeasurable criteria and approach shortfalls.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "OBSERVING_APPROACHES",
    "ARGUING_APPROACHES",
    "APPROACHES",
    "COVERAGE_TOLERANCE",
    "PLACEHOLDER_UNITS",
    "missing_sections",
    "validate_use_case",
    "validate_use_cases",
    "validate_criterion",
    "validate_activity",
    "validate_activities",
    "coverage_matrix",
    "weighted_coverage_fraction",
    "approach_shortfalls",
    "criterion_measurability",
    "evaluate_criterion",
    "assess_validation_plan",
]

# Sections the data item has to carry before coverage can be assessed at all.
REQUIRED_SECTIONS = (
    "scope",
    "validation-approach",
    "use-cases",
    "validation-activities",
    "pass-criteria",
    "schedule-and-resources",
)

# Approaches that produce an observation on the device itself.
OBSERVING_APPROACHES = ("test", "demonstration")

# Approaches that produce an argument about the device.
ARGUING_APPROACHES = ("analysis", "similarity", "review-of-design")

APPROACHES = OBSERVING_APPROACHES + ARGUING_APPROACHES

# Coverage comparisons are a ratio of sums: an exact equality can land a few
# ULPs on the wrong side. Absorb the representation error here instead of
# relaxing the required fraction.
COVERAGE_TOLERANCE = 1e-12

# Unit strings that look filled in but carry no measurable dimension.
PLACEHOLDER_UNITS = ("tbd", "tbc", "n/a", "na", "-", "none")

_COMPARATORS = ("<=", ">=", "<", ">", "==")


def _real(value, label):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _identifier(value, label):
    """Return value as a non-empty stripped identifier string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def missing_sections(sections):
    """Return the required sections absent from the supplied section list."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list or tuple of section names")
    present = set()
    for i, name in enumerate(sections):
        present.add(_identifier(name, "sections[%d]" % i).lower())
    return [name for name in REQUIRED_SECTIONS if name not in present]


def validate_use_case(use_case):
    """Return a normalized use-case record."""
    if not isinstance(use_case, dict):
        raise ValueError("use case must be a mapping")
    for key in ("id", "criticality_weight", "safety_driving"):
        if key not in use_case:
            raise ValueError("use case missing required key '%s'" % key)
    identifier = _identifier(use_case["id"], "use case id")
    weight = _real(use_case["criticality_weight"], "criticality_weight of %s" % identifier)
    if weight <= 0.0:
        raise ValueError("criticality_weight of %s must be positive, got %g" % (identifier, weight))
    flag = use_case["safety_driving"]
    if not isinstance(flag, bool):
        raise ValueError("safety_driving of %s must be a boolean" % identifier)
    return {"id": identifier, "criticality_weight": weight, "safety_driving": flag}


def validate_use_cases(use_cases):
    """Return the normalized use-case records, rejecting duplicate identifiers."""
    if not isinstance(use_cases, (list, tuple)) or not use_cases:
        raise ValueError("use_cases must be a non-empty sequence")
    records = []
    seen = set()
    for item in use_cases:
        record = validate_use_case(item)
        if record["id"] in seen:
            raise ValueError("duplicate use-case identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def validate_criterion(criterion, label="pass criterion"):
    """Return a normalized pass-criterion record."""
    if not isinstance(criterion, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("comparator", "bound", "unit"):
        if key not in criterion:
            raise ValueError("%s missing required key '%s'" % (label, key))
    comparator = _identifier(criterion["comparator"], "%s comparator" % label)
    if comparator not in _COMPARATORS:
        raise ValueError(
            "%s comparator %r is not one of %s" % (label, comparator, ", ".join(_COMPARATORS))
        )
    bound = _real(criterion["bound"], "%s bound" % label)
    unit = _identifier(criterion["unit"], "%s unit" % label)
    tolerance = criterion.get("tolerance")
    if tolerance is not None:
        tolerance = _real(tolerance, "%s tolerance" % label)
        if tolerance < 0.0:
            raise ValueError("%s tolerance must not be negative" % label)
    return {"comparator": comparator, "bound": bound, "unit": unit, "tolerance": tolerance}


def validate_activity(activity, known_use_case_ids):
    """Return a normalized validation-activity record."""
    if not isinstance(activity, dict):
        raise ValueError("validation activity must be a mapping")
    for key in ("id", "approach", "covers", "criterion"):
        if key not in activity:
            raise ValueError("validation activity missing required key '%s'" % key)
    identifier = _identifier(activity["id"], "activity id")
    approach = _identifier(activity["approach"], "approach of %s" % identifier).lower()
    if approach not in APPROACHES:
        raise ValueError(
            "approach %r of %s is not one of %s" % (approach, identifier, ", ".join(APPROACHES))
        )
    covers = activity["covers"]
    if not isinstance(covers, (list, tuple)) or not covers:
        raise ValueError("activity %s must cover at least one use case" % identifier)
    resolved = []
    for i, ref in enumerate(covers):
        ref_id = _identifier(ref, "activity %s covers[%d]" % (identifier, i))
        if ref_id not in known_use_case_ids:
            raise ValueError(
                "activity %s covers %r, which no use case declares" % (identifier, ref_id)
            )
        if ref_id not in resolved:
            resolved.append(ref_id)
    criterion = validate_criterion(activity["criterion"], "criterion of %s" % identifier)
    return {
        "id": identifier,
        "approach": approach,
        "covers": resolved,
        "criterion": criterion,
    }


def validate_activities(activities, known_use_case_ids):
    """Return the normalized activity records, rejecting duplicate identifiers."""
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("activities must be a non-empty sequence")
    records = []
    seen = set()
    for item in activities:
        record = validate_activity(item, known_use_case_ids)
        if record["id"] in seen:
            raise ValueError("duplicate activity identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def coverage_matrix(use_cases, activities):
    """Return use-case identifier -> ordered list of covering activity identifiers."""
    matrix = dict((record["id"], []) for record in use_cases)
    for activity in activities:
        for ref in activity["covers"]:
            if ref in matrix and activity["id"] not in matrix[ref]:
                matrix[ref].append(activity["id"])
    return matrix


def weighted_coverage_fraction(use_cases, matrix):
    """Return covered criticality weight divided by total criticality weight."""
    if not use_cases:
        raise ValueError("cannot compute coverage over an empty use-case set")
    total = 0.0
    covered = 0.0
    for record in use_cases:
        total += record["criticality_weight"]
        if matrix.get(record["id"]):
            covered += record["criticality_weight"]
    if total <= 0.0:
        raise ValueError("total criticality weight must be positive")
    return covered / total


def approach_shortfalls(use_cases, activities, matrix):
    """Return safety-driving use cases held up by arguing approaches only."""
    by_id = dict((activity["id"], activity) for activity in activities)
    shortfalls = []
    for record in use_cases:
        if not record["safety_driving"]:
            continue
        covering = matrix.get(record["id"], [])
        if not covering:
            continue
        approaches = [by_id[a]["approach"] for a in covering]
        if not any(a in OBSERVING_APPROACHES for a in approaches):
            shortfalls.append(record["id"])
    return shortfalls


def criterion_measurability(criterion):
    """Return (measurable, reason) for a normalized pass criterion."""
    if not isinstance(criterion, dict) or "comparator" not in criterion:
        raise ValueError("criterion must be a normalized criterion mapping")
    if criterion["unit"].strip().lower() in PLACEHOLDER_UNITS:
        return (False, "unit %r is a placeholder, not a dimension" % criterion["unit"])
    if criterion["comparator"] == "==" and criterion["tolerance"] is None:
        return (False, "equality criterion carries no tolerance")
    if criterion["comparator"] == "==" and criterion["tolerance"] == 0.0:
        return (False, "equality criterion carries a zero tolerance")
    return (True, "")


def evaluate_criterion(criterion, measured_value):
    """Return True when the measured value meets the normalized criterion."""
    measurable, reason = criterion_measurability(criterion)
    if not measurable:
        raise ValueError("criterion is not measurable: %s" % reason)
    value = _real(measured_value, "measured_value")
    bound = criterion["bound"]
    comparator = criterion["comparator"]
    slack = criterion["tolerance"] if criterion["tolerance"] is not None else 0.0
    if comparator == "==":
        return abs(value - bound) <= slack
    if comparator == "<=":
        return value <= bound + slack or math.isclose(value, bound, rel_tol=0.0, abs_tol=slack)
    if comparator == ">=":
        return value >= bound - slack or math.isclose(value, bound, rel_tol=0.0, abs_tol=slack)
    if comparator == "<":
        return value < bound - slack
    return value > bound + slack


def assess_validation_plan(plan):
    """Run the full Annex D validation-plan content assessment.

    plan keys: sections, use_cases, activities, required_coverage_fraction.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    for key in ("sections", "use_cases", "activities", "required_coverage_fraction"):
        if key not in plan:
            raise ValueError("plan missing required key '%s'" % key)
    required = _real(plan["required_coverage_fraction"], "required_coverage_fraction")
    if required < 0.0 or required > 1.0:
        raise ValueError("required_coverage_fraction must lie in [0, 1], got %g" % required)

    absent = missing_sections(plan["sections"])
    use_cases = validate_use_cases(plan["use_cases"])
    known = set(record["id"] for record in use_cases)
    activities = validate_activities(plan["activities"], known)
    matrix = coverage_matrix(use_cases, activities)
    fraction = weighted_coverage_fraction(use_cases, matrix)
    uncovered = [record["id"] for record in use_cases if not matrix[record["id"]]]
    shortfalls = approach_shortfalls(use_cases, activities, matrix)

    unmeasurable = []
    for activity in activities:
        measurable, reason = criterion_measurability(activity["criterion"])
        if not measurable:
            unmeasurable.append({"activity": activity["id"], "reason": reason})

    findings = []
    for name in absent:
        findings.append("required section %r is absent from the plan" % name)
    for ref in uncovered:
        findings.append("use case %s is covered by no validation activity" % ref)
    for entry in unmeasurable:
        findings.append(
            "pass criterion of activity %s is not measurable: %s"
            % (entry["activity"], entry["reason"])
        )
    for ref in shortfalls:
        findings.append(
            "safety-driving use case %s is covered by arguing approaches only" % ref
        )
    coverage_met = fraction > required or math.isclose(
        fraction, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if not coverage_met:
        findings.append(
            "criticality-weighted coverage %.4f is below the required %.4f" % (fraction, required)
        )
    return {
        "missing_sections": absent,
        "use_cases": use_cases,
        "activities": activities,
        "coverage_matrix": matrix,
        "coverage_fraction": fraction,
        "required_coverage_fraction": required,
        "uncovered_use_cases": uncovered,
        "unmeasurable_criteria": unmeasurable,
        "approach_shortfalls": shortfalls,
        "coverage_met": coverage_met,
        "compliant": not findings,
        "findings": findings,
    }
