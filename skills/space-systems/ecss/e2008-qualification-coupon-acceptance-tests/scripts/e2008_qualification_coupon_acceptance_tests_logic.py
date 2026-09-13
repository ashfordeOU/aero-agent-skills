"""Acceptance decision for a lot of solar-array qualification coupons.

Anchor: ECSS-E-ST-20-08C clause 5.5.2 (acceptance testing carried out on
qualification coupons to confirm the workmanship quality a supplier delivers).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Size the coupon sample the delivered lot has to be represented by, from a
   sampling fraction and a floor, never exceeding the lot itself.
2. Evaluate every acceptance measurement on every coupon against its limit in
   the correct direction of merit ("min" -- the measurement must reach the
   limit; "max" -- it must not exceed it), expressing each result as a margin
   fraction of the limit so measurements in different units compare.
3. Group the workmanship imperfections observed on the coupons by severity
   grade and compare each grade total with the allowance the acceptance
   specification carries for it.
4. Accept the lot only when the sample is large enough, no coupon fails a
   check, and no severity grade exceeds its allowance; otherwise report which
   of those three gates the lot fell at.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "CEIL_GUARD",
    "DEFAULT_SAMPLE_FRACTION",
    "DEFAULT_MINIMUM_SAMPLE",
    "SEVERITY_GRADES",
    "required_sample_size",
    "margin_fraction",
    "evaluate_check",
    "evaluate_coupon",
    "group_imperfections",
    "assess_coupon_lot",
]

# Margin comparisons are ratios of floats; a measurement sitting exactly on
# its limit can land a few ULPs either side. Absorb the representation error
# here instead of moving the acceptance limit.
MARGIN_TOLERANCE = 1e-9

# A sampling fraction times an integer lot size is a float product, so a whole
# number can arrive as 3.0000000000000004 and round up a whole coupon. Nudge
# down by far less than one coupon before taking the ceiling.
CEIL_GUARD = 1e-9

DEFAULT_SAMPLE_FRACTION = 0.10
DEFAULT_MINIMUM_SAMPLE = 3

# Workmanship imperfections are grouped by severity, worst grade first.
SEVERITY_GRADES = ("critical", "major", "minor")

DIRECTIONS = ("min", "max")


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative:
        if allow_zero and number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
        if not allow_zero and number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _count(label, value, allow_zero=True):
    """Return value as a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    if not allow_zero and value == 0:
        raise ValueError("%s must be greater than zero" % label)
    return value


def required_sample_size(lot_size, fraction=DEFAULT_SAMPLE_FRACTION,
                         minimum=DEFAULT_MINIMUM_SAMPLE):
    """Return how many coupons the lot has to be represented by."""
    size = _count("lot_size", lot_size, allow_zero=False)
    share = _real("fraction", fraction)
    if share > 1.0:
        raise ValueError("fraction must not exceed 1.0, got %r" % (fraction,))
    floor = _count("minimum", minimum, allow_zero=False)
    proportional = math.ceil(share * size - CEIL_GUARD)
    needed = max(floor, proportional)
    return min(needed, size)


def margin_fraction(measured, limit, direction):
    """Return the margin on a measurement as a fraction of its limit."""
    if direction not in DIRECTIONS:
        raise ValueError(
            "direction must be one of %s, got %r" % (", ".join(DIRECTIONS), direction)
        )
    value = _real("measured", measured, allow_negative=True)
    bound = _real("limit", limit, allow_negative=True)
    if bound == 0.0:
        raise ValueError("limit must be non-zero to express a margin fraction")
    if direction == "min":
        return (value - bound) / abs(bound)
    return (bound - value) / abs(bound)


def evaluate_check(check):
    """Evaluate one acceptance check and return its record."""
    if not isinstance(check, dict):
        raise ValueError("check must be a mapping")
    for key in ("name", "measured", "limit", "direction"):
        if key not in check:
            raise ValueError("check is missing required key '%s'" % key)
    name = check["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("check['name'] must be a non-empty string")
    margin = margin_fraction(check["measured"], check["limit"], check["direction"])
    conforms = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    return {
        "name": name.strip(),
        "measured": float(check["measured"]),
        "limit": float(check["limit"]),
        "direction": check["direction"],
        "margin_fraction": margin,
        "conforms": conforms,
    }


def _validate_criteria(criteria):
    """Return the acceptance criteria as an ordered list of validated entries."""
    if not isinstance(criteria, (list, tuple)) or not criteria:
        raise ValueError("criteria must be a non-empty sequence of acceptance checks")
    entries = []
    names = set()
    for index, item in enumerate(criteria):
        if not isinstance(item, dict):
            raise ValueError("criteria[%d] must be a mapping" % index)
        for key in ("name", "limit", "direction"):
            if key not in item:
                raise ValueError("criteria[%d] is missing required key '%s'" % (index, key))
        name = item["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("criteria[%d]['name'] must be a non-empty string" % index)
        name = name.strip()
        if name in names:
            raise ValueError("criterion '%s' is defined twice" % name)
        names.add(name)
        if item["direction"] not in DIRECTIONS:
            raise ValueError(
                "criteria[%d]['direction'] must be one of %s"
                % (index, ", ".join(DIRECTIONS))
            )
        limit = _real("criteria[%d]['limit']" % index, item["limit"], allow_negative=True)
        if limit == 0.0:
            raise ValueError("criteria[%d]['limit'] must be non-zero" % index)
        entries.append({"name": name, "limit": limit, "direction": item["direction"]})
    return entries


def _validate_imperfections(label, counts):
    """Return a severity-grade count map, zero-filled for absent grades."""
    if counts is None:
        return {grade: 0 for grade in SEVERITY_GRADES}
    if not isinstance(counts, dict):
        raise ValueError("%s must be a mapping of severity grade to count" % label)
    result = {grade: 0 for grade in SEVERITY_GRADES}
    for grade, value in counts.items():
        if grade not in SEVERITY_GRADES:
            raise ValueError(
                "%s carries unknown severity grade %r; use one of %s"
                % (label, grade, ", ".join(SEVERITY_GRADES))
            )
        result[grade] = _count("%s['%s']" % (label, grade), value)
    return result


def evaluate_coupon(coupon, criteria):
    """Evaluate one qualification coupon against the acceptance criteria."""
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping")
    for key in ("id", "measurements"):
        if key not in coupon:
            raise ValueError("coupon is missing required key '%s'" % key)
    coupon_id = coupon["id"]
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon['id'] must be a non-empty string")
    measurements = coupon["measurements"]
    if not isinstance(measurements, dict):
        raise ValueError("coupon['measurements'] must be a mapping")
    entries = _validate_criteria(criteria)
    checks = []
    failed = []
    for entry in entries:
        if entry["name"] not in measurements:
            raise ValueError(
                "coupon '%s' has no measurement for acceptance check '%s'"
                % (coupon_id.strip(), entry["name"])
            )
        record = evaluate_check(
            {
                "name": entry["name"],
                "measured": measurements[entry["name"]],
                "limit": entry["limit"],
                "direction": entry["direction"],
            }
        )
        checks.append(record)
        if not record["conforms"]:
            failed.append(record["name"])
    imperfections = _validate_imperfections(
        "coupon['imperfections']", coupon.get("imperfections")
    )
    return {
        "id": coupon_id.strip(),
        "checks": checks,
        "failed_checks": failed,
        "imperfections": imperfections,
        "conforms": not failed,
    }


def group_imperfections(coupon_records):
    """Return the imperfection totals of a coupon set, grouped by severity."""
    if not isinstance(coupon_records, (list, tuple)):
        raise ValueError("coupon_records must be a sequence of coupon records")
    totals = {grade: 0 for grade in SEVERITY_GRADES}
    for record in coupon_records:
        if not isinstance(record, dict) or "imperfections" not in record:
            raise ValueError("each coupon record must carry an 'imperfections' map")
        for grade in SEVERITY_GRADES:
            totals[grade] += _count(
                "imperfections['%s']" % grade, record["imperfections"].get(grade, 0)
            )
    return totals


def assess_coupon_lot(spec):
    """Run the full clause 5.5.2 qualification-coupon acceptance assessment.

    spec keys: lot_size, coupons (non-empty list), criteria (non-empty list),
    allowances (severity grade to permitted count), optional sample_fraction
    and minimum_sample.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "coupons", "criteria", "allowances"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    lot_size = _count("spec['lot_size']", spec["lot_size"], allow_zero=False)
    coupons = spec["coupons"]
    if not isinstance(coupons, (list, tuple)) or not coupons:
        raise ValueError("spec['coupons'] must be a non-empty sequence")
    if len(coupons) > lot_size:
        raise ValueError(
            "%d coupons were presented for a lot of %d" % (len(coupons), lot_size)
        )
    needed = required_sample_size(
        lot_size,
        spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        spec.get("minimum_sample", DEFAULT_MINIMUM_SAMPLE),
    )
    allowances = _validate_imperfections("spec['allowances']", spec["allowances"])
    records = []
    seen = set()
    for coupon in coupons:
        record = evaluate_coupon(coupon, spec["criteria"])
        if record["id"] in seen:
            raise ValueError("coupon id '%s' appears twice in the sample" % record["id"])
        seen.add(record["id"])
        records.append(record)
    totals = group_imperfections(records)
    findings = []
    if len(records) < needed:
        findings.append(
            "sample of %d coupons is below the %d a lot of %d has to be represented "
            "by" % (len(records), needed, lot_size)
        )
    for record in records:
        if not record["conforms"]:
            findings.append(
                "coupon '%s' fails acceptance check(s): %s"
                % (record["id"], ", ".join(record["failed_checks"]))
            )
    for grade in SEVERITY_GRADES:
        if totals[grade] > allowances[grade]:
            findings.append(
                "%d %s workmanship imperfections exceed the allowance of %d"
                % (totals[grade], grade, allowances[grade])
            )
    conforming = sum(1 for record in records if record["conforms"])
    return {
        "lot_size": lot_size,
        "sample_size": len(records),
        "required_sample_size": needed,
        "coupon_records": records,
        "imperfection_totals": totals,
        "allowances": allowances,
        "conforming_coupons": conforming,
        "workmanship_conformance": conforming / float(len(records)),
        "findings": findings,
        "accepted": not findings,
    }
