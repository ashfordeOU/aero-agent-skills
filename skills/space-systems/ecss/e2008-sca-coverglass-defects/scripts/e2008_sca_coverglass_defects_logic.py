#!/usr/bin/env python3
"""Coverglass inspection: is the bare cell surface completely covered?

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The question the clause asks is not how good the glass looks. It is
whether any part of the bare cell surface has been left uncovered. That
makes the screen a geometry problem before it is a defect problem: a
coverglass is a rectangle laid over a cell rectangle, and what matters
is the overhang it leaves on each of the four edges once the placement
offset has been taken off it.

Three outcomes come out of that geometry and they are not the same
finding:

  - The glass is large enough and sits square, leaving an overhang on
    every edge at or above the declared minimum. Coverage is complete
    with margin in hand.
  - The glass is large enough but sits off-centre far enough that an
    edge has run short. Coverage is incomplete, and the recovery is to
    lift and re-lay the glass, because the part is right and the
    placement is wrong.
  - The glass is smaller than the cell on an axis. No placement covers
    the cell, so re-laying it cannot help; the wrong part was fitted.

A chip broken out of the coverglass edge is read through the same
geometry. It does not fail the assembly because it is a chip; it fails
it when it has eaten further in than the overhang at that edge had to
give, because that is the point at which bare cell appears under it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COVERGLASS_EDGES = ("x-minus", "x-plus", "y-minus", "y-plus")

ACCEPT = "accept"
REWORK = "rework"
REFER = "refer-for-review"
REJECT = "reject"
COVERAGE_DISPOSITIONS = (ACCEPT, REWORK, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REFER: 2, REJECT: 3}

_X_EDGES = ("x-minus", "x-plus")

DEFAULT_COVERAGE_CRITERIA = {
    "min_overhang_mm": 0.2,
    "placement_tolerance_mm": 0.05,
    "max_exposed_area_fraction": 0.02,
    "max_chips_per_coverglass": 2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_finite(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_finite(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_finite(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Every overhang here is a difference of halved dimensions plus a
    signed offset, so an overhang that should land exactly on a bound
    can evaluate a few units in the last place under it. The bound is
    never lowered; only the comparison tolerates the representation
    error.
    """
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing the same representation error."""
    return value <= limit or _close(value, limit)


def _shortfall(value):
    """How far below zero a signed overhang has gone, floored at zero."""
    if _at_least(value, 0.0):
        return 0.0
    return -value


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_coverage_criteria(criteria):
    """Check a coverage criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive("criteria min_overhang_mm", criteria.get("min_overhang_mm"))
    tolerance = _require_non_negative(
        "criteria placement_tolerance_mm", criteria.get("placement_tolerance_mm")
    )
    fraction = _require_positive(
        "criteria max_exposed_area_fraction",
        criteria.get("max_exposed_area_fraction"),
    )
    if fraction > 1.0:
        raise ValueError(
            "criteria max_exposed_area_fraction must not exceed one, got %r"
            % (fraction,)
        )
    if not _at_most(tolerance, criteria["min_overhang_mm"]):
        raise ValueError(
            "a placement tolerance larger than the minimum overhang makes the "
            "margin unmeasurable"
        )
    _require_count(
        "criteria max_chips_per_coverglass",
        criteria.get("max_chips_per_coverglass"),
    )
    return criteria


def edge_overhangs_mm(cell, coverglass, offset_x_mm=0.0, offset_y_mm=0.0):
    """Signed glass overhang on each cell edge, offset taken off it.

    A positive overhang is glass standing proud of the cell edge. A
    negative one is bare cell: the glass edge has come inside the cell
    outline and the surface under that strip is uncovered.
    """
    cell_length = _require_positive("cell length_mm", cell.get("length_mm"))
    cell_width = _require_positive("cell width_mm", cell.get("width_mm"))
    glass_length = _require_positive(
        "coverglass length_mm", coverglass.get("length_mm")
    )
    glass_width = _require_positive(
        "coverglass width_mm", coverglass.get("width_mm")
    )
    offset_x = _require_finite("offset_x_mm", offset_x_mm)
    offset_y = _require_finite("offset_y_mm", offset_y_mm)
    base_x = 0.5 * (glass_length - cell_length)
    base_y = 0.5 * (glass_width - cell_width)
    return {
        "x-minus": base_x - offset_x,
        "x-plus": base_x + offset_x,
        "y-minus": base_y - offset_y,
        "y-plus": base_y + offset_y,
    }


def covered_area_mm2(cell, overhangs):
    """Bare cell area the glass outline actually sits over."""
    cell_length = _require_positive("cell length_mm", cell.get("length_mm"))
    cell_width = _require_positive("cell width_mm", cell.get("width_mm"))
    covered_length = (
        cell_length
        - _shortfall(overhangs["x-minus"])
        - _shortfall(overhangs["x-plus"])
    )
    covered_width = (
        cell_width
        - _shortfall(overhangs["y-minus"])
        - _shortfall(overhangs["y-plus"])
    )
    if covered_length <= 0.0 or covered_width <= 0.0:
        return 0.0
    return covered_length * covered_width


def glass_is_undersized(cell, coverglass):
    """Whether no placement at all could cover the cell.

    A glass shorter than the cell on an axis runs short on that axis
    whatever the offset does, so the finding is the wrong part rather
    than a wrong placement and no re-lay recovers it.
    """
    short_axes = []
    if not _at_least(
        _require_positive("coverglass length_mm", coverglass.get("length_mm")),
        _require_positive("cell length_mm", cell.get("length_mm")),
    ):
        short_axes.append("x")
    if not _at_least(
        _require_positive("coverglass width_mm", coverglass.get("width_mm")),
        _require_positive("cell width_mm", cell.get("width_mm")),
    ):
        short_axes.append("y")
    return short_axes


def assess_edge_chip(chip, overhangs, coverglass, criteria=DEFAULT_COVERAGE_CRITERIA):
    """Read one coverglass edge chip through the overhang it consumed."""
    validate_coverage_criteria(criteria)
    if not isinstance(chip, dict):
        raise ValueError("chip must be a mapping, got %r" % (chip,))
    edge = _require_choice("edge", chip.get("edge"), COVERGLASS_EDGES)
    ingress = _require_positive("ingress_mm", chip.get("ingress_mm"))
    length = _require_positive("length_mm", chip.get("length_mm"))
    span = (
        _require_positive("coverglass width_mm", coverglass.get("width_mm"))
        if edge in _X_EDGES
        else _require_positive("coverglass length_mm", coverglass.get("length_mm"))
    )
    if not _at_most(length, span):
        raise ValueError(
            "chip %r runs %.3f mm along a %.3f mm glass edge"
            % (chip.get("id"), length, span)
        )

    overhang = overhangs[edge]
    remaining = overhang - ingress
    placement_strip = _shortfall(overhang) * length
    total_strip = _shortfall(remaining) * length
    exposed = total_strip - placement_strip
    if exposed < 0.0:
        exposed = 0.0

    reasons = []
    if exposed > 0.0:
        disposition = REWORK
        reasons.append(
            "the chip has eaten %.3f mm into a %.3f mm overhang and leaves "
            "%.4f mm2 of bare cell under the glass edge"
            % (ingress, overhang, exposed)
        )
    elif not _at_least(remaining, criteria["min_overhang_mm"]):
        disposition = REFER
        reasons.append(
            "the cell is still covered, but the chip leaves only %.3f mm of "
            "overhang against a %.3f mm minimum"
            % (remaining, criteria["min_overhang_mm"])
        )
    else:
        disposition = ACCEPT

    return {
        "id": chip.get("id"),
        "edge": edge,
        "ingress_mm": ingress,
        "remaining_overhang_mm": remaining,
        "exposed_area_mm2": exposed,
        "exposes_bare_cell": exposed > 0.0,
        "disposition": disposition,
        "reasons": reasons,
    }


def assess_coverglass(record, criteria=DEFAULT_COVERAGE_CRITERIA):
    """Judge the coverage one coverglass gives the cell under it."""
    validate_coverage_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    item_id = record.get("coverglass_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("each coverglass record needs a non-empty coverglass_id")
    cell = record.get("cell")
    coverglass = record.get("coverglass")
    if not isinstance(cell, dict) or not isinstance(coverglass, dict):
        raise ValueError(
            "record %s needs a cell mapping and a coverglass mapping" % (item_id,)
        )
    offset_x = _require_finite("offset_x_mm", record.get("offset_x_mm", 0.0))
    offset_y = _require_finite("offset_y_mm", record.get("offset_y_mm", 0.0))

    overhangs = edge_overhangs_mm(cell, coverglass, offset_x, offset_y)
    cell_area = cell["length_mm"] * cell["width_mm"]
    covered = covered_area_mm2(cell, overhangs)
    placement_exposed = cell_area - covered
    short_axes = glass_is_undersized(cell, coverglass)

    chips = record.get("edge_chips", [])
    if not isinstance(chips, (list, tuple)):
        raise ValueError("edge_chips must be a list, got %r" % (chips,))
    seen = set()
    assessed = []
    for chip in chips:
        result = assess_edge_chip(chip, overhangs, coverglass, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate chip id %r on coverglass %s" % (marker, item_id)
                )
            seen.add(marker)
        assessed.append(result)

    chip_exposed = sum(result["exposed_area_mm2"] for result in assessed)
    exposed = placement_exposed + chip_exposed
    if not _at_most(exposed, cell_area):
        exposed = cell_area
    exposed_fraction = exposed / cell_area

    calls = [result["disposition"] for result in assessed]
    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    short_edges = [
        edge for edge in COVERGLASS_EDGES if _shortfall(overhangs[edge]) > 0.0
    ]
    indeterminate_edges = [
        edge
        for edge in COVERGLASS_EDGES
        if not _at_least(overhangs[edge], 0.0)
        and _at_most(_shortfall(overhangs[edge]), criteria["placement_tolerance_mm"])
    ]
    thin_edges = [
        edge
        for edge in COVERGLASS_EDGES
        if _at_least(overhangs[edge], 0.0)
        and not _at_least(overhangs[edge], criteria["min_overhang_mm"])
    ]

    if short_axes:
        calls.append(REJECT)
        findings.append(
            "the glass is shorter than the cell on %s, so no placement covers "
            "the bare surface and a re-lay cannot recover it"
            % (" and ".join(short_axes),)
        )
    elif short_edges and not set(short_edges) <= set(indeterminate_edges):
        disposition = REWORK
        if not _at_most(exposed_fraction, criteria["max_exposed_area_fraction"]):
            disposition = REJECT
        calls.append(disposition)
        findings.append(
            "%s left short by the placement; %.4f mm2 of bare cell is uncovered, "
            "%.5f of the cell" % (", ".join(short_edges), exposed, exposed_fraction)
        )
    elif indeterminate_edges:
        calls.append(REFER)
        findings.append(
            "%s sits under the cell outline by less than the %.3f mm placement "
            "tolerance, so the record cannot say whether the cell is covered"
            % (", ".join(indeterminate_edges), criteria["placement_tolerance_mm"])
        )

    if thin_edges:
        calls.append(REFER)
        findings.append(
            "%s carries less than the %.3f mm minimum overhang; the cell is "
            "covered with no margin against the next handling step"
            % (", ".join(thin_edges), criteria["min_overhang_mm"])
        )

    if len(assessed) > criteria["max_chips_per_coverglass"]:
        calls.append(REFER)
        findings.append(
            "%d edge chips against %d allowed on one glass"
            % (len(assessed), criteria["max_chips_per_coverglass"])
        )

    verdict = _worst(calls) if calls else ACCEPT
    return {
        "coverglass_id": item_id,
        "verdict": verdict,
        "overhangs_mm": overhangs,
        "min_overhang_mm": min(overhangs[edge] for edge in COVERGLASS_EDGES),
        "covered_area_mm2": covered,
        "cell_area_mm2": cell_area,
        "exposed_area_mm2": exposed,
        "exposed_area_fraction": exposed_fraction,
        "completely_covered": exposed == 0.0 and not indeterminate_edges,
        "coverage_indeterminate": bool(indeterminate_edges)
        and not short_axes
        and set(short_edges) <= set(indeterminate_edges)
        and chip_exposed == 0.0,
        "undersized_axes": short_axes,
        "short_edges": short_edges,
        "thin_edges": thin_edges,
        "edge_chips": assessed,
        "findings": findings,
    }


def inspect_assembly_coverage(assembly, criteria=DEFAULT_COVERAGE_CRITERIA):
    """Clause 6.4.3.1.5 coverage screen over every coverglass on the assembly."""
    validate_coverage_criteria(criteria)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = assembly.get("assembly_id")
    if not isinstance(assembly_id, str) or not assembly_id.strip():
        raise ValueError("assembly needs a non-empty assembly_id")
    declared = assembly.get("declared_coverglass_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_coverglass_count must be a positive integer, got %r"
            % (declared,)
        )
    records = assembly.get("coverglasses")
    if not isinstance(records, (list, tuple)):
        raise ValueError("coverglasses must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d coverglass records against a declared count of %d on %s"
            % (len(records), declared, assembly_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_coverglass(record, criteria)
        marker = result["coverglass_id"]
        if marker in seen:
            raise ValueError(
                "duplicate coverglass id %r on assembly %s" % (marker, assembly_id)
            )
        seen.add(marker)
        screened.append(result)

    findings = []
    counts = dict((state, 0) for state in COVERAGE_DISPOSITIONS)
    for result in screened:
        counts[result["verdict"]] += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["coverglass_id"], finding))

    total_cell_area = sum(result["cell_area_mm2"] for result in screened)
    total_exposed = sum(result["exposed_area_mm2"] for result in screened)
    exposed_fraction = (
        total_exposed / total_cell_area if total_cell_area > 0.0 else 0.0
    )

    missing = declared - len(screened)
    verdict = _worst([result["verdict"] for result in screened])
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d declared coverglasses carry no record; an unexamined "
            "glass is not a covered cell" % (missing, declared)
        )

    return {
        "assembly_id": assembly_id,
        "verdict": verdict,
        "inspection_complete": complete,
        "missing_record_count": missing,
        "screened_count": len(screened),
        "bare_cell_exposed_mm2": total_exposed,
        "bare_cell_exposed_fraction": exposed_fraction,
        "every_cell_completely_covered": complete
        and all(result["completely_covered"] for result in screened),
        "disposition_counts": counts,
        "exposed_ids": [
            result["coverglass_id"]
            for result in screened
            if not result["completely_covered"]
        ],
        "not_accepted_ids": [
            result["coverglass_id"]
            for result in screened
            if result["verdict"] != ACCEPT
        ],
        "coverglasses": screened,
        "findings": findings,
    }
