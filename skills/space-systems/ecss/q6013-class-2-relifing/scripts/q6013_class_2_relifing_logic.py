"""Relifing of stored commercial EEE parts at the middle assurance class.

Anchor: ECSS-Q-ST-60-13C clause 5.3.10 (intermediate assurance class use of
commercial EEE components -- extending the usable life of parts already in
store). Paraphrased into an implementable procedure; no standard text is
reproduced.

The question the clause answers
-------------------------------
Parts bought for a build sit in store while the build slips. A storage
period was granted when the lot was accepted; once it has run out the parts
are not scrap and they are not usable either, and relifing is the operation
that decides which. This class grants two allowances the class above does
not: a solderability failure may be re-tinned once and retested rather than
disposing of the lot, and electrical re-verification is owed only from a
declared relifing cycle onwards rather than at every cycle.

Procedure implemented here
--------------------------
1. Grade the environment the parts were actually stored in, and scale the
   baseline storage period of the package family by it. An environment with
   no credited factor grants no storage period at all, so a lot kept there
   cannot be relifed on the strength of its storage record.
2. Compare the elapsed storage against the scaled period. A lot inside its
   period is not relifed, it is simply still in date.
3. Check the ceiling on relifing cycles before any test is considered. A lot
   that has used its cycles goes for re-screening, not for another relife.
4. Assemble the test set this lot owes -- external visual and solderability
   always, a seal test for a hermetic family, moisture preconditioning for a
   moisture-sensitive plastic family, and electrical re-verification from the
   declared cycle onwards -- and refuse a record that is missing one.
5. Apply the re-tinning allowance: a solderability failure standing alone,
   on a lot that has not already used the allowance, permits one re-tin and
   retest. Any other failure disposes of the lot.
6. Compute the extension granted. Each cycle grants less than the one before
   it, and once the grant falls under the minimum useful extension the lot
   goes for re-screening rather than being relifed for a few weeks.
"""

import math

__all__ = [
    "MONTH_TOLERANCE",
    "DEFAULT_RELIFE_POLICY",
    "STORAGE_ENVIRONMENTS",
    "PACKAGE_FAMILIES",
    "HERMETIC_FAMILIES",
    "BASE_STORAGE_MONTHS",
    "EXTERNAL_VISUAL",
    "SOLDERABILITY",
    "PACKAGE_SEAL",
    "MOISTURE_PRECONDITIONING",
    "ELECTRICAL_RE_VERIFICATION",
    "RELIFE_NOT_REQUIRED",
    "RELIFE_GRANTED",
    "RETINNING_PERMITTED",
    "RELIFE_REFUSED_STORAGE_UNCONTROLLED",
    "RELIFE_REFUSED_CYCLE_LIMIT",
    "RELIFE_REFUSED_TESTS_INCOMPLETE",
    "RELIFE_REFUSED_TEST_FAILURE",
    "RELIFE_REFUSED_NO_USEFUL_EXTENSION",
    "validate_relife_policy",
    "storage_environment_factor",
    "base_storage_months",
    "effective_storage_months",
    "storage_period_expired",
    "required_relife_tests",
    "validate_test_results",
    "test_failures",
    "granted_extension_months",
    "assess_relifing",
]

# Storage periods are months carried as real numbers because a graded
# environment scales them. A lot landing exactly on its period is inside it,
# and the scaling can leave the two sides a few ULP apart on one platform and
# not on another, so the representation error is absorbed here.
MONTH_TOLERANCE = 1e-9

DEFAULT_RELIFE_POLICY = {
    # Each relifing cycle grants less than the one before it.
    "extension_decay": 0.5,
    # Below this the relife buys too little to be worth the tests.
    "min_extension_months": 3.0,
    # Hard ceiling on how many times one lot may be relifed.
    "max_relife_cycles": 3,
    # Electrical re-verification is owed from this cycle onwards.
    "electrical_from_cycle": 2,
    # One solderability failure may be re-tinned and retested at this class.
    "allow_retinning": True,
}

# Credited fraction of the baseline storage period, by the environment the
# parts were actually kept in. An uncontrolled store credits nothing: the
# record says where the box was, not what the atmosphere did to the leads.
STORAGE_ENVIRONMENTS = {
    "dry-nitrogen-cabinet": 1.0,
    "dry-cabinet-low-humidity": 0.8,
    "controlled-ambient": 0.5,
    "uncontrolled": 0.0,
}

# Baseline storage period in months by package family, before the storage
# environment is applied.
BASE_STORAGE_MONTHS = {
    "hermetic-ceramic": 60.0,
    "hermetic-metal": 60.0,
    "plastic-encapsulated": 24.0,
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
RELIFE_REFUSED_STORAGE_UNCONTROLLED = "relife-refused-storage-uncontrolled"
RELIFE_REFUSED_CYCLE_LIMIT = "relife-refused-cycle-limit-reached"
RELIFE_REFUSED_TESTS_INCOMPLETE = "relife-refused-tests-incomplete"
RELIFE_REFUSED_TEST_FAILURE = "relife-refused-test-failure"
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
    decay = policy["extension_decay"]
    if not isinstance(decay, (int, float)) or isinstance(decay, bool):
        raise ValueError("extension_decay must be a real number")
    decay = float(decay)
    if not math.isfinite(decay) or decay <= 0.0 or decay > 1.0:
        raise ValueError(
            "extension_decay must lie above zero and at most unity, got %r"
            % policy["extension_decay"]
        )
    _validate_months(policy["min_extension_months"], "min_extension_months", allow_zero=False)
    _validate_count(policy["max_relife_cycles"], "max_relife_cycles", minimum=1)
    _validate_count(policy["electrical_from_cycle"], "electrical_from_cycle", minimum=1)
    _validate_flag(policy["allow_retinning"], "allow_retinning")
    return policy


def storage_environment_factor(environment):
    """Return the credited fraction of the baseline period for a store."""
    key = _validate_text(environment, "environment").lower()
    if key not in STORAGE_ENVIRONMENTS:
        raise ValueError(
            "storage environment '%s' is not in the register; grade it explicitly "
            "rather than assuming a period that was never granted" % key
        )
    return STORAGE_ENVIRONMENTS[key]


def base_storage_months(family):
    """Return the baseline storage period in months for a package family."""
    key = _validate_text(family, "package family").lower()
    if key not in BASE_STORAGE_MONTHS:
        raise ValueError("package family '%s' is not in the register" % key)
    return BASE_STORAGE_MONTHS[key]


def effective_storage_months(family, environment):
    """Return the storage period a lot actually earned in its store."""
    return base_storage_months(family) * storage_environment_factor(environment)


def storage_period_expired(elapsed_months, permitted_months):
    """True when the elapsed storage has run past the permitted period.

    A lot sitting exactly on its permitted period is inside it.
    """
    elapsed = _validate_months(elapsed_months, "elapsed_months")
    permitted = _validate_months(permitted_months, "permitted_months")
    return not _at_or_below(elapsed, permitted)


def required_relife_tests(family, moisture_sensitive, completed_cycles, policy=None):
    """Return the ordered test set this lot owes for the next relife cycle."""
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    key = _validate_text(family, "package family").lower()
    if key not in PACKAGE_FAMILIES:
        raise ValueError("package family '%s' is not in the register" % key)
    moisture_sensitive = _validate_flag(moisture_sensitive, "moisture_sensitive")
    completed_cycles = _validate_count(completed_cycles, "completed_cycles")
    if moisture_sensitive and key in HERMETIC_FAMILIES:
        raise ValueError(
            "a hermetic family cannot also be declared moisture sensitive; the seal "
            "is what makes the distinction"
        )
    tests = [EXTERNAL_VISUAL, SOLDERABILITY]
    if key in HERMETIC_FAMILIES:
        tests.append(PACKAGE_SEAL)
    if moisture_sensitive:
        tests.append(MOISTURE_PRECONDITIONING)
    if completed_cycles + 1 >= policy["electrical_from_cycle"]:
        tests.append(ELECTRICAL_RE_VERIFICATION)
    return tests


def validate_test_results(results, required):
    """Validate a relifing test record against the test set it owes."""
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of test name to outcome")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of test names")
    cleaned = {}
    for name, outcome in results.items():
        key = _validate_text(name, "test name").lower()
        if key in cleaned:
            raise ValueError("test '%s' appears twice" % key)
        cleaned[key] = _validate_flag(outcome, "outcome for test '%s'" % key)
    unknown = sorted(set(cleaned) - set(required))
    if unknown:
        raise ValueError(
            "results carry tests this lot does not owe: %s" % ", ".join(unknown)
        )
    missing = [name for name in required if name not in cleaned]
    return {"results": cleaned, "missing": missing, "complete": not missing}


def test_failures(results, required):
    """Return the owed tests that were performed and did not pass."""
    record = validate_test_results(results, required)
    return [name for name in required if record["results"].get(name) is False]


def granted_extension_months(family, environment, completed_cycles, policy=None):
    """Return the extension a lot earns on its next relifing cycle.

    Each cycle grants a decayed share of the period the lot earned in its
    store. The decay is applied by repeated multiplication rather than by a
    power, so the result is reproducible across platforms.
    """
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    completed_cycles = _validate_count(completed_cycles, "completed_cycles")
    extension = effective_storage_months(family, environment)
    decay = float(policy["extension_decay"])
    for _ in range(completed_cycles + 1):
        extension *= decay
    return extension


def assess_relifing(case, policy=None):
    """Run the clause 5.3.10 assessment for one stored commercial lot.

    case keys: package_family, storage_environment, elapsed_storage_months,
    completed_relife_cycles, moisture_sensitive, test_results,
    retinning_already_used.
    """
    policy = validate_relife_policy(DEFAULT_RELIFE_POLICY if policy is None else policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in (
        "package_family",
        "storage_environment",
        "elapsed_storage_months",
        "completed_relife_cycles",
        "moisture_sensitive",
        "test_results",
        "retinning_already_used",
    ):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    family = _validate_text(case["package_family"], "package_family").lower()
    environment = _validate_text(case["storage_environment"], "storage_environment").lower()
    elapsed = _validate_months(case["elapsed_storage_months"], "elapsed_storage_months")
    completed = _validate_count(
        case["completed_relife_cycles"], "completed_relife_cycles"
    )
    moisture_sensitive = _validate_flag(case["moisture_sensitive"], "moisture_sensitive")
    retinning_used = _validate_flag(
        case["retinning_already_used"], "retinning_already_used"
    )
    factor = storage_environment_factor(environment)
    permitted = effective_storage_months(family, environment)
    findings = []
    record = {
        "package_family": family,
        "storage_environment": environment,
        "environment_factor": factor,
        "baseline_months": base_storage_months(family),
        "permitted_months": permitted,
        "elapsed_months": elapsed,
        "completed_relife_cycles": completed,
        "required_tests": [],
        "missing_tests": [],
        "failed_tests": [],
        "granted_extension_months": 0.0,
        "new_permitted_months": permitted,
        "findings": findings,
    }
    if factor == 0.0:
        findings.append(
            "storage environment '%s' credits no storage period; the lot goes for "
            "re-screening rather than relifing" % environment
        )
        record["verdict"] = RELIFE_REFUSED_STORAGE_UNCONTROLLED
        record["relifed"] = False
        return record
    if not storage_period_expired(elapsed, permitted):
        findings.append(
            "elapsed storage of %g month(s) is inside the permitted %g month(s)"
            % (elapsed, permitted)
        )
        record["verdict"] = RELIFE_NOT_REQUIRED
        record["relifed"] = False
        return record
    if completed >= policy["max_relife_cycles"]:
        findings.append(
            "lot has been relifed %d time(s), the ceiling is %d; it goes for "
            "re-screening" % (completed, policy["max_relife_cycles"])
        )
        record["verdict"] = RELIFE_REFUSED_CYCLE_LIMIT
        record["relifed"] = False
        return record
    required = required_relife_tests(family, moisture_sensitive, completed, policy)
    record["required_tests"] = required
    validated = validate_test_results(case["test_results"], required)
    record["missing_tests"] = validated["missing"]
    if not validated["complete"]:
        findings.append(
            "relifing record is missing %s" % ", ".join(validated["missing"])
        )
        record["verdict"] = RELIFE_REFUSED_TESTS_INCOMPLETE
        record["relifed"] = False
        return record
    failures = [name for name in required if validated["results"][name] is False]
    record["failed_tests"] = failures
    if failures:
        solderability_only = failures == [SOLDERABILITY]
        if solderability_only and policy["allow_retinning"] and not retinning_used:
            findings.append(
                "solderability is the only failure and the re-tinning allowance is "
                "unused; re-tin once and retest before disposing of the lot"
            )
            record["verdict"] = RETINNING_PERMITTED
            record["relifed"] = False
            return record
        for name in failures:
            findings.append("relifing test '%s' did not pass" % name)
        record["verdict"] = RELIFE_REFUSED_TEST_FAILURE
        record["relifed"] = False
        return record
    extension = granted_extension_months(family, environment, completed, policy)
    record["granted_extension_months"] = extension
    if not _at_or_below(float(policy["min_extension_months"]), extension):
        findings.append(
            "the cycle would grant %g month(s), under the %g month minimum; the lot "
            "goes for re-screening" % (extension, policy["min_extension_months"])
        )
        record["verdict"] = RELIFE_REFUSED_NO_USEFUL_EXTENSION
        record["relifed"] = False
        return record
    record["new_permitted_months"] = elapsed + extension
    findings.append(
        "relife cycle %d grants %g further month(s) of storage"
        % (completed + 1, extension)
    )
    record["verdict"] = RELIFE_GRANTED
    record["relifed"] = True
    return record
