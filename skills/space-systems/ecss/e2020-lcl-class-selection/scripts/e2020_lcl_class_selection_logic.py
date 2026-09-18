#!/usr/bin/env python3
"""Latching current limiter class selection for a protected load.

Anchor: ECSS-E-ST-20-20C clause 5.2.1.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A latching current limiter (LCL) sits between a regulated power bus and
one load. It carries the load current, holds the current to a limiting
band when the load draws too much, and after a trip-off delay it opens
and stays open until it is commanded on again. The standard fixes a
discrete set of LCL classes, and each class comes with the performance
figures the selection has to be shown against:

    max_continuous_current_a   the highest steady load current the class
                               carries without ever entering limitation
    limit_min_a / limit_max_a  the band the output current is held to
                               once the class is in limitation
    trip_off_time_min_s        the shortest delay before the class opens
    trip_off_time_max_s        the longest delay before the class opens

Selecting a class is therefore three questions at once, not one:

    1. Does the class carry the steady load, after derating?
    2. Can the load still START on this class? Energising a load
       capacitance is a limitation event by construction: the limiter
       holds its output to the band while the capacitance charges, and
       the charge has to finish before the trip-off timer expires.
       The binding case is the SLOWEST charge (lower limiting current)
       against the SHORTEST trip-off delay.
    3. Does the class still protect the hardware downstream? The upper
       limiting current is what the harness and the load see during a
       fault, so it has to sit under the harness rating.

The derating factor, the start-up time margin and the low-utilisation
advisory threshold below are a declared project policy, not physical
constants; a project substitutes its own. The class table likewise is a
placeholder shape for the project's own procurement table.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CLASS_FIELDS = (
    "name",
    "max_continuous_current_a",
    "limit_min_a",
    "limit_max_a",
    "trip_off_time_min_s",
    "trip_off_time_max_s",
)

LOAD_FIELDS = (
    "steady_state_current_a",
    "load_capacitance_f",
    "bus_voltage_v",
    "harness_rating_a",
)

VERDICT_SELECTED = "class-selected"
VERDICT_NO_CLASS = "no-class-meets-the-performance-figures"

FINDING_CAPABILITY = "continuous-capability-short"
FINDING_STARTUP = "start-up-charge-exceeds-trip-off"
FINDING_HARNESS = "upper-limit-above-harness-rating"
FINDING_OVERSIZED = "utilisation-below-advisory-floor"

# Placeholder class table: the shape a project's own table has to take.
DEFAULT_CLASS_TABLE = (
    {
        "name": "lcl-a",
        "max_continuous_current_a": 0.5,
        "limit_min_a": 0.60,
        "limit_max_a": 0.85,
        "trip_off_time_min_s": 6.0e-3,
        "trip_off_time_max_s": 12.0e-3,
    },
    {
        "name": "lcl-b",
        "max_continuous_current_a": 1.0,
        "limit_min_a": 1.20,
        "limit_max_a": 1.70,
        "trip_off_time_min_s": 6.0e-3,
        "trip_off_time_max_s": 12.0e-3,
    },
    {
        "name": "lcl-c",
        "max_continuous_current_a": 2.0,
        "limit_min_a": 2.40,
        "limit_max_a": 3.40,
        "trip_off_time_min_s": 8.0e-3,
        "trip_off_time_max_s": 16.0e-3,
    },
    {
        "name": "lcl-d",
        "max_continuous_current_a": 4.0,
        "limit_min_a": 4.80,
        "limit_max_a": 6.80,
        "trip_off_time_min_s": 10.0e-3,
        "trip_off_time_max_s": 20.0e-3,
    },
    {
        "name": "lcl-e",
        "max_continuous_current_a": 8.0,
        "limit_min_a": 9.60,
        "limit_max_a": 13.60,
        "trip_off_time_min_s": 12.0e-3,
        "trip_off_time_max_s": 24.0e-3,
    },
)

DEFAULT_SELECTION_POLICY = {
    "derating_factor": 0.80,
    "startup_time_margin": 1.25,
    "utilisation_advisory_floor": 0.25,
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A charge time and a trip-off delay are built by division and
    multiplication, so a case meant to sit exactly on the limit can land
    a few units in the last place above it. The limit is never widened;
    only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_selection_policy(policy):
    """Check the derating, start-up margin and advisory floor are sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    derating = _require_positive("derating_factor", policy.get("derating_factor"))
    if derating > 1.0:
        raise ValueError(
            "derating_factor must not exceed one, got %r" % (derating,)
        )
    margin = _require_positive("startup_time_margin", policy.get("startup_time_margin"))
    if margin < 1.0:
        raise ValueError(
            "startup_time_margin must be at least one, got %r" % (margin,)
        )
    floor = _require_non_negative(
        "utilisation_advisory_floor", policy.get("utilisation_advisory_floor")
    )
    if floor >= 1.0:
        raise ValueError(
            "utilisation_advisory_floor must be below one, got %r" % (floor,)
        )
    return policy


def validate_class_entry(entry):
    """Check one class row carries a consistent set of performance figures."""
    if not isinstance(entry, dict):
        raise ValueError("class entry must be a mapping, got %r" % (entry,))
    missing = [f for f in CLASS_FIELDS if f not in entry]
    if missing:
        raise ValueError(
            "class entry is missing figures: %s" % ", ".join(sorted(missing))
        )
    name = entry["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("class name must be a non-empty string, got %r" % (name,))
    carried = _require_positive(
        "max_continuous_current_a", entry["max_continuous_current_a"]
    )
    low = _require_positive("limit_min_a", entry["limit_min_a"])
    high = _require_positive("limit_max_a", entry["limit_max_a"])
    trip_low = _require_positive("trip_off_time_min_s", entry["trip_off_time_min_s"])
    trip_high = _require_positive("trip_off_time_max_s", entry["trip_off_time_max_s"])
    if high < low:
        raise ValueError(
            "class %s has an inverted limiting band (%g A .. %g A)" % (name, low, high)
        )
    if trip_high < trip_low:
        raise ValueError(
            "class %s has an inverted trip-off window (%g s .. %g s)"
            % (name, trip_low, trip_high)
        )
    if low <= carried:
        raise ValueError(
            "class %s would enter limitation at its own continuous rating "
            "(lower limit %g A, continuous %g A)" % (name, low, carried)
        )
    return {
        "name": name,
        "max_continuous_current_a": carried,
        "limit_min_a": low,
        "limit_max_a": high,
        "trip_off_time_min_s": trip_low,
        "trip_off_time_max_s": trip_high,
    }


def validate_class_table(table):
    """Normalise a class table and require unique, ascending class rows."""
    if isinstance(table, dict) or not hasattr(table, "__iter__"):
        raise ValueError("class table must be a sequence of entries")
    rows = [validate_class_entry(e) for e in table]
    if not rows:
        raise ValueError("class table is empty; nothing can be selected from it")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("class table repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    for earlier, later in zip(rows, rows[1:]):
        if later["max_continuous_current_a"] <= earlier["max_continuous_current_a"]:
            raise ValueError(
                "class table is not ascending in continuous rating: %s then %s"
                % (earlier["name"], later["name"])
            )
    return tuple(rows)


def validate_load(load):
    """Check the protected load carries every figure the selection needs."""
    if not isinstance(load, dict):
        raise ValueError("load must be a mapping, got %r" % (load,))
    missing = [f for f in LOAD_FIELDS if f not in load]
    if missing:
        raise ValueError("load is missing figures: %s" % ", ".join(sorted(missing)))
    return {
        "steady_state_current_a": _require_positive(
            "steady_state_current_a", load["steady_state_current_a"]
        ),
        "load_capacitance_f": _require_positive(
            "load_capacitance_f", load["load_capacitance_f"]
        ),
        "bus_voltage_v": _require_positive("bus_voltage_v", load["bus_voltage_v"]),
        "harness_rating_a": _require_positive(
            "harness_rating_a", load["harness_rating_a"]
        ),
    }


def derated_capability_a(entry, derating_factor):
    """Steady current the class may be used at under the project derating."""
    row = validate_class_entry(entry)
    factor = _require_positive("derating_factor", derating_factor)
    if factor > 1.0:
        raise ValueError("derating_factor must not exceed one, got %r" % (factor,))
    return row["max_continuous_current_a"] * factor


def inrush_charge_time_s(capacitance_f, bus_voltage_v, charge_current_a):
    """Time to charge the load capacitance at a held limiting current.

    While the limiter is in limitation the output is a current source, so
    the capacitance charges linearly: t = C * V / I.
    """
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    current = _require_positive("charge_current_a", charge_current_a)
    return capacitance * voltage / current


def utilisation_ratio(entry, steady_state_current_a, derating_factor):
    """Share of the derated capability the steady load actually uses."""
    capability = derated_capability_a(entry, derating_factor)
    steady = _require_positive("steady_state_current_a", steady_state_current_a)
    return steady / capability


def assess_class(entry, load, policy=DEFAULT_SELECTION_POLICY):
    """Assess one class against the three performance questions."""
    validate_selection_policy(policy)
    row = validate_class_entry(entry)
    case = validate_load(load)
    derating = float(policy["derating_factor"])
    capability = row["max_continuous_current_a"] * derating
    steady = case["steady_state_current_a"]
    carries = _at_most(steady, capability)

    charge_time = inrush_charge_time_s(
        case["load_capacitance_f"], case["bus_voltage_v"], row["limit_min_a"]
    )
    required_time = charge_time * float(policy["startup_time_margin"])
    starts = _at_most(required_time, row["trip_off_time_min_s"])

    protects = _at_most(row["limit_max_a"], case["harness_rating_a"])

    findings = []
    if not carries:
        findings.append(
            "%s: steady load %.4f A exceeds the derated capability %.4f A"
            % (FINDING_CAPABILITY, steady, capability)
        )
    if not starts:
        findings.append(
            "%s: charging %.4g F to %.4g V at the lower limit %.4f A needs "
            "%.6f s with margin, against a shortest trip-off of %.6f s"
            % (
                FINDING_STARTUP,
                case["load_capacitance_f"],
                case["bus_voltage_v"],
                row["limit_min_a"],
                required_time,
                row["trip_off_time_min_s"],
            )
        )
    if not protects:
        findings.append(
            "%s: upper limiting current %.4f A is above the harness rating %.4f A"
            % (FINDING_HARNESS, row["limit_max_a"], case["harness_rating_a"])
        )

    utilisation = steady / capability
    advisories = []
    if carries and utilisation < float(policy["utilisation_advisory_floor"]):
        advisories.append(
            "%s: utilisation %.3f leaves the class oversized for the load"
            % (FINDING_OVERSIZED, utilisation)
        )

    return {
        "name": row["name"],
        "derated_capability_a": capability,
        "utilisation": utilisation,
        "startup_charge_time_s": charge_time,
        "startup_required_time_s": required_time,
        "startup_slack_s": row["trip_off_time_min_s"] - required_time,
        "harness_slack_a": case["harness_rating_a"] - row["limit_max_a"],
        "carries_steady_load": carries,
        "permits_start_up": starts,
        "protects_harness": protects,
        "adequate": carries and starts and protects,
        "findings": findings,
        "advisories": advisories,
    }


def candidate_classes(table, load, policy=DEFAULT_SELECTION_POLICY):
    """Every class in the table that meets all three performance questions."""
    rows = validate_class_table(table)
    return [a for a in (assess_class(r, load, policy) for r in rows) if a["adequate"]]


def select_lcl_class(table, load, policy=DEFAULT_SELECTION_POLICY):
    """Full clause 5.2.1.1.1 class choice with a compliance verdict.

    The smallest adequate class wins: an oversized class holds a larger
    fault current for longer, which is what the downstream harness and
    the bus have to survive.
    """
    rows = validate_class_table(table)
    assessments = [assess_class(r, load, policy) for r in rows]
    adequate = [a for a in assessments if a["adequate"]]
    if not adequate:
        reasons = []
        for a in assessments:
            reasons.extend("%s %s" % (a["name"], f) for f in a["findings"])
        return {
            "verdict": VERDICT_NO_CLASS,
            "selected": None,
            "assessments": assessments,
            "candidates": [],
            "findings": reasons,
            "advisories": [],
        }
    chosen = adequate[0]
    return {
        "verdict": VERDICT_SELECTED,
        "selected": chosen["name"],
        "selected_assessment": chosen,
        "assessments": assessments,
        "candidates": [a["name"] for a in adequate],
        "findings": [],
        "advisories": list(chosen["advisories"]),
    }
