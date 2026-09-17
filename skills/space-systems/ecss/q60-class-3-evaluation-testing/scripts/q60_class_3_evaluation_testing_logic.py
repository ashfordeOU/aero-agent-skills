#!/usr/bin/env python3
"""Test methods, conditions and acceptance limits for a Class 3 evaluation.

Anchor: ECSS-Q-ST-60C clause 6.2.3.4. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A Class 3 evaluation campaign is only worth the three things it declares about
each test it runs:

    method      which test was run, and whether the mandatory ones are all
                there rather than the convenient ones
    condition   what severity it was run at, measured against the mission
                requirement opened out by an over-test factor, because a test
                run exactly at the mission condition demonstrates nothing
                about the margin beyond it
    acceptance  how many parts went in, how many came out failed, and against
                which limits the survivors were measured

The acceptance decision is an attribute one: a sample size that has to be
reached and a number of failures that must not be exceeded. It is kept apart
from the parametric one, where each reading is compared with a declared limit
band, because the two fail for different reasons and take different repairs.

Where the limits came from matters as much as the readings. A limit taken from
a typical column is a central value with a population around it, so a campaign
resting on one has not demonstrated an acceptance limit at all.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MANDATORY_TEST_METHODS = (
    "electrical-characterization",
    "temperature-cycling",
    "operating-life",
    "mechanical-robustness",
)

CONDITION_SENSES = ("at-least", "at-most")

LIMIT_SOURCES = (
    "project-specification",
    "manufacturer-datasheet-limit",
    "manufacturer-datasheet-typical",
)

GUARANTEED_LIMIT_SOURCES = (
    "project-specification",
    "manufacturer-datasheet-limit",
)

DEFAULT_OVER_TEST_FACTOR = 1.10
DEFAULT_ACCEPTANCE_NUMBER = 0

TESTING_PASSED = "class-3-evaluation-testing-passed"
TESTING_INCOMPLETE = "class-3-evaluation-testing-incomplete"
TESTING_FAILED = "class-3-evaluation-testing-failed"

SEVERITY_TOLERANCE = 1e-9
LIMIT_TOLERANCE = 1e-9


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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_whole(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _close(value, other, tolerance):
    return math.isclose(value, other, rel_tol=tolerance, abs_tol=1e-12)


def _at_least(value, bound, tolerance=SEVERITY_TOLERANCE):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or _close(value, bound, tolerance)


def _at_most(value, bound, tolerance=SEVERITY_TOLERANCE):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or _close(value, bound, tolerance)


def normalize_method_name(name):
    """Fold a test method name onto the hyphenated form used throughout."""
    text = _require_text("test method", name)
    return "-".join(text.replace("_", " ").replace("-", " ").lower().split())


def validate_over_test_factor(factor):
    """An over-test factor never pulls a test below the mission condition."""
    value = _require_number("over_test_factor", factor)
    if value < 1.0 and not _close(value, 1.0, SEVERITY_TOLERANCE):
        raise ValueError("over_test_factor must not sit below 1.0, got %r" % factor)
    return value


def validate_condition_sense(sense):
    """Which direction of this condition is the more severe one."""
    name = _require_text("sense", sense)
    if name not in CONDITION_SENSES:
        raise ValueError(
            "sense must be one of %s, got %r" % (", ".join(CONDITION_SENSES), sense)
        )
    return name


def demanded_severity(mission_value, sense, over_test_factor):
    """Severity the test has to reach once the over-test factor is applied.

    Expressed additively against the magnitude of the mission value, so a
    condition whose severe direction is downward — a cold soak, for instance —
    is opened out the same way as one whose severe direction is upward, and a
    mission value either side of zero behaves the same.
    """
    required = _require_number("mission_value", mission_value)
    direction = validate_condition_sense(sense)
    factor = validate_over_test_factor(over_test_factor)
    step = (factor - 1.0) * abs(required)
    if direction == "at-least":
        return required + step
    return required - step


def severity_met(applied, demanded, sense):
    """True when the applied severity reaches what the campaign demands."""
    applied_value = _require_number("applied", applied)
    demanded_value = _require_number("demanded", demanded)
    direction = validate_condition_sense(sense)
    if direction == "at-least":
        return _at_least(applied_value, demanded_value)
    return _at_most(applied_value, demanded_value)


def assess_condition(name, applied, requirement, default_factor=DEFAULT_OVER_TEST_FACTOR):
    """Grade one applied test condition against the mission requirement."""
    condition = _require_text("condition name", name)
    if not isinstance(requirement, dict):
        raise ValueError("requirement for %s must be a mapping" % condition)
    if "mission_value" not in requirement:
        raise ValueError("requirement for %s needs a mission_value" % condition)
    sense = validate_condition_sense(requirement.get("sense", "at-least"))
    factor = validate_over_test_factor(
        requirement.get("over_test_factor", default_factor)
    )
    demanded = demanded_severity(requirement["mission_value"], sense, factor)
    applied_value = _require_number("applied %s" % condition, applied)
    met = severity_met(applied_value, demanded, sense)
    return {
        "condition": condition,
        "applied": applied_value,
        "mission_value": float(requirement["mission_value"]),
        "sense": sense,
        "over_test_factor": factor,
        "demanded": demanded,
        "met": met,
    }


def validate_acceptance_limits(limits):
    """Read a declared limit band and where its numbers came from."""
    if not isinstance(limits, dict):
        raise ValueError("acceptance limits must be a mapping, got %r" % (limits,))
    for key in ("lower", "upper", "source"):
        if key not in limits:
            raise ValueError("acceptance limits are missing %s" % key)
    lower = _require_number("lower limit", limits["lower"])
    upper = _require_number("upper limit", limits["upper"])
    if not upper > lower:
        raise ValueError(
            "the upper limit must sit above the lower one, got %r and %r"
            % (limits["upper"], limits["lower"])
        )
    source = _require_text("limit source", limits["source"])
    if source not in LIMIT_SOURCES:
        raise ValueError(
            "limit source must be one of %s, got %r"
            % (", ".join(LIMIT_SOURCES), source)
        )
    return {
        "lower": lower,
        "upper": upper,
        "source": source,
        "guaranteed": source in GUARANTEED_LIMIT_SOURCES,
    }


def reading_within_limits(value, limits):
    """True when a measured reading sits inside its declared band."""
    band = validate_acceptance_limits(limits)
    reading = _require_number("reading", value)
    return _at_least(reading, band["lower"], LIMIT_TOLERANCE) and _at_most(
        reading, band["upper"], LIMIT_TOLERANCE
    )


def acceptance_decision(
    sample_size, failures, required_sample_size, acceptance_number=DEFAULT_ACCEPTANCE_NUMBER
):
    """Attribute accept-or-reject on a sample size and a failure count."""
    size = _require_whole("sample_size", sample_size, minimum=1)
    failed = _require_whole("failures", failures, minimum=0)
    required = _require_whole("required_sample_size", required_sample_size, minimum=1)
    allowed = _require_whole("acceptance_number", acceptance_number, minimum=0)
    if failed > size:
        raise ValueError(
            "a sample of %d cannot report %d failures" % (size, failed)
        )
    if allowed >= required:
        raise ValueError(
            "an acceptance number of %d against a sample of %d accepts every "
            "outcome" % (allowed, required)
        )
    size_met = size >= required
    within = failed <= allowed
    return {
        "sample_size": size,
        "required_sample_size": required,
        "sample_size_met": size_met,
        "failures": failed,
        "acceptance_number": allowed,
        "within_acceptance_number": within,
        "accepted": size_met and within,
    }


def assess_test_method(method, defaults=None):
    """Grade one declared test method: conditions, readings and acceptance."""
    if not isinstance(method, dict):
        raise ValueError("test method must be a mapping, got %r" % (method,))
    if defaults is None:
        defaults = {}
    if not isinstance(defaults, dict):
        raise ValueError("defaults must be a mapping, got %r" % (defaults,))
    name = normalize_method_name(method.get("name"))
    default_factor = validate_over_test_factor(
        defaults.get("over_test_factor", DEFAULT_OVER_TEST_FACTOR)
    )
    findings = []

    conditions = method.get("conditions", {})
    requirements = method.get("mission_requirements", {})
    if not isinstance(conditions, dict):
        raise ValueError("%s conditions must be a mapping" % name)
    if not isinstance(requirements, dict):
        raise ValueError("%s mission_requirements must be a mapping" % name)
    condition_records = []
    for key in sorted(requirements):
        requirement = requirements[key]
        if not isinstance(requirement, dict) or "mission_value" not in requirement:
            raise ValueError(
                "%s mission requirement %s needs a mission_value" % (name, key)
            )
        _require_number("%s mission_value for %s" % (name, key),
                        requirement["mission_value"])
        if key not in conditions:
            condition_records.append(
                {
                    "condition": key,
                    "applied": None,
                    "mission_value": float(requirement["mission_value"]),
                    "sense": validate_condition_sense(
                        requirement.get("sense", "at-least")
                    ),
                    "over_test_factor": None,
                    "demanded": None,
                    "met": False,
                }
            )
            findings.append(
                "%s demands a %s condition that the campaign never applied"
                % (name, key)
            )
            continue
        record = assess_condition(key, conditions[key], requirement, default_factor)
        condition_records.append(record)
        if not record["met"]:
            findings.append(
                "%s ran %s at %.4g against a demanded %.4g, so the mission "
                "condition is not covered with margin"
                % (name, key, record["applied"], record["demanded"])
            )

    readings = method.get("readings", [])
    if not isinstance(readings, (list, tuple)):
        raise ValueError("%s readings must be a sequence" % name)
    reading_records = []
    seen = set()
    for index, reading in enumerate(readings):
        if not isinstance(reading, dict):
            raise ValueError("%s readings[%d] must be a mapping" % (name, index))
        parameter = _require_text("%s readings[%d] parameter" % (name, index),
                                  reading.get("parameter"))
        if parameter in seen:
            raise ValueError("%s measures %s twice" % (name, parameter))
        seen.add(parameter)
        if "value" not in reading or "limits" not in reading:
            raise ValueError(
                "%s reading %s needs a value and a limits block" % (name, parameter)
            )
        band = validate_acceptance_limits(reading["limits"])
        value = _require_number("%s %s" % (name, parameter), reading["value"])
        inside = reading_within_limits(value, reading["limits"])
        reading_records.append(
            {
                "parameter": parameter,
                "value": value,
                "lower": band["lower"],
                "upper": band["upper"],
                "source": band["source"],
                "limits_guaranteed": band["guaranteed"],
                "within_limits": inside,
            }
        )
        if not inside:
            findings.append(
                "%s measured %s at %.4g outside its band of %.4g to %.4g"
                % (name, parameter, value, band["lower"], band["upper"])
            )
        if not band["guaranteed"]:
            findings.append(
                "%s grades %s against a typical column rather than a guaranteed "
                "limit, so the acceptance limit is not demonstrated"
                % (name, parameter)
            )

    decision = acceptance_decision(
        method.get("sample_size"),
        method.get("failures", 0),
        method.get(
            "required_sample_size", defaults.get("required_sample_size")
        ),
        method.get(
            "acceptance_number",
            defaults.get("acceptance_number", DEFAULT_ACCEPTANCE_NUMBER),
        ),
    )
    if not decision["sample_size_met"]:
        findings.append(
            "%s ran %d parts against %d required, so the attribute decision "
            "rests on too few devices"
            % (name, decision["sample_size"], decision["required_sample_size"])
        )
    if not decision["within_acceptance_number"]:
        findings.append(
            "%s returned %d failures against an acceptance number of %d"
            % (name, decision["failures"], decision["acceptance_number"])
        )

    conditions_met = all(record["met"] for record in condition_records)
    readings_inside = all(record["within_limits"] for record in reading_records)
    limits_guaranteed = all(
        record["limits_guaranteed"] for record in reading_records
    )
    return {
        "name": name,
        "conditions": condition_records,
        "readings": reading_records,
        "acceptance": decision,
        "conditions_met": conditions_met,
        "readings_within_limits": readings_inside,
        "limits_guaranteed": limits_guaranteed,
        "rejected": not decision["within_acceptance_number"] or not readings_inside,
        "passed": (
            conditions_met
            and readings_inside
            and limits_guaranteed
            and decision["accepted"]
        ),
        "findings": findings,
    }


def missing_methods(records):
    """Mandatory methods the campaign never ran, in the published order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    present = set()
    for record in records:
        if not isinstance(record, dict) or "name" not in record:
            raise ValueError("every method record needs a name")
        present.add(record["name"])
    return [name for name in MANDATORY_TEST_METHODS if name not in present]


def assess_evaluation_test_programme(spec):
    """Full clause 6.2.3.4 check over one Class 3 evaluation test campaign."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (spec,))
    manufacturer = _require_text("manufacturer", spec.get("manufacturer"))
    part_number = _require_text("part_number", spec.get("part_number"))
    methods = spec.get("methods")
    if not isinstance(methods, (list, tuple)) or not methods:
        raise ValueError("methods must be a non-empty sequence")
    defaults = spec.get("defaults", {})
    records = []
    seen = set()
    for method in methods:
        record = assess_test_method(method, defaults)
        if record["name"] in seen:
            raise ValueError("test method %s is declared twice" % record["name"])
        seen.add(record["name"])
        records.append(record)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    absent = missing_methods(records)
    for name in absent:
        findings.append(
            "the campaign never ran %s, which the Class 3 evaluation demands"
            % name
        )
    rejected = [record["name"] for record in records if record["rejected"]]
    if rejected:
        verdict = TESTING_FAILED
    elif absent or not all(record["passed"] for record in records):
        verdict = TESTING_INCOMPLETE
    else:
        verdict = TESTING_PASSED
    return {
        "manufacturer": manufacturer,
        "part_number": part_number,
        "methods": records,
        "missing_methods": absent,
        "rejected_methods": rejected,
        "verdict": verdict,
        "evaluated": verdict == TESTING_PASSED,
        "findings": findings,
    }
