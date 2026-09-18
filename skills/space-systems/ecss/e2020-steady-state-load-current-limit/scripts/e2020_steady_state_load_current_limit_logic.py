#!/usr/bin/env python3
"""Steady-state load current against the class current of its line.

Anchor: ECSS-E-ST-20-20C clause 5.3.1.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Once a protected line has switched on and the turn-on transient is over,
the current the load draws has to stay BELOW the current of the class
the line was given. The turn-on excess is a separate allowance with its
own clause; this one governs everything after it.

The failure it prevents is nuisance limitation. A limiter that is asked
to carry a steady current at or above its class current enters
limitation with nothing wrong downstream, holds the load at a reduced
voltage and then opens on its trip-off delay, so a perfectly healthy
unit looks like a fault.

Three things make the comparison less obvious than it reads:

    a constant-power load draws hardest at the LOW end of the bus
    voltage window, because the power is fixed and the current is what
    moves. Sizing the load at the nominal bus is the classic defect, and
    it understates the current by exactly the regulation band

    the converter in front of the load moves the figure again: the
    current on the bus is the load power divided by both the bus voltage
    and the conversion efficiency, and efficiency is worst where the
    input voltage is lowest

    the equipment has more than one operating mode, and the mode that
    binds is not always the one the data sheet leads with. Every mode is
    converted and the largest is carried forward

On top of the bounding mode sits a one-sided uncertainty stack --
consumption tolerance, temperature drift, ageing, a sense or return
offset. Only the upward direction can threaten the class current, so the
stack is one-sided by construction. Arithmetic stacking is the bounding
answer; root-sum-square assumes the contributors are independent and
always returns a smaller figure, so the method travels with the result.

The class current is then derated by the project factor before the
comparison, and the result is a strict separation: equality with the
derated capability is not compliance, it is the boundary the clause
draws.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MODE_FIELDS = ("name", "kind", "value")
MODE_KINDS = ("constant-power", "constant-current")
UNCERTAINTY_FIELDS = ("name", "kind", "plus")
UNCERTAINTY_KINDS = ("relative", "absolute")
METHODS = ("arithmetic", "rss")
DEFAULT_METHOD = "arithmetic"

VERDICT_BELOW = "steady-state-load-current-below-the-class-current"
VERDICT_NOT_BELOW = "steady-state-load-current-not-below-the-class-current"

FINDING_AT_OR_ABOVE_DERATED = (
    "steady-state-current-at-or-above-the-derated-class-current"
)
FINDING_AT_OR_ABOVE_CLASS = "steady-state-current-at-or-above-the-class-current-itself"
ADVISORY_HIGH_UTILISATION = (
    "steady-state-current-consumes-most-of-the-derated-class-current"
)

# Placeholder mode set: the shape a project's own consumption table takes.
DEFAULT_OPERATING_MODES = (
    {"name": "acquisition", "kind": "constant-power", "value": 22.0, "efficiency": 0.85},
    {"name": "science", "kind": "constant-power", "value": 18.0, "efficiency": 0.85},
    {"name": "standby", "kind": "constant-power", "value": 6.0, "efficiency": 0.80},
    {"name": "survival-heater", "kind": "constant-current", "value": 0.25},
)

# Placeholder one-sided uncertainty set.
DEFAULT_UNCERTAINTIES = (
    {"name": "consumption-tolerance", "kind": "relative", "plus": 0.05},
    {"name": "temperature-drift", "kind": "relative", "plus": 0.03},
    {"name": "ageing", "kind": "relative", "plus": 0.02},
    {"name": "return-path-offset", "kind": "absolute", "plus": 0.010},
)

DEFAULT_LIMIT_POLICY = {
    "class_current_derating_factor": 0.80,
    "utilisation_advisory_fraction": 0.90,
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


def _strictly_below(value, limit):
    """value < limit, treating an exact landing on the limit as NOT below.

    A steady current is built from divisions, sums and sometimes a square
    root, so a case meant to sit exactly on the derated capability can
    land a few units in the last place either side of it. The tie is
    resolved against the design, which is what a strict separation means.
    """
    if math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    return value < limit


def validate_limit_policy(policy):
    """Check the class-current derating factor and the advisory floor."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    factor = _require_positive(
        "class_current_derating_factor", policy.get("class_current_derating_factor")
    )
    if factor > 1.0:
        raise ValueError(
            "class_current_derating_factor above one uprates the class, got %r"
            % (factor,)
        )
    fraction = _require_positive(
        "utilisation_advisory_fraction", policy.get("utilisation_advisory_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "utilisation_advisory_fraction must not exceed one, got %r" % (fraction,)
        )
    return policy


def validate_bus_window(bus_min_v, bus_max_v):
    """Check the bus voltage window is positive and the right way up."""
    low = _require_positive("bus_min_v", bus_min_v)
    high = _require_positive("bus_max_v", bus_max_v)
    if high < low:
        raise ValueError("bus voltage window is inverted (%g V .. %g V)" % (low, high))
    return (low, high)


def validate_mode(mode):
    """Check one operating mode is a usable consumption declaration."""
    if not isinstance(mode, dict):
        raise ValueError("mode must be a mapping, got %r" % (mode,))
    missing = [f for f in MODE_FIELDS if f not in mode]
    if missing:
        raise ValueError("mode is missing fields: %s" % ", ".join(sorted(missing)))
    name = mode["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("mode name must be a non-empty string, got %r" % (name,))
    kind = _require_choice("kind", mode["kind"], MODE_KINDS)
    value = _require_positive("value", mode["value"])
    if kind == "constant-power":
        efficiency = _require_positive("efficiency", mode.get("efficiency", 1.0))
        if efficiency > 1.0:
            raise ValueError(
                "mode %s declares an efficiency above unity (%r)" % (name, efficiency)
            )
        return {
            "name": name,
            "kind": kind,
            "value": value,
            "efficiency": efficiency,
        }
    if "efficiency" in mode:
        raise ValueError(
            "mode %s is constant-current; an efficiency does not apply to it" % (name,)
        )
    return {"name": name, "kind": kind, "value": value}


def validate_modes(modes):
    """Normalise a mode set and require unique names."""
    if isinstance(modes, dict) or not hasattr(modes, "__iter__"):
        raise ValueError("modes must be a sequence of mappings")
    rows = [validate_mode(m) for m in modes]
    if not rows:
        raise ValueError("mode set is empty; there is no consumption to compare")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("mode set repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def mode_current_a(mode, bus_voltage_v):
    """Bus current one operating mode draws at a given bus voltage."""
    row = validate_mode(mode)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    if row["kind"] == "constant-current":
        return row["value"]
    return row["value"] / (row["efficiency"] * voltage)


def bounding_mode_current(mode, bus_min_v, bus_max_v):
    """Largest current one mode draws anywhere in the bus window.

    Both ends are evaluated rather than assumed, and the voltage that
    produced the larger current is reported so a reviewer can see that a
    constant-power load binds at the bottom of the window.
    """
    low, high = validate_bus_window(bus_min_v, bus_max_v)
    row = validate_mode(mode)
    at_low = mode_current_a(row, low)
    at_high = mode_current_a(row, high)
    if at_high > at_low:
        return {
            "name": row["name"],
            "kind": row["kind"],
            "current_a": at_high,
            "bounding_bus_voltage_v": high,
        }
    return {
        "name": row["name"],
        "kind": row["kind"],
        "current_a": at_low,
        "bounding_bus_voltage_v": low,
    }


def rank_modes(modes, bus_min_v, bus_max_v):
    """Every mode at its own bounding bus voltage, heaviest first."""
    rows = validate_modes(modes)
    ranked = [bounding_mode_current(row, bus_min_v, bus_max_v) for row in rows]
    ranked.sort(key=lambda row: (-row["current_a"], row["name"]))
    return tuple(ranked)


def worst_case_mode(modes, bus_min_v, bus_max_v):
    """The single mode that decides the comparison."""
    return rank_modes(modes, bus_min_v, bus_max_v)[0]


def validate_uncertainty(uncertainty):
    """Check one upward uncertainty contributor."""
    if not isinstance(uncertainty, dict):
        raise ValueError("uncertainty must be a mapping, got %r" % (uncertainty,))
    missing = [f for f in UNCERTAINTY_FIELDS if f not in uncertainty]
    if missing:
        raise ValueError(
            "uncertainty is missing fields: %s" % ", ".join(sorted(missing))
        )
    name = uncertainty["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("uncertainty name must be a non-empty string, got %r" % (name,))
    kind = _require_choice("kind", uncertainty["kind"], UNCERTAINTY_KINDS)
    plus = _require_non_negative("plus", uncertainty["plus"])
    if kind == "relative" and plus >= 1.0:
        raise ValueError(
            "relative uncertainty %s is %g; at or beyond unity it is not an "
            "uncertainty" % (name, plus)
        )
    if plus == 0.0:
        raise ValueError(
            "uncertainty %s adds nothing; drop it rather than stacking a zero"
            % (name,)
        )
    return {"name": name, "kind": kind, "plus": plus}


def validate_uncertainties(uncertainties):
    """Normalise an uncertainty set and require unique names."""
    if isinstance(uncertainties, dict) or not hasattr(uncertainties, "__iter__"):
        raise ValueError("uncertainties must be a sequence of mappings")
    rows = [validate_uncertainty(u) for u in uncertainties]
    if not rows:
        raise ValueError("uncertainty set is empty; nothing can be stacked")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("uncertainty set repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    return tuple(rows)


def stack_uncertainties(base_a, uncertainties, method=DEFAULT_METHOD):
    """Amperes the uncertainty set adds on top of the bounding mode."""
    base = _require_positive("base_a", base_a)
    rows = validate_uncertainties(uncertainties)
    _require_choice("method", method, METHODS)
    terms = []
    for row in rows:
        if row["kind"] == "relative":
            terms.append(row["plus"] * base)
        else:
            terms.append(row["plus"])
    if method == "arithmetic":
        return math.fsum(terms)
    return math.sqrt(math.fsum(t * t for t in terms))


def worst_case_steady_current_a(
    modes, bus_min_v, bus_max_v, uncertainties, method=DEFAULT_METHOD
):
    """Bounding mode plus its uncertainty stack, in amperes."""
    worst = worst_case_mode(modes, bus_min_v, bus_max_v)
    added = stack_uncertainties(worst["current_a"], uncertainties, method)
    return worst["current_a"] + added


def derated_class_current_a(class_current_a, derating_factor):
    """Class current after the project derating factor."""
    current = _require_positive("class_current_a", class_current_a)
    factor = _require_positive("derating_factor", derating_factor)
    if factor > 1.0:
        raise ValueError("derating_factor above one uprates the class, got %r" % factor)
    return current * factor


def verify_below_class_current(
    steady_current_a, class_current_a, policy=DEFAULT_LIMIT_POLICY
):
    """Compare the worst-case steady current with the class current."""
    validate_limit_policy(policy)
    steady = _require_positive("steady_current_a", steady_current_a)
    rated = _require_positive("class_current_a", class_current_a)
    derated = derated_class_current_a(
        rated, policy["class_current_derating_factor"]
    )
    return {
        "steady_current_a": steady,
        "class_current_a": rated,
        "derating_factor": float(policy["class_current_derating_factor"]),
        "derated_class_current_a": derated,
        "margin_a": derated - steady,
        "utilisation": steady / derated,
        "below_derated": _strictly_below(steady, derated),
        "below_class": _strictly_below(steady, rated),
    }


def assess_steady_state_load_current(case, policy=DEFAULT_LIMIT_POLICY):
    """Full clause 5.3.1.1.1 steady-state check with a compliance verdict."""
    validate_limit_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    required = (
        "modes",
        "bus_min_v",
        "bus_max_v",
        "uncertainties",
        "class_current_a",
    )
    missing = [f for f in required if f not in case]
    if missing:
        raise ValueError("case is missing fields: %s" % ", ".join(sorted(missing)))
    method = _require_choice("method", case.get("method", DEFAULT_METHOD), METHODS)
    ranked = rank_modes(case["modes"], case["bus_min_v"], case["bus_max_v"])
    worst = ranked[0]
    added = stack_uncertainties(worst["current_a"], case["uncertainties"], method)
    steady = worst["current_a"] + added
    comparison = verify_below_class_current(steady, case["class_current_a"], policy)

    findings = []
    advisories = []
    if not comparison["below_derated"]:
        findings.append(
            "%s: %.4f A against a derated capability of %.4f A"
            % (
                FINDING_AT_OR_ABOVE_DERATED,
                steady,
                comparison["derated_class_current_a"],
            )
        )
    if not comparison["below_class"]:
        findings.append(
            "%s: %.4f A against a class current of %.4f A; the line limits "
            "with nothing wrong downstream"
            % (FINDING_AT_OR_ABOVE_CLASS, steady, comparison["class_current_a"])
        )
    if not findings and comparison["utilisation"] > float(
        policy["utilisation_advisory_fraction"]
    ):
        advisories.append(
            "%s: the load uses %.1f%% of the derated capability"
            % (ADVISORY_HIGH_UTILISATION, 100.0 * comparison["utilisation"])
        )

    compliant = not findings
    return {
        "verdict": VERDICT_BELOW if compliant else VERDICT_NOT_BELOW,
        "compliant": compliant,
        "method": method,
        "modes": ranked,
        "bounding_mode": worst["name"],
        "bounding_bus_voltage_v": worst["bounding_bus_voltage_v"],
        "uncertainty_a": added,
        "steady_current_a": steady,
        "comparison": comparison,
        "findings": findings,
        "advisories": advisories,
    }
