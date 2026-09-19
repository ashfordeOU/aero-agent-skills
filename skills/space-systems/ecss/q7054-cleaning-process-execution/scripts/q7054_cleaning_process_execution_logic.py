#!/usr/bin/env python3
"""Execution of an ultracleaning process on flight hardware.

Anchor: ECSS-Q-ST-70-54C process clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Execution is where a qualified method becomes a result, and the three
things that decide the result are the order of the steps, the size of
the rinse cascade, and whether the drying actually reaches the fluid.

    order     coarse removal runs before precision work, never after;
              a chemical step is followed by a rinse before anything
              dries it on; nothing wet is inspected or bagged.

    rinsing   a rinse does not remove the bath liquor, it dilutes it.
              Each stage leaves a carryover fraction of the previous
              stage behind, so the residual falls geometrically and the
              number of stages is computed from the fraction, not
              chosen by habit.

    drying    a drying method reaches the geometry its transport can
              reach and handles the volatility of the fluid actually
              present. Ambient evaporation on a low-volatility fluid in
              a blind hole leaves the fluid there.

The residual the cascade reaches is the number the process owes; a
sequence that is well ordered but under-rinsed delivers a part that
looks processed and is not clean.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STEP_TYPES = (
    "gross-precleaning",
    "chemical-cleaning",
    "rinse",
    "drying",
    "inspection",
    "packaging",
)

WET_STEP_TYPES = ("chemical-cleaning", "rinse")

GEOMETRIES = ("open-surface", "blind-hole", "internal-passage", "complex-assembly")

VOLATILITIES = ("high", "medium", "low")

DRYING_METHODS = {
    "ambient-evaporation": {
        "reaches": frozenset({"open-surface"}),
        "volatilities": frozenset({"high"}),
    },
    "warm-air-cabinet": {
        "reaches": frozenset({"open-surface", "complex-assembly"}),
        "volatilities": frozenset({"high", "medium"}),
    },
    "hot-nitrogen-purge": {
        "reaches": frozenset(
            {"open-surface", "blind-hole", "internal-passage", "complex-assembly"}
        ),
        "volatilities": frozenset({"high", "medium"}),
    },
    "vacuum-bake": {
        "reaches": frozenset(
            {"open-surface", "blind-hole", "internal-passage", "complex-assembly"}
        ),
        "volatilities": frozenset({"high", "medium", "low"}),
    },
}

PROCESS_CLOSES = "process-closes"
PROCESS_OPEN = "process-open"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12
_INTEGER_SNAP = 1e-9


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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def require_carryover_fraction(value):
    """Fraction of one bath's liquor a part carries into the next stage."""
    if not _is_finite_number(value):
        raise ValueError("carryover_fraction must be a finite number, got %r" % (value,))
    if value <= 0.0 or value >= 1.0:
        raise ValueError(
            "carryover_fraction must lie strictly between 0 and 1, got %r" % (value,)
        )
    return float(value)


def residual_after_rinses(initial_mg_per_l, carryover_fraction, stages):
    """Concentration retained on the part after a cascade of rinse stages."""
    initial = _require_positive("initial_mg_per_l", initial_mg_per_l)
    carryover = require_carryover_fraction(carryover_fraction)
    if not isinstance(stages, int) or isinstance(stages, bool):
        raise ValueError("stages must be an integer, got %r" % (stages,))
    if stages < 0:
        raise ValueError("stages must not be negative, got %r" % (stages,))
    return initial * carryover**stages


def rinse_stages_required(initial_mg_per_l, target_mg_per_l, carryover_fraction):
    """Number of cascade stages that brings the residual to the target.

    The ratio is a quotient of logarithms, so a cascade that lands exactly
    on the target can compute a hair above or below an integer. The near
    integer is snapped before the ceiling is taken, otherwise an exact
    four-stage cascade silently becomes five.
    """
    initial = _require_positive("initial_mg_per_l", initial_mg_per_l)
    target = _require_positive("target_mg_per_l", target_mg_per_l)
    carryover = require_carryover_fraction(carryover_fraction)
    if _at_most(initial, target):
        return 0
    raw = math.log(target / initial) / math.log(carryover)
    nearest = round(raw)
    if nearest >= 0 and abs(raw - nearest) <= _INTEGER_SNAP:
        return int(nearest)
    return int(math.ceil(raw))


def drying_adequate(method, geometry, volatility):
    """Whether a drying method clears this fluid out of this geometry."""
    name = _require_choice("method", method, tuple(DRYING_METHODS))
    where = _require_choice("geometry", geometry, GEOMETRIES)
    how_volatile = _require_choice("volatility", volatility, VOLATILITIES)
    spec = DRYING_METHODS[name]
    if where not in spec["reaches"]:
        return {
            "adequate": False,
            "reason": "%s does not reach a %s; the fluid stays where the "
            "transport cannot go" % (name, where),
        }
    if how_volatile not in spec["volatilities"]:
        return {
            "adequate": False,
            "reason": "%s does not clear a %s volatility fluid; it evaporates "
            "the surface film and leaves the rest" % (name, how_volatile),
        }
    return {
        "adequate": True,
        "reason": "%s reaches a %s and clears a %s volatility fluid"
        % (name, where, how_volatile),
    }


def validate_sequence(steps):
    """Check an ordered step list is a real sequence of known step types."""
    if isinstance(steps, dict) or not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple of mappings, got %r" % (steps,))
    if not steps:
        raise ValueError("steps must not be empty; a process has at least one step")
    checked = []
    for position, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError("step %d must be a mapping, got %r" % (position, step))
        step_type = _require_choice("step %d type" % position, step.get("type"), STEP_TYPES)
        name = step.get("name", step_type)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("step %d name must be a non-empty string" % position)
        checked.append({"position": position, "type": step_type, "name": name})
    return checked


def check_step_order(steps):
    """Ordering findings against the execution rules, in sequence order."""
    checked = validate_sequence(steps)
    types = [entry["type"] for entry in checked]
    findings = []
    if types[0] in ("rinse", "drying", "inspection", "packaging"):
        findings.append(
            "sequence opens with %s; execution opens with gross precleaning or "
            "a chemical cleaning step" % types[0]
        )
    seen_chemical = False
    wet_pending = False
    for position, step_type in enumerate(types, start=1):
        if step_type == "gross-precleaning":
            if seen_chemical:
                findings.append(
                    "gross precleaning at position %d follows precision work; "
                    "coarse removal after a chemical step puts the contamination "
                    "back on a cleaned surface" % position
                )
        elif step_type == "chemical-cleaning":
            seen_chemical = True
            wet_pending = True
        elif step_type == "rinse":
            wet_pending = True
        elif step_type == "drying":
            if not wet_pending:
                findings.append(
                    "drying at position %d has no wet step behind it to dry"
                    % position
                )
            wet_pending = False
        elif step_type == "inspection":
            if wet_pending:
                findings.append(
                    "inspection at position %d runs on a wet surface; a wet part "
                    "cannot be graded for particles or residue" % position
                )
        elif step_type == "packaging":
            if wet_pending:
                findings.append(
                    "packaging at position %d closes a bag over a wet surface"
                    % position
                )
            if position != len(types):
                findings.append(
                    "packaging at position %d is not the last step" % position
                )
    for index, step_type in enumerate(types):
        if step_type != "chemical-cleaning":
            continue
        rinsed = False
        for later in types[index + 1 :]:
            if later == "rinse":
                rinsed = True
                break
            if later in ("drying", "inspection", "packaging", "gross-precleaning"):
                break
        if not rinsed:
            findings.append(
                "chemical cleaning at position %d is not followed by a rinse; the "
                "bath liquor dries onto the part" % (index + 1)
            )
    if "packaging" not in types:
        findings.append(
            "sequence does not close with packaging; the state after the last "
            "step is uncontrolled"
        )
    elif types.count("packaging") > 1:
        findings.append(
            "sequence contains %d packaging steps; it closes once"
            % types.count("packaging")
        )
    return findings


def execute_cleaning_process(case):
    """Full execution check: ordering, rinse cascade and drying, with a verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    checked = validate_sequence(case.get("steps"))
    initial = _require_positive(
        "initial_carryover_mg_per_l", case.get("initial_carryover_mg_per_l")
    )
    target = _require_positive(
        "target_carryover_mg_per_l", case.get("target_carryover_mg_per_l")
    )
    carryover = require_carryover_fraction(case.get("carryover_fraction"))
    geometry = _require_choice("geometry", case.get("geometry"), GEOMETRIES)
    volatility = _require_choice("volatility", case.get("volatility"), VOLATILITIES)
    drying_method = _require_choice(
        "drying_method", case.get("drying_method"), tuple(DRYING_METHODS)
    )

    findings = list(check_step_order(checked))
    required_stages = rinse_stages_required(initial, target, carryover)
    provided_stages = sum(1 for entry in checked if entry["type"] == "rinse")
    if provided_stages < required_stages:
        findings.append(
            "the sequence provides %d rinse stage(s) against %d required to "
            "reach %.4g mg per litre from %.4g at a carryover of %.4g"
            % (provided_stages, required_stages, target, initial, carryover)
        )
    achieved = residual_after_rinses(initial, carryover, provided_stages)
    target_met = _at_most(achieved, target)

    drying = drying_adequate(drying_method, geometry, volatility)
    if not drying["adequate"]:
        findings.append("drying is inadequate: %s" % drying["reason"])

    return {
        "steps": checked,
        "required_rinse_stages": required_stages,
        "provided_rinse_stages": provided_stages,
        "achieved_residual_mg_per_l": achieved,
        "target_residual_mg_per_l": target,
        "target_met": target_met,
        "drying": drying,
        "findings": findings,
        "verdict": PROCESS_CLOSES if not findings else PROCESS_OPEN,
    }
