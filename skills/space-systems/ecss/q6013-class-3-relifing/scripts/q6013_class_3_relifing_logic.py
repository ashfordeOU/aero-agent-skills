"""Relifing of stored commercial EEE parts at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.3.10 (lowest assurance class use of
commercial EEE components -- renewing the usable life of parts already in
store). Paraphrased into an implementable procedure; no standard text is
reproduced.

The question the clause answers
-------------------------------
Parts bought for a build sit in store while the build slips. A storage
period was earned when the lot was accepted; once it has run out the parts
are neither scrap nor usable, and relifing is the operation that decides
which. The lightest class relaxes the operation in three places and tightens
it in one, and the shape of the procedure follows from those four moves.

What this class does differently
--------------------------------
1. An uncontrolled store still earns a short period here, where the classes
   above credit it with nothing. The relaxation is paid for: an uncontrolled
   store reopens moisture preconditioning and electrical re-verification,
   which a graded store does not owe at this class.
2. Relifing evidence is taken on an attribute sample sized from the lot
   rather than on every unit, so the sample plan and the number of units
   actually inspected are part of the decision.
3. Re-tinning after a lone solderability failure is repeatable here up to a
   declared ceiling, instead of being a single allowance.
4. In exchange, the sequence is ended by a cumulative life cap -- a multiple
   of the period the lot originally earned -- rather than by counting
   cycles. Each cycle grants a flat share of the earned period, trimmed to
   whatever headroom is left under the cap, and once that trimmed grant
   falls under the minimum useful extension the lot goes for re-screening.

Procedure implemented here
--------------------------
1. Grade the store the parts actually sat in and scale the package family
   baseline by it to get the period the lot earned.
2. Compare elapsed storage against that period. A lot inside its period is
   not relifed, it is simply still in date.
3. Test the cumulative relifed months against the life cap before any
   evidence is considered.
4. Size the attribute sample from the lot size, assemble the test set the
   lot owes, and refuse a record that is short of the sample or missing an
   owed test.
5. Judge each owed test against the acceptance number; apply the repeatable
   re-tinning allowance to a lone solderability failure.
6. Compute the grant this cycle earns, trim it to the cap headroom, and
   return the renewed period with the findings that produced it.
"""

import math

__all__ = [
    "MONTH_TOLERANCE",
    "DEFAULT_RELIFE_POLICY",
    "STORAGE_GRADES",
    "REOPENING_GRADES",
    "BASE_STORAGE_MONTHS",
    "PACKAGE_FAMILIES",
    "HERMETIC_FAMILIES",
    "EXTERNAL_VISUAL",
    "SOLDERABILITY",
    "PACKAGE_SEAL",
    "MOISTURE_PRECONDITIONING",
    "ELECTRICAL_RE_VERIFICATION",
    "RELIFE_NOT_REQUIRED",
    "RELIFE_GRANTED",
    "RETINNING_PERMITTED",
    "RELIFE_REFUSED_LIFE_CAP_REACHED",
    "RELIFE_REFUSED_SAMPLE_SHORT",
    "RELIFE_REFUSED_TESTS_INCOMPLETE",
    "RELIFE_REFUSED_SAMPLE_DEFECTIVE",
    "RELIFE_REFUSED_NO_USEFUL_EXTENSION",
    "validate_relife_policy",
    "storage_grade_factor",
    "base_storage_months",
    "earned_storage_months",
    "storage_period_expired",
    "relife_sample_size",
    "required_relife_tests",
    "validate_sample_record",
    "failing_relife_tests",
    "cumulative_life_cap_months",
    "granted_extension_months",
    "assess_relifing",
]

# Storage periods are months carried as real numbers because a graded store
# scales them. A lot landing exactly on its period is inside it, and the
# scaling can leave the two sides a few ULP apart on one platform and not on
# another, so the representation error is absorbed here rather than by
# padding a period.
MONTH_TOLERANCE = 1e-9

DEFAULT_RELIFE_POLICY = {
    # Flat share of the earned period granted by each relifing cycle.
    "extension_fraction": 0.25,
    # Below this the relife buys too little to be worth the evidence.
    "min_extension_months": 2.0,
    # Total relifed months may not exceed this multiple of the earned period.
    "cumulative_life_multiple": 2.0,
    # How many times one lot may be re-tinned and retested.
    "max_retins": 2,
    # Attribute sample plan bounds and acceptance number.
    "sample_floor": 5,
    "sample_ceiling": 32,
    "accept_defects": 0,
}

# Credited fraction of the baseline storage period, by the store the parts
# were actually kept in. The lightest class still credits an uncontrolled
# store, but only just, and it pays for the credit in extra evidence.
STORAGE_GRADES = {
    "dry-nitrogen-cabinet": 1.0,
    "dry-cabinet-low-humidity": 0.8,
    "humidity-controlled-store": 0.6,
    "uncontrolled-store": 0.25,
}

# Stores whose credit reopens the fuller test set.
REOPENING_GRADES = frozenset({"uncontrolled-store"})

# Baseline storage period in months by package family, before the store is
# applied.
BASE_STORAGE_MONTHS = {
    "hermetic-ceramic": 48.0,
    "hermetic-metal": 48.0,
    "plastic-encapsulated": 24.0,
    "tape-and-reel-passive": 36.0,
    "bare-die-in-waffle-pack": 12.0,
}

PACKAGE_FAMILIES = frozenset(BASE_STORAGE_MONTHS)

HERMETIC_FAMILIES = frozenset({"hermetic-ceramic", "hermetic-metal"})

EXTERNAL_VISUAL = "external-visual"
SOLDERABILITY = "solderability"
PACKAGE_SEAL = "package-seal"
MOISTURE_PRECONDITIONING = "moisture-preconditioning"
ELECTRICAL_RE_VERIFICATION = "electrical-re-verification"

RELIFE_NOT_REQUIRED = "storage-period-still-running"
RELIFE_GRANTED = "relife-granted"
RETINNING_PERMITTED = "retinning-and-retest-permitted"
RELIFE_REFUSED_LIFE_CAP_REACHED = "relife-refused-cumulative-life-cap-reached"
RELIFE_REFUSED_SAMPLE_SHORT = "relife-refused-sample-short"
RELIFE_REFUSED_TESTS_INCOMPLETE = "relife-refused-tests-incomplete"
RELIFE_REFUSED_SAMPLE_DEFECTIVE = "relife-refused-sample-defective"
RELIFE_REFUSED_NO_USEFUL_EXTENSION = "relife-refused-no-useful-extension"


def _at_or_below(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=MONTH_TOLERANCE, abs_tol=0.0
    )


def _validate_months(value, label, allow_zero=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number of months" % label)
    months = float(value)
    if not math.isfinite(months):
        raise ValueError("%s must be finite" % label)
    if months < 0.0 or (months == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return months


def _validate_count(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (label, minimum, value))
    return value


def _validate_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def _validate_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def validate_relife_policy(policy):
    """Validate a relifing policy and return it unchanged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in DEFAULT_RELIFE_POLICY:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    fraction = policy["extension_fraction"]
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise ValueError("extension_fraction must be a real number")
    fraction = float(fraction)
    if not math.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "extension_fraction must lie above zero and at most unity, got %r"
            % policy["extension_fraction"]
        )
    multiple = policy["cumulative_life_multiple"]
    if not isinstance(multiple, (int, float)) or isinstance(multiple, bool):
        raise ValueError("cumulative_life_multiple must be a real number")
    multiple = float(multiple)
    if not math.isfinite(multiple) or multiple <= 0.0:
        raise ValueError(
            "cumulative_life_multiple must lie above zero, got %r"
            % policy["cumulative_life_multiple"]
        )
    _validate_months(
        policy["min_extension_months"], "min_extension_months", allow_zero=False
    )
    _validate_count(policy["max_retins"], "max_retins")
    floor = _validate_count(policy["sample_floor"], "sample_floor", minimum=1)
    ceiling = _validate_count(policy["sample_ceiling"], "sample_ceiling", minimum=1)
    if ceiling < floor:
        raise ValueError(
            "sample_ceiling %d sits below sample_floor %d" % (ceiling, floor)
        )
    _validate_count(policy["accept_defects"], "accept_defects")
    return policy


def storage_grade_factor(environment):
    """Return the credited fraction of the baseline period for a store."""
    key = _validate_text(environment, "environment").lower()
    if key not in STORAGE_GRADES:
        raise ValueError(
            "storage environment '%s' is not in the register; grade it explicitly "
            "rather than assuming a period that was never earned" % key
        )
    return STORAGE_GRADES[key]


def base_storage_months(family):
    """Return the baseline storage period in months for a package family."""
    key = _validate_text(family, "package family").lower()
    if key not in BASE_STORAGE_MONTHS:
        raise ValueError("package family '%s' is not in the register" % key)
    return BASE_STORAGE_MONTHS[key]


def earned_storage_months(family, environment):
    """Return the storage period a lot actually earned in its store."""
    return base_storage_months(family) * storage_grade_factor(environment)


def storage_period_expired(elapsed_months, permitted_months):
    """True when elapsed storage has run past the permitted period.

    A lot sitting exactly on its permitted period is inside it.
    """
    elapsed = _validate_months(elapsed_months, "elapsed_months")
    permitted = _validate_months(permitted_months, "permitted_months")
    return not _at_or_below(elapsed, permitted)


def relife_sample_size(lot_size, policy=None):
    """Return the number of units the attribute sample plan inspects.

    The plan is the integer square root of the lot size, held between the
    declared floor and ceiling and never above the lot itself. An integer
    square root is used rather than a floating one so the plan is the same
    number on every platform the leaf runs on.
    """
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    units = _validate_count(lot_size, "lot_size", minimum=1)
    size = math.isqrt(units)
    floor = policy["sample_floor"]
    ceiling = policy["sample_ceiling"]
    if size < floor:
        size = floor
    if size > ceiling:
        size = ceiling
    if size > units:
        size = units
    return size


def required_relife_tests(family, environment, moisture_sensitive):
    """Return the ordered test set this lot owes for the next relife cycle."""
    key = _validate_text(family, "package family").lower()
    if key not in PACKAGE_FAMILIES:
        raise ValueError("package family '%s' is not in the register" % key)
    grade = _validate_text(environment, "environment").lower()
    if grade not in STORAGE_GRADES:
        raise ValueError("storage environment '%s' is not in the register" % grade)
    moisture_sensitive = _validate_flag(moisture_sensitive, "moisture_sensitive")
    hermetic = key in HERMETIC_FAMILIES
    if moisture_sensitive and hermetic:
        raise ValueError(
            "a hermetic family cannot also be declared moisture sensitive; the seal "
            "is what makes the distinction"
        )
    reopened = grade in REOPENING_GRADES
    tests = [EXTERNAL_VISUAL, SOLDERABILITY]
    if hermetic:
        tests.append(PACKAGE_SEAL)
    if not hermetic and (moisture_sensitive or reopened):
        tests.append(MOISTURE_PRECONDITIONING)
    if reopened:
        tests.append(ELECTRICAL_RE_VERIFICATION)
    return tests


def validate_sample_record(record, required, sample_size, policy=None):
    """Validate a relifing sample record against the test set it owes.

    The record maps each owed test to the number of defective units the
    sample showed. A test the lot does not owe is refused rather than
    quietly credited, and an owed test absent from the record is reported
    by name rather than read as a pass.
    """
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping of test name to defect count")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of test names")
    size = _validate_count(sample_size, "sample_size", minimum=1)
    cleaned = {}
    for name, defects in record.items():
        key = _validate_text(name, "test name").lower()
        if key in cleaned:
            raise ValueError("test '%s' appears twice" % key)
        count = _validate_count(defects, "defect count for test '%s'" % key)
        if count > size:
            raise ValueError(
                "test '%s' reports %d defective unit(s) from a sample of %d"
                % (key, count, size)
            )
        cleaned[key] = count
    unknown = sorted(set(cleaned) - set(required))
    if unknown:
        raise ValueError(
            "record carries tests this lot does not owe: %s" % ", ".join(unknown)
        )
    missing = [name for name in required if name not in cleaned]
    return {
        "defects": cleaned,
        "missing": missing,
        "complete": not missing,
        "sample_size": size,
    }


def failing_relife_tests(record, required, sample_size, policy=None):
    """Return the owed tests whose defect count exceeds the acceptance number."""
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    checked = validate_sample_record(record, required, sample_size, policy)
    accept = policy["accept_defects"]
    return [
        name
        for name in required
        if checked["defects"].get(name, 0) > accept
    ]


def cumulative_life_cap_months(family, environment, policy=None):
    """Return the total relifed months this lot may ever be granted."""
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    return earned_storage_months(family, environment) * float(
        policy["cumulative_life_multiple"]
    )


def granted_extension_months(family, environment, relifed_to_date, policy=None):
    """Return the extension the next relifing cycle grants.

    Each cycle grants a flat share of the period the lot earned in its
    store, trimmed to whatever headroom is left under the cumulative life
    cap. The trim, not a decay, is what ends the sequence at this class.
    """
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    already = _validate_months(relifed_to_date, "relifed_to_date")
    earned = earned_storage_months(family, environment)
    cap = cumulative_life_cap_months(family, environment, policy)
    headroom = cap - already
    if headroom <= 0.0:
        return 0.0
    grant = earned * float(policy["extension_fraction"])
    if grant > headroom:
        grant = headroom
    return grant


def assess_relifing(case, policy=None):
    """Run the clause 6.3.10 assessment for one stored commercial lot.

    case keys: package_family, storage_environment, elapsed_storage_months,
    lot_size, units_inspected, moisture_sensitive, sample_results,
    relifed_months_to_date, retins_used.
    """
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in (
        "package_family",
        "storage_environment",
        "elapsed_storage_months",
        "lot_size",
        "units_inspected",
        "moisture_sensitive",
        "sample_results",
        "relifed_months_to_date",
        "retins_used",
    ):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    family = _validate_text(case["package_family"], "package_family").lower()
    environment = _validate_text(
        case["storage_environment"], "storage_environment"
    ).lower()
    elapsed = _validate_months(case["elapsed_storage_months"], "elapsed_storage_months")
    lot_size = _validate_count(case["lot_size"], "lot_size", minimum=1)
    inspected = _validate_count(case["units_inspected"], "units_inspected")
    moisture_sensitive = _validate_flag(case["moisture_sensitive"], "moisture_sensitive")
    already = _validate_months(
        case["relifed_months_to_date"], "relifed_months_to_date"
    )
    retins_used = _validate_count(case["retins_used"], "retins_used")
    factor = storage_grade_factor(environment)
    earned = earned_storage_months(family, environment)
    cap = cumulative_life_cap_months(family, environment, policy)
    sample = relife_sample_size(lot_size, policy)
    findings = []
    record = {
        "package_family": family,
        "storage_environment": environment,
        "storage_factor": factor,
        "baseline_months": base_storage_months(family),
        "earned_months": earned,
        "elapsed_months": elapsed,
        "cumulative_cap_months": cap,
        "relifed_months_to_date": already,
        "sample_size": sample,
        "units_inspected": inspected,
        "required_tests": [],
        "missing_tests": [],
        "failed_tests": [],
        "granted_extension_months": 0.0,
        "renewed_period_months": earned,
        "findings": findings,
    }
    if not storage_period_expired(elapsed, earned):
        findings.append(
            "elapsed storage of %g month(s) is inside the %g month(s) the lot "
            "earned in a %s" % (elapsed, earned, environment)
        )
        record["verdict"] = RELIFE_NOT_REQUIRED
        record["relifed"] = False
        return record
    if _at_or_below(cap, already):
        findings.append(
            "the lot has already been relifed %g month(s) against a cumulative cap "
            "of %g; it goes for re-screening rather than another relife"
            % (already, cap)
        )
        record["verdict"] = RELIFE_REFUSED_LIFE_CAP_REACHED
        record["relifed"] = False
        return record
    required = required_relife_tests(family, environment, moisture_sensitive)
    record["required_tests"] = required
    if inspected < sample:
        findings.append(
            "the record covers %d unit(s) where the attribute plan for a lot of %d "
            "inspects %d" % (inspected, lot_size, sample)
        )
        record["verdict"] = RELIFE_REFUSED_SAMPLE_SHORT
        record["relifed"] = False
        return record
    checked = validate_sample_record(case["sample_results"], required, sample, policy)
    record["missing_tests"] = checked["missing"]
    if not checked["complete"]:
        findings.append(
            "relifing record is missing %s" % ", ".join(checked["missing"])
        )
        record["verdict"] = RELIFE_REFUSED_TESTS_INCOMPLETE
        record["relifed"] = False
        return record
    accept = policy["accept_defects"]
    failures = [name for name in required if checked["defects"][name] > accept]
    record["failed_tests"] = failures
    if failures:
        if failures == [SOLDERABILITY] and retins_used < policy["max_retins"]:
            findings.append(
                "solderability is the only test over the acceptance number and %d of "
                "%d re-tins remain; re-tin and retest before disposing of the lot"
                % (policy["max_retins"] - retins_used, policy["max_retins"])
            )
            record["verdict"] = RETINNING_PERMITTED
            record["relifed"] = False
            return record
        for name in failures:
            findings.append(
                "relifing test '%s' showed %d defective unit(s) against an acceptance "
                "number of %d" % (name, checked["defects"][name], accept)
            )
        record["verdict"] = RELIFE_REFUSED_SAMPLE_DEFECTIVE
        record["relifed"] = False
        return record
    grant = granted_extension_months(family, environment, already, policy)
    record["granted_extension_months"] = grant
    if not _at_or_below(float(policy["min_extension_months"]), grant):
        findings.append(
            "the cycle would grant %g month(s), under the %g month minimum; the lot "
            "goes for re-screening" % (grant, policy["min_extension_months"])
        )
        record["verdict"] = RELIFE_REFUSED_NO_USEFUL_EXTENSION
        record["relifed"] = False
        return record
    record["renewed_period_months"] = elapsed + grant
    findings.append(
        "the cycle grants %g further month(s) against %g month(s) of cap headroom"
        % (grant, cap - already)
    )
    record["verdict"] = RELIFE_GRANTED
    record["relifed"] = True
    return record
