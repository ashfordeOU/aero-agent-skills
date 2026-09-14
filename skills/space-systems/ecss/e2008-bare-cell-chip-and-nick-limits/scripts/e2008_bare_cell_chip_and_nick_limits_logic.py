#!/usr/bin/env python3
"""Chip and surface nick limits for a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare cell arrives with material missing from its perimeter and marks on
its face, and the clause bounds both by position as well as by size. The
two questions the geometry answers are:

    where    does the missing material start at a corner or along an
             edge, and how far does it reach in toward the junction
    how big  how far does it run along the edge, how deep does a face
             nick go into the wafer thickness, and how much of the
             perimeter and of the cell face has gone once every accepted
             defect is added up

Position is decided first because it changes the limit, not just the
verdict. A chip that includes a corner has the diagonal of the inactive
border to work through before it opens the junction, which is longer than
the straight-in reach an edge chip has; the same lost millimetre is
therefore benign at a corner and marginal mid-edge. The reach limits below
are derived from the declared inactive border rather than typed in as
absolutes, so a cell drawn with a narrower border tightens its own limits.

A face nick is a different failure. It is graded on depth against the
wafer thickness, because a nick that runs an appreciable fraction into a
brittle wafer is a fracture origin under launch and thermal load, and on
its clearance from the contacts, because material lost under a busbar
edge undercuts the contact the interconnect will later be welded to.

Dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LENGTH_EDGE_A = "length-edge-a"
LENGTH_EDGE_B = "length-edge-b"
WIDTH_EDGE_A = "width-edge-a"
WIDTH_EDGE_B = "width-edge-b"
CELL_EDGES = (LENGTH_EDGE_A, LENGTH_EDGE_B, WIDTH_EDGE_A, WIDTH_EDGE_B)

EDGE_CHIP = "edge-chip"
CORNER_CHIP = "corner-chip"

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
CHIP_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

CELL_ACCEPTED = "bare-cell-edges-accepted"
CELL_REFERRED = "bare-cell-edges-referred"
CELL_REJECTED = "bare-cell-edges-rejected"

_ROLLUP_BY_SEVERITY = {ACCEPT: CELL_ACCEPTED, REFER: CELL_REFERRED, REJECT: CELL_REJECTED}

DEFAULT_CHIP_CRITERIA = {
    # reach toward the junction, as a share of the available border
    "edge_chip_reach_fraction": 0.5,
    "corner_chip_reach_fraction": 0.5,
    # run along an edge, as a share of that edge's own length
    "edge_chip_run_fraction": 0.05,
    "edge_chip_run_review_factor": 2.0,
    "max_corner_leg_mm": 2.0,
    "corner_leg_review_factor": 1.5,
    # face nicks
    "nick_depth_fraction_of_thickness": 0.10,
    "nick_depth_review_factor": 2.0,
    "max_nick_diameter_mm": 0.6,
    "min_nick_clearance_mm": 0.3,
    # accumulation over the whole cell
    "max_cumulative_chip_perimeter_fraction": 0.04,
    "max_cumulative_chip_area_fraction": 0.005,
    "max_chips_per_edge": 2,
    "max_nicks_per_cell": 4,
    "min_chip_separation_mm": 1.0,
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


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every limit here is a product of a criteria fraction and a measured
    dimension, so a measurement sitting exactly on the limit can evaluate
    a few units in the last place above it. The limit is never raised;
    only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_chip_criteria(criteria):
    """Check a chip and nick criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in (
        "max_corner_leg_mm",
        "max_nick_diameter_mm",
        "max_cumulative_chip_perimeter_fraction",
        "max_cumulative_chip_area_fraction",
    ):
        _require_positive("criteria %s" % key, criteria.get(key))
    for key in ("min_nick_clearance_mm", "min_chip_separation_mm"):
        _require_non_negative("criteria %s" % key, criteria.get(key))
    for key in (
        "edge_chip_reach_fraction",
        "corner_chip_reach_fraction",
        "edge_chip_run_fraction",
        "nick_depth_fraction_of_thickness",
    ):
        fraction = _require_positive("criteria %s" % key, criteria.get(key))
        if fraction > 1.0:
            raise ValueError(
                "criteria %s is a share of a measured dimension and cannot "
                "exceed one, got %r" % (key, fraction)
            )
    for key in (
        "edge_chip_run_review_factor",
        "corner_leg_review_factor",
        "nick_depth_review_factor",
    ):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one; a review band cannot be "
                "tighter than the accept band, got %r" % (key, factor)
            )
    _require_count("criteria max_chips_per_edge", criteria.get("max_chips_per_edge"))
    _require_count("criteria max_nicks_per_cell", criteria.get("max_nicks_per_cell"))
    return criteria


def validate_cell_geometry(geometry):
    """Check the cell outline the chip limits are derived from."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    length = _require_positive("length_mm", geometry.get("length_mm"))
    width = _require_positive("width_mm", geometry.get("width_mm"))
    thickness = _require_positive("thickness_um", geometry.get("thickness_um"))
    border = _require_positive(
        "inactive_border_mm", geometry.get("inactive_border_mm")
    )
    if 2.0 * border >= min(length, width):
        raise ValueError(
            "an inactive border of %.3f mm leaves no active area on a "
            "%.3f by %.3f mm cell" % (border, length, width)
        )
    return {
        "length_mm": length,
        "width_mm": width,
        "thickness_um": thickness,
        "inactive_border_mm": border,
        "perimeter_mm": 2.0 * (length + width),
        "cell_area_mm2": length * width,
        "active_area_mm2": (length - 2.0 * border) * (width - 2.0 * border),
    }


def edge_length_mm(edge, geometry):
    """Length of one named edge of the cell outline."""
    _require_choice("edge", edge, CELL_EDGES)
    resolved = validate_cell_geometry(geometry)
    if edge in (LENGTH_EDGE_A, LENGTH_EDGE_B):
        return resolved["length_mm"]
    return resolved["width_mm"]


def locate_chip(chip, geometry):
    """Place one chip on the outline and derive the reach it has to spend.

    The chip occupies the span from position_mm to position_mm + run_mm
    along its edge. A span that touches either end of the edge includes a
    corner, and a corner chip has the diagonal of the inactive border to
    work through before it reaches the junction rather than the straight
    border width an edge chip has.
    """
    if not isinstance(chip, dict):
        raise ValueError("chip must be a mapping, got %r" % (chip,))
    resolved = validate_cell_geometry(geometry)
    edge = _require_choice("edge", chip.get("edge"), CELL_EDGES)
    span = edge_length_mm(edge, geometry)
    position = _require_non_negative("position_mm", chip.get("position_mm"))
    run = _require_positive("run_mm", chip.get("run_mm"))
    if not _at_most(position + run, span):
        raise ValueError(
            "a chip from %.3f mm running %.3f mm does not fit on a %.3f mm edge"
            % (position, run, span)
        )
    gap_start = position
    gap_end = span - (position + run)
    at_corner = _at_most(gap_start, 0.0) or _at_most(gap_end, 0.0)
    border = resolved["inactive_border_mm"]
    return {
        "edge": edge,
        "edge_length_mm": span,
        "zone": CORNER_CHIP if at_corner else EDGE_CHIP,
        "distance_to_corner_mm": min(gap_start, gap_end),
        "available_reach_mm": border * math.sqrt(2.0) if at_corner else border,
    }


def assess_chip(chip, geometry, criteria=DEFAULT_CHIP_CRITERIA):
    """Disposition one perimeter chip against the criteria set."""
    validate_chip_criteria(criteria)
    placement = locate_chip(chip, geometry)
    reach = _require_positive("reach_mm", chip.get("reach_mm"))
    run = float(chip.get("run_mm"))
    available = placement["available_reach_mm"]
    corner = placement["zone"] == CORNER_CHIP

    reasons = []
    dispositions = []

    fraction = (
        criteria["corner_chip_reach_fraction"]
        if corner
        else criteria["edge_chip_reach_fraction"]
    )
    allowed_reach = available * fraction
    if _at_most(reach, allowed_reach):
        dispositions.append(ACCEPT)
    elif _at_most(reach, available):
        dispositions.append(REFER)
        reasons.append(
            "reaches %.3f mm into the %.3f mm the border offers here, past the "
            "%.3f mm allowance" % (reach, available, allowed_reach)
        )
    else:
        dispositions.append(REJECT)
        reasons.append(
            "reaches %.3f mm, past the %.3f mm of border, so the junction is "
            "open at this edge" % (reach, available)
        )

    if corner:
        adjacent = _require_non_negative(
            "adjacent_run_mm", chip.get("adjacent_run_mm", 0.0)
        )
        longest_leg = max(run, adjacent)
        limit = criteria["max_corner_leg_mm"]
        review_limit = limit * criteria["corner_leg_review_factor"]
        if _at_most(longest_leg, limit):
            dispositions.append(ACCEPT)
        elif _at_most(longest_leg, review_limit):
            dispositions.append(REFER)
            reasons.append(
                "corner leg %.3f mm exceeds the %.3f mm limit" % (longest_leg, limit)
            )
        else:
            dispositions.append(REJECT)
            reasons.append(
                "corner leg %.3f mm exceeds the %.3f mm review limit"
                % (longest_leg, review_limit)
            )
        area = 0.5 * run * adjacent if adjacent > 0.0 else 0.5 * run * reach
        perimeter_loss = run + adjacent
    else:
        limit = placement["edge_length_mm"] * criteria["edge_chip_run_fraction"]
        review_limit = limit * criteria["edge_chip_run_review_factor"]
        if _at_most(run, limit):
            dispositions.append(ACCEPT)
        elif _at_most(run, review_limit):
            dispositions.append(REFER)
            reasons.append(
                "runs %.3f mm along a %.3f mm edge, past the %.3f mm allowance"
                % (run, placement["edge_length_mm"], limit)
            )
        else:
            dispositions.append(REJECT)
            reasons.append(
                "runs %.3f mm along a %.3f mm edge, past the %.3f mm review limit"
                % (run, placement["edge_length_mm"], review_limit)
            )
        area = 0.5 * run * reach
        perimeter_loss = run

    return {
        "id": chip.get("id"),
        "edge": placement["edge"],
        "zone": placement["zone"],
        "reach_mm": reach,
        "run_mm": run,
        "available_reach_mm": available,
        "distance_to_corner_mm": placement["distance_to_corner_mm"],
        "chip_area_mm2": area,
        "perimeter_loss_mm": perimeter_loss,
        "disposition": _worst(dispositions),
        "reasons": reasons,
    }


def assess_nick(nick, geometry, criteria=DEFAULT_CHIP_CRITERIA):
    """Disposition one face nick against depth and contact clearance."""
    validate_chip_criteria(criteria)
    resolved = validate_cell_geometry(geometry)
    if not isinstance(nick, dict):
        raise ValueError("nick must be a mapping, got %r" % (nick,))
    depth = _require_positive("depth_um", nick.get("depth_um"))
    diameter = _require_positive("diameter_mm", nick.get("diameter_mm"))
    clearance = _require_non_negative(
        "contact_clearance_mm", nick.get("contact_clearance_mm")
    )
    thickness = resolved["thickness_um"]
    if not _at_most(depth, thickness):
        raise ValueError(
            "a nick %.1f um deep cannot sit in a %.1f um cell; it is a hole"
            % (depth, thickness)
        )

    reasons = []
    dispositions = []
    depth_fraction = depth / thickness
    limit = criteria["nick_depth_fraction_of_thickness"]
    review_limit = limit * criteria["nick_depth_review_factor"]
    if _at_most(depth_fraction, limit):
        dispositions.append(ACCEPT)
    elif _at_most(depth_fraction, review_limit):
        dispositions.append(REFER)
        reasons.append(
            "depth is %.4f of the wafer thickness, past the %.4f allowance"
            % (depth_fraction, limit)
        )
    else:
        dispositions.append(REJECT)
        reasons.append(
            "depth is %.4f of the wafer thickness; a nick that deep is a "
            "fracture origin under launch and thermal load" % (depth_fraction,)
        )

    if _at_most(diameter, criteria["max_nick_diameter_mm"]):
        dispositions.append(ACCEPT)
    else:
        dispositions.append(REFER)
        reasons.append(
            "diameter %.3f mm exceeds the %.3f mm limit"
            % (diameter, criteria["max_nick_diameter_mm"])
        )

    if _at_most(criteria["min_nick_clearance_mm"], clearance):
        dispositions.append(ACCEPT)
    else:
        dispositions.append(REJECT)
        reasons.append(
            "sits %.3f mm from a contact, inside the %.3f mm clearance, so it "
            "undercuts the pad the interconnect is attached to"
            % (clearance, criteria["min_nick_clearance_mm"])
        )

    return {
        "id": nick.get("id"),
        "depth_um": depth,
        "depth_fraction_of_thickness": depth_fraction,
        "diameter_mm": diameter,
        "contact_clearance_mm": clearance,
        "nick_area_mm2": math.pi * (diameter / 2.0) ** 2,
        "disposition": _worst(dispositions),
        "reasons": reasons,
    }


def _chip_clusters(chips, criteria):
    """Chips on one edge sitting closer together than the separation rule."""
    by_edge = {}
    for chip in chips:
        by_edge.setdefault(chip["edge"], []).append(chip)
    clustered = []
    separation = criteria["min_chip_separation_mm"]
    for edge, group in sorted(by_edge.items()):
        ordered = sorted(group, key=lambda item: item["position_mm"])
        for first, second in zip(ordered, ordered[1:]):
            gap = second["position_mm"] - (first["position_mm"] + first["run_mm"])
            if gap < separation and not math.isclose(
                gap, separation, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
            ):
                clustered.append((edge, first.get("id"), second.get("id"), gap))
    return clustered


def assess_bare_cell_edges(cell, criteria=DEFAULT_CHIP_CRITERIA):
    """Clause 7.5.1.4.1 screen of every chip and nick on one bare cell."""
    validate_chip_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("each cell needs a non-empty cell_id")
    geometry = validate_cell_geometry(cell.get("geometry"))
    chips = cell.get("chips", [])
    nicks = cell.get("nicks", [])
    if not isinstance(chips, (list, tuple)) or not isinstance(nicks, (list, tuple)):
        raise ValueError("chips and nicks must both be lists")

    seen = set()
    assessed_chips = []
    for chip in chips:
        result = assess_chip(chip, cell.get("geometry"), criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError("duplicate defect id %r on cell %s" % (marker, cell_id))
            seen.add(marker)
        assessed_chips.append(result)

    assessed_nicks = []
    for nick in nicks:
        result = assess_nick(nick, cell.get("geometry"), criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError("duplicate defect id %r on cell %s" % (marker, cell_id))
            seen.add(marker)
        assessed_nicks.append(result)

    findings = []
    for result in assessed_chips + assessed_nicks:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst(
        [result["disposition"] for result in assessed_chips + assessed_nicks]
    )

    perimeter_loss = sum(result["perimeter_loss_mm"] for result in assessed_chips)
    perimeter_fraction = perimeter_loss / geometry["perimeter_mm"]
    chip_area = sum(result["chip_area_mm2"] for result in assessed_chips)
    area_fraction = chip_area / geometry["cell_area_mm2"]

    if not _at_most(
        perimeter_fraction, criteria["max_cumulative_chip_perimeter_fraction"]
    ):
        verdict = _worst((verdict, REFER))
        findings.append(
            "chips take %.4f of the perimeter, past the %.4f allowance, even "
            "though no single chip did"
            % (perimeter_fraction, criteria["max_cumulative_chip_perimeter_fraction"])
        )
    if not _at_most(area_fraction, criteria["max_cumulative_chip_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "chips take %.5f of the cell face, past the %.5f allowance"
            % (area_fraction, criteria["max_cumulative_chip_area_fraction"])
        )

    per_edge = {}
    for result in assessed_chips:
        per_edge[result["edge"]] = per_edge.get(result["edge"], 0) + 1
    for edge in sorted(per_edge):
        if per_edge[edge] > criteria["max_chips_per_edge"]:
            verdict = _worst((verdict, REFER))
            findings.append(
                "%d chips on %s exceed the %d allowed on one edge"
                % (per_edge[edge], edge, criteria["max_chips_per_edge"])
            )
    if len(assessed_nicks) > criteria["max_nicks_per_cell"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d nicks exceed the %d allowed on one cell"
            % (len(assessed_nicks), criteria["max_nicks_per_cell"])
        )

    clusters = _chip_clusters([dict(chip) for chip in chips], criteria)
    for edge, first, second, gap in clusters:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%s and %s sit %.3f mm apart on %s, inside the %.3f mm separation; "
            "the ligament between two chips is weaker than either chip"
            % (first, second, gap, edge, criteria["min_chip_separation_mm"])
        )

    return {
        "cell_id": cell_id,
        "verdict": _ROLLUP_BY_SEVERITY[verdict],
        "disposition": verdict,
        "chips": assessed_chips,
        "nicks": assessed_nicks,
        "corner_chip_count": sum(
            1 for result in assessed_chips if result["zone"] == CORNER_CHIP
        ),
        "chips_per_edge": per_edge,
        "perimeter_loss_mm": perimeter_loss,
        "perimeter_loss_fraction": perimeter_fraction,
        "chip_area_mm2": chip_area,
        "chip_area_fraction": area_fraction,
        "clustered_chip_pairs": len(clusters),
        "not_accepted_ids": [
            result["id"]
            for result in assessed_chips + assessed_nicks
            if result["disposition"] != ACCEPT
        ],
        "findings": findings,
    }
