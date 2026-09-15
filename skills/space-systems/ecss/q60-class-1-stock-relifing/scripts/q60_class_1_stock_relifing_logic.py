"""Relifing of stored Class 1 EEE stock whose storage period has run out.

Anchor: ECSS-Q-ST-60C clause 4.3.10 (Class 1 EEE components -- restoring the
validity of stored parts whose original storage period has expired).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Work out the storage period actually in force. It is the base period the
   part was accepted under, shortened by a step for every relifing round the
   stock has already had, and never shortened below a floor.
2. Add that period to the date of the last acceptance or relifing operation to
   get the expiry, and test the assessment date against it.
3. For expired stock, test the round ceiling before anything else: stock that
   has used up its permitted relifing rounds goes to full re-screening, and no
   re-verification result can buy it another round.
4. Measure how much of the moisture-sensitivity floor-life budget the stock has
   consumed since it left its dry pack. A budget over-run obliges a bake, whose
   duration comes from the package thickness band, before the re-verification
   is worth running.
5. Size the relifing sample, derive the tests the package owes, and judge each
   result against its accept number. A required test with no result is refused.
6. Return the disposition: in date, relifed with a shortened new period, stock
   rejected on a failed test, or sent for re-screening.
"""

import datetime
import math

__all__ = [
    "FRACTION_TOLERANCE",
    "MSL_FLOOR_LIFE_HOURS",
    "BAKE_THICKNESS_BANDS_125C",
    "HERMETIC_PACKAGE_FAMILIES",
    "BASE_RELIFING_TESTS",
    "DEFAULT_SAMPLE_FRACTION",
    "DEFAULT_MINIMUM_SAMPLE",
    "DEFAULT_MAXIMUM_SAMPLE",
    "DEFAULT_STEP_MONTHS",
    "DEFAULT_FLOOR_MONTHS",
    "parse_date",
    "add_months",
    "full_months_between",
    "floor_life_hours",
    "floor_time_fraction",
    "bake_required",
    "bake_duration_hours",
    "granted_storage_months",
    "required_relifing_tests",
    "relifing_sample_size",
    "evaluate_relifing_sample",
    "assess_stock_relifing",
]

# Consumed-budget fractions are ratios of small numbers; an intentional equality
# with a limit can land a few ULP either side of it after the division.
FRACTION_TOLERANCE = 1e-12

# Floor life in hours outside the dry pack, by moisture sensitivity level.
# None means unlimited; zero means the budget is spent the moment the pack is
# opened, so a bake is owed whatever the exposure.
MSL_FLOOR_LIFE_HOURS = {
    "1": None,
    "2": 8760,
    "2a": 672,
    "3": 168,
    "4": 72,
    "5": 48,
    "5a": 24,
    "6": 0,
}

# Bake duration in hours at 125 C, by package body thickness band in
# millimetres. A package thicker than the widest band is refused, because a
# bake time for it was never established.
BAKE_THICKNESS_BANDS_125C = ((1.4, 9), (2.0, 18), (4.5, 48))

# Sealed packages carry a leak check that a plastic-encapsulated part cannot be
# given.
HERMETIC_PACKAGE_FAMILIES = frozenset(
    {"ceramic-hermetic", "metal-can", "glass-sealed", "ceramic-flatpack"}
)

BASE_RELIFING_TESTS = ("external-visual", "solderability")

DEFAULT_SAMPLE_FRACTION = 0.05
DEFAULT_MINIMUM_SAMPLE = 5
DEFAULT_MAXIMUM_SAMPLE = 20
DEFAULT_STEP_MONTHS = 6
DEFAULT_FLOOR_MONTHS = 6


def _positive_int(value, label):
    """Return value as a positive integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _non_negative_int(value, label):
    """Return value as a non-negative integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _non_negative_real(value, label):
    """Return value as a finite non-negative float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return value


def _exceeds(value, bound):
    """Return True when value is strictly above bound, tolerant of float noise."""
    if math.isinf(value):
        return True
    if math.isclose(value, bound, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0):
        return False
    return value > bound


def _clean_name(value, label):
    """Return a lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _days_in_month(year, month):
    """Return the number of days in a calendar month, leap years included."""
    if month == 12:
        first_of_next = datetime.date(year + 1, 1, 1)
    else:
        first_of_next = datetime.date(year, month + 1, 1)
    return (first_of_next - datetime.timedelta(days=1)).day


def parse_date(value, label="date"):
    """Return a date from an ISO day string or an existing date object."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string or a date object" % label)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO calendar date: %r" % (label, value))


def add_months(start, months):
    """Return the date that many whole calendar months after start.

    The day of month is clamped to the length of the target month, so stock
    accepted on 31 January under a one-month period expires at the end of
    February rather than sliding into March.
    """
    start = parse_date(start, "start")
    months = _non_negative_int(months, "months")
    index = (start.year * 12 + (start.month - 1)) + months
    year, month = divmod(index, 12)
    month += 1
    day = min(start.day, _days_in_month(year, month))
    return datetime.date(year, month, day)


def full_months_between(start, end):
    """Return the number of whole calendar months from start to end."""
    start = parse_date(start, "start")
    end = parse_date(end, "end")
    if end < start:
        raise ValueError(
            "end %s precedes start %s" % (end.isoformat(), start.isoformat())
        )
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < min(start.day, _days_in_month(end.year, end.month)):
        months -= 1
    return max(0, months)


def floor_life_hours(level, register=None):
    """Return the floor life of a moisture sensitivity level, in hours."""
    if register is None:
        register = MSL_FLOOR_LIFE_HOURS
    if not isinstance(register, dict) or not register:
        raise ValueError("register must be a non-empty mapping of level to floor life")
    key = _clean_name(level, "moisture sensitivity level")
    if key not in register:
        raise ValueError(
            "moisture sensitivity level '%s' is not in the floor-life register" % key
        )
    hours = register[key]
    if hours is None:
        return None
    return _non_negative_int(hours, "floor life for level '%s'" % key)


def floor_time_fraction(exposure_hours, level, register=None):
    """Return the share of the floor-life budget the stock has consumed.

    An unlimited level consumes nothing. A level whose floor life is zero owes a
    bake whatever the exposure, which is reported as an infinite fraction rather
    than as a division by zero.
    """
    exposure = _non_negative_real(exposure_hours, "exposure_hours")
    hours = floor_life_hours(level, register)
    if hours is None:
        return 0.0
    if hours == 0:
        return math.inf
    return exposure / float(hours)


def bake_required(fraction, threshold=1.0):
    """Return True when the consumed floor-life budget obliges a bake."""
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
        raise ValueError("fraction must be a real number, got %r" % (fraction,))
    fraction = float(fraction)
    if math.isnan(fraction):
        raise ValueError("fraction must not be a NaN")
    if fraction < 0.0:
        raise ValueError("fraction must be non-negative, got %r" % (fraction,))
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be a real number, got %r" % (threshold,))
    threshold = float(threshold)
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("threshold must be finite and positive, got %r" % (threshold,))
    return _exceeds(fraction, threshold)


def bake_duration_hours(package_thickness_mm, level, bands=None, register=None):
    """Return the bake duration the package thickness band carries, in hours."""
    if bands is None:
        bands = BAKE_THICKNESS_BANDS_125C
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty sequence of (thickness, hours) pairs")
    key = _clean_name(level, "moisture sensitivity level")
    if floor_life_hours(key, register) is None:
        raise ValueError(
            "moisture sensitivity level '%s' has unlimited floor life; no bake is "
            "defined for it" % key
        )
    thickness = _non_negative_real(package_thickness_mm, "package_thickness_mm")
    if thickness <= 0.0:
        raise ValueError("package_thickness_mm must be positive, got %r" % (thickness,))
    widest = None
    for entry in bands:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("bands entries must be (thickness, hours) pairs")
        limit = _non_negative_real(entry[0], "band thickness")
        hours = _positive_int(entry[1], "band bake hours")
        if widest is None or limit > widest:
            widest = limit
        if not _exceeds(thickness, limit):
            return hours
    raise ValueError(
        "package thickness %g mm is above the widest band of %g mm; no bake "
        "duration was established for it" % (thickness, widest)
    )


def granted_storage_months(
    base_months,
    relifing_round,
    step_months=DEFAULT_STEP_MONTHS,
    floor_months=DEFAULT_FLOOR_MONTHS,
):
    """Return the storage period in force after this many relifing rounds.

    Every round shortens the period by a step, because stock that has already
    been kept once is not re-granted the period fresh parts were accepted under.
    The period never falls below the floor.
    """
    base = _positive_int(base_months, "base_months")
    rounds = _non_negative_int(relifing_round, "relifing_round")
    step = _non_negative_int(step_months, "step_months")
    floor = _positive_int(floor_months, "floor_months")
    if floor > base:
        raise ValueError(
            "floor_months %d exceeds base_months %d" % (floor, base)
        )
    return max(floor, base - rounds * step)


def required_relifing_tests(package_family, bake_needed=False):
    """Return the re-verification tests this stock owes before it may be used."""
    family = _clean_name(package_family, "package_family")
    tests = list(BASE_RELIFING_TESTS)
    if family in HERMETIC_PACKAGE_FAMILIES:
        tests.append("fine-and-gross-leak")
    if bake_needed:
        tests.append("post-bake-moisture-verification")
    return tuple(tests)


def relifing_sample_size(
    stock_quantity,
    fraction=DEFAULT_SAMPLE_FRACTION,
    minimum=DEFAULT_MINIMUM_SAMPLE,
    maximum=DEFAULT_MAXIMUM_SAMPLE,
):
    """Return the relifing sample a stored quantity owes."""
    quantity = _positive_int(stock_quantity, "stock_quantity")
    minimum = _positive_int(minimum, "minimum")
    maximum = _positive_int(maximum, "maximum")
    if maximum < minimum:
        raise ValueError(
            "maximum sample %d is below the minimum sample %d" % (maximum, minimum)
        )
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
        raise ValueError("fraction must be a real number, got %r" % (fraction,))
    fraction = float(fraction)
    if not math.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("fraction must lie in (0, 1], got %r" % (fraction,))
    proportional = int(math.ceil(quantity * fraction - FRACTION_TOLERANCE))
    return min(quantity, maximum, max(minimum, proportional))


def evaluate_relifing_sample(results, required_tests, accept_numbers=None):
    """Judge the relifing results against the tests the stock owes.

    results maps a test name to a mapping with units_tested and units_failed.
    Every required test must have a result; a missing one is a refusal, not a
    pass. Accept numbers default to zero failures.
    """
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of test name to counts")
    if not isinstance(required_tests, (list, tuple)) or not required_tests:
        raise ValueError("required_tests must be a non-empty sequence")
    if accept_numbers is None:
        accept_numbers = {}
    if not isinstance(accept_numbers, dict):
        raise ValueError("accept_numbers must be a mapping of test name to a count")
    evaluated = []
    failed = []
    for name in required_tests:
        if name not in results:
            raise ValueError(
                "required re-verification test '%s' has no result; a missing result "
                "is not a pass" % name
            )
        entry = results[name]
        if not isinstance(entry, dict):
            raise ValueError("result for '%s' must be a mapping" % name)
        for key in ("units_tested", "units_failed"):
            if key not in entry:
                raise ValueError("result for '%s' missing key '%s'" % (name, key))
        tested = _positive_int(entry["units_tested"], "units_tested for '%s'" % name)
        units_failed = _non_negative_int(
            entry["units_failed"], "units_failed for '%s'" % name
        )
        if units_failed > tested:
            raise ValueError(
                "result for '%s' reports %d failure(s) out of %d unit(s) tested"
                % (name, units_failed, tested)
            )
        accept = _non_negative_int(
            accept_numbers.get(name, 0), "accept number for '%s'" % name
        )
        compliant = units_failed <= accept
        evaluated.append(
            {
                "test": name,
                "units_tested": tested,
                "units_failed": units_failed,
                "accept_number": accept,
                "compliant": compliant,
            }
        )
        if not compliant:
            failed.append(name)
    return {
        "results": evaluated,
        "failed_tests": failed,
        "compliant": not failed,
    }


def assess_stock_relifing(spec):
    """Run the clause 4.3.10 relifing assessment for one stored Class 1 lot.

    spec keys: package_family, moisture_sensitivity_level, floor_exposure_hours,
    package_thickness_mm, base_storage_months, last_operation_date, as_of_date,
    stock_quantity, test_results; optional relifing_rounds_done,
    max_relifing_rounds, step_months, floor_months, sample_fraction,
    minimum_sample, maximum_sample, accept_numbers.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "package_family",
        "moisture_sensitivity_level",
        "floor_exposure_hours",
        "package_thickness_mm",
        "base_storage_months",
        "last_operation_date",
        "as_of_date",
        "stock_quantity",
        "test_results",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    base = _positive_int(spec["base_storage_months"], "base_storage_months")
    rounds_done = _non_negative_int(
        spec.get("relifing_rounds_done", 0), "relifing_rounds_done"
    )
    step = _non_negative_int(spec.get("step_months", DEFAULT_STEP_MONTHS), "step_months")
    floor = _positive_int(spec.get("floor_months", DEFAULT_FLOOR_MONTHS), "floor_months")
    granted = granted_storage_months(base, rounds_done, step, floor)
    last_operation = parse_date(spec["last_operation_date"], "last_operation_date")
    as_of = parse_date(spec["as_of_date"], "as_of_date")
    if as_of < last_operation:
        raise ValueError("as_of_date precedes last_operation_date")
    expiry = add_months(last_operation, granted)
    expired = as_of > expiry
    elapsed = full_months_between(last_operation, as_of)

    findings = []
    result = {
        "granted_storage_months": granted,
        "expiry_date": expiry.isoformat(),
        "as_of_date": as_of.isoformat(),
        "elapsed_months": elapsed,
        "expired": expired,
        "relifing_rounds_done": rounds_done,
        "floor_time_fraction": None,
        "bake_required": False,
        "bake_duration_hours": None,
        "required_tests": None,
        "sample_size": None,
        "test_evaluation": None,
        "new_expiry_date": None,
        "new_granted_storage_months": None,
    }
    if not expired:
        findings.append(
            "storage period of %d month(s) runs to %s; the stock is in date"
            % (granted, expiry.isoformat())
        )
        result["disposition"] = "in-date"
        result["findings"] = findings
        return result

    findings.append(
        "storage period of %d month(s) ran out on %s; %d month(s) have elapsed"
        % (granted, expiry.isoformat(), elapsed)
    )
    max_rounds = spec.get("max_relifing_rounds")
    if max_rounds is not None:
        max_rounds = _positive_int(max_rounds, "max_relifing_rounds")
        if rounds_done >= max_rounds:
            findings.append(
                "stock has already been relifed %d time(s) against a ceiling of %d"
                % (rounds_done, max_rounds)
            )
            result["disposition"] = "re-screening-required"
            result["findings"] = findings
            return result

    fraction = floor_time_fraction(
        spec["floor_exposure_hours"], spec["moisture_sensitivity_level"]
    )
    needs_bake = bake_required(fraction)
    result["floor_time_fraction"] = fraction
    result["bake_required"] = needs_bake
    if needs_bake:
        hours = bake_duration_hours(
            spec["package_thickness_mm"], spec["moisture_sensitivity_level"]
        )
        result["bake_duration_hours"] = hours
        findings.append(
            "floor-life budget is over-run; a %d hour bake precedes the "
            "re-verification" % hours
        )

    required_tests = required_relifing_tests(spec["package_family"], needs_bake)
    result["required_tests"] = list(required_tests)
    sample = relifing_sample_size(
        spec["stock_quantity"],
        spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        spec.get("minimum_sample", DEFAULT_MINIMUM_SAMPLE),
        spec.get("maximum_sample", DEFAULT_MAXIMUM_SAMPLE),
    )
    result["sample_size"] = sample
    evaluation = evaluate_relifing_sample(
        spec["test_results"], required_tests, spec.get("accept_numbers")
    )
    result["test_evaluation"] = evaluation
    if not evaluation["compliant"]:
        for name in evaluation["failed_tests"]:
            findings.append(
                "re-verification test '%s' exceeded its accept number" % name
            )
        result["disposition"] = "stock-rejected"
        result["findings"] = findings
        return result

    new_granted = granted_storage_months(base, rounds_done + 1, step, floor)
    result["new_granted_storage_months"] = new_granted
    result["new_expiry_date"] = add_months(as_of, new_granted).isoformat()
    findings.append(
        "re-verification is clean; a shortened period of %d month(s) is granted "
        "from %s" % (new_granted, as_of.isoformat())
    )
    result["disposition"] = "relifed"
    result["findings"] = findings
    return result
