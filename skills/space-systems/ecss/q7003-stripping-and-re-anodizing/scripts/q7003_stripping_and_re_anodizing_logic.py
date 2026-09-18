#!/usr/bin/env python3
"""Stripping and re-anodizing rules for a rejected anodized part.

Anchor: ECSS-Q-ST-70-03 rework clause on anodizing. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

A non-conforming anodized part can sometimes be stripped and put back
through the line, but never freely. Three limits run at once and the
tightest one governs:

dimension   the anodic layer grows both outward and inward, so stripping
            it takes base metal with it. Each cycle costs metal on every
            treated surface, and the part has to stay above the drawing
            minimum after the cycle that is being proposed, not merely
            before it.
policy      a declared ceiling on reprocessing cycles. It exists because
            repeated etching roughens the surface and works the grain
            boundaries whatever the dimension says, and it is lower for
            an alloy that is sensitive to that attack.
cladding    a clad sheet carries a corrosion-protective skin over a
            stronger core. Stripping through that skin does not fail a
            dimension check, it removes the protection the cladding was
            there to give, so the clad layer sets its own cycle count.

The part is graded on how many further cycles all three permit. Where
metal is the binding limit there is no route back: a concession cannot
restore material. Where policy or cladding binds, a documented deviation
is at least a decision someone can take.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ALLOY_CLASSES = ("bare-standard", "clad-sheet", "high-strength")

REWORK_PERMITTED = "re-anodize-permitted"
REWORK_FINAL_CYCLE = "re-anodize-final-cycle"
REWORK_CONCESSION = "concession-required"
REWORK_SCRAP = "scrap"

BINDING_DIMENSION = "dimension"
BINDING_POLICY = "cycle-policy"
BINDING_CLADDING = "cladding"

DEFAULT_REWORK_POLICY = {
    "max_cycles": {
        "bare-standard": 3,
        "clad-sheet": 2,
        "high-strength": 1,
    }
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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _tolerant_floor(value):
    """floor(value), pulled up when value sits on an integer already.

    A cycle count is a budget divided by a per-cycle cost, and a budget
    that was set as a whole number of cycles can evaluate a few units in
    the last place below that integer. Flooring it raw would silently
    throw away a cycle the part is entitled to, and would throw it away
    on one platform and not another.
    """
    lower = math.floor(value)
    if math.isclose(value, lower + 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return int(lower) + 1
    return int(lower)


def validate_rework_policy(policy):
    """Check a reprocessing policy covers every alloy class sensibly."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    table = policy.get("max_cycles")
    if not isinstance(table, dict):
        raise ValueError("policy max_cycles must be a mapping")
    missing = set(ALLOY_CLASSES) - set(table)
    if missing:
        raise ValueError(
            "policy max_cycles is missing: %s" % ", ".join(sorted(missing))
        )
    for alloy in ALLOY_CLASSES:
        _require_count("policy max_cycles[%s]" % alloy, table[alloy])
    return policy


def metal_loss_per_cycle_mm(loss_per_surface_um, treated_surfaces):
    """Dimensional loss one strip-and-re-anodize cycle costs, in mm."""
    loss = _require_positive("loss_per_surface_um", loss_per_surface_um)
    surfaces = _require_count("treated_surfaces", treated_surfaces, minimum=1)
    if surfaces > 2:
        raise ValueError(
            "treated_surfaces %d is more than the two faces a single dimension "
            "spans; split the part into separate dimensions" % surfaces
        )
    return loss * surfaces / 1000.0


def dimension_after_cycles(
    current_mm, cycles, loss_per_surface_um, treated_surfaces
):
    """Dimension left after a given number of further strip cycles."""
    current = _require_positive("current_mm", current_mm)
    count = _require_count("cycles", cycles)
    per_cycle = metal_loss_per_cycle_mm(loss_per_surface_um, treated_surfaces)
    return current - count * per_cycle


def cycles_remaining_by_dimension(
    current_mm, minimum_mm, loss_per_surface_um, treated_surfaces
):
    """Further cycles the drawing minimum leaves room for."""
    current = _require_positive("current_mm", current_mm)
    minimum = _require_positive("minimum_mm", minimum_mm)
    if minimum > current:
        raise ValueError(
            "current dimension %g mm is already below the %g mm minimum"
            % (current, minimum)
        )
    per_cycle = metal_loss_per_cycle_mm(loss_per_surface_um, treated_surfaces)
    return max(0, _tolerant_floor((current - minimum) / per_cycle))


def cycles_remaining_by_policy(
    cycles_completed, alloy_class, policy=DEFAULT_REWORK_POLICY
):
    """Further cycles the declared reprocessing ceiling leaves."""
    validate_rework_policy(policy)
    _require_choice("alloy_class", alloy_class, ALLOY_CLASSES)
    done = _require_count("cycles_completed", cycles_completed)
    return max(0, policy["max_cycles"][alloy_class] - done)


def cycles_remaining_by_cladding(
    alloy_class, clad_remaining_um, loss_per_surface_um, treated_surfaces
):
    """Further cycles the remaining cladding thickness leaves.

    Only a clad sheet carries this limit; on any other alloy class the
    cladding is not the thing being protected and the limit does not
    apply.
    """
    _require_choice("alloy_class", alloy_class, ALLOY_CLASSES)
    if alloy_class != "clad-sheet":
        return None
    if clad_remaining_um is None:
        raise ValueError(
            "a clad-sheet part needs clad_remaining_um to size the stripping limit"
        )
    remaining = _require_non_negative("clad_remaining_um", clad_remaining_um)
    loss = _require_positive("loss_per_surface_um", loss_per_surface_um)
    _require_count("treated_surfaces", treated_surfaces, minimum=1)
    return max(0, _tolerant_floor(remaining / loss))


def assess_rework(case, policy=DEFAULT_REWORK_POLICY):
    """Decide whether a rejected part may be stripped and re-anodized."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    alloy = _require_choice("alloy_class", case.get("alloy_class"), ALLOY_CLASSES)
    surfaces = case.get("treated_surfaces", 1)
    loss = case.get("loss_per_surface_um")
    by_dimension = cycles_remaining_by_dimension(
        case.get("current_mm"), case.get("minimum_mm"), loss, surfaces
    )
    by_policy = cycles_remaining_by_policy(
        case.get("cycles_completed", 0), alloy, policy
    )
    by_cladding = cycles_remaining_by_cladding(
        alloy, case.get("clad_remaining_um"), loss, surfaces
    )
    limits = [(BINDING_DIMENSION, by_dimension), (BINDING_POLICY, by_policy)]
    if by_cladding is not None:
        limits.append((BINDING_CLADDING, by_cladding))
    governing = min(value for _, value in limits)
    binding = sorted(name for name, value in limits if value == governing)
    findings = []
    if governing >= 2:
        disposition = REWORK_PERMITTED
    elif governing == 1:
        disposition = REWORK_FINAL_CYCLE
        findings.append(
            "one cycle left before the %s limit; plan the rework as the last "
            "attempt on this part" % ", ".join(binding)
        )
    elif BINDING_DIMENSION in binding:
        disposition = REWORK_SCRAP
        findings.append(
            "no dimensional allowance left; a further cycle would take the part "
            "below the %g mm minimum, and a concession cannot restore metal"
            % _require_positive("minimum_mm", case.get("minimum_mm"))
        )
    else:
        disposition = REWORK_CONCESSION
        findings.append(
            "the %s limit is reached while metal remains; a further cycle needs a "
            "documented deviation rather than a shop decision" % ", ".join(binding)
        )
    next_dimension = dimension_after_cycles(
        case.get("current_mm"), 1, loss, surfaces
    )
    return {
        "disposition": disposition,
        "cycles_remaining": governing,
        "binding_limits": binding,
        "cycles_remaining_by_dimension": by_dimension,
        "cycles_remaining_by_policy": by_policy,
        "cycles_remaining_by_cladding": by_cladding,
        "dimension_after_next_cycle_mm": next_dimension,
        "loss_per_cycle_mm": metal_loss_per_cycle_mm(loss, surfaces),
        "findings": findings,
    }
