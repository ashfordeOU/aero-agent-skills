#!/usr/bin/env python3
"""Quality assurance control of the equipment a test is run with.

Anchor: ECSS-Q-ST-20 clause 5.6.2, the quality assurance duty over test
equipment — that it is calibrated, held under configuration control,
ready, and suitable for the measurement it is about to make, electrical
ground support equipment included. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Five things follow from what the control is for.

Calibration is judged at the day of use, not at the day of the audit. An
instrument in date this morning and out of date on the test day is out
of date, and a due day that contradicts the calibration interval is an
input error rather than a finding.

Being in calibration is not the same as being good enough. The
uncertainty the instrument carries has to be small against the tolerance
the measurement is being judged on, and that ratio is what separates a
usable reading from a reading that cannot decide the pass.

Suitability is a range question as well as an accuracy one. A measurand
sitting at the very end of an instrument's span is measured where the
instrument is least trustworthy, so a guard band is kept at each end.

Electrical ground support equipment is test equipment. It stimulates and
it measures, its build standard changes between campaigns, and an
unapproved change to it is an uncontrolled change to the test.

Ready is a state with a date on it. A passed self-test and a functional
check inside its window are what make the equipment ready now, rather
than ready the last time anybody looked.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

KIND_MEASUREMENT_INSTRUMENT = "measurement-instrument"
KIND_STIMULUS_SOURCE = "stimulus-source"
KIND_ELECTRICAL_GSE = "electrical-ground-support-equipment"
KIND_MECHANICAL_GSE = "mechanical-ground-support-equipment"

RECOGNISED_KINDS = (
    KIND_MEASUREMENT_INSTRUMENT,
    KIND_STIMULUS_SOURCE,
    KIND_ELECTRICAL_GSE,
    KIND_MECHANICAL_GSE,
)

TEST_EQUIPMENT_NOT_IDENTIFIED = "test-equipment-not-identified"
CALIBRATION_NOT_VALID = "test-equipment-calibration-not-valid"
CONFIGURATION_NOT_CONTROLLED = "test-equipment-configuration-not-controlled"
MEASUREMENT_CAPABILITY_INSUFFICIENT = "test-equipment-measurement-capability-insufficient"
RANGE_NOT_SUITABLE = "test-equipment-range-not-suitable"
EQUIPMENT_NOT_READY = "test-equipment-not-ready"
RELEASED_FOR_TEST = "test-equipment-released-for-test"

DEFAULT_TEST_EQUIPMENT_POLICY = {
    "min_accuracy_ratio": 4.0,
    "calibration_margin_days": 5,
    "functional_check_window_days": 14,
    "require_self_test": True,
    "range_guard_band": 0.1,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return count


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_test_equipment_policy(policy):
    """Check the release policy the equipment is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    ratio = _require_positive("min_accuracy_ratio", policy.get("min_accuracy_ratio"))
    if ratio < 1.0:
        raise ValueError(
            "min_accuracy_ratio %g below one would accept an instrument less "
            "accurate than the tolerance it is judging" % ratio
        )
    _require_count("calibration_margin_days", policy.get("calibration_margin_days"))
    _require_positive_count(
        "functional_check_window_days", policy.get("functional_check_window_days")
    )
    _require_flag("require_self_test", policy.get("require_self_test"))
    guard = _require_fraction("range_guard_band", policy.get("range_guard_band"))
    if guard >= 0.5:
        raise ValueError(
            "range_guard_band %g leaves no usable span between the guard bands"
            % guard
        )
    return policy


def validate_equipment(item):
    """Read one item of test equipment and refuse an impossible one."""
    if not isinstance(item, dict):
        raise ValueError("equipment must be a mapping, got %r" % (item,))

    kind = _require_label("kind", item.get("kind", ""))
    if kind not in RECOGNISED_KINDS:
        raise ValueError("unrecognised equipment kind %r; the kinds are fixed" % kind)

    range_min = _require_number("range_min", item.get("range_min"))
    range_max = _require_number("range_max", item.get("range_max"))
    if not range_max > range_min:
        raise ValueError(
            "range_max %g does not sit above range_min %g" % (range_max, range_min)
        )

    measurand_min = _require_number("measurand_min", item.get("measurand_min"))
    measurand_max = _require_number("measurand_max", item.get("measurand_max"))
    if measurand_max < measurand_min:
        raise ValueError(
            "measurand_max %g sits below measurand_min %g"
            % (measurand_max, measurand_min)
        )

    calibrated_on_day = item.get("calibrated_on_day")
    if calibrated_on_day is not None:
        calibrated_on_day = _require_count("calibrated_on_day", calibrated_on_day)

    declared_due_day = item.get("calibration_due_day")
    if declared_due_day is not None:
        declared_due_day = _require_count("calibration_due_day", declared_due_day)

    last_functional_check_day = item.get("last_functional_check_day")
    if last_functional_check_day is not None:
        last_functional_check_day = _require_count(
            "last_functional_check_day", last_functional_check_day
        )

    return {
        "equipment_identifier": _require_label(
            "equipment_identifier", item.get("equipment_identifier", "")
        ),
        "kind": kind,
        "calibrated_on_day": calibrated_on_day,
        "calibration_interval_days": _require_positive_count(
            "calibration_interval_days", item.get("calibration_interval_days")
        ),
        "calibration_due_day": declared_due_day,
        "use_day": _require_count("use_day", item.get("use_day")),
        "measurement_uncertainty": _require_positive(
            "measurement_uncertainty", item.get("measurement_uncertainty")
        ),
        "required_tolerance": _require_positive(
            "required_tolerance", item.get("required_tolerance")
        ),
        "configuration_baseline": _require_label(
            "configuration_baseline", item.get("configuration_baseline", "")
        ),
        "unapproved_configuration_changes": _require_count(
            "unapproved_configuration_changes",
            item.get("unapproved_configuration_changes", 0),
        ),
        "self_test_passed": _require_flag(
            "self_test_passed", item.get("self_test_passed", False)
        ),
        "last_functional_check_day": last_functional_check_day,
        "range_min": range_min,
        "range_max": range_max,
        "measurand_min": measurand_min,
        "measurand_max": measurand_max,
    }


def calibration_due_day(item):
    """The day the calibration runs out, declared or derived."""
    record = validate_equipment(item)
    if record["calibrated_on_day"] is None:
        return None
    derived = record["calibrated_on_day"] + record["calibration_interval_days"]
    declared = record["calibration_due_day"]
    if declared is None:
        return derived
    if declared != derived:
        raise ValueError(
            "the declared due day %d contradicts the calibration day %d plus "
            "the %d day interval"
            % (declared, record["calibrated_on_day"], record["calibration_interval_days"])
        )
    return declared


def calibration_margin_days(item):
    """Days between the day of use and the day the calibration runs out."""
    record = validate_equipment(item)
    due = calibration_due_day(record)
    if due is None:
        raise ValueError(
            "%s carries no calibration record, so it has no margin"
            % (record["equipment_identifier"] or "the equipment")
        )
    return due - record["use_day"]


def calibration_is_valid(item):
    """True when the equipment is in calibration on the day it is used."""
    record = validate_equipment(item)
    if calibration_due_day(record) is None:
        return False
    return calibration_margin_days(record) >= 0


def accuracy_ratio(item):
    """Tolerance being judged over the uncertainty the equipment carries."""
    record = validate_equipment(item)
    return record["required_tolerance"] / record["measurement_uncertainty"]


def capability_is_sufficient(item, policy=None):
    """True when the accuracy ratio reaches what the policy demands."""
    policy = validate_test_equipment_policy(policy or DEFAULT_TEST_EQUIPMENT_POLICY)
    return _at_least(accuracy_ratio(item), float(policy["min_accuracy_ratio"]))


def range_span(item):
    """The span the equipment covers."""
    record = validate_equipment(item)
    return record["range_max"] - record["range_min"]


def measurand_span(item):
    """The span the measurement has to cover."""
    record = validate_equipment(item)
    return record["measurand_max"] - record["measurand_min"]


def guard_band(item, policy=None):
    """The margin kept clear at each end of the equipment's span."""
    policy = validate_test_equipment_policy(policy or DEFAULT_TEST_EQUIPMENT_POLICY)
    return float(policy["range_guard_band"]) * range_span(item)


def range_is_suitable(item, policy=None):
    """True when the measurand sits inside the span, guard bands aside."""
    policy = validate_test_equipment_policy(policy or DEFAULT_TEST_EQUIPMENT_POLICY)
    record = validate_equipment(item)
    band = guard_band(record, policy)
    lower = record["range_min"] + band
    upper = record["range_max"] - band
    return _at_least(record["measurand_min"], lower) and _at_most(
        record["measurand_max"], upper
    )


def configuration_is_controlled(item):
    """True when the build standard is named and nothing is unapproved."""
    record = validate_equipment(item)
    if not record["configuration_baseline"]:
        return False
    return record["unapproved_configuration_changes"] == 0


def readiness_gaps(item, policy=None):
    """Reasons the equipment is not ready on the day it is to be used."""
    policy = validate_test_equipment_policy(policy or DEFAULT_TEST_EQUIPMENT_POLICY)
    record = validate_equipment(item)
    gaps = []
    if policy["require_self_test"] and not record["self_test_passed"]:
        gaps.append("the self-test has not been passed")
    check_day = record["last_functional_check_day"]
    window = int(policy["functional_check_window_days"])
    if check_day is None:
        gaps.append("no functional check has been recorded")
    elif check_day > record["use_day"]:
        raise ValueError(
            "the functional check day %d sits after the day of use %d"
            % (check_day, record["use_day"])
        )
    elif record["use_day"] - check_day > window:
        gaps.append(
            "the functional check is %d days old against a %d day window"
            % (record["use_day"] - check_day, window)
        )
    return tuple(gaps)


def assess_test_equipment(case):
    """Decide whether one item of test equipment may be released for a test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_test_equipment_policy(
        case.get("policy") or DEFAULT_TEST_EQUIPMENT_POLICY
    )

    findings = []
    advisories = []
    result = {
        "equipment_identifier": None,
        "kind": None,
        "calibration_due_day": None,
        "calibration_margin_days": None,
        "accuracy_ratio": None,
        "range_suitable": None,
        "configuration_controlled": None,
        "readiness_gaps": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    item = case.get("equipment")
    if item is None:
        findings.append(
            "no test equipment has been identified for the measurement, so "
            "nothing can be released for it"
        )
        result["verdict"] = TEST_EQUIPMENT_NOT_IDENTIFIED
        return result

    record = validate_equipment(item)
    result["equipment_identifier"] = record["equipment_identifier"]
    result["kind"] = record["kind"]
    if not record["equipment_identifier"]:
        findings.append(
            "the equipment carries no identifier, so no calibration or "
            "configuration record could be tied to it"
        )
        result["verdict"] = TEST_EQUIPMENT_NOT_IDENTIFIED
        return result

    due = calibration_due_day(record)
    result["calibration_due_day"] = due
    if due is None:
        findings.append(
            "%s carries no calibration record at all" % record["equipment_identifier"]
        )
        result["verdict"] = CALIBRATION_NOT_VALID
        return result

    margin = calibration_margin_days(record)
    result["calibration_margin_days"] = margin
    if margin < 0:
        findings.append(
            "%s is out of calibration by %d day(s) on the day it is to be used"
            % (record["equipment_identifier"], -margin)
        )
        result["verdict"] = CALIBRATION_NOT_VALID
        return result
    if margin <= int(policy["calibration_margin_days"]):
        advisories.append(
            "%s falls due for calibration in %d day(s), so a slipped test date "
            "takes it out of calibration"
            % (record["equipment_identifier"], margin)
        )

    controlled = configuration_is_controlled(record)
    result["configuration_controlled"] = controlled
    if not controlled:
        if not record["configuration_baseline"]:
            findings.append(
                "%s names no configuration baseline, so the build standard "
                "under test is not recorded" % record["equipment_identifier"]
            )
        else:
            findings.append(
                "%s carries %d unapproved configuration change(s), so the test "
                "would be run on an uncontrolled build"
                % (
                    record["equipment_identifier"],
                    record["unapproved_configuration_changes"],
                )
            )
        result["verdict"] = CONFIGURATION_NOT_CONTROLLED
        return result

    ratio = accuracy_ratio(record)
    result["accuracy_ratio"] = ratio
    if not capability_is_sufficient(record, policy):
        findings.append(
            "the accuracy ratio is %.3g against the %.3g demanded, so the "
            "reading cannot decide the tolerance it is judging"
            % (ratio, float(policy["min_accuracy_ratio"]))
        )
        result["verdict"] = MEASUREMENT_CAPABILITY_INSUFFICIENT
        return result

    suitable = range_is_suitable(record, policy)
    result["range_suitable"] = suitable
    if not suitable:
        findings.append(
            "the measurand spans %g to %g, which does not sit inside the %g to "
            "%g span of %s once the guard bands are kept clear"
            % (
                record["measurand_min"],
                record["measurand_max"],
                record["range_min"],
                record["range_max"],
                record["equipment_identifier"],
            )
        )
        result["verdict"] = RANGE_NOT_SUITABLE
        return result

    gaps = readiness_gaps(record, policy)
    result["readiness_gaps"] = gaps
    if gaps:
        for gap in gaps:
            findings.append(
                "%s is not ready: %s" % (record["equipment_identifier"], gap)
            )
        result["verdict"] = EQUIPMENT_NOT_READY
        return result

    result["verdict"] = RELEASED_FOR_TEST
    return result


def unreleased_equipment(items, policy=None):
    """Across a test set-up, the items that cannot be released and why."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a sequence of equipment records")
    held = []
    seen = set()
    for item in items:
        record = validate_equipment(item)
        identifier = record["equipment_identifier"]
        if identifier:
            if identifier in seen:
                raise ValueError("equipment %r appears twice in the set-up" % identifier)
            seen.add(identifier)
        outcome = assess_test_equipment({"policy": policy, "equipment": record})
        if outcome["verdict"] != RELEASED_FOR_TEST:
            held.append((identifier, outcome["verdict"]))
    return tuple(held)
