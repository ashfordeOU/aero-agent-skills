"""Disposition of a limited-shelf-life material lot found past its expiry date.

Anchor: ECSS-Q-ST-70-22C, use-control clause -- what happens to a lot whose
shelf life has run out: it is refused for the intended use, re-validated by
test and given a bounded extension, or physically scrapped. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Measure the overrun: days past expiry, and that overrun as a fraction of
   the lot's original shelf life, which is the scale-free figure the eligibility
   rules are written against.
2. Screen the lot for re-validation eligibility. A material family with no
   defined re-validation test, a storage history with an unquantified
   excursion, an extension budget already spent, or an overrun beyond the
   allowed fraction all remove the option before any test is booked.
3. Where the lot is eligible and no re-validation results exist yet, the
   disposition is to re-test.
4. Where results exist, grade every measured property against its acceptance
   window; one property outside its window ends the lot.
5. On a clean re-validation, size the extension as a bounded fraction of the
   original shelf life, shrinking with each extension already granted, and
   issue the new expiry date from the assessment date.
"""

import datetime
import math

__all__ = [
    "DISPOSITIONS",
    "NON_RETESTABLE_FAMILIES",
    "MAX_OVERRUN_FRACTION",
    "MAX_EXTENSIONS",
    "BASE_EXTENSION_FRACTION",
    "PROPERTY_TOLERANCE",
    "parse_date",
    "days_past_expiry",
    "overrun_fraction",
    "is_retestable_family",
    "eligibility_findings",
    "grade_revalidation",
    "extension_days",
    "new_expiry_date",
    "decide_disposition",
]

DISPOSITIONS = ("extend", "re-test", "reject", "scrap")

# Families whose degradation cannot be read back from a property measurement:
# the ageing mechanism is internal, progressive and not exposed by any test
# short of destroying the article the material would have gone into.
NON_RETESTABLE_FAMILIES = (
    "pyrotechnic-composition",
    "solid-propellant-grain",
    "single-component-activated-adhesive",
    "hydrogen-getter",
)

# An overrun larger than this fraction of the original shelf life is past the
# range any re-validation result can be extrapolated over.
MAX_OVERRUN_FRACTION = 0.50

# A lot may be re-validated at most this many times before it is spent.
MAX_EXTENSIONS = 2

# The first extension is worth this fraction of the original shelf life; each
# extension already granted halves the next one.
BASE_EXTENSION_FRACTION = 0.25

# Property windows are engineering limits; an exactly-on-limit measurement is a
# representation question absorbed here rather than by widening the window.
PROPERTY_TOLERANCE = 1e-9


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def parse_date(value, label="date"):
    """Return an ISO date string or date object as a datetime.date."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string or a date, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError("three components expected")
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except Exception:
        raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))


def days_past_expiry(expiry_date, assessment_date):
    """Return whole days elapsed since expiry; zero or negative means still in date."""
    expiry = parse_date(expiry_date, "expiry_date")
    assessed = parse_date(assessment_date, "assessment_date")
    return (assessed - expiry).days


def overrun_fraction(days_past, original_shelf_life_days):
    """Return the overrun as a fraction of the lot's original shelf life."""
    if not isinstance(days_past, int) or isinstance(days_past, bool):
        raise ValueError("days_past must be an integer number of days")
    if not isinstance(original_shelf_life_days, (int, float)) or isinstance(
        original_shelf_life_days, bool
    ):
        raise ValueError("original_shelf_life_days must be a real number")
    total = float(original_shelf_life_days)
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("original_shelf_life_days must be positive and finite, got %r"
                         % (original_shelf_life_days,))
    return float(days_past) / total


def is_retestable_family(material_family):
    """Return True when the family has a defined re-validation test."""
    if not isinstance(material_family, str) or not material_family.strip():
        raise ValueError("material_family must be a non-empty string")
    return material_family.strip().lower() not in NON_RETESTABLE_FAMILIES


def eligibility_findings(lot):
    """Return the reasons, if any, that remove the re-validation option."""
    _require_mapping(lot, "lot")
    for key in ("material_family", "expiry_date", "assessment_date", "original_shelf_life_days"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    findings = []
    if not is_retestable_family(lot["material_family"]):
        findings.append(
            "material family '%s' has no defined re-validation test; degradation "
            "cannot be read back from a property measurement" % lot["material_family"]
        )
    if lot.get("storage_compliant", True) is not True:
        findings.append(
            "storage history carries an unquantified excursion; the state of the "
            "lot at expiry is not known well enough to extrapolate a re-test"
        )
    prior = lot.get("prior_extensions", 0)
    if not isinstance(prior, int) or isinstance(prior, bool) or prior < 0:
        raise ValueError("prior_extensions must be a non-negative integer, got %r" % (prior,))
    if prior >= MAX_EXTENSIONS:
        findings.append(
            "the lot has already been extended %d times, exhausting its budget of %d"
            % (prior, MAX_EXTENSIONS)
        )
    past = days_past_expiry(lot["expiry_date"], lot["assessment_date"])
    fraction = overrun_fraction(past, lot["original_shelf_life_days"])
    if fraction > MAX_OVERRUN_FRACTION + PROPERTY_TOLERANCE:
        findings.append(
            "overrun of %d days is %.3f of the original shelf life, beyond the %.2f "
            "an extension may be extrapolated over" % (past, fraction, MAX_OVERRUN_FRACTION)
        )
    return findings


def grade_revalidation(measurements, acceptance_windows):
    """Grade measured properties against their acceptance windows."""
    _require_mapping(measurements, "measurements")
    _require_mapping(acceptance_windows, "acceptance_windows")
    if not acceptance_windows:
        raise ValueError("acceptance_windows must name at least one property")
    failures = []
    not_measured = []
    for name, window in sorted(acceptance_windows.items()):
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError("acceptance window for '%s' must be a (low, high) pair" % name)
        low, high = window
        for label, bound in (("low", low), ("high", high)):
            if not isinstance(bound, (int, float)) or isinstance(bound, bool):
                raise ValueError("acceptance %s bound for '%s' must be a real number"
                                 % (label, name))
            if not math.isfinite(float(bound)):
                raise ValueError("acceptance %s bound for '%s' must be finite" % (label, name))
        low = float(low)
        high = float(high)
        if low > high:
            raise ValueError("acceptance window for '%s' is inverted: %g > %g" % (name, low, high))
        if name not in measurements:
            not_measured.append(name)
            continue
        value = measurements[name]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("measurement '%s' must be a real number, got %r" % (name, value))
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("measurement '%s' must be finite" % name)
        if value < low - PROPERTY_TOLERANCE:
            failures.append("%s measured %g, below its acceptance low of %g" % (name, value, low))
        elif value > high + PROPERTY_TOLERANCE:
            failures.append("%s measured %g, above its acceptance high of %g" % (name, value, high))
    if not_measured:
        failures.append(
            "acceptance properties not measured: %s" % ", ".join(sorted(not_measured))
        )
    return {
        "passed": not failures,
        "failures": failures,
        "not_measured": sorted(not_measured),
    }


def extension_days(original_shelf_life_days, prior_extensions=0):
    """Return the extension a clean re-validation earns, in whole days."""
    if not isinstance(original_shelf_life_days, (int, float)) or isinstance(
        original_shelf_life_days, bool
    ):
        raise ValueError("original_shelf_life_days must be a real number")
    total = float(original_shelf_life_days)
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("original_shelf_life_days must be positive and finite")
    if not isinstance(prior_extensions, int) or isinstance(prior_extensions, bool):
        raise ValueError("prior_extensions must be an integer")
    if prior_extensions < 0:
        raise ValueError("prior_extensions must be non-negative")
    if prior_extensions >= MAX_EXTENSIONS:
        raise ValueError(
            "extension budget of %d is already spent; no further extension may be sized"
            % MAX_EXTENSIONS
        )
    fraction = BASE_EXTENSION_FRACTION / float(2 ** prior_extensions)
    days = int(total * fraction)
    if days < 1:
        raise ValueError(
            "the sized extension rounds to less than a day; the lot is too short-lived "
            "to extend and should be dispositioned without one"
        )
    return days


def new_expiry_date(assessment_date, days):
    """Return the expiry date an extension issues, measured from the assessment."""
    assessed = parse_date(assessment_date, "assessment_date")
    if not isinstance(days, int) or isinstance(days, bool):
        raise ValueError("days must be an integer")
    if days < 1:
        raise ValueError("days must be at least one, got %d" % days)
    return assessed + datetime.timedelta(days=days)


def decide_disposition(lot):
    """Decide the disposition of one expired lot and return the full record.

    lot keys: material_family, expiry_date, assessment_date,
    original_shelf_life_days, optional storage_compliant, prior_extensions,
    acceptance_windows, measurements, flight_critical.
    """
    _require_mapping(lot, "lot")
    findings = eligibility_findings(lot)
    past = days_past_expiry(lot["expiry_date"], lot["assessment_date"])
    fraction = overrun_fraction(past, lot["original_shelf_life_days"])
    record = {
        "days_past_expiry": past,
        "overrun_fraction": fraction,
        "eligibility_findings": findings,
        "revalidation": None,
        "extension_days": None,
        "new_expiry_date": None,
        "findings": list(findings),
    }
    if past <= 0:
        record["disposition"] = "reject"
        record["findings"].append(
            "lot is not past its expiry date; this procedure applies to expired "
            "material only and the lot should be handled under normal use control"
        )
        return record
    if findings:
        record["disposition"] = "scrap"
        return record

    windows = lot.get("acceptance_windows")
    measurements = lot.get("measurements")
    if not windows or measurements is None:
        record["disposition"] = "re-test"
        record["findings"].append(
            "lot is eligible for re-validation; no results on file, so the "
            "material stays quarantined until it has been tested"
        )
        return record

    graded = grade_revalidation(measurements, windows)
    record["revalidation"] = graded
    if not graded["passed"]:
        record["findings"].extend(graded["failures"])
        record["disposition"] = "scrap" if lot.get("flight_critical", True) else "reject"
        return record

    prior = lot.get("prior_extensions", 0)
    days = extension_days(lot["original_shelf_life_days"], prior)
    record["extension_days"] = days
    record["new_expiry_date"] = new_expiry_date(lot["assessment_date"], days).isoformat()
    record["disposition"] = "extend"
    return record
