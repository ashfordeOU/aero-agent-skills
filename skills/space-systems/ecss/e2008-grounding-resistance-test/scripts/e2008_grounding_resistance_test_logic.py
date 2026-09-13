#!/usr/bin/env python3
"""Grounding resistance test of a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Every grounding point declared for the assembly is measured back to the
one structural reference the grounding plan names, and the number is
graded against the window that point is allowed to sit in. Two families
of point live in the same plan and they fail in opposite directions:

    bonding point        a structural or electrical bond, milliohm
                         class, which fails by being too resistive
    dissipative point    a path that bleeds surface charge, which has a
                         floor as well as a ceiling and fails by being
                         too conductive as well as by being open

So a grounding point carries a window, not a single limit, and the
verdict says which edge was crossed.

Milliohm measurements are fragile in ways the number does not show, so
three things are graded alongside the value itself: the reading has to
be taken to the declared reference rather than to a convenient neighbour
point, the test current has to be large enough to break through the
oxide and contamination films that sit on a bolted joint, and repeated
readings on the same point have to agree -- a spread between repeats is
a contact moving under the probe, and the mean of an unstable contact is
not a measurement of anything.

The limits and the repeatability numbers below are declared project
policy, not physical constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROBE_TECHNIQUES = ("two-wire", "four-wire")

POINT_CATEGORIES = ("bonding-point", "dissipative-point")

# Default windows per grounding point category, in ohm.
DEFAULT_POINT_WINDOWS_OHM = {
    "bonding-point": (0.0, 0.010),
    "dissipative-point": (1.0e5, 1.0e9),
}

BOND_WITHIN_WINDOW = "within-window"
BOND_ABOVE_WINDOW = "above-window"
BOND_BELOW_WINDOW = "below-window"
BOND_OPEN = "open-bond"
BOND_NOT_MEASURED = "not-measured"
BOND_NOT_EVALUATED = "not-evaluated"

GROUNDING_VERIFIED = "grounding-verified"
GROUNDING_NOT_VERIFIED = "grounding-not-verified"
GROUNDING_NOT_EVALUATED = "grounding-not-evaluated"

DEFAULT_GROUNDING_POLICY = {
    "min_test_current_a": 0.1,
    "min_repeat_readings": 2,
    "max_relative_spread": 0.10,
    "four_wire_required_below_ohm": 1.0,
    "open_above_ohm": 1.0e12,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A compensated bond resistance is a difference and a mean is a
    quotient, so a point sitting exactly on a window edge can land a few
    units in the last place outside it. The window is never widened;
    only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_grounding_policy(policy):
    """Check the measurement policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    _require_positive("min_test_current_a", policy.get("min_test_current_a"))
    repeats = policy.get("min_repeat_readings")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("min_repeat_readings must be an integer of at least 1")
    spread = _require_non_negative("max_relative_spread", policy.get("max_relative_spread"))
    if spread > 1.0:
        raise ValueError("max_relative_spread must not exceed 1.0")
    _require_positive(
        "four_wire_required_below_ohm", policy.get("four_wire_required_below_ohm")
    )
    _require_positive("open_above_ohm", policy.get("open_above_ohm"))
    return policy


def point_window_ohm(point):
    """Resolve the resistance window a grounding point has to sit in."""
    _require_mapping("point", point)
    category = _require_choice("category", point.get("category"), POINT_CATEGORIES)
    default_low, default_high = DEFAULT_POINT_WINDOWS_OHM[category]
    low = point.get("min_resistance_ohm", default_low)
    high = point.get("max_resistance_ohm", default_high)
    low = _require_non_negative("min_resistance_ohm", low)
    high = _require_positive("max_resistance_ohm", high)
    if low > high:
        raise ValueError(
            "grounding point window is inverted: %r above %r" % (low, high)
        )
    return (low, high)


def validate_grounding_plan(plan):
    """Check the grounding point list and the reference it is measured to."""
    _require_mapping("plan", plan)
    _require_identifier("structural_reference", plan.get("structural_reference"))
    points = plan.get("points")
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("plan must carry a non-empty points sequence")
    seen = set()
    for point in points:
        _require_mapping("point", point)
        identifier = _require_identifier("point id", point.get("id"))
        if identifier in seen:
            raise ValueError("grounding point %r is declared twice" % identifier)
        seen.add(identifier)
        if identifier == plan["structural_reference"]:
            raise ValueError(
                "grounding point %r is the structural reference itself" % identifier
            )
        point_window_ohm(point)
    return plan


def reading_statistics(readings):
    """Reduce the repeat readings on one point to a value and a spread."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence, got %r" % (readings,))
    values = [_require_non_negative("reading", value) for value in readings]
    count = len(values)
    mean = sum(values) / count
    lowest = min(values)
    highest = max(values)
    spread = highest - lowest
    relative = spread / mean if mean > 0.0 else 0.0
    return {
        "count": count,
        "mean_ohm": mean,
        "min_ohm": lowest,
        "max_ohm": highest,
        "spread_ohm": spread,
        "relative_spread": relative,
    }


def compensated_bond_ohm(measurement, window_high_ohm, policy=DEFAULT_GROUNDING_POLICY):
    """Strip the fixture contribution from the mean reading, or refuse to."""
    _require_mapping("measurement", measurement)
    validate_grounding_policy(policy)
    ceiling = _require_positive("window_high_ohm", window_high_ohm)
    stats = reading_statistics(measurement.get("readings"))
    technique = _require_choice(
        "probe_technique", measurement.get("probe_technique"), PROBE_TECHNIQUES
    )
    if technique == "four-wire":
        return stats["mean_ohm"]
    fixture = measurement.get("fixture_resistance_ohm")
    if fixture is None:
        if ceiling < float(policy["four_wire_required_below_ohm"]):
            raise ValueError(
                "a two-wire reading against a %.5f ohm ceiling needs a declared "
                "fixture_resistance_ohm; the fixture is the same size as the "
                "window" % ceiling
            )
        return stats["mean_ohm"]
    fixture_value = _require_non_negative("fixture_resistance_ohm", fixture)
    if fixture_value > stats["mean_ohm"]:
        raise ValueError(
            "declared fixture resistance %.6f ohm exceeds the mean reading "
            "%.6f ohm" % (fixture_value, stats["mean_ohm"])
        )
    return stats["mean_ohm"] - fixture_value


def measurement_quality_findings(measurement, window, policy=DEFAULT_GROUNDING_POLICY):
    """Findings raised by how a grounding reading was taken, not by its value."""
    _require_mapping("measurement", measurement)
    validate_grounding_policy(policy)
    ceiling = _require_positive("window ceiling", window[1])
    findings = []
    stats = reading_statistics(measurement.get("readings"))
    if stats["count"] < int(policy["min_repeat_readings"]):
        findings.append(
            "only %d reading(s) on this point against a required %d; a single "
            "reading cannot show the contact was stable"
            % (stats["count"], int(policy["min_repeat_readings"]))
        )
    elif not _at_most(stats["relative_spread"], float(policy["max_relative_spread"])):
        findings.append(
            "repeat readings spread %.1f%% of the mean against an allowed %.1f%%; "
            "the contact moved under the probe"
            % (100.0 * stats["relative_spread"], 100.0 * float(policy["max_relative_spread"]))
        )
    current = _require_positive("test_current_a", measurement.get("test_current_a"))
    if not _at_least(current, float(policy["min_test_current_a"])):
        findings.append(
            "test current %.4f A is below the %.4f A needed to break through "
            "the film on a bolted joint"
            % (current, float(policy["min_test_current_a"]))
        )
    technique = _require_choice(
        "probe_technique", measurement.get("probe_technique"), PROBE_TECHNIQUES
    )
    if (
        technique == "two-wire"
        and ceiling < float(policy["four_wire_required_below_ohm"])
        and measurement.get("fixture_resistance_ohm") is None
    ):
        findings.append(
            "a %.5f ohm ceiling needs a four-wire probe or a declared fixture "
            "resistance; a two-wire reading cannot resolve it" % ceiling
        )
    return findings


def evaluate_grounding_point(
    point, measurement, structural_reference, policy=DEFAULT_GROUNDING_POLICY
):
    """Grade one grounding point against the readings taken on it."""
    _require_mapping("point", point)
    validate_grounding_policy(policy)
    identifier = _require_identifier("point id", point.get("id"))
    reference = _require_identifier("structural_reference", structural_reference)
    window = point_window_ohm(point)

    record = {
        "id": identifier,
        "category": point["category"],
        "window_ohm": window,
        "mean_reading_ohm": None,
        "bond_resistance_ohm": None,
        "relative_spread": None,
        "verdict": BOND_NOT_MEASURED,
        "within_window": None,
        "findings": [],
    }

    if measurement is None:
        record["findings"].append(
            "grounding point %s is on the plan but was never measured" % identifier
        )
        return record

    _require_mapping("measurement", measurement)
    measured_to = _require_identifier("measured_to", measurement.get("measured_to"))
    if measured_to != reference:
        record["verdict"] = BOND_NOT_EVALUATED
        record["findings"].append(
            "point %s was measured to %s, not to the declared reference %s; the "
            "reading does not grade the path to structure"
            % (identifier, measured_to, reference)
        )
        return record

    readings = measurement.get("readings")
    if readings is None:
        record["verdict"] = BOND_OPEN
        record["within_window"] = False
        record["findings"].append(
            "instrument reported no reading at grounding point %s" % identifier
        )
        return record

    findings = measurement_quality_findings(measurement, window, policy)
    stats = reading_statistics(readings)
    record["mean_reading_ohm"] = stats["mean_ohm"]
    record["relative_spread"] = stats["relative_spread"]

    if (
        measurement.get("probe_technique") == "two-wire"
        and window[1] < float(policy["four_wire_required_below_ohm"])
        and measurement.get("fixture_resistance_ohm") is None
    ):
        record["verdict"] = BOND_NOT_EVALUATED
        record["findings"] = findings
        return record

    bond = compensated_bond_ohm(measurement, window[1], policy)
    record["bond_resistance_ohm"] = bond

    if not _at_most(bond, float(policy["open_above_ohm"])):
        record["verdict"] = BOND_OPEN
        record["within_window"] = False
        findings.append(
            "point %s reads %.4g ohm, above the declared open threshold %.4g ohm"
            % (identifier, bond, float(policy["open_above_ohm"]))
        )
    elif not _at_least(bond, window[0]):
        record["verdict"] = BOND_BELOW_WINDOW
        record["within_window"] = False
        findings.append(
            "point %s reads %.4g ohm, below its %.4g ohm floor; the path is more "
            "conductive than the grounding plan allows" % (identifier, bond, window[0])
        )
    elif not _at_most(bond, window[1]):
        record["verdict"] = BOND_ABOVE_WINDOW
        record["within_window"] = False
        findings.append(
            "point %s reads %.6g ohm against a %.6g ohm ceiling"
            % (identifier, bond, window[1])
        )
    else:
        record["verdict"] = BOND_WITHIN_WINDOW
        record["within_window"] = True

    record["findings"] = findings
    return record


def grounding_point_coverage(plan, measurements):
    """Match the readings taken against the points the plan declares."""
    validate_grounding_plan(plan)
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("measurements must be a sequence, got %r" % (measurements,))
    declared = [point["id"] for point in plan["points"]]
    seen = {}
    duplicates = []
    unknown = []
    for measurement in measurements:
        _require_mapping("measurement", measurement)
        identifier = _require_identifier("measurement point_id", measurement.get("point_id"))
        if identifier not in declared:
            unknown.append(identifier)
            continue
        if identifier in seen:
            duplicates.append(identifier)
            continue
        seen[identifier] = measurement
    unmeasured = [identifier for identifier in declared if identifier not in seen]
    return {
        "declared_count": len(declared),
        "measured": seen,
        "measured_count": len(seen),
        "unmeasured_ids": unmeasured,
        "duplicate_ids": duplicates,
        "unknown_ids": unknown,
        "complete": not unmeasured and not duplicates and not unknown,
    }


def evaluate_grounding_campaign(campaign, policy=DEFAULT_GROUNDING_POLICY):
    """Full clause 5.5.3.3.4 grounding resistance assessment with a verdict."""
    validate_grounding_policy(policy)
    _require_mapping("campaign", campaign)
    plan = validate_grounding_plan(campaign.get("plan"))
    measurements = campaign.get("measurements")
    if not isinstance(measurements, (list, tuple)):
        raise ValueError("campaign must carry a measurements sequence")

    coverage = grounding_point_coverage(plan, measurements)
    findings = []
    if coverage["duplicate_ids"]:
        findings.append(
            "grounding point(s) measured more than once with no stated reason: %s"
            % ", ".join(sorted(set(coverage["duplicate_ids"])))
        )
    if coverage["unknown_ids"]:
        findings.append(
            "reading(s) taken at point(s) the grounding plan does not list: %s"
            % ", ".join(sorted(set(coverage["unknown_ids"])))
        )

    points = []
    for point in plan["points"]:
        record = evaluate_grounding_point(
            point,
            coverage["measured"].get(point["id"]),
            plan["structural_reference"],
            policy,
        )
        points.append(record)
        findings.extend(record["findings"])

    grouped = {}
    for record in points:
        grouped.setdefault(record["verdict"], []).append(record["id"])

    failing = (
        grouped.get(BOND_ABOVE_WINDOW, [])
        + grouped.get(BOND_BELOW_WINDOW, [])
        + grouped.get(BOND_OPEN, [])
    )
    inconclusive = grouped.get(BOND_NOT_MEASURED, []) + grouped.get(
        BOND_NOT_EVALUATED, []
    )

    if failing:
        verdict = GROUNDING_NOT_VERIFIED
        compliant = False
    elif inconclusive or coverage["duplicate_ids"] or coverage["unknown_ids"]:
        verdict = GROUNDING_NOT_EVALUATED
        compliant = None
    else:
        verdict = GROUNDING_VERIFIED
        compliant = True

    return {
        "structural_reference": plan["structural_reference"],
        "points": points,
        "grouped_by_verdict": grouped,
        "coverage": {
            "declared_count": coverage["declared_count"],
            "measured_count": coverage["measured_count"],
            "unmeasured_ids": coverage["unmeasured_ids"],
            "duplicate_ids": coverage["duplicate_ids"],
            "unknown_ids": coverage["unknown_ids"],
            "complete": coverage["complete"],
        },
        "failing_ids": failing,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
