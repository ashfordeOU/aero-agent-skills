#!/usr/bin/env python3
"""Corner chip limits for a solar cell coverglass.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A corner chip takes a triangle out of the corner of a coverglass. Two legs
run away from the corner along the two edges that meet there, and the chord
that closes them off is the hypotenuse. The clause is written on that
hypotenuse: three quarters of a millimetre is the ceiling.

The hypotenuse is the graded dimension because it is the one measurement
that does not change when the bite is lopsided. A leg along one edge says
nothing on its own; a chip taking a tenth of a millimetre off one edge and
seven tenths off the other is a gouge running along an edge, not a corner
bite, and its longest leg would fail a limit that the corner geometry never
intended to catch. The chord across the two legs bounds the whole bite in
one number, which is why the allowance is written on it.

The hypotenuse is derived from the two measured legs rather than taken on
trust. Where a hypotenuse was also measured directly it is cross-checked:
a value outside the triangle inequality is not a measurement of this chip
at all and is rejected as input, and a value inside it but disagreeing with
the legs is referred, because one of the two readings is wrong and no
disposition taken from either is worth anything until that is settled.

Reach is separate from size. The perpendicular from the corner to the chord
is how far the bite actually penetrates toward the cell, and at a corner
the glass has the diagonal of its overhang to give up before the chip is
standing over the illuminated aperture. That bound is derived from the
declared overhang, so a glass laid out with less of it tightens its own
corner limit without a table edit.

Dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CORNER_A = "corner-a"
CORNER_B = "corner-b"
CORNER_C = "corner-c"
CORNER_D = "corner-d"
COVERGLASS_CORNERS = (CORNER_A, CORNER_B, CORNER_C, CORNER_D)

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
CORNER_CHIP_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

GLASS_ACCEPTED = "coverglass-corners-accepted"
GLASS_REFERRED = "coverglass-corners-referred"
GLASS_REJECTED = "coverglass-corners-rejected"

_ROLLUP_BY_SEVERITY = {
    ACCEPT: GLASS_ACCEPTED,
    REFER: GLASS_REFERRED,
    REJECT: GLASS_REJECTED,
}

EDGE_CLAUSE_ROUTE = "coverglass-edge-chip-clause"

DEFAULT_CORNER_CHIP_CRITERIA = {
    # the clause ceiling on the chord across the corner
    "max_hypotenuse_mm": 0.75,
    "hypotenuse_review_factor": 1.2,
    # a bite this lopsided is an edge gouge wearing a corner's name
    "max_leg_ratio": 3.0,
    # agreement required between a measured chord and the one the legs give
    "max_hypotenuse_mismatch_fraction": 0.05,
    # accumulation over the whole glass
    "max_corners_affected": 2,
    "max_cumulative_corner_area_fraction": 0.0005,
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

    The chord is a square root of a sum of squares and several limits are a
    product of a criteria share and a measured dimension, so a chip sitting
    exactly on a limit can evaluate a few units in the last place above it.
    The limit is never raised; only the comparison tolerates the
    representation error.
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


def validate_corner_chip_criteria(criteria):
    """Check a corner chip criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive(
        "criteria max_hypotenuse_mm", criteria.get("max_hypotenuse_mm")
    )
    ratio = _require_positive("criteria max_leg_ratio", criteria.get("max_leg_ratio"))
    if ratio < 1.0:
        raise ValueError(
            "criteria max_leg_ratio compares the longer leg with the shorter "
            "and cannot be below one, got %r" % (ratio,)
        )
    for key in (
        "max_hypotenuse_mismatch_fraction",
        "max_cumulative_corner_area_fraction",
    ):
        fraction = _require_positive("criteria %s" % key, criteria.get(key))
        if fraction > 1.0:
            raise ValueError(
                "criteria %s is a share and cannot exceed one, got %r"
                % (key, fraction)
            )
    factor = _require_positive(
        "criteria hypotenuse_review_factor",
        criteria.get("hypotenuse_review_factor"),
    )
    if factor < 1.0:
        raise ValueError(
            "criteria hypotenuse_review_factor must be at least one; a review "
            "band cannot be tighter than the accept band, got %r" % (factor,)
        )
    _require_count(
        "criteria max_corners_affected", criteria.get("max_corners_affected")
    )
    return criteria


def validate_coverglass_geometry(geometry):
    """Check the coverglass outline the corner limits are read against."""
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
        "face_area_mm2": length * width,
        "aperture_area_mm2": (length - 2.0 * overhang) * (width - 2.0 * overhang),
        "corner_reach_available_mm": overhang * math.sqrt(2.0),
    }


def derive_hypotenuse_mm(leg_a_mm, leg_b_mm):
    """Chord across the two legs of a corner bite."""
    leg_a = _require_positive("leg_a_mm", leg_a_mm)
    leg_b = _require_positive("leg_b_mm", leg_b_mm)
    return math.hypot(leg_a, leg_b)


def corner_area_mm2(leg_a_mm, leg_b_mm):
    """Face area a corner bite of these two legs takes off the glass."""
    leg_a = _require_positive("leg_a_mm", leg_a_mm)
    leg_b = _require_positive("leg_b_mm", leg_b_mm)
    return 0.5 * leg_a * leg_b


def corner_reach_mm(leg_a_mm, leg_b_mm):
    """Perpendicular from the corner to the chord.

    This is how far the bite penetrates toward the cell, which is shorter
    than either leg and much shorter than the chord. Grading a corner chip
    on a leg overstates its reach; grading it on the chord alone never
    reports the reach at all.
    """
    leg_a = _require_positive("leg_a_mm", leg_a_mm)
    leg_b = _require_positive("leg_b_mm", leg_b_mm)
    return leg_a * leg_b / math.hypot(leg_a, leg_b)


def leg_ratio(leg_a_mm, leg_b_mm):
    """Longer leg over shorter leg; one for a symmetric bite."""
    leg_a = _require_positive("leg_a_mm", leg_a_mm)
    leg_b = _require_positive("leg_b_mm", leg_b_mm)
    return max(leg_a, leg_b) / min(leg_a, leg_b)


def resolve_corner_chip(chip):
    """Read one corner chip's geometry and reconcile its measurements.

    A directly measured chord that falls outside the triangle inequality
    cannot belong to these two legs, so it is refused as input rather than
    dispositioned. A chord inside the inequality but disagreeing with the
    legs is kept and flagged, because which of the two readings is wrong is
    a metrology question and not this screen's to decide.
    """
    if not isinstance(chip, dict):
        raise ValueError("chip must be a mapping, got %r" % (chip,))
    corner = _require_choice("corner", chip.get("corner"), COVERGLASS_CORNERS)
    leg_a = _require_positive("leg_a_mm", chip.get("leg_a_mm"))
    leg_b = _require_positive("leg_b_mm", chip.get("leg_b_mm"))
    derived = derive_hypotenuse_mm(leg_a, leg_b)
    measured = chip.get("measured_hypotenuse_mm")
    mismatch = None
    if measured is not None:
        measured = _require_positive("measured_hypotenuse_mm", measured)
        if not _at_most(max(leg_a, leg_b), measured) or not _at_most(
            measured, leg_a + leg_b
        ):
            raise ValueError(
                "a measured chord of %.3f mm cannot close legs of %.3f and "
                "%.3f mm; it is not a measurement of this chip"
                % (measured, leg_a, leg_b)
            )
        mismatch = abs(measured - derived) / derived
    return {
        "id": chip.get("id"),
        "corner": corner,
        "leg_a_mm": leg_a,
        "leg_b_mm": leg_b,
        "hypotenuse_mm": derived,
        "measured_hypotenuse_mm": measured,
        "hypotenuse_mismatch_fraction": mismatch,
        "leg_ratio": leg_ratio(leg_a, leg_b),
        "corner_reach_mm": corner_reach_mm(leg_a, leg_b),
        "corner_area_mm2": corner_area_mm2(leg_a, leg_b),
    }


def assess_corner_chip(chip, geometry, criteria=DEFAULT_CORNER_CHIP_CRITERIA):
    """Disposition one coverglass corner chip against the criteria set."""
    validate_corner_chip_criteria(criteria)
    resolved = validate_coverglass_geometry(geometry)
    measurement = resolve_corner_chip(chip)

    reasons = []
    dispositions = []

    limit = criteria["max_hypotenuse_mm"]
    review_limit = limit * criteria["hypotenuse_review_factor"]
    hypotenuse = measurement["hypotenuse_mm"]
    if _at_most(hypotenuse, limit):
        dispositions.append(ACCEPT)
    elif _at_most(hypotenuse, review_limit):
        dispositions.append(REFER)
        reasons.append(
            "the chord across the corner is %.3f mm, past the %.3f mm ceiling"
            % (hypotenuse, limit)
        )
    else:
        dispositions.append(REJECT)
        reasons.append(
            "the chord across the corner is %.3f mm, past the %.3f mm review "
            "limit" % (hypotenuse, review_limit)
        )

    available = resolved["corner_reach_available_mm"]
    reach = measurement["corner_reach_mm"]
    if _at_most(reach, available):
        dispositions.append(ACCEPT)
    else:
        dispositions.append(REJECT)
        reasons.append(
            "the bite reaches %.3f mm in from the corner, past the %.3f mm "
            "the overhang diagonal offers, so it stands over the illuminated "
            "aperture" % (reach, available)
        )

    routed_to = None
    if not _at_most(measurement["leg_ratio"], criteria["max_leg_ratio"]):
        dispositions.append(REFER)
        routed_to = EDGE_CLAUSE_ROUTE
        reasons.append(
            "legs of %.3f and %.3f mm are a ratio of %.2f, so this is a gouge "
            "running along one edge rather than a corner bite and belongs to "
            "the edge chip clause"
            % (
                measurement["leg_a_mm"],
                measurement["leg_b_mm"],
                measurement["leg_ratio"],
            )
        )

    mismatch = measurement["hypotenuse_mismatch_fraction"]
    if mismatch is not None and not _at_most(
        mismatch, criteria["max_hypotenuse_mismatch_fraction"]
    ):
        dispositions.append(REFER)
        reasons.append(
            "the measured chord of %.3f mm disagrees with the %.3f mm the legs "
            "give by %.3f, past the %.3f agreement allowance; one of the two "
            "readings is wrong"
            % (
                measurement["measured_hypotenuse_mm"],
                measurement["hypotenuse_mm"],
                mismatch,
                criteria["max_hypotenuse_mismatch_fraction"],
            )
        )

    result = dict(measurement)
    result.update(
        {
            "hypotenuse_margin_mm": limit - hypotenuse,
            "corner_reach_available_mm": available,
            "routed_to": routed_to,
            "disposition": _worst(dispositions),
            "reasons": reasons,
        }
    )
    return result


def assess_coverglass_corners(glass, criteria=DEFAULT_CORNER_CHIP_CRITERIA):
    """Clause 8.7.1.3.5 screen of every corner chip on one coverglass."""
    validate_corner_chip_criteria(criteria)
    if not isinstance(glass, dict):
        raise ValueError("glass must be a mapping, got %r" % (glass,))
    glass_id = glass.get("coverglass_id")
    if not isinstance(glass_id, str) or not glass_id.strip():
        raise ValueError("each coverglass needs a non-empty coverglass_id")
    geometry = validate_coverglass_geometry(glass.get("geometry"))
    chips = glass.get("corner_chips", [])
    if not isinstance(chips, (list, tuple)):
        raise ValueError("corner_chips must be a list")

    seen_ids = set()
    seen_corners = set()
    assessed = []
    for chip in chips:
        result = assess_corner_chip(chip, glass.get("geometry"), criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen_ids:
                raise ValueError(
                    "duplicate chip id %r on coverglass %s" % (marker, glass_id)
                )
            seen_ids.add(marker)
        if result["corner"] in seen_corners:
            raise ValueError(
                "coverglass %s has two chips recorded at %s; a corner carries "
                "one bite, so the two readings must be reconciled first"
                % (glass_id, result["corner"])
            )
        seen_corners.add(result["corner"])
        assessed.append(result)

    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])

    corner_area = sum(result["corner_area_mm2"] for result in assessed)
    area_fraction = corner_area / geometry["face_area_mm2"]

    if not _at_most(area_fraction, criteria["max_cumulative_corner_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "corner bites take %.6f of the glass face, past the %.6f allowance, "
            "even though no single corner did"
            % (area_fraction, criteria["max_cumulative_corner_area_fraction"])
        )
    if len(assessed) > criteria["max_corners_affected"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d of the four corners are chipped, past the %d allowed"
            % (len(assessed), criteria["max_corners_affected"])
        )

    return {
        "coverglass_id": glass_id,
        "verdict": _ROLLUP_BY_SEVERITY[verdict],
        "disposition": verdict,
        "corner_chips": assessed,
        "corners_affected": sorted(seen_corners),
        "largest_hypotenuse_mm": max(
            (result["hypotenuse_mm"] for result in assessed), default=0.0
        ),
        "deepest_corner_reach_mm": max(
            (result["corner_reach_mm"] for result in assessed), default=0.0
        ),
        "corner_area_mm2": corner_area,
        "corner_area_fraction": area_fraction,
        "routed_to_edge_clause": [
            result["id"] for result in assessed if result["routed_to"]
        ],
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "findings": findings,
    }
