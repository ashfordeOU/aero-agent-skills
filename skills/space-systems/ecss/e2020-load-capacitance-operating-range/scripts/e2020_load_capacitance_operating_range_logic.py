#!/usr/bin/env python3
"""Load capacitance operating range of a protected power line.

Anchor: ECSS-E-ST-20-20C clause 5.2.19.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A limiter class does not tabulate one load capacitance, it tabulates a
MAXIMUM, and the clause asks for normal operation at every capacitance
value from nothing up to that maximum. Two consequences follow and both
are routinely missed:

    the declared bulk capacitance is not the quantity being compared.
    Initial tolerance, temperature coefficient, ageing and the DC bias
    derating of a ceramic part all move it, and the value that has to
    fit under the tabulated maximum is the worst-case HIGH effective
    capacitance, not the part-number figure

    a class has to be able to start its OWN tabulated maximum. While the
    limiter is limiting, its output is a current source, so the load
    capacitance charges linearly and the charge time is C*V/I. The
    binding case is the slowest charge against the earliest opening:
    the LOWER edge of the limiting current band paired with the SHORTEST
    trip-off delay. A class table that tabulates more capacitance than
    the class can charge in that window is a data error that only shows
    up as a unit which refuses to come on

So the check is a sweep, not a point. Every capacitance from zero to the
tabulated maximum is walked; charge time grows with capacitance, so the
tabulated maximum is the binding sample, and the largest capacitance the
class can actually start is reported alongside it.

The smallest class that covers the worst-case effective capacitance and
can start its own tabulated maximum is the answer. Going up a class
raises the held fault current for no benefit.

Derating contributors, the start-up time margin and the low-usage
advisory floor are declared project policy, not physical constants; the
defaults here are a shape a project substitutes its own values into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CLASS_FIELDS = (
    "name",
    "max_load_capacitance_f",
    "limiting_current_min_a",
    "trip_off_time_min_s",
)
CONTRIBUTOR_FIELDS = ("name", "kind", "minus", "plus")
KINDS = ("relative", "absolute")

VERDICT_COVERED = "load-capacitance-operating-range-covered"
VERDICT_NOT_COVERED = "load-capacitance-operating-range-not-covered"

FINDING_NO_CLASS = "no-class-tabulates-a-capacitance-covering-the-load"
FINDING_ABOVE_TABULATED = "effective-capacitance-above-the-tabulated-class-maximum"
FINDING_RANGE_NOT_STARTABLE = (
    "tabulated-class-capacitance-outruns-the-shortest-trip-off-delay"
)
ADVISORY_LOW_USAGE = "tabulated-class-capacitance-heavily-underused-by-the-load"
ADVISORY_THIN_RANGE = "class-range-headroom-thin-at-the-tabulated-maximum"

# Placeholder class table: the shape a project's own table has to take.
DEFAULT_CLASS_TABLE = (
    {
        "name": "class-1",
        "max_load_capacitance_f": 100.0e-6,
        "limiting_current_min_a": 0.85,
        "trip_off_time_min_s": 8.0e-3,
    },
    {
        "name": "class-2",
        "max_load_capacitance_f": 220.0e-6,
        "limiting_current_min_a": 1.70,
        "trip_off_time_min_s": 8.0e-3,
    },
    {
        "name": "class-3",
        "max_load_capacitance_f": 470.0e-6,
        "limiting_current_min_a": 3.40,
        "trip_off_time_min_s": 10.0e-3,
    },
    {
        "name": "class-4",
        "max_load_capacitance_f": 1000.0e-6,
        "limiting_current_min_a": 6.80,
        "trip_off_time_min_s": 12.0e-3,
    },
)

# Placeholder derating set for a bulk capacitance declaration.
DEFAULT_CAPACITANCE_CONTRIBUTORS = (
    {"name": "initial-tolerance", "kind": "relative", "minus": 0.10, "plus": 0.10},
    {"name": "temperature-coefficient", "kind": "relative", "minus": 0.15, "plus": 0.05},
    {"name": "ageing", "kind": "relative", "minus": 0.05, "plus": 0.0},
    {"name": "dc-bias-derating", "kind": "relative", "minus": 0.20, "plus": 0.0},
)

DEFAULT_RANGE_POLICY = {
    "start_up_time_margin": 1.20,
    "low_usage_advisory_fraction": 0.25,
    "thin_range_advisory_fraction": 0.05,
    "sweep_points": 9,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A charge time and a startable capacitance are both built from a
    product and a division, so a case meant to sit exactly on the bound
    can land a few units in the last place the wrong side of it. The
    bound is never widened; only the comparison tolerates the error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_range_policy(policy):
    """Check the start-up margin, advisory floors and sweep resolution."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_positive(
        "start_up_time_margin", policy.get("start_up_time_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "start_up_time_margin below one relaxes the trip-off delay, got %r"
            % (margin,)
        )
    for key in ("low_usage_advisory_fraction", "thin_range_advisory_fraction"):
        fraction = _require_positive(key, policy.get(key))
        if fraction > 1.0:
            raise ValueError("%s must not exceed one, got %r" % (key, fraction))
    points = policy.get("sweep_points")
    if not isinstance(points, int) or isinstance(points, bool):
        raise ValueError("sweep_points must be an integer, got %r" % (points,))
    if points < 3:
        raise ValueError(
            "sweep_points must be at least three to walk the range, got %d" % points
        )
    return policy


def validate_capacitance_contributor(contributor):
    """Check one derating contributor is a usable two-sided tolerance."""
    if not isinstance(contributor, dict):
        raise ValueError("contributor must be a mapping, got %r" % (contributor,))
    missing = [f for f in CONTRIBUTOR_FIELDS if f not in contributor]
    if missing:
        raise ValueError(
            "contributor is missing fields: %s" % ", ".join(sorted(missing))
        )
    name = contributor["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("contributor name must be a non-empty string, got %r" % (name,))
    kind = _require_choice("kind", contributor["kind"], KINDS)
    minus = _require_non_negative("minus", contributor["minus"])
    plus = _require_non_negative("plus", contributor["plus"])
    if kind == "relative":
        for side, value in (("minus", minus), ("plus", plus)):
            if value >= 1.0:
                raise ValueError(
                    "relative contributor %s has a %s side of %g; a relative "
                    "derating at or beyond unity is not a derating"
                    % (name, side, value)
                )
    if minus == 0.0 and plus == 0.0:
        raise ValueError(
            "contributor %s moves the capacitance on neither side; drop it "
            "rather than stacking a zero" % (name,)
        )
    return {"name": name, "kind": kind, "minus": minus, "plus": plus}


def validate_capacitance_contributors(contributors):
    """Normalise a derating set and require unique names."""
    if isinstance(contributors, dict) or not hasattr(contributors, "__iter__"):
        raise ValueError("contributors must be a sequence of mappings")
    rows = [validate_capacitance_contributor(c) for c in contributors]
    if not rows:
        raise ValueError("derating set is empty; nothing can be stacked")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("derating set repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def effective_capacitance_range(declared_f, contributors):
    """Worst-case low and high effective capacitance of a declared part.

    The value that has to fit under the tabulated class maximum is the
    HIGH end; the low end is reported because it is what the filtering
    argument elsewhere in the design actually gets.
    """
    declared = _require_positive("declared_f", declared_f)
    rows = validate_capacitance_contributors(contributors)
    minus_terms = []
    plus_terms = []
    for row in rows:
        if row["kind"] == "relative":
            minus_terms.append(row["minus"] * declared)
            plus_terms.append(row["plus"] * declared)
        else:
            minus_terms.append(row["minus"])
            plus_terms.append(row["plus"])
    minus_f = math.fsum(minus_terms)
    plus_f = math.fsum(plus_terms)
    low = declared - minus_f
    if low <= 0.0:
        raise ValueError(
            "the downward derating of %g F consumes the declared %g F"
            % (minus_f, declared)
        )
    return {
        "declared_f": declared,
        "minus_f": minus_f,
        "plus_f": plus_f,
        "min_f": low,
        "max_f": declared + plus_f,
    }


def validate_class_row(row):
    """Check one class table entry carries a usable capacitance limit."""
    if not isinstance(row, dict):
        raise ValueError("class row must be a mapping, got %r" % (row,))
    missing = [f for f in CLASS_FIELDS if f not in row]
    if missing:
        raise ValueError("class row is missing fields: %s" % ", ".join(sorted(missing)))
    name = row["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("class name must be a non-empty string, got %r" % (name,))
    return {
        "name": name,
        "max_load_capacitance_f": _require_positive(
            "max_load_capacitance_f", row["max_load_capacitance_f"]
        ),
        "limiting_current_min_a": _require_positive(
            "limiting_current_min_a", row["limiting_current_min_a"]
        ),
        "trip_off_time_min_s": _require_positive(
            "trip_off_time_min_s", row["trip_off_time_min_s"]
        ),
    }


def validate_class_table(table):
    """Normalise a class table and require ascending unique entries."""
    if isinstance(table, dict) or not hasattr(table, "__iter__"):
        raise ValueError("class table must be a sequence of mappings")
    rows = [validate_class_row(r) for r in table]
    if not rows:
        raise ValueError("class table is empty; no class can be taken from it")
    seen = set()
    previous = None
    for row in rows:
        if row["name"] in seen:
            raise ValueError("class table repeats the name %r" % (row["name"],))
        seen.add(row["name"])
        if previous is not None and row["max_load_capacitance_f"] <= previous:
            raise ValueError(
                "class table is not ascending in tabulated capacitance at %r"
                % (row["name"],)
            )
        previous = row["max_load_capacitance_f"]
    return tuple(rows)


def charge_time_s(capacitance_f, bus_voltage_v, limiting_current_a):
    """Time to charge a capacitance from a limiter held at a fixed current."""
    capacitance = _require_non_negative("capacitance_f", capacitance_f)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    current = _require_positive("limiting_current_a", limiting_current_a)
    return capacitance * voltage / current


def startable_capacitance_f(
    bus_voltage_v, limiting_current_a, trip_off_time_min_s, margin
):
    """Largest capacitance that charges inside the shortest trip-off delay."""
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    current = _require_positive("limiting_current_a", limiting_current_a)
    window = _require_positive("trip_off_time_min_s", trip_off_time_min_s)
    factor = _require_positive("margin", margin)
    if factor < 1.0:
        raise ValueError("margin below one relaxes the trip-off delay, got %r" % factor)
    return current * window / (voltage * factor)


def sweep_operating_range(class_row, bus_voltage_v, policy=DEFAULT_RANGE_POLICY):
    """Walk the capacitance range from nothing to the tabulated maximum.

    Charge time rises with capacitance, so the tabulated maximum is the
    binding sample; the sweep is what demonstrates the clause covers the
    whole range rather than one declared value.
    """
    validate_range_policy(policy)
    row = validate_class_row(class_row)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    margin = float(policy["start_up_time_margin"])
    points = int(policy["sweep_points"])
    top = row["max_load_capacitance_f"]
    samples = []
    for index in range(points):
        capacitance = top * index / (points - 1)
        charge = charge_time_s(capacitance, voltage, row["limiting_current_min_a"])
        required = charge * margin
        samples.append(
            {
                "capacitance_f": capacitance,
                "charge_time_s": charge,
                "required_time_s": required,
                "within_trip_off": _at_most(required, row["trip_off_time_min_s"]),
            }
        )
    return tuple(samples)


def assess_class_capacitance_range(
    class_row, bus_voltage_v, policy=DEFAULT_RANGE_POLICY
):
    """Can this class operate normally over its own tabulated range."""
    validate_range_policy(policy)
    row = validate_class_row(class_row)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    margin = float(policy["start_up_time_margin"])
    samples = sweep_operating_range(row, voltage, policy)
    top = row["max_load_capacitance_f"]
    startable = startable_capacitance_f(
        voltage, row["limiting_current_min_a"], row["trip_off_time_min_s"], margin
    )
    charge = charge_time_s(top, voltage, row["limiting_current_min_a"])
    return {
        "name": row["name"],
        "tabulated_max_f": top,
        "limiting_current_min_a": row["limiting_current_min_a"],
        "trip_off_time_min_s": row["trip_off_time_min_s"],
        "startable_max_f": startable,
        "charge_time_at_tabulated_max_s": charge,
        "required_time_at_tabulated_max_s": charge * margin,
        "range_headroom_f": startable - top,
        "covers_own_range": all(s["within_trip_off"] for s in samples),
        "sweep": samples,
    }


def select_capacitance_class(
    table, effective_max_f, bus_voltage_v, policy=DEFAULT_RANGE_POLICY
):
    """Smallest class that tabulates the load and can start its own range.

    Two independent reasons reject a class and both are reported: the
    tabulated maximum does not cover the worst-case effective load
    capacitance, or the class cannot charge its own tabulated maximum
    inside the shortest trip-off delay.
    """
    validate_range_policy(policy)
    rows = validate_class_table(table)
    wanted = _require_positive("effective_max_f", effective_max_f)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    assessments = []
    rejections = []
    selected = None
    for row in rows:
        assessment = assess_class_capacitance_range(row, voltage, policy)
        covers_load = _at_most(wanted, assessment["tabulated_max_f"])
        assessment["covers_load"] = covers_load
        assessment["capacitance_headroom_f"] = assessment["tabulated_max_f"] - wanted
        assessments.append(assessment)
        reasons = []
        if not covers_load:
            reasons.append(
                "%s: %.4g F tabulated against %.4g F effective"
                % (FINDING_ABOVE_TABULATED, assessment["tabulated_max_f"], wanted)
            )
        if not assessment["covers_own_range"]:
            reasons.append(
                "%s: %.4g F tabulated against %.4g F startable"
                % (
                    FINDING_RANGE_NOT_STARTABLE,
                    assessment["tabulated_max_f"],
                    assessment["startable_max_f"],
                )
            )
        if reasons:
            rejections.append({"name": row["name"], "reasons": reasons})
        elif selected is None:
            selected = assessment
    return {
        "effective_max_f": wanted,
        "selected": selected,
        "assessments": tuple(assessments),
        "rejections": tuple(rejections),
    }


def assess_load_capacitance_operating_range(case, policy=DEFAULT_RANGE_POLICY):
    """Full clause 5.2.19.2.1 range check with a compliance verdict."""
    validate_range_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    required = (
        "declared_capacitance_f",
        "contributors",
        "class_table",
        "bus_voltage_v",
    )
    missing = [f for f in required if f not in case]
    if missing:
        raise ValueError("case is missing fields: %s" % ", ".join(sorted(missing)))
    spread = effective_capacitance_range(
        case["declared_capacitance_f"], case["contributors"]
    )
    selection = select_capacitance_class(
        case["class_table"], spread["max_f"], case["bus_voltage_v"], policy
    )

    findings = []
    advisories = []
    chosen = selection["selected"]
    if chosen is None:
        findings.append(
            "%s: %.4g F effective against a largest tabulated %.4g F"
            % (
                FINDING_NO_CLASS,
                spread["max_f"],
                max(a["tabulated_max_f"] for a in selection["assessments"]),
            )
        )
        for rejection in selection["rejections"]:
            for reason in rejection["reasons"]:
                findings.append("%s rejected — %s" % (rejection["name"], reason))
        usage = None
    else:
        usage = spread["max_f"] / chosen["tabulated_max_f"]
        if usage < float(policy["low_usage_advisory_fraction"]):
            advisories.append(
                "%s: the load uses %.1f%% of the tabulated capacitance"
                % (ADVISORY_LOW_USAGE, 100.0 * usage)
            )
        thin = float(policy["thin_range_advisory_fraction"])
        if chosen["range_headroom_f"] < thin * chosen["tabulated_max_f"]:
            advisories.append(
                "%s: %.4g F of headroom on a %.4g F tabulated maximum"
                % (
                    ADVISORY_THIN_RANGE,
                    chosen["range_headroom_f"],
                    chosen["tabulated_max_f"],
                )
            )

    compliant = not findings
    return {
        "verdict": VERDICT_COVERED if compliant else VERDICT_NOT_COVERED,
        "compliant": compliant,
        "effective_capacitance": spread,
        "selection": selection,
        "selected_class": None if chosen is None else chosen["name"],
        "tabulated_usage": usage,
        "findings": findings,
        "advisories": advisories,
    }
