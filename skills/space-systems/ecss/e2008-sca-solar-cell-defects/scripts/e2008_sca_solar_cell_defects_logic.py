#!/usr/bin/env python3
"""Chips and nicks on a solar cell body: permitted position and size.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause governs where a chip or a nick is allowed to sit on the cell
body and how large it is allowed to be. Both halves matter and they are
not the same question. Position is decided against the inactive border
the cell carries between its physical edge and the start of its active
area: a chip that stays inside that border has taken nothing the cell
was generating with, and a chip that reaches past it has removed
generating area and may have severed a grid finger on the way. Size is
decided against the cell area, once per defect and again over the whole
cell, because many small chips are a handling problem even when each
one of them passes.

Nothing here is reworkable. Silicon cannot be put back, so the
dispositions are accept, refer-for-review and reject; a rework verdict
would be an invitation to do something the article does not allow.

Defect kinds
    edge-chip     material broken out of a cell edge
    corner-chip   material broken out of a corner, measured on the
                  diagonal, so its perpendicular reach into either
                  margin is the diagonal reach resolved back onto an
                  axis
    nick          a small notch in the edge, same geometry as a chip
                  and separated only so the record keeps the operator's
                  own word
    surface-chip  a flake off the face that is not connected to an
                  edge, declared by its stand-off from the nearest edge

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEFECT_KINDS = ("edge-chip", "corner-chip", "nick", "surface-chip")
CELL_EDGES = ("x-minus", "x-plus", "y-minus", "y-plus")

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
CELL_DISPOSITIONS = (ACCEPT, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

_EDGE_KINDS = ("edge-chip", "corner-chip", "nick")

REQUIRED_DEFECT_FIELDS = {
    "edge-chip": ("edge", "ingress_mm", "length_mm", "depth_fraction"),
    "corner-chip": ("edge", "ingress_mm", "length_mm", "depth_fraction"),
    "nick": ("edge", "ingress_mm", "length_mm", "depth_fraction"),
    "surface-chip": (
        "edge",
        "stand_off_mm",
        "inward_extent_mm",
        "length_mm",
        "depth_fraction",
    ),
}

# A broken-out chip is a rough conchoidal scallop rather than a
# rectangle, so its planar footprint is taken at half of the bounding
# box. A surface flake is lifted over its whole outline and takes the
# full box.
_FOOTPRINT_SHAPE = {
    "edge-chip": 0.5,
    "corner-chip": 0.5,
    "nick": 0.5,
    "surface-chip": 1.0,
}

DEFAULT_CELL_BODY_CRITERIA = {
    "max_ingress_fraction_of_margin": 0.5,
    "through_thickness_fraction": 0.9,
    "through_thickness_ingress_factor": 0.6,
    "max_defect_area_fraction": 0.002,
    "defect_review_factor": 2.0,
    "max_total_area_fraction": 0.005,
    "max_defects_per_edge": 2,
    "corner_area_factor": 0.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_CORNER_RESOLVE = 1.0 / math.sqrt(2.0)


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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every limit in this module is a product of a criteria fraction and a
    measured dimension, and the corner reach is resolved through an
    irrational factor, so a measurement sitting exactly on a limit can
    evaluate a few units in the last place above it. The limit is never
    raised; only the comparison tolerates the representation error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing the same representation error."""
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_cell_body_criteria(criteria):
    """Check a cell body criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in (
        "max_ingress_fraction_of_margin",
        "through_thickness_fraction",
        "through_thickness_ingress_factor",
        "max_defect_area_fraction",
        "max_total_area_fraction",
        "corner_area_factor",
    ):
        value = _require_positive("criteria %s" % key, criteria.get(key))
        if value > 1.0:
            raise ValueError(
                "criteria %s is a fraction and must not exceed one, got %r"
                % (key, value)
            )
    factor = _require_positive(
        "criteria defect_review_factor", criteria.get("defect_review_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "criteria defect_review_factor must be at least one, got %r" % (factor,)
        )
    if criteria["max_defect_area_fraction"] > criteria["max_total_area_fraction"]:
        raise ValueError(
            "a single defect may not be allowed more area than the whole cell "
            "is allowed to lose"
        )
    _require_count(
        "criteria max_defects_per_edge", criteria.get("max_defects_per_edge")
    )
    return criteria


def cell_geometry(length_mm, width_mm, edge_margin_mm):
    """Derive the cell areas and the inactive border a defect may sit in."""
    length = _require_positive("length_mm", length_mm)
    width = _require_positive("width_mm", width_mm)
    margin = _require_positive("edge_margin_mm", edge_margin_mm)
    if not 2.0 * margin < min(length, width):
        raise ValueError(
            "an edge margin of %.3f mm leaves no active area on a %.3f by "
            "%.3f mm cell" % (margin, length, width)
        )
    active_length = length - 2.0 * margin
    active_width = width - 2.0 * margin
    return {
        "length_mm": length,
        "width_mm": width,
        "edge_margin_mm": margin,
        "cell_area_mm2": length * width,
        "active_area_mm2": active_length * active_width,
    }


def defect_reach_mm(defect):
    """How far the defect has come in from the cell edge, perpendicular.

    An edge chip and a nick are measured straight in, so the recorded
    ingress is already the perpendicular reach. A corner chip is
    measured on the diagonal, and the diagonal resolved onto either axis
    is shorter, which is why a corner tolerates a longer measurement
    before it touches the active border. A surface flake is not
    connected to an edge at all: its reach is the far side of the flake,
    the stand-off plus the inward extent.
    """
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    kind = _require_choice("kind", defect.get("kind"), DEFECT_KINDS)
    if kind == "surface-chip":
        stand_off = _require_non_negative("stand_off_mm", defect.get("stand_off_mm"))
        extent = _require_positive(
            "inward_extent_mm", defect.get("inward_extent_mm")
        )
        return stand_off + extent
    ingress = _require_positive("ingress_mm", defect.get("ingress_mm"))
    if kind == "corner-chip":
        return ingress * _CORNER_RESOLVE
    return ingress


def defect_footprint_mm2(defect):
    """Planar area the defect has taken out of the cell body."""
    kind = _require_choice("kind", defect.get("kind"), DEFECT_KINDS)
    length = _require_positive("length_mm", defect.get("length_mm"))
    if kind == "surface-chip":
        extent = _require_positive(
            "inward_extent_mm", defect.get("inward_extent_mm")
        )
        return length * extent * _FOOTPRINT_SHAPE[kind]
    ingress = _require_positive("ingress_mm", defect.get("ingress_mm"))
    return length * ingress * _FOOTPRINT_SHAPE[kind]


def permitted_reach_mm(defect, geometry, criteria=DEFAULT_CELL_BODY_CRITERIA):
    """How far into the inactive border this defect is allowed to come.

    The allowance is a fraction of the border, tightened when the break
    goes the whole way through the wafer: a through-thickness chip is a
    crack starter under thermal cycling, not simply a deeper scallop.
    """
    validate_cell_body_criteria(criteria)
    margin = geometry["edge_margin_mm"]
    allowance = margin * criteria["max_ingress_fraction_of_margin"]
    if is_through_thickness(defect, criteria):
        allowance = allowance * criteria["through_thickness_ingress_factor"]
    return allowance


def is_through_thickness(defect, criteria=DEFAULT_CELL_BODY_CRITERIA):
    """Whether the break goes through enough of the wafer to count as through."""
    depth = _require_positive("depth_fraction", defect.get("depth_fraction"))
    if depth > 1.0 and not _close(depth, 1.0):
        raise ValueError(
            "depth_fraction is a fraction of the cell thickness and must not "
            "exceed one, got %r" % (depth,)
        )
    return _at_least(depth, criteria["through_thickness_fraction"])


def assess_cell_defect(defect, geometry, criteria=DEFAULT_CELL_BODY_CRITERIA):
    """Disposition one chip or nick on position first, then on size."""
    validate_cell_body_criteria(criteria)
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    kind = _require_choice("kind", defect.get("kind"), DEFECT_KINDS)
    for field in REQUIRED_DEFECT_FIELDS[kind]:
        if defect.get(field) is None:
            raise ValueError("a %s record needs %s" % (kind, field))
    edge = _require_choice("edge", defect.get("edge"), CELL_EDGES)
    length = _require_positive("length_mm", defect.get("length_mm"))

    margin = geometry["edge_margin_mm"]
    edge_span = (
        geometry["length_mm"] if edge in ("y-minus", "y-plus") else geometry["width_mm"]
    )
    if not _at_most(length, edge_span):
        raise ValueError(
            "defect %r runs %.3f mm along a %.3f mm edge"
            % (defect.get("id"), length, edge_span)
        )

    reach = defect_reach_mm(defect)
    half_span = 0.5 * min(geometry["length_mm"], geometry["width_mm"])
    if not _at_most(reach, half_span):
        raise ValueError(
            "defect %r reaches %.3f mm into a cell whose half span is %.3f mm; "
            "that is a fractured cell, not a chip"
            % (defect.get("id"), reach, half_span)
        )

    footprint = defect_footprint_mm2(defect)
    through = is_through_thickness(defect, criteria)
    allowed_reach = permitted_reach_mm(defect, geometry, criteria)

    accept_area = geometry["cell_area_mm2"] * criteria["max_defect_area_fraction"]
    if kind == "corner-chip":
        accept_area = accept_area * criteria["corner_area_factor"]
    review_area = accept_area * criteria["defect_review_factor"]

    encroachment_depth = 0.0
    if not _at_most(reach, margin):
        encroachment_depth = reach - margin
    if kind == "surface-chip":
        encroachment_depth = min(
            encroachment_depth, float(defect.get("inward_extent_mm"))
        )
    encroached_area = encroachment_depth * length * _FOOTPRINT_SHAPE[kind]

    calls = []
    reasons = []

    if encroachment_depth > 0.0:
        calls.append(REJECT)
        reasons.append(
            "the break reaches %.3f mm past the %.3f mm inactive border and has "
            "taken %.4f mm2 of active area with it; silicon cannot be put back"
            % (encroachment_depth, margin, encroached_area)
        )
    elif not _at_most(reach, allowed_reach):
        calls.append(REFER)
        reasons.append(
            "the break reaches %.3f mm into a border that allows %.3f mm; it is "
            "still clear of the active area, so the call is a review and not a "
            "scrap" % (reach, allowed_reach)
        )

    if not _at_most(footprint, review_area):
        calls.append(REJECT)
        reasons.append(
            "footprint %.4f mm2 is past the %.4f mm2 review limit"
            % (footprint, review_area)
        )
    elif not _at_most(footprint, accept_area):
        calls.append(REFER)
        reasons.append(
            "footprint %.4f mm2 exceeds the %.4f mm2 single-defect allowance"
            % (footprint, accept_area)
        )

    if through and kind in _EDGE_KINDS:
        reasons.append(
            "the break goes through the wafer, so the position allowance was "
            "tightened to %.3f mm before it was applied" % (allowed_reach,)
        )

    disposition = _worst(calls) if calls else ACCEPT
    return {
        "id": defect.get("id"),
        "kind": kind,
        "edge": edge,
        "reach_mm": reach,
        "permitted_reach_mm": allowed_reach,
        "footprint_mm2": footprint,
        "encroached_active_area_mm2": encroached_area,
        "reaches_active_area": encroachment_depth > 0.0,
        "through_thickness": through,
        "disposition": disposition,
        "reasons": reasons,
    }


def inspect_cell_body(cell, criteria=DEFAULT_CELL_BODY_CRITERIA):
    """Clause 6.4.3.1.4 chip and nick screen over one whole cell body."""
    validate_cell_body_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("cell needs a non-empty cell_id")
    geometry = cell_geometry(
        cell.get("length_mm"), cell.get("width_mm"), cell.get("edge_margin_mm")
    )

    examined = cell.get("examined_edges")
    if not isinstance(examined, (list, tuple)):
        raise ValueError("examined_edges must be a list, got %r" % (examined,))
    seen_edges = []
    for edge in examined:
        _require_choice("examined edge", edge, CELL_EDGES)
        if edge in seen_edges:
            raise ValueError("edge %r is listed twice as examined" % (edge,))
        seen_edges.append(edge)
    unexamined = [edge for edge in CELL_EDGES if edge not in seen_edges]

    defects = cell.get("defects", [])
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list, got %r" % (defects,))

    seen_ids = set()
    assessed = []
    per_edge = dict((edge, 0) for edge in CELL_EDGES)
    for defect in defects:
        result = assess_cell_defect(defect, geometry, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen_ids:
                raise ValueError(
                    "duplicate defect id %r on cell %s" % (marker, cell_id)
                )
            seen_ids.add(marker)
        if result["edge"] not in seen_edges:
            raise ValueError(
                "defect %r sits on edge %s, which the record says was never "
                "examined" % (marker, result["edge"])
            )
        per_edge[result["edge"]] += 1
        assessed.append(result)

    total_footprint = sum(result["footprint_mm2"] for result in assessed)
    if not _at_most(total_footprint, geometry["cell_area_mm2"]):
        raise ValueError(
            "recorded defects claim %.3f mm2 of a %.3f mm2 cell"
            % (total_footprint, geometry["cell_area_mm2"])
        )
    total_encroached = sum(
        result["encroached_active_area_mm2"] for result in assessed
    )
    area_fraction = total_footprint / geometry["cell_area_mm2"]
    active_loss_fraction = total_encroached / geometry["active_area_mm2"]

    findings = []
    counts = dict((state, 0) for state in CELL_DISPOSITIONS)
    for result in assessed:
        counts[result["disposition"]] += 1
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])
    if not _at_most(area_fraction, criteria["max_total_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "chips and nicks together take %.5f of the cell against a %.5f "
            "allowance, even though no single one did"
            % (area_fraction, criteria["max_total_area_fraction"])
        )
    crowded = [
        edge
        for edge in CELL_EDGES
        if per_edge[edge] > criteria["max_defects_per_edge"]
    ]
    for edge in crowded:
        verdict = _worst((verdict, REFER))
        findings.append(
            "edge %s carries %d breaks against %d allowed; that is a handling "
            "problem upstream of this cell"
            % (edge, per_edge[edge], criteria["max_defects_per_edge"])
        )

    complete = not unexamined
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of the four cell edges carry no record: %s"
            % (len(unexamined), ", ".join(unexamined))
        )

    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "inspection_complete": complete,
        "unexamined_edges": unexamined,
        "geometry": geometry,
        "defect_area_fraction": area_fraction,
        "active_area_loss_fraction": active_loss_fraction,
        "defects_per_edge": per_edge,
        "crowded_edges": crowded,
        "disposition_counts": counts,
        "reaching_active_area_ids": [
            result["id"] for result in assessed if result["reaches_active_area"]
        ],
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "defects": assessed,
        "findings": findings,
    }
