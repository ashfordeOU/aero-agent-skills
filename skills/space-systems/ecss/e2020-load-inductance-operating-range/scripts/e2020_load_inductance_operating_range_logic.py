#!/usr/bin/env python3
"""Normal operation is a claim about a range, not about one inductance.

Anchor: ECSS-E-ST-20-20C clause 5.2.19.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A limiter feeding an inductive load has to behave normally for every load
inductance the design allows, from a nearly resistive load up to the
maximum the specification names. Two separate things have to hold, and a
review that checks one and calls it done is the usual failure.

The first is capability at the worst point. The energy the load stores at
the limitation current has to go somewhere when the switch opens, and the
freewheel or clamp path is what absorbs it. The voltage that same
inductance drives across the opening switch has to stay inside what the
switch can stand. Both scale with the inductance, so the declared maximum
is where they are evaluated -- and both are computed from the limitation
current, not from the nominal load current, because the interesting
turn-off is the one that follows an overload.

The second is evidence across the range. A design demonstrated at the
maximum and nowhere else has shown one point. Behaviour in between is not
guaranteed to be monotonic: a resonance between the load inductance and
the output filter sits at one inductance and nowhere near the ends, and a
range demonstrated only at its endpoints steps straight over it. The
spacing of the demonstrated points is therefore part of the assessment.

Underneath both sits a precondition: a maximum has to have been
specified. "Up to the maximum" names no number when nobody wrote one
down, and nothing can be shown across a range that does not exist.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INDUCTANCE_RANGE_NOT_DECLARED = "load-inductance-range-not-declared"
TRANSIENT_BEYOND_CLAMP = "load-inductance-transient-beyond-clamp-capability"
RANGE_COVERAGE_INCOMPLETE = "load-inductance-range-coverage-incomplete"
OPERATION_ACROSS_RANGE_DEMONSTRATED = (
    "load-inductance-operation-across-range-demonstrated"
)

DEFAULT_INDUCTANCE_POLICY = {
    "min_clamp_energy_margin": 1.5,
    "min_clamp_voltage_margin": 1.3,
    "max_coverage_gap_fraction": 0.34,
    "require_endpoint_demonstration": True,
    "thin_margin_advisory": 2.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed one, got %r" % (name, value))
    return value


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, bound):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_inductance_policy(policy):
    """Check the declared operating-range policy can be assessed against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    energy = _require_positive(
        "min_clamp_energy_margin", policy.get("min_clamp_energy_margin")
    )
    if energy < 1.0:
        raise ValueError(
            "min_clamp_energy_margin below one accepts a clamp path that the "
            "stored energy already exceeds, got %r" % (energy,)
        )
    voltage = _require_positive(
        "min_clamp_voltage_margin", policy.get("min_clamp_voltage_margin")
    )
    if voltage < 1.0:
        raise ValueError(
            "min_clamp_voltage_margin below one accepts a transient above what "
            "the switch can stand, got %r" % (voltage,)
        )
    gap = _require_fraction(
        "max_coverage_gap_fraction", policy.get("max_coverage_gap_fraction")
    )
    if gap <= 0.0:
        raise ValueError(
            "max_coverage_gap_fraction of zero demands a continuum of test "
            "points and can never be met"
        )
    _require_flag(
        "require_endpoint_demonstration",
        policy.get("require_endpoint_demonstration"),
    )
    thin = _require_positive("thin_margin_advisory", policy.get("thin_margin_advisory"))
    if thin < max(energy, voltage):
        raise ValueError(
            "thin_margin_advisory %r sits below a required margin, so the "
            "advisory could never fire on a passing case" % (thin,)
        )
    return policy


def validate_limiter_record(limiter):
    """Read the limiter, its limitation current and what its clamp path can take."""
    if not isinstance(limiter, dict):
        raise ValueError("limiter must be a mapping, got %r" % (limiter,))
    identifier = _require_label("limiter id", limiter.get("id"))
    if not identifier:
        raise ValueError("limiter id must not be blank")
    current = _require_positive(
        "limitation_current_a on %s" % identifier, limiter.get("limitation_current_a")
    )
    fall_time = _require_positive(
        "current_fall_s on %s" % identifier, limiter.get("current_fall_s")
    )
    bus_voltage = _require_positive(
        "bus_voltage_v on %s" % identifier, limiter.get("bus_voltage_v")
    )
    clamp_voltage = _require_positive(
        "clamp_voltage_v on %s" % identifier, limiter.get("clamp_voltage_v")
    )
    clamp_energy = _require_positive(
        "clamp_energy_j on %s" % identifier, limiter.get("clamp_energy_j")
    )
    if clamp_voltage <= bus_voltage:
        raise ValueError(
            "clamp_voltage_v on %s does not exceed the bus voltage, which "
            "leaves no headroom for any inductive turn-off at all" % identifier
        )
    return {
        "id": identifier,
        "limitation_current_a": current,
        "current_fall_s": fall_time,
        "bus_voltage_v": bus_voltage,
        "clamp_voltage_v": clamp_voltage,
        "clamp_energy_j": clamp_energy,
    }


def validate_declared_range(declared):
    """Read the specified load-inductance range the limiter must cover."""
    if declared is None:
        return None
    if not isinstance(declared, dict):
        raise ValueError("declared range must be a mapping, got %r" % (declared,))
    lower = _require_non_negative(
        "min_load_inductance_h", declared.get("min_load_inductance_h", 0.0)
    )
    upper = _require_positive(
        "max_load_inductance_h", declared.get("max_load_inductance_h")
    )
    if not upper > lower:
        raise ValueError(
            "max_load_inductance_h %r does not exceed min_load_inductance_h %r, "
            "so the specification names a point rather than a range"
            % (upper, lower)
        )
    return {"min_load_inductance_h": lower, "max_load_inductance_h": upper}


def validate_demonstrated_point(point):
    """Read one inductance value at which behaviour was actually demonstrated."""
    if not isinstance(point, dict):
        raise ValueError("demonstrated point must be a mapping, got %r" % (point,))
    name = _require_label("point name", point.get("name"))
    if not name:
        raise ValueError("point name must not be blank")
    inductance = _require_non_negative(
        "inductance_h on %s" % name, point.get("inductance_h")
    )
    return {"name": name, "inductance_h": inductance}


def demonstrated_points(points):
    """Read every demonstrated point, sorted by inductance."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError(
            "demonstrated points must be a non-empty sequence; a range cannot "
            "be shown covered by an empty test record"
        )
    records = []
    seen = set()
    for point in points:
        record = validate_demonstrated_point(point)
        if record["name"] in seen:
            raise ValueError("duplicate demonstrated point %r" % record["name"])
        seen.add(record["name"])
        records.append(record)
    records.sort(key=lambda item: (item["inductance_h"], item["name"]))
    return tuple(records)


def stored_energy_j(inductance_h, current_a):
    """Energy held by the load inductance at the limitation current."""
    inductance = _require_non_negative("inductance", inductance_h)
    current = _require_positive("current", current_a)
    return 0.5 * inductance * current * current


def turn_off_transient_v(limiter, inductance_h):
    """Voltage the opening switch sees while the inductive current commutes."""
    record = validate_limiter_record(limiter)
    inductance = _require_non_negative("inductance", inductance_h)
    return record["bus_voltage_v"] + inductance * record[
        "limitation_current_a"
    ] / record["current_fall_s"]


def clamp_energy_margin(limiter, inductance_h):
    """How many times the stored energy the clamp path can absorb."""
    record = validate_limiter_record(limiter)
    stored = stored_energy_j(inductance_h, record["limitation_current_a"])
    if stored <= 0.0:
        return float("inf")
    return record["clamp_energy_j"] / stored


def clamp_voltage_margin(limiter, inductance_h):
    """How much of the switch's standoff the turn-off transient leaves unused."""
    record = validate_limiter_record(limiter)
    return record["clamp_voltage_v"] / turn_off_transient_v(record, inductance_h)


def coverage_gaps(declared, points):
    """Gaps in the demonstrated points, as fractions of the declared span.

    The gap below the first point and above the last are included: a range
    demonstrated only near its top has a gap at the bottom, and that gap is
    exactly where a lightly inductive load lives.
    """
    span_record = validate_declared_range(declared)
    if span_record is None:
        raise ValueError("no declared range, so coverage has nothing to measure")
    records = demonstrated_points(points)
    lower = span_record["min_load_inductance_h"]
    upper = span_record["max_load_inductance_h"]
    span = upper - lower
    inside = [
        record
        for record in records
        if _at_least(record["inductance_h"], lower)
        and _at_most(record["inductance_h"], upper)
    ]
    edges = [lower] + [record["inductance_h"] for record in inside] + [upper]
    gaps = []
    for index in range(1, len(edges)):
        width = edges[index] - edges[index - 1]
        if width > 0.0:
            gaps.append(width / span)
    return tuple(gaps)


def widest_coverage_gap(declared, points):
    """The largest fraction of the declared span with no demonstrated point."""
    gaps = coverage_gaps(declared, points)
    if not gaps:
        return 0.0
    return max(gaps)


def endpoint_demonstrated(declared, points):
    """True when the declared maximum itself was demonstrated, not approached."""
    span_record = validate_declared_range(declared)
    if span_record is None:
        raise ValueError("no declared range, so no endpoint to look for")
    upper = span_record["max_load_inductance_h"]
    return any(
        math.isclose(record["inductance_h"], upper, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)
        or record["inductance_h"] > upper
        for record in demonstrated_points(points)
    )


def points_outside_range(declared, points):
    """Demonstrated points above the declared maximum, which are a bonus."""
    span_record = validate_declared_range(declared)
    if span_record is None:
        raise ValueError("no declared range, so nothing sits outside it")
    upper = span_record["max_load_inductance_h"]
    return tuple(
        record["name"]
        for record in demonstrated_points(points)
        if record["inductance_h"] > upper
        and not math.isclose(
            record["inductance_h"], upper, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        )
    )


def inductance_advisories(
    limiter, declared, points, policy=DEFAULT_INDUCTANCE_POLICY
):
    """Things worth saying about a design that already meets the clause."""
    validate_inductance_policy(policy)
    record = validate_limiter_record(limiter)
    span_record = validate_declared_range(declared)
    if span_record is None:
        raise ValueError(
            "no declared range, so there is nothing for an advisory to be "
            "measured against"
        )
    advisories = []
    upper = span_record["max_load_inductance_h"]
    energy_margin = clamp_energy_margin(record, upper)
    voltage_margin = clamp_voltage_margin(record, upper)
    for label, margin in (
        ("clamp energy", energy_margin),
        ("clamp voltage", voltage_margin),
    ):
        if _at_least(margin, policy["thin_margin_advisory"]):
            continue
        advisories.append(
            "%s margin at the declared maximum is %.3f, above the required "
            "floor but close enough that a later increase in the specified "
            "inductance would cross it" % (label, margin)
        )
    inside = [
        item
        for item in demonstrated_points(points)
        if _at_least(item["inductance_h"], span_record["min_load_inductance_h"])
        and _at_most(item["inductance_h"], upper)
    ]
    if len(inside) <= 2:
        advisories.append(
            "the range is demonstrated at %d point(s); behaviour between them "
            "is assumed monotonic, which a resonance with the output filter "
            "does not have to be" % len(inside)
        )
    extra = points_outside_range(span_record, points)
    if extra:
        advisories.append(
            "demonstration at %s sits above the specified maximum; that is "
            "margin evidence rather than range coverage and is worth recording "
            "as such" % ", ".join(extra)
        )
    return tuple(advisories)


def assess_load_inductance_operating_range(case, policy=DEFAULT_INDUCTANCE_POLICY):
    """Full clause 5.2.19.1.1 verdict for one limiter over its inductance range."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_inductance_policy(policy)

    findings = []
    advisories = []
    result = {
        "limiter_id": None,
        "max_load_inductance_h": None,
        "stored_energy_j": None,
        "turn_off_transient_v": None,
        "clamp_energy_margin": None,
        "clamp_voltage_margin": None,
        "widest_coverage_gap": None,
        "endpoint_demonstrated": None,
        "findings": findings,
        "advisories": advisories,
    }

    limiter = validate_limiter_record(case.get("limiter"))
    result["limiter_id"] = limiter["id"]
    declared = validate_declared_range(case.get("declared_range"))

    if declared is None:
        findings.append(
            "limiter %s has no specified maximum load inductance, so there is "
            "no range for normal operation to be shown across" % limiter["id"]
        )
        result["verdict"] = INDUCTANCE_RANGE_NOT_DECLARED
        return result

    upper = declared["max_load_inductance_h"]
    result["max_load_inductance_h"] = upper
    result["stored_energy_j"] = stored_energy_j(
        upper, limiter["limitation_current_a"]
    )
    result["turn_off_transient_v"] = turn_off_transient_v(limiter, upper)
    result["clamp_energy_margin"] = clamp_energy_margin(limiter, upper)
    result["clamp_voltage_margin"] = clamp_voltage_margin(limiter, upper)

    if not _at_least(
        result["clamp_energy_margin"], policy["min_clamp_energy_margin"]
    ):
        findings.append(
            "at the specified maximum the load stores %.6f J against a clamp "
            "capability of %.6f J, a margin of %.3f below the declared %.3f"
            % (
                result["stored_energy_j"],
                limiter["clamp_energy_j"],
                result["clamp_energy_margin"],
                policy["min_clamp_energy_margin"],
            )
        )
    if not _at_least(
        result["clamp_voltage_margin"], policy["min_clamp_voltage_margin"]
    ):
        findings.append(
            "at the specified maximum the turn-off transient reaches %.3f V "
            "against a standoff of %.3f V, a margin of %.3f below the declared "
            "%.3f"
            % (
                result["turn_off_transient_v"],
                limiter["clamp_voltage_v"],
                result["clamp_voltage_margin"],
                policy["min_clamp_voltage_margin"],
            )
        )
    if findings:
        result["verdict"] = TRANSIENT_BEYOND_CLAMP
        return result

    points = demonstrated_points(case.get("demonstrated_points"))
    result["widest_coverage_gap"] = widest_coverage_gap(declared, points)
    result["endpoint_demonstrated"] = endpoint_demonstrated(declared, points)

    if policy["require_endpoint_demonstration"] and not result[
        "endpoint_demonstrated"
    ]:
        findings.append(
            "the specified maximum of %.6f H is approached but never "
            "demonstrated; the clause asks for operation up to it, not near it"
            % upper
        )
    if not _at_most(
        result["widest_coverage_gap"], policy["max_coverage_gap_fraction"]
    ):
        findings.append(
            "the widest untested stretch covers %.3f of the declared range "
            "against an allowance of %.3f; a resonance inside it would not "
            "have been seen"
            % (
                result["widest_coverage_gap"],
                policy["max_coverage_gap_fraction"],
            )
        )
    if findings:
        result["verdict"] = RANGE_COVERAGE_INCOMPLETE
        return result

    advisories.extend(inductance_advisories(limiter, declared, points, policy))
    result["verdict"] = OPERATION_ACROSS_RANGE_DEMONSTRATED
    return result
