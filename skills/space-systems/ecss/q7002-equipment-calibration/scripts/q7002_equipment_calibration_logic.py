"""Calibration state of the instruments used in an outgassing screening run.

Anchor: ECSS-Q-ST-70-02C, apparatus clause -- the microbalance, the specimen
and collector thermocouples and the pressure gauge all have to be calibrated,
and their accuracy has to be good enough for the quantity each one decides.
Paraphrased into an implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether the instrument set may be used for a run on a given day, and what has
to be corrected first.

1. Currency. A calibration has a date and an interval. Adding months to a date
   is not adding days: the due day follows the calendar, and the end of a long
   month falls back to the last day of a short one.
2. Capability. An instrument is fit for a measurement when its uncertainty is
   comfortably smaller than the tolerance it is used to police. That ratio is
   the quantity graded, not the uncertainty on its own.
3. Readability. A balance whose smallest division is a large share of the
   mass change being looked for cannot resolve the result, even with a
   blameless calibration certificate.
4. Budget. Independent contributions combine in quadrature, so a chain of
   small terms is not the sum of them, and the combined figure is what the
   tolerance is compared against.
"""

import math
from datetime import date

__all__ = [
    "DEFAULT_MIN_UNCERTAINTY_RATIO",
    "DEFAULT_RESOLUTION_DIVISOR",
    "DEFAULT_DUE_SOON_DAYS",
    "parse_day",
    "add_months",
    "calibration_due_day",
    "days_remaining",
    "calibration_findings",
    "test_uncertainty_ratio",
    "capability_findings",
    "balance_readability_finding",
    "combined_uncertainty",
    "assess_equipment_calibration",
]

# An instrument policing a tolerance needs an uncertainty at least this many
# times smaller than the tolerance itself.
DEFAULT_MIN_UNCERTAINTY_RATIO = 4.0

# The smallest balance division has to be at least this many times below the
# mass change the run is looking for.
DEFAULT_RESOLUTION_DIVISOR = 10.0

# A calibration inside this many days of expiry is reported before the run,
# not after it.
DEFAULT_DUE_SOON_DAYS = 30

# Ratio comparisons are inclusive; absorb representation error at the edge
# rather than relaxing the metrology requirement itself.
RATIO_TOLERANCE = 1e-9

_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _as_positive_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-blank string, got %r" % (label, value))
    return value.strip()


def _month_length(year, month):
    if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        return 29
    return _DAYS_IN_MONTH[month - 1]


def parse_day(text):
    """Return a date from an ISO yyyy-mm-dd day string."""
    if isinstance(text, date):
        return text
    if not isinstance(text, str):
        raise ValueError("day must be an ISO yyyy-mm-dd string, got %r" % (text,))
    parts = text.strip().split("-")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("day must be an ISO yyyy-mm-dd string, got %r" % (text,))
    year, month, day = (int(part) for part in parts)
    if not 1 <= month <= 12:
        raise ValueError("month %d is not a calendar month" % month)
    if not 1 <= day <= _month_length(year, month):
        raise ValueError("day %d does not exist in %04d-%02d" % (day, year, month))
    return date(year, month, day)


def add_months(day, months):
    """Return the day that many whole calendar months later."""
    start = parse_day(day)
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer, got %r" % (months,))
    if months < 0:
        raise ValueError("months must not be negative, got %d" % months)
    index = (start.year * 12 + start.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(start.day, _month_length(year, month)))


def calibration_due_day(last_calibration, interval_months):
    """Return the day the calibration of an instrument runs out."""
    if not isinstance(interval_months, int) or isinstance(interval_months, bool):
        raise ValueError("interval_months must be an integer, got %r" % (interval_months,))
    if interval_months < 1:
        raise ValueError("interval_months must be at least one, got %d" % interval_months)
    return add_months(last_calibration, interval_months)


def days_remaining(due_day, run_day):
    """Return whole days from the run day to the calibration due day."""
    return (parse_day(due_day) - parse_day(run_day)).days


def calibration_findings(instruments, run_day, due_soon_days=DEFAULT_DUE_SOON_DAYS):
    """Return currency findings for every instrument on the run day."""
    if not isinstance(instruments, (list, tuple)) or not instruments:
        raise ValueError("instruments must be a non-empty sequence")
    if not isinstance(due_soon_days, int) or isinstance(due_soon_days, bool):
        raise ValueError("due_soon_days must be an integer, got %r" % (due_soon_days,))
    if due_soon_days < 0:
        raise ValueError("due_soon_days must not be negative, got %d" % due_soon_days)
    findings = []
    for item in instruments:
        if not isinstance(item, dict):
            raise ValueError("instrument must be a mapping")
        for key in ("id", "last_calibration", "interval_months"):
            if key not in item:
                raise ValueError("instrument is missing '%s'" % key)
        name = _identifier(item["id"], "instrument id")
        due = calibration_due_day(item["last_calibration"], item["interval_months"])
        left = days_remaining(due, run_day)
        if left < 0:
            findings.append(
                "instrument '%s' ran out of calibration %d day(s) before the run"
                % (name, -left)
            )
        elif left <= due_soon_days:
            findings.append(
                "instrument '%s' has %d day(s) of calibration left on the run day"
                % (name, left)
            )
    return findings


def test_uncertainty_ratio(tolerance, uncertainty):
    """Return how many times smaller an uncertainty is than its tolerance."""
    limit = _as_positive_float(tolerance, "tolerance")
    spread = _as_positive_float(uncertainty, "uncertainty")
    return limit / spread


def capability_findings(instruments, minimum_ratio=DEFAULT_MIN_UNCERTAINTY_RATIO):
    """Return a finding per instrument too coarse for the tolerance it polices."""
    if not isinstance(instruments, (list, tuple)) or not instruments:
        raise ValueError("instruments must be a non-empty sequence")
    floor = _as_positive_float(minimum_ratio, "minimum_ratio")
    findings = []
    for item in instruments:
        if not isinstance(item, dict):
            raise ValueError("instrument must be a mapping")
        for key in ("id", "tolerance", "uncertainty"):
            if key not in item:
                raise ValueError("instrument is missing '%s'" % key)
        name = _identifier(item["id"], "instrument id")
        ratio = test_uncertainty_ratio(item["tolerance"], item["uncertainty"])
        if ratio < floor - RATIO_TOLERANCE:
            findings.append(
                "instrument '%s' gives a tolerance-to-uncertainty ratio of %.2f, "
                "below the required %.2f" % (name, ratio, floor)
            )
    return findings


def balance_readability_finding(readability_mg, mass_change_mg,
                                divisor=DEFAULT_RESOLUTION_DIVISOR):
    """Return a finding when the balance cannot resolve the mass change sought."""
    division = _as_positive_float(readability_mg, "readability_mg")
    change = _as_positive_float(mass_change_mg, "mass_change_mg")
    factor = _as_positive_float(divisor, "divisor")
    allowed = change / factor
    if division > allowed + RATIO_TOLERANCE * allowed:
        return (
            "balance division of %.6f mg cannot resolve a %.6f mg change; "
            "%.6f mg or finer is required" % (division, change, allowed)
        )
    return None


def combined_uncertainty(components):
    """Return the quadrature sum of independent uncertainty contributions."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("components must be a non-empty sequence")
    total = 0.0
    for i, value in enumerate(components):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("component %d must be a real number, got %r" % (i, value))
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("component %d must be finite" % i)
        if number < 0.0:
            raise ValueError("component %d must not be negative, got %r" % (i, value))
        total += number * number
    return math.sqrt(total)


def assess_equipment_calibration(spec):
    """Run the full instrument calibration assessment for one run.

    spec keys: instruments (sequence carrying id, last_calibration,
    interval_months, tolerance, uncertainty), run_day, balance_readability_mg,
    resolved_mass_change_mg, optional minimum_ratio, resolution_divisor,
    due_soon_days and budget_components / budget_tolerance.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("instruments", "run_day", "balance_readability_mg",
                "resolved_mass_change_mg"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    instruments = spec["instruments"]
    findings = []
    findings.extend(
        calibration_findings(
            instruments, spec["run_day"], spec.get("due_soon_days", DEFAULT_DUE_SOON_DAYS)
        )
    )
    findings.extend(
        capability_findings(
            instruments, spec.get("minimum_ratio", DEFAULT_MIN_UNCERTAINTY_RATIO)
        )
    )
    readability_note = balance_readability_finding(
        spec["balance_readability_mg"],
        spec["resolved_mass_change_mg"],
        spec.get("resolution_divisor", DEFAULT_RESOLUTION_DIVISOR),
    )
    if readability_note:
        findings.append(readability_note)
    budget = None
    components = spec.get("budget_components")
    if components is not None:
        budget = combined_uncertainty(components)
        limit = spec.get("budget_tolerance")
        if limit is not None:
            ratio = test_uncertainty_ratio(limit, budget)
            floor = _as_positive_float(
                spec.get("minimum_ratio", DEFAULT_MIN_UNCERTAINTY_RATIO), "minimum_ratio"
            )
            if ratio < floor - RATIO_TOLERANCE:
                findings.append(
                    "combined measurement uncertainty %.6f gives a ratio of %.2f "
                    "against its tolerance, below the required %.2f"
                    % (budget, ratio, floor)
                )
    ratios = {}
    due_days = {}
    for item in instruments:
        name = _identifier(item["id"], "instrument id")
        ratios[name] = test_uncertainty_ratio(item["tolerance"], item["uncertainty"])
        due_days[name] = days_remaining(
            calibration_due_day(item["last_calibration"], item["interval_months"]),
            spec["run_day"],
        )
    return {
        "uncertainty_ratios": ratios,
        "days_to_due": due_days,
        "combined_uncertainty": budget,
        "findings": findings,
        "usable": not findings,
    }
