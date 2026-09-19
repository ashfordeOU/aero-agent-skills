"""Fine and gross seal integrity testing of hermetic hybrid packages.

Anchor: ECSS-Q-ST-60-05C clause 10.3.7 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Set the limit from the cavity, not from the instrument. The rate a
   seal may leak is banded on the internal free volume, because the same
   leak empties a small cavity quickly and a large one slowly. A single
   house limit is either wrong for the small parts or wrong for the
   large ones.
2. Model what the instrument reads, not what the seal does. In the fixed
   method the unit is pressurized in a tracer atmosphere, removed, and
   measured; the reading is the tracer that got in during the bomb and
   has not yet got out again. Bomb pressure, bomb time, cavity volume,
   dwell before measurement and the molecular weight of the tracer all
   enter that reading, and it is not the leak rate.
3. Recover the seal from the reading. Turning a measured tracer rate
   back into an equivalent air leak rate is the actual job, and it has
   no closed form, so it is solved numerically inside a bracket the
   relation is monotonic over and refused outside it.
4. Bound the conditions the reading depends on. A bomb that did not
   reach its pressure-time product did not charge the cavity, and a
   dwell longer than the measurement window has let the tracer back out:
   both make a leaking part read clean, and neither is visible in the
   number alone.
5. Run both tests, in the right order. A hole large enough to let the
   tracer straight back out is invisible to the fine test, which is why
   the gross test exists; and the gross test wets the part, so it comes
   second. A fine-only result on a package with a large hole is a pass
   the method cannot support.

Stdlib only, offline, deterministic.
"""

import math

MOLECULAR_WEIGHT_AIR = 28.7

# Tracer gases used by the fixed method, with their molecular weights.
TRACER_MOLECULAR_WEIGHT = {
    "helium": 4.0,
    "krypton-85": 85.0,
}

# Equivalent standard air leak rate a seal may carry, in atm*cm3/s,
# banded on the internal free volume of the cavity in cm3.
REJECT_LIMIT_BANDS = (
    (0.01, 5.0e-8),
    (0.40, 1.0e-7),
)
LARGE_CAVITY_REJECT_LIMIT = 1.0e-6

# The bomb has to charge the cavity, and that is a pressure acting for a
# time rather than either one alone.
MIN_BOMB_PRESSURE_TIME_ATM_HOURS = 120.0

# Tracer starts leaving the moment the unit comes out of the bomb, so
# the reading is only meaningful inside this window.
MAX_DWELL_HOURS = 1.0

# Above this equivalent air leak rate the tracer enters and escapes
# before the measurement, and the fine test reads clean on a part that
# is wide open.
FINE_TEST_BLIND_THRESHOLD = 1.0e-5

# Bracket the numerical recovery searches over, in atm*cm3/s.
SOLVER_LOWER_BOUND = 1.0e-13
SOLVER_UPPER_BOUND = 1.0e-3
SOLVER_ITERATIONS = 200

TEST_ORDERS = ("fine-then-gross", "gross-then-fine")

COMPARISON_TOLERANCE = 1.0e-12

PASS = "seal-accepted"
FAIL = "seal-rejected"


class AmbiguousReading(ValueError):
    """A reading above the turning point answers to two seals at once."""


def _positive_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("%s must be finite and positive, got %r" % (label, value))
    return float(value)


def _non_negative_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(value) or value < 0:
        raise ValueError("%s must be finite and >= 0, got %r" % (label, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def reject_limit_for_volume(cavity_volume_cm3):
    """Equivalent air leak rate a cavity of this volume may carry."""
    volume = _positive_number("cavity_volume_cm3", cavity_volume_cm3)
    for ceiling, limit in REJECT_LIMIT_BANDS:
        if volume <= ceiling:
            return limit
    return LARGE_CAVITY_REJECT_LIMIT


def tracer_molecular_weight(tracer):
    """Molecular weight of a tracer gas used by the fixed method."""
    if tracer not in TRACER_MOLECULAR_WEIGHT:
        raise ValueError(
            "unknown tracer %r (expected one of %s)"
            % (tracer, ", ".join(sorted(TRACER_MOLECULAR_WEIGHT)))
        )
    return TRACER_MOLECULAR_WEIGHT[tracer]


def molecular_weight_ratio(tracer):
    """Square root of the air-to-tracer molecular weight ratio."""
    return math.sqrt(MOLECULAR_WEIGHT_AIR / tracer_molecular_weight(tracer))


def measured_tracer_rate(
    true_leak_rate,
    cavity_volume_cm3,
    bomb_pressure_atm,
    bomb_time_h,
    dwell_time_h,
    tracer="helium",
):
    """Tracer rate the instrument reads for a seal of this true leak rate.

    The fixed-method relation: what the cavity took up during the bomb,
    scaled by the molecular weight ratio, less what has already escaped
    during the dwell before the measurement.
    """
    leak = _positive_number("true_leak_rate", true_leak_rate)
    volume = _positive_number("cavity_volume_cm3", cavity_volume_cm3)
    pressure = _positive_number("bomb_pressure_atm", bomb_pressure_atm)
    bomb_time = _positive_number("bomb_time_h", bomb_time_h)
    dwell = _non_negative_number("dwell_time_h", dwell_time_h)
    ratio = molecular_weight_ratio(tracer)
    bomb_seconds = bomb_time * 3600.0
    dwell_seconds = dwell * 3600.0
    exponent = leak * ratio / volume
    charge = 1.0 - math.exp(-exponent * bomb_seconds)
    decay = math.exp(-exponent * dwell_seconds)
    return leak * pressure * ratio * charge * decay


def dwell_retention_fraction(
    true_leak_rate, cavity_volume_cm3, dwell_time_h, tracer="helium"
):
    """Fraction of the charged tracer still inside after the dwell."""
    leak = _positive_number("true_leak_rate", true_leak_rate)
    volume = _positive_number("cavity_volume_cm3", cavity_volume_cm3)
    dwell = _non_negative_number("dwell_time_h", dwell_time_h)
    ratio = molecular_weight_ratio(tracer)
    return math.exp(-leak * ratio * dwell * 3600.0 / volume)


def _reading_function(
    cavity_volume_cm3, bomb_pressure_atm, bomb_time_h, dwell_time_h, tracer
):
    """Close the fixed-method relation over one set of test conditions."""

    def reading(leak):
        return measured_tracer_rate(
            leak,
            cavity_volume_cm3,
            bomb_pressure_atm,
            bomb_time_h,
            dwell_time_h,
            tracer,
        )

    return reading


def solvable_reading_ceiling(
    cavity_volume_cm3,
    bomb_pressure_atm,
    bomb_time_h,
    dwell_time_h,
    tracer="helium",
):
    """Largest reading these conditions can produce, and the leak behind it.

    The relation is not monotonic. A leak small enough to hold its charge
    reads higher as it grows, but past a turning point the same leak
    empties the cavity during the dwell faster than the bomb filled it,
    and the reading falls away again. Above the turning point one reading
    answers to two seals, and the fine test cannot say which: that is the
    regime the gross test exists to cover.
    """
    reading = _reading_function(
        cavity_volume_cm3, bomb_pressure_atm, bomb_time_h, dwell_time_h, tracer
    )
    low = math.log(SOLVER_LOWER_BOUND)
    high = math.log(SOLVER_UPPER_BOUND)
    for _ in range(SOLVER_ITERATIONS):
        left = low + (high - low) / 3.0
        right = high - (high - low) / 3.0
        if reading(math.exp(left)) < reading(math.exp(right)):
            low = left
        else:
            high = right
    peak_leak = math.exp(0.5 * (low + high))
    return peak_leak, reading(peak_leak)


def solve_true_leak_rate(
    measured_rate,
    cavity_volume_cm3,
    bomb_pressure_atm,
    bomb_time_h,
    dwell_time_h,
    tracer="helium",
):
    """Recover the equivalent air leak rate behind a measured tracer rate.

    The fixed-method relation has no closed inverse, so it is bisected
    over its rising branch - the branch on which a larger leak really
    does read higher. A reading above the turning point answers to two
    seals at once and is refused rather than resolved to the tighter of
    them.
    """
    target = _positive_number("measured_rate", measured_rate)
    peak_leak, peak_reading = solvable_reading_ceiling(
        cavity_volume_cm3, bomb_pressure_atm, bomb_time_h, dwell_time_h, tracer
    )
    reading = _reading_function(
        cavity_volume_cm3, bomb_pressure_atm, bomb_time_h, dwell_time_h, tracer
    )
    if target > peak_reading * (1.0 + COMPARISON_TOLERANCE):
        raise AmbiguousReading(
            "measured rate %g exceeds the largest reading these conditions "
            "can produce (%g); the reading is ambiguous and the gross test "
            "governs" % (target, peak_reading)
        )
    low, high = SOLVER_LOWER_BOUND, peak_leak
    if reading(low) > target:
        raise ValueError(
            "measured rate %g is below the solvable bracket" % (target,)
        )
    for _ in range(SOLVER_ITERATIONS):
        mid = 0.5 * (low + high)
        if reading(mid) < target:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def bomb_pressure_time_product(bomb_pressure_atm, bomb_time_h):
    """Pressure acting for a time, which is what charges the cavity."""
    pressure = _positive_number("bomb_pressure_atm", bomb_pressure_atm)
    time_h = _positive_number("bomb_time_h", bomb_time_h)
    return pressure * time_h


def fine_test_is_blind(true_leak_rate):
    """True when the hole is wide enough for the fine test to miss it."""
    leak = _positive_number("true_leak_rate", true_leak_rate)
    return leak > FINE_TEST_BLIND_THRESHOLD * (1.0 + COMPARISON_TOLERANCE)


def validate_seal(record):
    """Validate one seal test record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    unit_id = record.get("id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("record needs a non-empty string id")
    tracer = record.get("tracer", "helium")
    tracer_molecular_weight(tracer)
    order = record.get("test_order", "fine-then-gross")
    if order not in TEST_ORDERS:
        raise ValueError(
            "unit %s has unknown test_order %r (expected one of %s)"
            % (unit_id, order, ", ".join(TEST_ORDERS))
        )
    return {
        "id": unit_id,
        "tracer": tracer,
        "test_order": order,
        "cavity_volume_cm3": _positive_number(
            "unit %s cavity_volume_cm3" % unit_id, record.get("cavity_volume_cm3")
        ),
        "bomb_pressure_atm": _positive_number(
            "unit %s bomb_pressure_atm" % unit_id, record.get("bomb_pressure_atm")
        ),
        "bomb_time_h": _positive_number(
            "unit %s bomb_time_h" % unit_id, record.get("bomb_time_h")
        ),
        "dwell_time_h": _non_negative_number(
            "unit %s dwell_time_h" % unit_id, record.get("dwell_time_h", 0.0)
        ),
        "measured_tracer_rate": _positive_number(
            "unit %s measured_tracer_rate" % unit_id,
            record.get("measured_tracer_rate"),
        ),
        "gross_test_performed": _boolean(
            "unit %s gross_test_performed" % unit_id,
            record.get("gross_test_performed", True),
        ),
        "gross_test_bubbles_observed": _boolean(
            "unit %s gross_test_bubbles_observed" % unit_id,
            record.get("gross_test_bubbles_observed", False),
        ),
    }


def recovered_leak_rate(record):
    """Equivalent air leak rate behind a record, or None when ambiguous.

    Unknown is not zero and it is not the tighter of the two seals the
    reading answers to: when the conditions cannot resolve the reading,
    the rate is reported absent and the gross test governs.
    """
    norm = validate_seal(record)
    try:
        return solve_true_leak_rate(
            norm["measured_tracer_rate"],
            norm["cavity_volume_cm3"],
            norm["bomb_pressure_atm"],
            norm["bomb_time_h"],
            norm["dwell_time_h"],
            norm["tracer"],
        )
    except AmbiguousReading:
        return None


def check_conditions(record):
    """Findings about the bomb and the dwell the reading depends on."""
    norm = validate_seal(record)
    findings = []
    product = bomb_pressure_time_product(
        norm["bomb_pressure_atm"], norm["bomb_time_h"]
    )
    if product < MIN_BOMB_PRESSURE_TIME_ATM_HOURS * (1.0 - COMPARISON_TOLERANCE):
        findings.append("bomb-pressure-time-product-below-the-minimum")
    if norm["dwell_time_h"] > MAX_DWELL_HOURS * (1.0 + COMPARISON_TOLERANCE):
        findings.append("dwell-exceeds-the-measurement-window")
    return findings


def check_fine_leak(record):
    """Findings about the fine test reading against the cavity limit."""
    norm = validate_seal(record)
    leak = recovered_leak_rate(norm)
    if leak is None:
        return ["reading-above-what-the-conditions-can-resolve"]
    limit = reject_limit_for_volume(norm["cavity_volume_cm3"])
    if leak > limit * (1.0 + COMPARISON_TOLERANCE):
        return ["equivalent-leak-rate-above-the-cavity-limit"]
    return []


def check_gross_leak(record):
    """Findings about the gross test and where it sat in the sequence."""
    norm = validate_seal(record)
    findings = []
    if not norm["gross_test_performed"]:
        findings.append("gross-leak-test-not-performed")
    elif norm["test_order"] == "gross-then-fine":
        findings.append("gross-leak-test-run-before-the-fine-leak-test")
    if norm["gross_test_bubbles_observed"]:
        findings.append("gross-leak-indication-observed")
    leak = recovered_leak_rate(norm)
    blind = leak is None or fine_test_is_blind(leak)
    if blind and not norm["gross_test_performed"]:
        findings.append("fine-test-blind-to-a-hole-this-large")
    return findings


def assess_seal(record):
    """Assess one hermetic seal test against clause 10.3.7."""
    norm = validate_seal(record)
    leak = recovered_leak_rate(norm)
    findings = list(check_conditions(norm))
    findings.extend(check_fine_leak(norm))
    findings.extend(check_gross_leak(norm))
    return {
        "id": norm["id"],
        "tracer": norm["tracer"],
        "cavity_volume_cm3": norm["cavity_volume_cm3"],
        "reject_limit": reject_limit_for_volume(norm["cavity_volume_cm3"]),
        "measured_tracer_rate": norm["measured_tracer_rate"],
        "equivalent_leak_rate": leak,
        "bomb_pressure_time": bomb_pressure_time_product(
            norm["bomb_pressure_atm"], norm["bomb_time_h"]
        ),
        "dwell_retention_fraction": None
        if leak is None
        else dwell_retention_fraction(
            leak, norm["cavity_volume_cm3"], norm["dwell_time_h"], norm["tracer"]
        ),
        "fine_test_blind": leak is None or fine_test_is_blind(leak),
        "findings": findings,
        "disposition": FAIL if findings else PASS,
    }


def assess_seal_batch(records):
    """Run the clause 10.3.7 assessment over a batch of sealed units."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_seal(record)
        if result["id"] in seen:
            raise ValueError("duplicate unit id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    rejected = [r["id"] for r in results if r["disposition"] == FAIL]
    return {
        "units": results,
        "accepted_ids": [r["id"] for r in results if r["disposition"] == PASS],
        "rejected_ids": rejected,
        "worst_equivalent_leak_rate": max(
            (
                r["equivalent_leak_rate"]
                for r in results
                if r["equivalent_leak_rate"] is not None
            ),
            default=None,
        ),
        "unresolved_ids": [
            r["id"] for r in results if r["equivalent_leak_rate"] is None
        ],
        "batch_accepted": not rejected,
    }


def limit_is_saturated(cavity_volume_cm3):
    """True when the cavity is large enough to take the loosest limit."""
    return reject_limit_for_volume(cavity_volume_cm3) == LARGE_CAVITY_REJECT_LIMIT
