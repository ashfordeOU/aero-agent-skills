#!/usr/bin/env python3
"""Edge chip limits for a solar cell coverglass.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass arrives with material missing from one of its four edges, and
the clause bounds the measurement that matters optically: not how long the
chip runs along the edge it sits on, but how far it projects inward across
the face of the glass. A quarter of a millimetre is the ceiling.

Projection is the graded dimension because a chip that reaches in across
the face has taken cover off the cell underneath it. A coverglass is laid
over the cell with a small overhang, so the first fraction of a millimetre
of projection eats overhang and nothing else; past the overhang the chip is
standing over the illuminated aperture, where it shades the cell, exposes
the adhesive bond line to ultraviolet, and leaves the junction without the
radiation cover the glass exists to provide. The overhang is therefore read
from the declared geometry and used as the second, harder bound, so a glass
laid out with less overhang tightens its own limits without a table edit.

Run along the edge is bounded too, but separately and more loosely: it
decides how much of the sealing edge is now a stress raiser, not how much
cover is gone.

A chip whose span reaches either end of its edge takes a corner, and a
corner chip is not this clause's work. It is routed on rather than graded
here, because the corner allowance is written on the hypotenuse across the
corner and grading it as an edge chip would apply the wrong limit.

Dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LENGTH_EDGE_A = "length-edge-a"
LENGTH_EDGE_B = "length-edge-b"
WIDTH_EDGE_A = "width-edge-a"
WIDTH_EDGE_B = "width-edge-b"
COVERGLASS_EDGES = (LENGTH_EDGE_A, LENGTH_EDGE_B, WIDTH_EDGE_A, WIDTH_EDGE_B)

EDGE_CHIP = "coverglass-edge-chip"
CORNER_CHIP = "coverglass-corner-chip"

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
EDGE_CHIP_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

GLASS_ACCEPTED = "coverglass-edges-accepted"
GLASS_REFERRED = "coverglass-edges-referred"
GLASS_REJECTED = "coverglass-edges-rejected"

_ROLLUP_BY_SEVERITY = {
    ACCEPT: GLASS_ACCEPTED,
    REFER: GLASS_REFERRED,
    REJECT: GLASS_REJECTED,
}

CORNER_CLAUSE_ROUTE = "coverglass-corner-chip-clause"

DEFAULT_EDGE_CHIP_CRITERIA = {
    # the clause ceiling on how far a chip may project in across the face
    "max_face_projection_mm": 0.25,
    # run along the edge, as a share of that edge's own length
    "max_run_fraction_of_edge": 0.10,
    "run_review_factor": 2.0,
    # accumulation over the whole glass
    "max_chips_per_edge": 2,
    "max_chips_per_glass": 4,
    "max_cumulative_face_area_fraction": 0.002,
    "max_cumulative_run_fraction_of_perimeter": 0.03,
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

    Several limits here are a product of a criteria share and a measured
    dimension, so a measurement sitting exactly on the limit can evaluate a
    few units in the last place above it. The limit is never raised; only
    the comparison tolerates the representation error.
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


def validate_edge_chip_criteria(criteria):
    """Check an edge chip criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive(
        "criteria max_face_projection_mm", criteria.get("max_face_projection_mm")
    )
    _require_non_negative(
        "criteria min_chip_separation_mm", criteria.get("min_chip_separation_mm")
    )
    for key in (
        "max_run_fraction_of_edge",
        "max_cumulative_face_area_fraction",
        "max_cumulative_run_fraction_of_perimeter",
    ):
        fraction = _require_positive("criteria %s" % key, criteria.get(key))
        if fraction > 1.0:
            raise ValueError(
                "criteria %s is a share of a measured dimension and cannot "
                "exceed one, got %r" % (key, fraction)
            )
    factor = _require_positive(
        "criteria run_review_factor", criteria.get("run_review_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "criteria run_review_factor must be at least one; a review band "
            "cannot be tighter than the accept band, got %r" % (factor,)
        )
    _require_count("criteria max_chips_per_edge", criteria.get("max_chips_per_edge"))
    _require_count("criteria max_chips_per_glass", criteria.get("max_chips_per_glass"))
    return criteria


def validate_coverglass_geometry(geometry):
    """Check the coverglass outline the edge chip limits are read against."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    length = _require_positive("length_mm", geometry.get("length_mm"))
    width = _require_positive("width_mm", geometry.get("width_mm"))
    thickness = _require_positive("thickness_um", geometry.get("thickness_um"))
    overhang = _require_positive("overhang_mm", geometry.get("overhang_mm"))
    if 2.0 * overhang >= min(length, width):
        raise ValueError(
            "an overhang of %.3f mm leaves no illuminated aperture on a "
            "%.3f by %.3f mm coverglass" % (overhang, length, width)
        )
    return {
        "length_mm": length,
        "width_mm": width,
        "thickness_um": thickness,
        "overhang_mm": overhang,
        "perimeter_mm": 2.0 * (length + width),
        "face_area_mm2": length * width,
        "aperture_area_mm2": (length - 2.0 * overhang) * (width - 2.0 * overhang),
    }


def edge_length_mm(edge, geometry):
    """Length of one named edge of the coverglass outline."""
    _require_choice("edge", edge, COVERGLASS_EDGES)
    resolved = validate_coverglass_geometry(geometry)
    if edge in (LENGTH_EDGE_A, LENGTH_EDGE_B):
        return resolved["length_mm"]
    return resolved["width_mm"]


def locate_edge_chip(chip, geometry):
    """Place one chip on the outline and report what it is standing on.

    The chip occupies the span from position_mm to position_mm + run_mm
    along its edge. A span that touches either end of the edge takes a
    corner and belongs to the corner clause, whose allowance is written on
    the hypotenuse across the corner rather than on inward projection.
    """
    if not isinstance(chip, dict):
        raise ValueError("chip must be a mapping, got %r" % (chip,))
    resolved = validate_coverglass_geometry(geometry)
    edge = _require_choice("edge", chip.get("edge"), COVERGLASS_EDGES)
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
    return {
        "edge": edge,
        "edge_length_mm": span,
        "zone": CORNER_CHIP if at_corner else EDGE_CHIP,
        "distance_to_corner_mm": min(gap_start, gap_end),
        "overhang_mm": resolved["overhang_mm"],
    }


def face_area_lost_mm2(run_mm, projection_mm):
    """Face area a chip of this run and projection takes off the glass.

    The bite is treated as a triangle sitting on the edge: deepest at its
    middle, tapering to nothing where it meets undamaged glass. That is the
    shape a conchoidal chip actually leaves, and it keeps the accumulated
    area honest rather than doubling it with a rectangle.
    """
    run = _require_positive("run_mm", run_mm)
    projection = _require_positive("projection_mm", projection_mm)
    return 0.5 * run * projection


def aperture_encroachment_mm(projection_mm, geometry):
    """How far past the overhang a chip of this projection stands.

    Zero while the chip is still eating overhang; positive once it is over
    the illuminated aperture, where it shades the cell and leaves the bond
    line and the junction without cover.
    """
    projection = _require_positive("projection_mm", projection_mm)
    resolved = validate_coverglass_geometry(geometry)
    overhang = resolved["overhang_mm"]
    if _at_most(projection, overhang):
        return 0.0
    return projection - overhang


def assess_edge_chip(chip, geometry, criteria=DEFAULT_EDGE_CHIP_CRITERIA):
    """Disposition one coverglass edge chip against the criteria set."""
    validate_edge_chip_criteria(criteria)
    placement = locate_edge_chip(chip, geometry)
    projection = _require_positive(
        "face_projection_mm", chip.get("face_projection_mm")
    )
    run = float(chip.get("run_mm"))
    overhang = placement["overhang_mm"]
    encroachment = aperture_encroachment_mm(projection, geometry)

    reasons = []
    dispositions = []

    if placement["zone"] == CORNER_CHIP:
        dispositions.append(REFER)
        reasons.append(
            "the span reaches the end of %s, so this chip takes a corner and "
            "is graded on the hypotenuse across it, not on inward projection"
            % (placement["edge"],)
        )

    limit = criteria["max_face_projection_mm"]
    if _at_most(projection, limit):
        dispositions.append(ACCEPT)
    elif encroachment <= 0.0:
        dispositions.append(REFER)
        reasons.append(
            "projects %.3f mm in across the face, past the %.3f mm ceiling, "
            "though still inside the %.3f mm overhang"
            % (projection, limit, overhang)
        )
    else:
        dispositions.append(REJECT)
        reasons.append(
            "projects %.3f mm in across the face, %.3f mm past the %.3f mm "
            "overhang, so the chip now stands over the illuminated aperture"
            % (projection, encroachment, overhang)
        )

    run_limit = placement["edge_length_mm"] * criteria["max_run_fraction_of_edge"]
    run_review_limit = run_limit * criteria["run_review_factor"]
    if _at_most(run, run_limit):
        dispositions.append(ACCEPT)
    elif _at_most(run, run_review_limit):
        dispositions.append(REFER)
        reasons.append(
            "runs %.3f mm along a %.3f mm edge, past the %.3f mm allowance"
            % (run, placement["edge_length_mm"], run_limit)
        )
    else:
        dispositions.append(REJECT)
        reasons.append(
            "runs %.3f mm along a %.3f mm edge, past the %.3f mm review limit"
            % (run, placement["edge_length_mm"], run_review_limit)
        )

    return {
        "id": chip.get("id"),
        "edge": placement["edge"],
        "zone": placement["zone"],
        "face_projection_mm": projection,
        "run_mm": run,
        "projection_margin_mm": limit - projection,
        "aperture_encroachment_mm": encroachment,
        "distance_to_corner_mm": placement["distance_to_corner_mm"],
        "face_area_lost_mm2": face_area_lost_mm2(run, projection),
        "routed_to": CORNER_CLAUSE_ROUTE
        if placement["zone"] == CORNER_CHIP
        else None,
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


def assess_coverglass_edge_chips(glass, criteria=DEFAULT_EDGE_CHIP_CRITERIA):
    """Clause 8.7.1.3.4 screen of every edge chip on one coverglass."""
    validate_edge_chip_criteria(criteria)
    if not isinstance(glass, dict):
        raise ValueError("glass must be a mapping, got %r" % (glass,))
    glass_id = glass.get("coverglass_id")
    if not isinstance(glass_id, str) or not glass_id.strip():
        raise ValueError("each coverglass needs a non-empty coverglass_id")
    geometry = validate_coverglass_geometry(glass.get("geometry"))
    chips = glass.get("chips", [])
    if not isinstance(chips, (list, tuple)):
        raise ValueError("chips must be a list")

    seen = set()
    assessed = []
    for chip in chips:
        result = assess_edge_chip(chip, glass.get("geometry"), criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate chip id %r on coverglass %s" % (marker, glass_id)
                )
            seen.add(marker)
        assessed.append(result)

    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])

    face_area = sum(result["face_area_lost_mm2"] for result in assessed)
    area_fraction = face_area / geometry["face_area_mm2"]
    run_total = sum(result["run_mm"] for result in assessed)
    run_fraction = run_total / geometry["perimeter_mm"]

    if not _at_most(area_fraction, criteria["max_cumulative_face_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "edge chips take %.5f of the glass face, past the %.5f allowance, "
            "even though no single chip did"
            % (area_fraction, criteria["max_cumulative_face_area_fraction"])
        )
    if not _at_most(
        run_fraction, criteria["max_cumulative_run_fraction_of_perimeter"]
    ):
        verdict = _worst((verdict, REFER))
        findings.append(
            "edge chips take %.4f of the perimeter, past the %.4f allowance"
            % (run_fraction, criteria["max_cumulative_run_fraction_of_perimeter"])
        )

    per_edge = {}
    for result in assessed:
        per_edge[result["edge"]] = per_edge.get(result["edge"], 0) + 1
    for edge in sorted(per_edge):
        if per_edge[edge] > criteria["max_chips_per_edge"]:
            verdict = _worst((verdict, REFER))
            findings.append(
                "%d chips on %s exceed the %d allowed on one edge"
                % (per_edge[edge], edge, criteria["max_chips_per_edge"])
            )
    if len(assessed) > criteria["max_chips_per_glass"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d chips exceed the %d allowed on one coverglass"
            % (len(assessed), criteria["max_chips_per_glass"])
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
        "coverglass_id": glass_id,
        "verdict": _ROLLUP_BY_SEVERITY[verdict],
        "disposition": verdict,
        "chips": assessed,
        "chips_per_edge": per_edge,
        "deepest_projection_mm": max(
            (result["face_projection_mm"] for result in assessed), default=0.0
        ),
        "face_area_lost_mm2": face_area,
        "face_area_lost_fraction": area_fraction,
        "cumulative_run_mm": run_total,
        "cumulative_run_fraction": run_fraction,
        "clustered_chip_pairs": len(clusters),
        "routed_to_corner_clause": [
            result["id"] for result in assessed if result["routed_to"]
        ],
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "findings": findings,
    }
