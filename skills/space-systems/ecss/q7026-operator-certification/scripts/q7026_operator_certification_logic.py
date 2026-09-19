"""Certification of operators who make flight crimped terminations.

Anchor: ECSS-Q-ST-70-26C, the personnel clause of the crimping practice
-- what an operator has to have done before crimping flight hardware,
and what keeps that standing alive afterwards (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Certification rests on two separate legs. Training says the
   operator was taught the process; the qualification sample set says
   the operator's own hands produced conforming terminations. Neither
   leg substitutes for the other.
2. Samples are counted per tool and contact combination, not in total.
   Thirty good samples on one contact family say nothing about the one
   the operator is about to crimp, so an uncovered combination is a
   gap rather than a rounding of the total.
3. Every sample in the required set has to pass both the pull test and
   the visual. A pass rate is not the criterion; a failed sample means
   the set was not demonstrated.
4. Standing decays three ways. The certification itself expires on its
   interval, the vision check expires on its own shorter one, and
   practice lapses when too long has passed since the last crimp.
   These are independent clocks and the earliest one governs.
5. A lapse in practice is a suspension pending refresher samples, not
   a loss of qualification. It routes differently from an expiry and
   from an incomplete sample set, and collapsing them sends operators
   through the wrong queue.
6. A clock landing exactly on its interval has not exceeded it. Days
   are whole numbers here precisely so the boundary is decided by the
   calendar and not by a fraction.

Stdlib only, offline, deterministic.
"""

import datetime

CERTIFIED = "certified-for-flight-crimping"
NOT_QUALIFIED = "not-qualified-training-or-samples-incomplete"
EXPIRED = "certification-expired-requalify"
VISION_OVERDUE = "suspended-vision-check-overdue"
LAPSED = "suspended-practice-lapsed-refresher-samples"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _count(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def parse_date(label, value):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(label, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s %r is not an ISO calendar date" % (label, value))


def validate_scheme(scheme):
    """Validate the declared operator certification scheme."""
    if not isinstance(scheme, dict):
        raise ValueError("scheme must be a mapping")

    modules = scheme.get("required_training_modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("required_training_modules must be a non-empty list")
    modules = sorted({_text("training_module", m).lower() for m in modules})

    combinations = scheme.get("combinations")
    if not isinstance(combinations, list) or not combinations:
        raise ValueError("combinations must be a non-empty list")
    minima = {}
    for row in combinations:
        if not isinstance(row, dict):
            raise ValueError("each combination must be a mapping")
        key = _text("combination", row.get("combination")).lower()
        if key in minima:
            raise ValueError("combination %r is declared twice" % key)
        force = _numeric(
            "minimum_pull_off_n", row.get("minimum_pull_off_n"), 0.0
        )
        if force <= 0.0:
            raise ValueError("minimum_pull_off_n must be greater than zero")
        minima[key] = force

    recert = _count(
        "recertification_interval_days",
        scheme.get("recertification_interval_days"),
        1,
    )
    notice = _count(
        "recertification_notice_days",
        scheme.get("recertification_notice_days", 0),
        0,
    )
    if notice >= recert:
        raise ValueError(
            "recertification_notice_days must be shorter than the interval"
        )

    return {
        "required_training_modules": modules,
        "samples_per_combination": _count(
            "samples_per_combination", scheme.get("samples_per_combination"), 1
        ),
        "combination_minima": minima,
        "vision_check_validity_days": _count(
            "vision_check_validity_days",
            scheme.get("vision_check_validity_days"),
            1,
        ),
        "recertification_interval_days": recert,
        "recertification_notice_days": notice,
        "practice_currency_days": _count(
            "practice_currency_days", scheme.get("practice_currency_days"), 1
        ),
    }


def validate_operator(operator):
    """Validate one operator record."""
    if not isinstance(operator, dict):
        raise ValueError("operator must be a mapping")

    modules = operator.get("training_modules", [])
    if not isinstance(modules, list):
        raise ValueError("training_modules must be a list")

    samples = operator.get("samples", [])
    if not isinstance(samples, list):
        raise ValueError("samples must be a list")
    graded = []
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("each sample must be a mapping")
        graded.append(
            {
                "combination": _text(
                    "combination", sample.get("combination")
                ).lower(),
                "pull_off_force_n": _numeric(
                    "pull_off_force_n", sample.get("pull_off_force_n"), 0.0
                ),
                "visual_pass": _flag("visual_pass", sample.get("visual_pass")),
            }
        )

    certification_date = parse_date(
        "certification_date", operator.get("certification_date")
    )
    vision_check_date = parse_date(
        "vision_check_date", operator.get("vision_check_date")
    )
    last_crimp = operator.get("last_crimp_date")
    return {
        "operator_id": _text("operator_id", operator.get("operator_id")),
        "training_modules": sorted(
            {_text("training_module", m).lower() for m in modules}
        ),
        "samples": graded,
        "certification_date": certification_date,
        "vision_check_date": vision_check_date,
        "last_crimp_date": (
            None if last_crimp is None else parse_date("last_crimp_date", last_crimp)
        ),
    }


def missing_training_modules(operator, scheme):
    """Which required training modules the operator has not completed."""
    checked_operator = validate_operator(operator)
    checked_scheme = validate_scheme(scheme)
    held = set(checked_operator["training_modules"])
    return [
        module
        for module in checked_scheme["required_training_modules"]
        if module not in held
    ]


def grade_sample(sample, scheme):
    """Grade one qualification sample against its combination minimum."""
    checked_scheme = validate_scheme(scheme)
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    combination = _text("combination", sample.get("combination")).lower()
    if combination not in checked_scheme["combination_minima"]:
        raise ValueError(
            "combination %r has no declared pull-off minimum" % combination
        )
    minimum = checked_scheme["combination_minima"][combination]
    force = _numeric("pull_off_force_n", sample.get("pull_off_force_n"), 0.0)
    visual = _flag("visual_pass", sample.get("visual_pass"))
    pull_pass = force >= minimum - 1.0e-9
    return {
        "combination": combination,
        "minimum_n": minimum,
        "measured_n": force,
        "pull_pass": pull_pass,
        "visual_pass": visual,
        "pass": pull_pass and visual,
    }


def sample_coverage(operator, scheme):
    """Which combinations the operator's sample set actually demonstrates."""
    checked_operator = validate_operator(operator)
    checked_scheme = validate_scheme(scheme)
    needed = checked_scheme["samples_per_combination"]

    per_combination = {}
    for combination in checked_scheme["combination_minima"]:
        per_combination[combination] = {"submitted": 0, "passed": 0, "failed": 0}

    for sample in checked_operator["samples"]:
        graded = grade_sample(sample, scheme)
        entry = per_combination[graded["combination"]]
        entry["submitted"] += 1
        if graded["pass"]:
            entry["passed"] += 1
        else:
            entry["failed"] += 1

    gaps = []
    for combination in sorted(per_combination):
        entry = per_combination[combination]
        entry["sufficient"] = entry["failed"] == 0 and entry["passed"] >= needed
        if not entry["sufficient"]:
            gaps.append(combination)

    return {
        "required_per_combination": needed,
        "per_combination": per_combination,
        "gaps": gaps,
        "complete": not gaps,
    }


def days_since(reference, as_of):
    """Whole days between a reference date and the date of the check."""
    start = parse_date("reference", reference)
    today = parse_date("as_of", as_of)
    elapsed = (today - start).days
    if elapsed < 0:
        raise ValueError("as_of precedes the reference date")
    return elapsed


def vision_check_state(operator, scheme, as_of):
    """Whether the operator's vision check is still inside its validity."""
    checked_operator = validate_operator(operator)
    checked_scheme = validate_scheme(scheme)
    elapsed = days_since(checked_operator["vision_check_date"], as_of)
    validity = checked_scheme["vision_check_validity_days"]
    return {
        "elapsed_days": elapsed,
        "validity_days": validity,
        "valid": elapsed <= validity,
    }


def certification_state(operator, scheme, as_of):
    """Whether the certification itself is still inside its interval."""
    checked_operator = validate_operator(operator)
    checked_scheme = validate_scheme(scheme)
    elapsed = days_since(checked_operator["certification_date"], as_of)
    interval = checked_scheme["recertification_interval_days"]
    notice = checked_scheme["recertification_notice_days"]
    return {
        "elapsed_days": elapsed,
        "interval_days": interval,
        "valid": elapsed <= interval,
        "due_soon": interval - elapsed <= notice and elapsed <= interval,
    }


def practice_state(operator, scheme, as_of):
    """Whether the operator has crimped recently enough to stay current."""
    checked_operator = validate_operator(operator)
    checked_scheme = validate_scheme(scheme)
    last = checked_operator["last_crimp_date"]
    if last is None:
        return {"elapsed_days": None, "currency_days": checked_scheme[
            "practice_currency_days"
        ], "current": False}
    elapsed = days_since(last, as_of)
    return {
        "elapsed_days": elapsed,
        "currency_days": checked_scheme["practice_currency_days"],
        "current": elapsed <= checked_scheme["practice_currency_days"],
    }


def assess_operator(operator, scheme, as_of):
    """Decide whether this operator may crimp flight hardware today."""
    checked_operator = validate_operator(operator)
    missing = missing_training_modules(operator, scheme)
    coverage = sample_coverage(operator, scheme)
    vision = vision_check_state(operator, scheme, as_of)
    certification = certification_state(operator, scheme, as_of)
    practice = practice_state(operator, scheme, as_of)

    reasons = []
    if missing:
        reasons.append("training-modules-outstanding")
    if coverage["gaps"]:
        reasons.append("qualification-sample-set-incomplete")

    if reasons:
        disposition = NOT_QUALIFIED
    elif not certification["valid"]:
        disposition = EXPIRED
        reasons.append("recertification-interval-exceeded")
    elif not vision["valid"]:
        disposition = VISION_OVERDUE
        reasons.append("vision-check-validity-exceeded")
    elif not practice["current"]:
        disposition = LAPSED
        reasons.append("no-crimp-inside-the-currency-period")
    else:
        disposition = CERTIFIED

    findings = []
    if disposition == CERTIFIED and certification["due_soon"]:
        findings.append("recertification-due-inside-the-notice-period")

    return {
        "operator_id": checked_operator["operator_id"],
        "disposition": disposition,
        "reasons": reasons,
        "findings": findings,
        "missing_training_modules": missing,
        "sample_gaps": coverage["gaps"],
        "vision_check": vision,
        "certification": certification,
        "practice": practice,
        "may_crimp": disposition == CERTIFIED,
    }


def assess_operator_pool(operators, scheme, as_of):
    """Roll a bench of operators up into who may crimp today."""
    if not isinstance(operators, list) or not operators:
        raise ValueError("operators must be a non-empty list")
    results = [assess_operator(o, scheme, as_of) for o in operators]
    return {
        "results": results,
        "may_crimp": [r["operator_id"] for r in results if r["may_crimp"]],
        "suspended": [
            r["operator_id"]
            for r in results
            if r["disposition"] in (VISION_OVERDUE, LAPSED)
        ],
        "requalify": [
            r["operator_id"]
            for r in results
            if r["disposition"] in (EXPIRED, NOT_QUALIFIED)
        ],
        "bench_can_crimp": any(r["may_crimp"] for r in results),
    }
