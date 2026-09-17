"""Relifing of stored Class 2 EEE stock.

Anchor: ECSS-Q-ST-60C clause 5.3.10 (restoring the validity of stored Class 2
parts whose original storage period has expired). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Scale the package family's baseline storage period by the store the parts
   actually sat in, so a lot kept under dry nitrogen and a lot kept in an
   uncontrolled bay are not granted the same period.
2. Test the elapsed storage against the period that grant allows. Stock still
   inside its period owes nothing; relifing is a recovery, not a routine.
3. Check the relifing round ceiling before any test is sized. Stock that has
   used up its permitted rounds is referred to full re-screening, because
   repeated relifing cannot substitute for re-establishing the screen.
4. Assemble the test set the package family, the lead finish and the part
   function owe, and judge every result against its accept number.
5. Re-grant a shortened storage period from the relifing date, decaying with
   each round and floored so a re-grant too short to be useful is refused.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "PACKAGE_BASELINE_MONTHS",
    "STORE_MULTIPLIER",
    "MAX_RELIFING_ROUNDS",
    "REGRANT_DECAY",
    "MINIMUM_REGRANT_MONTHS",
    "DEFAULT_SAMPLE_FRACTION",
    "MINIMUM_RELIFING_SAMPLE",
    "MAXIMUM_RELIFING_SAMPLE",
    "DEFAULT_ACCEPT_NUMBER",
    "HERMETIC_FAMILIES",
    "BASE_RELIFING_TESTS",
    "baseline_storage_months",
    "store_multiplier",
    "granted_storage_months",
    "storage_expired",
    "relifing_round_ceiling_reached",
    "relifing_test_set",
    "relifing_sample_size",
    "evaluate_relifing_results",
    "regranted_period_months",
    "assess_relifing",
]

# Scaled periods and decayed re-grants are products of measured values; a case
# meant to land exactly on a period can sit a few ULP either side of it.
# Absorb the representation error here, never by moving the period.
BOUND_TOLERANCE = 1e-9

# Baseline storage period in months by package family, before the store the
# parts sat in is taken into account.
PACKAGE_BASELINE_MONTHS = {
    "hermetic-metal": 60.0,
    "hermetic-ceramic": 60.0,
    "glass-sealed": 48.0,
    "passive-chip": 36.0,
    "plastic-encapsulated": 24.0,
}

# The store is a multiplier on the baseline, not a separate clock.
STORE_MULTIPLIER = {
    "dry-nitrogen": 1.5,
    "controlled": 1.0,
    "uncontrolled": 0.5,
}

HERMETIC_FAMILIES = ("hermetic-metal", "hermetic-ceramic", "glass-sealed")

# Every relifing starts with an external visual: it is the only test that can
# find handling damage the store itself caused.
BASE_RELIFING_TESTS = ("external-visual",)

MAX_RELIFING_ROUNDS = 3
REGRANT_DECAY = 0.5
MINIMUM_REGRANT_MONTHS = 3.0

DEFAULT_SAMPLE_FRACTION = 0.05
MINIMUM_RELIFING_SAMPLE = 3
MAXIMUM_RELIFING_SAMPLE = 12
DEFAULT_ACCEPT_NUMBER = 0


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
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _positive_real(value, label):
    """Return value as a finite positive float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_real(value, label):
    """Return value as a finite non-negative float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _clean_token(value, label):
    """Return a stripped lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _at_most(value, bound):
    """Return True when value sits at or under bound, tolerant of float noise."""
    return value < bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def _at_least(value, bound):
    """Return True when value sits at or above bound, tolerant of float noise."""
    return value > bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def baseline_storage_months(package_family, table=None):
    """Return the baseline storage period a package family carries."""
    if table is None:
        table = PACKAGE_BASELINE_MONTHS
    if not isinstance(table, dict) or not table:
        raise ValueError("table must be a non-empty mapping of family to months")
    family = _clean_token(package_family, "package_family")
    if family not in table:
        raise ValueError(
            "package family '%s' is not in the storage period register; an unlisted "
            "family is refused, not interpolated from a neighbour" % family
        )
    return _positive_real(table[family], "baseline period for '%s'" % family)


def store_multiplier(store_class, table=None):
    """Return the multiplier the store the parts sat in applies."""
    if table is None:
        table = STORE_MULTIPLIER
    if not isinstance(table, dict) or not table:
        raise ValueError("table must be a non-empty mapping of store to multiplier")
    store = _clean_token(store_class, "store_class")
    if store not in table:
        raise ValueError(
            "store '%s' is not a graded storage condition; grade the store before "
            "the period is scaled by it" % store
        )
    return _positive_real(table[store], "multiplier for store '%s'" % store)


def granted_storage_months(package_family, store_class, baselines=None, stores=None):
    """Return the storage period the package and the store together grant."""
    return baseline_storage_months(package_family, baselines) * store_multiplier(
        store_class, stores
    )


def storage_expired(elapsed_months, granted_months):
    """Return True when the elapsed storage has run past the granted period.

    Stock sitting exactly on its period has not expired: the period is a
    duration the stock is entitled to, and the last day of it is inside.
    """
    elapsed = _non_negative_real(elapsed_months, "elapsed_months")
    granted = _positive_real(granted_months, "granted_months")
    return not _at_most(elapsed, granted)


def relifing_round_ceiling_reached(completed_rounds, ceiling=MAX_RELIFING_ROUNDS):
    """Return True when the stock has used up its permitted relifing rounds."""
    completed = _non_negative_int(completed_rounds, "completed_rounds")
    ceiling = _positive_int(ceiling, "ceiling")
    return completed >= ceiling


def relifing_test_set(package_family, lead_finish, part_function):
    """Return the tests this stock owes before its validity can be restored."""
    family = _clean_token(package_family, "package_family")
    if family not in PACKAGE_BASELINE_MONTHS:
        raise ValueError("package family '%s' is not in the storage register" % family)
    finish = _clean_token(lead_finish, "lead_finish")
    function = _clean_token(part_function, "part_function")
    if function not in ("active", "passive"):
        raise ValueError(
            "part_function must be 'active' or 'passive', got '%s'" % function
        )
    tests = list(BASE_RELIFING_TESTS)
    if finish != "none":
        tests.append("solderability-sample")
    if finish == "pure-tin":
        tests.append("whisker-risk-review")
    if family in HERMETIC_FAMILIES:
        tests.append("fine-and-gross-leak")
    if function == "active":
        tests.append("electrical-at-temperature-extremes")
    return tuple(tests)


def relifing_sample_size(
    lot_size,
    fraction=DEFAULT_SAMPLE_FRACTION,
    minimum=MINIMUM_RELIFING_SAMPLE,
    maximum=MAXIMUM_RELIFING_SAMPLE,
):
    """Return the number of units the relifing tests are run on."""
    lot_size = _positive_int(lot_size, "lot_size")
    minimum = _positive_int(minimum, "minimum")
    maximum = _positive_int(maximum, "maximum")
    if maximum < minimum:
        raise ValueError(
            "maximum sample %d sits below the minimum sample %d" % (maximum, minimum)
        )
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
        raise ValueError("fraction must be a real number, got %r" % (fraction,))
    fraction = float(fraction)
    if not math.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("fraction must lie in (0, 1], got %r" % (fraction,))
    if lot_size < minimum:
        raise ValueError(
            "a lot of %d unit(s) cannot supply the minimum relifing sample of %d"
            % (lot_size, minimum)
        )
    proportional = int(math.ceil(lot_size * fraction - BOUND_TOLERANCE))
    return min(lot_size, maximum, max(minimum, proportional))


def evaluate_relifing_results(
    owed_tests, results, sample_size, accept_number=DEFAULT_ACCEPT_NUMBER
):
    """Judge each owed relifing test against its accept number.

    results maps a test name to the number of units that failed it. A test the
    stock owes with no result is refused, and so is a result for a test it does
    not owe: neither can be silently read as a pass.
    """
    if not isinstance(owed_tests, (list, tuple)) or not owed_tests:
        raise ValueError("owed_tests must be a non-empty sequence of test names")
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of test name to a failure count")
    sample_size = _positive_int(sample_size, "sample_size")
    accept_number = _non_negative_int(accept_number, "accept_number")
    owed = [_clean_token(name, "owed test name") for name in owed_tests]
    reported = {_clean_token(name, "result test name"): count for name, count in results.items()}
    for name in owed:
        if name not in reported:
            raise ValueError("relifing test '%s' was owed but has no result" % name)
    for name in reported:
        if name not in owed:
            raise ValueError(
                "result reported for '%s', which this stock does not owe" % name
            )
    verdicts = {}
    failed_tests = []
    for name in owed:
        failures = _non_negative_int(reported[name], "failure count for '%s'" % name)
        if failures > sample_size:
            raise ValueError(
                "test '%s' reports %d failure(s) from a sample of %d"
                % (name, failures, sample_size)
            )
        passed = failures <= accept_number
        verdicts[name] = {
            "failures": failures,
            "accept_number": accept_number,
            "passed": passed,
        }
        if not passed:
            failed_tests.append(name)
    return {
        "sample_size": sample_size,
        "verdicts": verdicts,
        "failed_tests": tuple(failed_tests),
        "all_passed": not failed_tests,
    }


def regranted_period_months(
    granted_months,
    completed_rounds,
    decay=REGRANT_DECAY,
    minimum=MINIMUM_REGRANT_MONTHS,
):
    """Return the shortened period a successful relifing re-grants.

    The period decays with every round already completed, because each round
    restores validity to stock that has spent longer in store than the round
    before it. The decay is applied by repeated multiplication rather than by
    an exponent, so the same rounds give the same answer on every platform.
    """
    granted = _positive_real(granted_months, "granted_months")
    completed = _non_negative_int(completed_rounds, "completed_rounds")
    decay = _positive_real(decay, "decay")
    if decay > 1.0:
        raise ValueError("decay must not extend the period, got %r" % (decay,))
    minimum = _positive_real(minimum, "minimum")
    period = granted
    for _ in range(completed + 1):
        period = period * decay
    return {
        "regranted_months": period,
        "rounds_applied": completed + 1,
        "minimum_months": minimum,
        "usable": _at_least(period, minimum),
    }


def assess_relifing(spec):
    """Run the clause 5.3.10 relifing assessment for one stored Class 2 lot.

    Required spec keys: package_family, store_class, elapsed_months, lot_size,
    lead_finish, part_function, test_results. Optional: completed_rounds,
    round_ceiling, sample_fraction, minimum_sample, maximum_sample,
    accept_number, regrant_decay, minimum_regrant_months.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "package_family",
        "store_class",
        "elapsed_months",
        "lot_size",
        "lead_finish",
        "part_function",
        "test_results",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    granted = granted_storage_months(spec["package_family"], spec["store_class"])
    elapsed = _non_negative_real(spec["elapsed_months"], "elapsed_months")
    completed = _non_negative_int(spec.get("completed_rounds", 0), "completed_rounds")
    ceiling = _positive_int(spec.get("round_ceiling", MAX_RELIFING_ROUNDS), "round_ceiling")

    result = {
        "granted_storage_months": granted,
        "elapsed_months": elapsed,
        "months_over_period": max(0.0, elapsed - granted),
        "completed_rounds": completed,
        "round_ceiling": ceiling,
    }

    if not storage_expired(elapsed, granted):
        result["disposition"] = "relifing-not-required"
        result["reasons"] = [
            "elapsed storage of %g month(s) is inside the %g month(s) the package "
            "and store grant" % (elapsed, granted)
        ]
        return result

    if relifing_round_ceiling_reached(completed, ceiling):
        result["disposition"] = "re-screening-required"
        result["reasons"] = [
            "%d relifing round(s) already completed against a ceiling of %d; the "
            "stock owes full re-screening rather than a further relifing"
            % (completed, ceiling)
        ]
        return result

    owed = relifing_test_set(
        spec["package_family"], spec["lead_finish"], spec["part_function"]
    )
    sample = relifing_sample_size(
        spec["lot_size"],
        spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        spec.get("minimum_sample", MINIMUM_RELIFING_SAMPLE),
        spec.get("maximum_sample", MAXIMUM_RELIFING_SAMPLE),
    )
    tests = evaluate_relifing_results(
        owed,
        spec["test_results"],
        sample,
        spec.get("accept_number", DEFAULT_ACCEPT_NUMBER),
    )
    result["owed_tests"] = owed
    result["test_evaluation"] = tests

    if not tests["all_passed"]:
        result["disposition"] = "relifing-refused"
        result["reasons"] = [
            "relifing test '%s' exceeded its accept number" % name
            for name in tests["failed_tests"]
        ]
        return result

    regrant = regranted_period_months(
        granted,
        completed,
        spec.get("regrant_decay", REGRANT_DECAY),
        spec.get("minimum_regrant_months", MINIMUM_REGRANT_MONTHS),
    )
    result["regrant"] = regrant
    if not regrant["usable"]:
        result["disposition"] = "re-screening-required"
        result["reasons"] = [
            "a re-granted period of %.2f month(s) is under the %.2f month floor; the "
            "stock owes re-screening rather than a period too short to issue against"
            % (regrant["regranted_months"], regrant["minimum_months"])
        ]
        return result

    result["disposition"] = "relifing-granted"
    result["reasons"] = [
        "every owed relifing test met its accept number on a sample of %d" % sample,
        "a further %.2f month(s) are granted from the relifing date"
        % regrant["regranted_months"],
    ]
    return result
