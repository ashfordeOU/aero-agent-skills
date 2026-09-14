"""Relifing of stored commercial EEE lots whose storage period has expired.

Anchor: ECSS-Q-ST-60-13C clause 4.3.10 (Class 1 use of commercial EEE
components -- relifing of stored parts). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the permitted storage period for the lot from its package family
   and the environment it is actually stored in, using a project storage
   register. An unlisted combination is refused, because a period that was
   never granted cannot be assumed.
2. Compute the storage expiry date by calendar month arithmetic from the date
   of the last acceptance or relifing operation, and test it against the
   assessment date.
3. Where the period has run out, check the two ceilings that stop a lot being
   extended forever: the number of relifing operations already performed and
   the cumulative storage since original acceptance.
4. Size the relifing sample and evaluate the re-verification results --
   visual, solderability, hermeticity where the package is sealed, and
   electrical -- against the per-test pass fraction required of each.
5. Return the disposition: in date, relifed with a new expiry date, sent for
   re-screening because a ceiling was reached, or rejected on a failed test.
"""

import datetime
import math

__all__ = [
    "FRACTION_TOLERANCE",
    "DEFAULT_SAMPLE_FRACTION",
    "DEFAULT_MIN_SAMPLE",
    "HERMETIC_PACKAGE_FAMILIES",
    "BASE_RELIFING_TESTS",
    "parse_date",
    "add_months",
    "full_months_between",
    "permitted_storage_months",
    "expiry_date",
    "is_expired",
    "required_relifing_tests",
    "relifing_sample_size",
    "evaluate_relifing_tests",
    "assess_relifing",
]

# Pass fractions are ratios of small integers; an intentional equality with a
# required fraction can land a few ULP either side of it after the division.
FRACTION_TOLERANCE = 1e-12

DEFAULT_SAMPLE_FRACTION = 0.02
DEFAULT_MIN_SAMPLE = 3

# Sealed packages carry a seal integrity check that plastic-encapsulated
# commercial parts cannot be given.
HERMETIC_PACKAGE_FAMILIES = frozenset(
    {"ceramic-hermetic", "metal-can", "glass-sealed", "ceramic-flatpack"}
)

# Re-verification every relifed commercial lot gets, whatever its package.
BASE_RELIFING_TESTS = ("visual", "solderability", "electrical")


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

    The day of month is clamped to the length of the target month, so a lot
    accepted on 31 January and given a one-month period expires on 28 or 29
    February rather than sliding into March.
    """
    start = parse_date(start, "start")
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer")
    if months < 0:
        raise ValueError("months must be non-negative, got %d" % months)
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
        raise ValueError("end %s precedes start %s" % (end.isoformat(), start.isoformat()))
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < min(start.day, _days_in_month(end.year, end.month)):
        months -= 1
    return max(0, months)


def permitted_storage_months(register, package_family, environment):
    """Look up the permitted storage period in whole months.

    register maps a package family to a mapping of storage environment to a
    permitted period in months. A combination the project never granted is
    refused rather than defaulted.
    """
    if not isinstance(register, dict) or not register:
        raise ValueError("register must be a non-empty mapping of package family to periods")
    for label, value in (("package_family", package_family), ("environment", environment)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be a non-empty string" % label)
    family = package_family.strip().lower()
    env = environment.strip().lower()
    by_env = register.get(family)
    if not isinstance(by_env, dict) or not by_env:
        raise ValueError(
            "package family '%s' is not in the storage register" % family
        )
    if env not in by_env:
        raise ValueError(
            "storage environment '%s' is not granted for package family '%s'"
            % (env, family)
        )
    months = by_env[env]
    if not isinstance(months, int) or isinstance(months, bool) or months <= 0:
        raise ValueError(
            "permitted period for '%s' in '%s' must be a positive whole number of "
            "months" % (family, env)
        )
    return months


def expiry_date(reference_date, permitted_months):
    """Return the storage expiry date of a lot from its reference date."""
    if not isinstance(permitted_months, int) or isinstance(permitted_months, bool):
        raise ValueError("permitted_months must be an integer")
    if permitted_months <= 0:
        raise ValueError("permitted_months must be positive, got %d" % permitted_months)
    return add_months(reference_date, permitted_months)


def is_expired(as_of, expiry):
    """Return True when the assessment date is past the expiry date."""
    as_of = parse_date(as_of, "as_of")
    expiry = parse_date(expiry, "expiry")
    return as_of > expiry


def required_relifing_tests(package_family):
    """Return the re-verification tests a relifed lot of this package needs."""
    if not isinstance(package_family, str) or not package_family.strip():
        raise ValueError("package_family must be a non-empty string")
    tests = list(BASE_RELIFING_TESTS)
    if package_family.strip().lower() in HERMETIC_PACKAGE_FAMILIES:
        tests.append("hermeticity")
    return tuple(tests)


def relifing_sample_size(lot_size, fraction=DEFAULT_SAMPLE_FRACTION, minimum=DEFAULT_MIN_SAMPLE):
    """Return the relifing sample size for a stored lot."""
    for label, value in (("lot_size", lot_size), ("minimum", minimum)):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError("%s must be a positive integer, got %r" % (label, value))
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise ValueError("fraction must be a real number")
    fraction = float(fraction)
    if not math.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("fraction must lie in (0, 1], got %r" % (fraction,))
    proportional = int(math.ceil(lot_size * fraction - FRACTION_TOLERANCE))
    return min(lot_size, max(minimum, proportional))


def evaluate_relifing_tests(results, required_tests, required_pass_fraction=1.0):
    """Evaluate the re-verification results against the required tests.

    results maps a test name to a mapping with units_tested and units_passed.
    Every required test must be present; a missing result is a refusal, not a
    pass.
    """
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of test name to counts")
    if not isinstance(required_tests, (list, tuple)) or not required_tests:
        raise ValueError("required_tests must be a non-empty sequence")
    if not isinstance(required_pass_fraction, (int, float)) or isinstance(
        required_pass_fraction, bool
    ):
        raise ValueError("required_pass_fraction must be a real number")
    required_fraction = float(required_pass_fraction)
    if not math.isfinite(required_fraction) or not 0.0 < required_fraction <= 1.0:
        raise ValueError("required_pass_fraction must lie in (0, 1]")
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
        for key in ("units_tested", "units_passed"):
            if key not in entry:
                raise ValueError("result for '%s' missing key '%s'" % (name, key))
            if not isinstance(entry[key], int) or isinstance(entry[key], bool):
                raise ValueError("result for '%s' %s must be an integer" % (name, key))
        tested = entry["units_tested"]
        passed = entry["units_passed"]
        if tested <= 0:
            raise ValueError("result for '%s' must report at least one unit tested" % name)
        if passed < 0 or passed > tested:
            raise ValueError(
                "result for '%s' passed %d of %d units, which is out of range"
                % (name, passed, tested)
            )
        fraction = passed / tested
        ok = fraction > required_fraction or math.isclose(
            fraction, required_fraction, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
        )
        evaluated.append(
            {
                "test": name,
                "units_tested": tested,
                "units_passed": passed,
                "pass_fraction": fraction,
                "compliant": ok,
            }
        )
        if not ok:
            failed.append(name)
    return {
        "results": evaluated,
        "failed_tests": failed,
        "compliant": not failed,
        "required_pass_fraction": required_fraction,
    }


def assess_relifing(spec):
    """Run the clause 4.3.10 relifing assessment for one stored commercial lot.

    spec keys: package_family, storage_environment, storage_register,
    last_acceptance_date, as_of_date, lot_size, test_results; optional
    original_acceptance_date, relifing_operations_done, max_relifing_operations,
    max_cumulative_storage_months, extension_months, sample_fraction,
    minimum_sample, required_pass_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "package_family",
        "storage_environment",
        "storage_register",
        "last_acceptance_date",
        "as_of_date",
        "lot_size",
        "test_results",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    family = spec["package_family"]
    permitted = permitted_storage_months(
        spec["storage_register"], family, spec["storage_environment"]
    )
    last_acceptance = parse_date(spec["last_acceptance_date"], "last_acceptance_date")
    as_of = parse_date(spec["as_of_date"], "as_of_date")
    if as_of < last_acceptance:
        raise ValueError("as_of_date precedes last_acceptance_date")
    original = parse_date(
        spec.get("original_acceptance_date", last_acceptance), "original_acceptance_date"
    )
    if last_acceptance < original:
        raise ValueError("last_acceptance_date precedes original_acceptance_date")
    expiry = expiry_date(last_acceptance, permitted)
    expired = is_expired(as_of, expiry)
    elapsed = full_months_between(last_acceptance, as_of)
    cumulative = full_months_between(original, as_of)
    sample = relifing_sample_size(
        spec["lot_size"],
        spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        spec.get("minimum_sample", DEFAULT_MIN_SAMPLE),
    )
    required_tests = required_relifing_tests(family)
    findings = []
    result = {
        "permitted_storage_months": permitted,
        "expiry_date": expiry.isoformat(),
        "as_of_date": as_of.isoformat(),
        "elapsed_months": elapsed,
        "cumulative_storage_months": cumulative,
        "expired": expired,
        "sample_size": sample,
        "required_tests": list(required_tests),
        "test_evaluation": None,
        "new_expiry_date": None,
    }
    if not expired:
        result["disposition"] = "in-date"
        result["findings"] = findings
        return result

    findings.append(
        "storage period of %d month(s) ran out on %s; %d month(s) have elapsed"
        % (permitted, expiry.isoformat(), elapsed)
    )
    operations_done = spec.get("relifing_operations_done", 0)
    max_operations = spec.get("max_relifing_operations")
    for label, value in (
        ("relifing_operations_done", operations_done),
        ("max_relifing_operations", max_operations),
    ):
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("%s must be a non-negative integer" % label)
    max_cumulative = spec.get("max_cumulative_storage_months")
    if max_cumulative is not None and (
        not isinstance(max_cumulative, int)
        or isinstance(max_cumulative, bool)
        or max_cumulative <= 0
    ):
        raise ValueError("max_cumulative_storage_months must be a positive integer")

    ceiling_reached = False
    if max_operations is not None and operations_done >= max_operations:
        ceiling_reached = True
        findings.append(
            "lot has already been relifed %d time(s) against a ceiling of %d"
            % (operations_done, max_operations)
        )
    if max_cumulative is not None and cumulative >= max_cumulative:
        ceiling_reached = True
        findings.append(
            "cumulative storage of %d month(s) has reached the ceiling of %d"
            % (cumulative, max_cumulative)
        )
    if ceiling_reached:
        result["disposition"] = "re-screening-required"
        result["findings"] = findings
        return result

    evaluation = evaluate_relifing_tests(
        spec["test_results"], required_tests, spec.get("required_pass_fraction", 1.0)
    )
    result["test_evaluation"] = evaluation
    if not evaluation["compliant"]:
        for name in evaluation["failed_tests"]:
            findings.append("re-verification test '%s' did not meet its pass fraction" % name)
        result["disposition"] = "lot-rejected"
        result["findings"] = findings
        return result

    extension = spec.get("extension_months", permitted)
    if not isinstance(extension, int) or isinstance(extension, bool) or extension <= 0:
        raise ValueError("extension_months must be a positive integer")
    result["new_expiry_date"] = add_months(as_of, extension).isoformat()
    result["extension_months"] = extension
    result["disposition"] = "relifed"
    result["findings"] = findings
    return result
