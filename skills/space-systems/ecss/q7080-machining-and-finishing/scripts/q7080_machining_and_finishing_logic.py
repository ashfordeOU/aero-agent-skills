#!/usr/bin/env python3
"""Machining and finishing allowance rules for additively manufactured parts.

Anchor: ECSS-Q-ST-70-80 post-process clause on machining and surface
finishing of parts made by additive manufacturing. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What the clause actually decides
--------------------------------
An as-built surface is not the surface the drawing describes, and the stock
left on it has to be large enough for the cut to reach sound material while
leaving a wall that still meets the design. Five quantities decide it:

stock needed   the cut has to go below the as-built valley depth, below the
               near-surface layer of partly fused powder and porosity, past
               the positional deviation the part shows once it is released,
               past the uncertainty of the fixture datum, and still be a
               real depth of cut rather than a rub.
stock declared what was actually left on the model.
wall left      machining and finishing both take material off the same
               wall, from every machined side, and what remains has to meet
               the minimum design wall.
finishing      a finishing process removes stock too, and only some
               processes reach an internal surface at all.
bore growth    on an internal passage the removal opens the bore on both
               sides, so a passage can be finished straight out of its
               diameter tolerance.

The verdict is the worst of them and the driving quantity is named.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FINISHING_PROCESSES = (
    "abrasive-flow",
    "vibratory-tumbling",
    "electropolish",
    "shot-peen",
    "manual-blend",
)

# Which finishing processes reach a surface inside the part at all.
PROCESS_REACHES_INTERNAL = {
    "abrasive-flow": True,
    "vibratory-tumbling": False,
    "electropolish": True,
    "shot-peen": False,
    "manual-blend": False,
}

# Peening works by displacing material into compression, not by taking it
# away, so a declared stock removal for it is a bookkeeping error.
PROCESS_REMOVES_STOCK = {
    "abrasive-flow": True,
    "vibratory-tumbling": True,
    "electropolish": True,
    "shot-peen": False,
    "manual-blend": True,
}

SURFACE_LOCATIONS = ("external", "internal")

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

UM_PER_MM = 1000.0

# Stock beyond this multiple of what the cut needs is not conservatism, it
# is build time and distortion nobody asked for.
DEFAULT_EXCESS_STOCK_FACTOR = 3.0


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
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
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


def _worst(verdicts):
    worst = VERDICT_ACCEPT
    for verdict in verdicts:
        if _VERDICT_RANK[verdict] > _VERDICT_RANK[worst]:
            worst = verdict
    return worst


def required_stock_mm(surface_rz_um, subsurface_defect_depth_um, distortion_mm,
                      fixture_uncertainty_mm, minimum_cut_mm):
    """Stock one machined side needs before the cut reaches sound material.

    Every term is a separate reason the tool has to go deeper, and they add:
    the as-built valley, the partly fused near-surface layer, where the part
    actually sits once it is released, how well the fixture locates it, and
    the smallest depth at which the tool cuts instead of rubbing.
    """
    valley = _require_non_negative("surface_rz_um", surface_rz_um) / UM_PER_MM
    defect = (
        _require_non_negative("subsurface_defect_depth_um", subsurface_defect_depth_um)
        / UM_PER_MM
    )
    distortion = _require_non_negative("distortion_mm", distortion_mm)
    fixture = _require_non_negative("fixture_uncertainty_mm", fixture_uncertainty_mm)
    minimum_cut = _require_positive("minimum_cut_mm", minimum_cut_mm)
    return valley + defect + distortion + fixture + minimum_cut


def grade_stock_allowance(declared_stock_mm, required_mm,
                          excess_factor=DEFAULT_EXCESS_STOCK_FACTOR):
    """Grade the declared machining stock against what the cut needs."""
    declared = _require_non_negative("declared_stock_mm", declared_stock_mm)
    required = _require_positive("required_mm", required_mm)
    factor = _require_positive("excess_factor", excess_factor)
    if factor < 1.0:
        raise ValueError("excess_factor must be at least 1.0, got %r" % (excess_factor,))
    findings = []
    verdicts = [VERDICT_ACCEPT]
    if not _at_least(declared, required):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%.3f mm of stock against the %.3f mm the cut needs; the tool "
            "finishes inside the as-built surface layer"
            % (declared, required)
        )
    elif not _at_most(declared, required * factor):
        verdicts.append(VERDICT_REVIEW)
        findings.append(
            "%.3f mm of stock is more than %.1f times the %.3f mm needed; the "
            "excess is build time, mass and distortion, not margin"
            % (declared, factor, required)
        )
    return {
        "declared_stock_mm": declared,
        "required_stock_mm": required,
        "margin_mm": declared - required,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def grade_finishing(process, surface_location, passes, per_pass_um, allowance_um):
    """Grade a finishing operation on reach, stock removed and its budget."""
    process = _require_choice("process", process, FINISHING_PROCESSES)
    location = _require_choice("surface_location", surface_location, SURFACE_LOCATIONS)
    pass_count = _require_count("passes", passes, minimum=0)
    per_pass = _require_non_negative("per_pass_um", per_pass_um)
    allowance = _require_non_negative("allowance_um", allowance_um)

    removes = PROCESS_REMOVES_STOCK[process]
    total = per_pass * pass_count if removes else 0.0

    findings = []
    verdicts = [VERDICT_ACCEPT]

    if location == "internal" and not PROCESS_REACHES_INTERNAL[process]:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%s cannot reach an internal surface, so the passage keeps its "
            "as-built condition however many passes are run" % process
        )

    if not removes and per_pass > 0.0:
        verdicts.append(VERDICT_REVIEW)
        findings.append(
            "%s displaces material into compression rather than removing it; "
            "the declared %.1f um per pass is not stock coming off"
            % (process, per_pass)
        )

    if not _at_most(total, allowance):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%d passes of %s remove %.1f um against the %.1f um finishing "
            "allowance" % (pass_count, process, total, allowance)
        )

    return {
        "process": process,
        "surface_location": location,
        "removal_um": total,
        "allowance_um": allowance,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def wall_after_machining(as_built_wall_mm, stock_per_side_mm, finishing_removal_um,
                         machined_sides, minimum_wall_mm):
    """Wall left once machining and finishing have taken their material."""
    as_built = _require_positive("as_built_wall_mm", as_built_wall_mm)
    stock = _require_non_negative("stock_per_side_mm", stock_per_side_mm)
    finishing = _require_non_negative("finishing_removal_um", finishing_removal_um)
    sides = _require_count("machined_sides", machined_sides, minimum=0)
    minimum = _require_positive("minimum_wall_mm", minimum_wall_mm)
    if sides > 2:
        raise ValueError("machined_sides must be 0, 1 or 2 for one wall, got %d" % sides)
    per_side = stock + finishing / UM_PER_MM
    remaining = as_built - per_side * sides
    findings = []
    verdicts = [VERDICT_ACCEPT]
    if remaining <= 0.0:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "machining %d side(s) at %.3f mm removes the whole %.3f mm wall"
            % (sides, per_side, as_built)
        )
    elif not _at_least(remaining, minimum):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%.3f mm of wall left against the %.3f mm minimum after %d side(s) "
            "at %.3f mm" % (remaining, minimum, sides, per_side)
        )
    return {
        "removal_per_side_mm": per_side,
        "remaining_wall_mm": remaining,
        "minimum_wall_mm": minimum,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def bore_after_finishing(bore_mm, finishing_removal_um, upper_tolerance_mm):
    """Bore a finished internal passage ends at; removal opens both sides."""
    bore = _require_positive("bore_mm", bore_mm)
    removal = _require_non_negative("finishing_removal_um", finishing_removal_um)
    tolerance = _require_non_negative("upper_tolerance_mm", upper_tolerance_mm)
    growth = 2.0 * removal / UM_PER_MM
    final = bore + growth
    findings = []
    acceptable = _at_most(growth, tolerance)
    if not acceptable:
        findings.append(
            "finishing opens the %.3f mm bore by %.3f mm to %.3f mm, past the "
            "%.3f mm upper tolerance" % (bore, growth, final, tolerance)
        )
    return {
        "bore_mm": bore,
        "growth_mm": growth,
        "final_bore_mm": final,
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def assess_machining_plan(case):
    """Full machining and finishing allowance verdict for one feature."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    required = required_stock_mm(
        case.get("surface_rz_um"),
        case.get("subsurface_defect_depth_um"),
        case.get("distortion_mm"),
        case.get("fixture_uncertainty_mm"),
        case.get("minimum_cut_mm"),
    )
    stock = grade_stock_allowance(
        case.get("declared_stock_mm"),
        required,
        case.get("excess_factor", DEFAULT_EXCESS_STOCK_FACTOR),
    )
    finishing = grade_finishing(
        case.get("finishing_process"),
        case.get("surface_location", "external"),
        case.get("finishing_passes", 0),
        case.get("finishing_per_pass_um", 0.0),
        case.get("finishing_allowance_um", 0.0),
    )
    wall = wall_after_machining(
        case.get("as_built_wall_mm"),
        case.get("declared_stock_mm"),
        finishing["removal_um"],
        case.get("machined_sides", 2),
        case.get("minimum_wall_mm"),
    )
    parts = {"stock": stock, "finishing": finishing, "wall": wall}
    findings = []
    findings.extend("stock: %s" % text for text in stock["findings"])
    findings.extend("finishing: %s" % text for text in finishing["findings"])
    findings.extend("wall: %s" % text for text in wall["findings"])
    bore = None
    if case.get("surface_location") == "internal":
        bore = bore_after_finishing(
            case.get("bore_mm"),
            finishing["removal_um"],
            case.get("bore_upper_tolerance_mm", 0.0),
        )
        parts["bore"] = bore
        findings.extend("bore: %s" % text for text in bore["findings"])
    verdict = _worst(part["verdict"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _VERDICT_RANK[part["verdict"]] == _VERDICT_RANK[verdict]
        and verdict != VERDICT_ACCEPT
    )
    return {
        "verdict": verdict,
        "driving_quantities": driving,
        "required_stock_mm": required,
        "stock": stock,
        "finishing": finishing,
        "wall": wall,
        "bore": bore,
        "findings": findings,
    }
