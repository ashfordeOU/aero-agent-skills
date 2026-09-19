"""Qualification and lot-acceptance programme for explosive devices.

Anchor: ECSS-E-ST-33-11C Rev.1 clause 4.14.4 and the Annex A requirement
mapping (qualification and lot-acceptance test programmes, sample sizes and
test levels). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Check the lot is one lot: a single explosive batch, a single manufacturing
   period, a single build standard. A sample only speaks for a homogeneous
   population.
2. Size the attribute sample from the reliability and confidence the
   specification asks for, allowing for a stated number of failures, using an
   exact binomial tail rather than a normal approximation.
3. Report the reliability a completed zero-failure run actually demonstrates at
   the stated confidence, which is the number the specification is met or
   missed against.
4. Derive qualification test levels from the acceptance levels through the
   qualification factor, and refuse a factor that would test qualification
   below acceptance.
5. Apply the accept/reject rule to the observed failures and report whether the
   run that was actually performed matches the plan it claims to implement.
"""

import math

__all__ = [
    "SNAP_TOLERANCE",
    "MAX_SAMPLE_SIZE",
    "validate_probability",
    "validate_count",
    "snap_to_integer",
    "zero_failure_sample_size",
    "acceptance_probability",
    "attribute_sample_size",
    "demonstrated_reliability",
    "qualification_level",
    "lot_homogeneity",
    "build_sample_plan",
    "lot_verdict",
    "assess_qualification_programme",
]

# A sample size is the ceiling of a ratio of logarithms. Logarithms are not
# correctly rounded, so a ratio that is mathematically an integer can land a
# few ULP either side of it and the ceiling then jumps by one. Snap first.
SNAP_TOLERANCE = 1e-9

# A sample plan that does not converge inside this many units is a
# specification problem, not a search problem.
MAX_SAMPLE_SIZE = 100000


def validate_probability(label, value, allow_one=False):
    """Return value as a probability strictly inside (0, 1), or (0, 1]."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    upper_ok = number <= 1.0 if allow_one else number < 1.0
    if number <= 0.0 or not upper_ok:
        raise ValueError(
            "%s must lie in (0, 1%s, got %r"
            % (label, "]" if allow_one else ")", value)
        )
    return number


def validate_count(label, value, minimum=0):
    """Return value as an integer count at or above a minimum."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def snap_to_integer(value):
    """Return value rounded to a neighbouring integer when it is within tolerance."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number, got %r" % (value,))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("value must be finite, got %r" % (value,))
    nearest = round(number)
    if abs(number - nearest) <= SNAP_TOLERANCE * max(1.0, abs(number)):
        return float(nearest)
    return number


def zero_failure_sample_size(reliability, confidence):
    """Return the units a zero-failure run needs for a reliability at a confidence."""
    r = validate_probability("reliability", reliability)
    c = validate_probability("confidence", confidence)
    raw = math.log(1.0 - c) / math.log(r)
    return int(math.ceil(snap_to_integer(raw)))


def acceptance_probability(sample_size, allowed_failures, defect_rate):
    """Return the probability a lot at this defect rate is accepted by the plan."""
    n = validate_count("sample_size", sample_size, minimum=1)
    c = validate_count("allowed_failures", allowed_failures, minimum=0)
    p = validate_probability("defect_rate", defect_rate, allow_one=True)
    if c >= n:
        return 1.0
    total = 0.0
    for k in range(0, c + 1):
        total += math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))
    if total > 1.0:
        return 1.0
    return total


def attribute_sample_size(reliability, confidence, allowed_failures=0):
    """Return the smallest sample that demonstrates a reliability at a confidence."""
    r = validate_probability("reliability", reliability)
    c = validate_probability("confidence", confidence)
    allowed = validate_count("allowed_failures", allowed_failures, minimum=0)
    if allowed == 0:
        return zero_failure_sample_size(r, c)
    target = 1.0 - c
    n = allowed + 1
    while n <= MAX_SAMPLE_SIZE:
        risk = acceptance_probability(n, allowed, 1.0 - r)
        if risk < target or math.isclose(risk, target, rel_tol=SNAP_TOLERANCE, abs_tol=0.0):
            return n
        n += 1
    raise ValueError(
        "no sample size at or below %d demonstrates reliability %g at confidence %g "
        "with %d allowed failures" % (MAX_SAMPLE_SIZE, r, c, allowed)
    )


def demonstrated_reliability(sample_size, confidence):
    """Return the reliability a completed zero-failure run of this size demonstrates."""
    n = validate_count("sample_size", sample_size, minimum=1)
    c = validate_probability("confidence", confidence)
    return (1.0 - c) ** (1.0 / n)


def qualification_level(acceptance_level, qualification_factor):
    """Return the qualification test level derived from an acceptance level."""
    for label, value in (
        ("acceptance_level", acceptance_level),
        ("qualification_factor", qualification_factor),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    factor = float(qualification_factor)
    if factor < 1.0:
        raise ValueError(
            "qualification_factor must not sit below the acceptance level, got %r"
            % (qualification_factor,)
        )
    return float(acceptance_level) * factor


def lot_homogeneity(units):
    """Report whether a set of units forms one lot."""
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of unit mappings")
    batches = set()
    periods = set()
    builds = set()
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            raise ValueError("units[%d] must be a mapping" % index)
        for key in ("explosive_batch", "manufacturing_period", "build_standard"):
            if key not in unit:
                raise ValueError("units[%d] missing '%s'" % (index, key))
            if not isinstance(unit[key], str) or not unit[key].strip():
                raise ValueError("units[%d]['%s'] must be a non-empty string" % (index, key))
        batches.add(unit["explosive_batch"].strip())
        periods.add(unit["manufacturing_period"].strip())
        builds.add(unit["build_standard"].strip())
    findings = []
    if len(batches) > 1:
        findings.append(
            "lot mixes %d explosive batches: %s" % (len(batches), ", ".join(sorted(batches)))
        )
    if len(periods) > 1:
        findings.append(
            "lot mixes %d manufacturing periods: %s" % (len(periods), ", ".join(sorted(periods)))
        )
    if len(builds) > 1:
        findings.append(
            "lot mixes %d build standards: %s" % (len(builds), ", ".join(sorted(builds)))
        )
    return {
        "lot_size": len(units),
        "batches": sorted(batches),
        "periods": sorted(periods),
        "build_standards": sorted(builds),
        "homogeneous": not findings,
        "findings": findings,
    }


def build_sample_plan(lot_size, reliability, confidence, allowed_failures=0):
    """Return the sample plan for a lot, or refuse one the lot cannot supply."""
    size = validate_count("lot_size", lot_size, minimum=1)
    needed = attribute_sample_size(reliability, confidence, allowed_failures)
    findings = []
    if needed > size:
        findings.append(
            "plan needs %d units but the lot holds %d; the lot cannot demonstrate "
            "the specified reliability" % (needed, size)
        )
    return {
        "lot_size": size,
        "sample_size": needed,
        "allowed_failures": int(allowed_failures),
        "reliability": float(reliability),
        "confidence": float(confidence),
        "feasible": not findings,
        "findings": findings,
    }


def lot_verdict(plan, units_tested, observed_failures):
    """Apply the accept/reject rule of a plan to the run that was performed."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping from build_sample_plan")
    for key in ("sample_size", "allowed_failures", "lot_size"):
        if key not in plan:
            raise ValueError("plan missing '%s'" % key)
    tested = validate_count("units_tested", units_tested, minimum=0)
    failures = validate_count("observed_failures", observed_failures, minimum=0)
    findings = []
    if failures > tested:
        raise ValueError(
            "observed_failures %d exceeds units_tested %d" % (failures, tested)
        )
    if tested < plan["sample_size"]:
        findings.append(
            "run tested %d units against a plan of %d" % (tested, plan["sample_size"])
        )
    if tested > plan["lot_size"]:
        findings.append(
            "run tested %d units from a lot of %d" % (tested, plan["lot_size"])
        )
    accepted = failures <= plan["allowed_failures"]
    if not accepted:
        findings.append(
            "lot rejected: %d failures against %d allowed"
            % (failures, plan["allowed_failures"])
        )
    return {
        "units_tested": tested,
        "observed_failures": failures,
        "accepted": accepted and not findings,
        "plan_followed": tested >= plan["sample_size"] and tested <= plan["lot_size"],
        "findings": findings,
    }


def assess_qualification_programme(spec):
    """Run the full clause 4.14.4 qualification and lot-acceptance assessment.

    spec keys: units, reliability, confidence, optional allowed_failures,
    units_tested, observed_failures, acceptance_level, qualification_factor,
    declared_qualification_level.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("units", "reliability", "confidence"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    homogeneity = lot_homogeneity(spec["units"])
    plan = build_sample_plan(
        homogeneity["lot_size"],
        spec["reliability"],
        spec["confidence"],
        spec.get("allowed_failures", 0),
    )
    verdict = lot_verdict(
        plan,
        spec.get("units_tested", plan["sample_size"]),
        spec.get("observed_failures", 0),
    )
    levels = None
    findings = list(homogeneity["findings"]) + list(plan["findings"]) + list(verdict["findings"])
    if "acceptance_level" in spec and "qualification_factor" in spec:
        required = qualification_level(spec["acceptance_level"], spec["qualification_factor"])
        declared = spec.get("declared_qualification_level", required)
        if not isinstance(declared, (int, float)) or isinstance(declared, bool):
            raise ValueError("declared_qualification_level must be a real number")
        declared = float(declared)
        shortfall = declared < required and not math.isclose(
            declared, required, rel_tol=SNAP_TOLERANCE, abs_tol=0.0
        )
        if shortfall:
            findings.append(
                "declared qualification level %.6g is below the required %.6g"
                % (declared, required)
            )
        levels = {
            "required_level": required,
            "declared_level": declared,
            "adequate": not shortfall,
        }
    if verdict["observed_failures"] == 0 and verdict["units_tested"] > 0:
        shown = demonstrated_reliability(verdict["units_tested"], spec["confidence"])
    else:
        shown = None
    return {
        "homogeneity": homogeneity,
        "plan": plan,
        "verdict": verdict,
        "levels": levels,
        "demonstrated_reliability": shown,
        "qualified": not findings,
        "findings": findings,
    }
