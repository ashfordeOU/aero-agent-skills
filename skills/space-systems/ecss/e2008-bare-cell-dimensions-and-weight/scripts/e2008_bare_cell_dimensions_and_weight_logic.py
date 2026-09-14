#!/usr/bin/env python3
"""Bare cell outline, thickness, mass, contact geometry and pad positions.

Anchor: ECSS-E-ST-20-08C clause 7.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare cell is bought to a drawing. The clause asks whether the cell in
hand is the cell the drawing describes, across five families of
measurement that fail in different ways:

    outline       length and width against their plus and minus bands.
                  An oversize cell will not fit the string pitch; an
                  undersize one leaves a gap the coverglass overhangs.
    thickness     the band the cell is bought to. Thickness drives
                  handling breakage and the bond line the laydown
                  assumes.
    mass          what the cell weighs, against its band. Mass is an
                  array-level budget: a few per cent per cell becomes
                  kilograms across a wing.
    contacts      the width and length of each contact feature, each
                  against its own band, because the weld schedule was
                  qualified on that geometry.
    positions     where the interconnector attachment points sit. A
                  position is not two independent numbers -- what
                  matters is the radial deviation from nominal, so the
                  check is a true-position test against one tolerance,
                  not two axis tests against two.

Two things separate this from arithmetic on a measurement sheet.

First, a bare cell cannot be machined back into tolerance. There is no
rework disposition. What exists instead is a review band: a deviation
outside tolerance but inside a declared multiple of it is raised as a
non-conformance and submitted for a use-as-is decision. Past that
multiple the cell is refused outright.

Second, mass and outline are not independent measurements. Their ratio
is the areal density, and a cell whose measured density departs from
the density its nominal drawing implies is telling you that one of the
two measurements is wrong -- a cracked cell weighed with a fragment
missing, or an outline read off the wrong datum. That cross-check has
to run before the individual bands are believed.

Dimensional states are within-tolerance, above-upper-limit and
below-lower-limit. Dispositions are accept, review and reject. The
bands below travel with the cell specification, not with this module.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIMENSION_WITHIN = "within-tolerance"
DIMENSION_ABOVE = "above-upper-limit"
DIMENSION_BELOW = "below-lower-limit"
DIMENSION_STATES = (DIMENSION_WITHIN, DIMENSION_ABOVE, DIMENSION_BELOW)

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

# Bands every bare cell specification has to carry.
REQUIRED_BANDS = (
    "length_mm",
    "width_mm",
    "thickness_um",
    "mass_g",
)

DEFAULT_REVIEW_BAND_FACTOR = 2.0
DEFAULT_AREAL_DENSITY_TOLERANCE = 0.10

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


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a nominal plus a tolerance and a review limit multiplies
    that tolerance again, so a measurement meant to sit exactly on a
    limit can evaluate a few units in the last place to either side. The
    limit is never moved; only the comparison tolerates the error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_band(name, band):
    """Check one nominal-plus-tolerance band and return it normalised."""
    if not isinstance(band, dict):
        raise ValueError("band %s must be a mapping, got %r" % (name, band))
    nominal = _require_positive("band %s nominal" % name, band.get("nominal"))
    minus = _require_non_negative("band %s minus" % name, band.get("minus"))
    plus = _require_non_negative("band %s plus" % name, band.get("plus"))
    if minus <= 0.0 and plus <= 0.0:
        raise ValueError(
            "band %s has no width; a zero-tolerance band cannot be measured "
            "against and would refuse every real cell" % name
        )
    if minus > nominal:
        raise ValueError(
            "band %s allows a lower limit at or below zero; the minus "
            "tolerance exceeds the nominal" % name
        )
    return {"nominal": nominal, "minus": minus, "plus": plus}


def validate_cell_specification(spec):
    """Check a bare cell specification carries every band it needs."""
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping, got %r" % (spec,))
    bands = {}
    for name in REQUIRED_BANDS:
        if name not in spec:
            raise ValueError(
                "specification is missing the %s band; an unstated band is "
                "not an open one" % name
            )
        bands[name] = validate_band(name, spec[name])

    contacts = spec.get("contacts", [])
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("specification contacts must be a list")
    contact_bands = {}
    for contact in contacts:
        if not isinstance(contact, dict):
            raise ValueError("each contact spec must be a mapping")
        contact_id = contact.get("id")
        if not isinstance(contact_id, str) or not contact_id.strip():
            raise ValueError("each contact spec needs a non-empty id")
        if contact_id in contact_bands:
            raise ValueError("duplicate contact id %r in the specification" % contact_id)
        entry = {}
        for feature in ("width_mm", "length_mm"):
            if feature in contact:
                entry[feature] = validate_band(
                    "%s %s" % (contact_id, feature), contact[feature]
                )
        if not entry:
            raise ValueError(
                "contact %s declares no width or length band, so nothing about "
                "it can be checked" % contact_id
            )
        contact_bands[contact_id] = entry

    positions = spec.get("interconnector_positions", [])
    if not isinstance(positions, (list, tuple)):
        raise ValueError("specification interconnector_positions must be a list")
    nominal_positions = {}
    for position in positions:
        if not isinstance(position, dict):
            raise ValueError("each interconnector position must be a mapping")
        position_id = position.get("id")
        if not isinstance(position_id, str) or not position_id.strip():
            raise ValueError("each interconnector position needs a non-empty id")
        if position_id in nominal_positions:
            raise ValueError(
                "duplicate interconnector position id %r in the specification"
                % position_id
            )
        nominal_positions[position_id] = (
            _require_number("%s x_mm" % position_id, position.get("x_mm")),
            _require_number("%s y_mm" % position_id, position.get("y_mm")),
        )
    if nominal_positions:
        _require_positive(
            "position_tolerance_mm", spec.get("position_tolerance_mm")
        )

    factor = spec.get("review_band_factor", DEFAULT_REVIEW_BAND_FACTOR)
    factor = _require_positive("review_band_factor", factor)
    if factor < 1.0 and not _close(factor, 1.0):
        raise ValueError(
            "review_band_factor cannot be under one; the review band widens a "
            "tolerance, it never narrows one"
        )
    _require_positive(
        "areal_density_tolerance",
        spec.get("areal_density_tolerance", DEFAULT_AREAL_DENSITY_TOLERANCE),
    )
    return {
        "bands": bands,
        "contacts": contact_bands,
        "positions": nominal_positions,
        "position_tolerance_mm": spec.get("position_tolerance_mm"),
        "review_band_factor": factor,
        "areal_density_tolerance": spec.get(
            "areal_density_tolerance", DEFAULT_AREAL_DENSITY_TOLERANCE
        ),
    }


def evaluate_dimension(name, measured, band, review_band_factor=DEFAULT_REVIEW_BAND_FACTOR):
    """Place one measurement inside its band and name the disposition."""
    checked = validate_band(name, band)
    value = _require_number("%s measured" % name, measured)
    factor = _require_positive("review_band_factor", review_band_factor)
    lower = checked["nominal"] - checked["minus"]
    upper = checked["nominal"] + checked["plus"]
    review_lower = checked["nominal"] - checked["minus"] * factor
    review_upper = checked["nominal"] + checked["plus"] * factor

    if _at_least(value, lower) and _at_most(value, upper):
        state = DIMENSION_WITHIN
        disposition = ACCEPT
    elif value > upper:
        state = DIMENSION_ABOVE
        disposition = REVIEW if _at_most(value, review_upper) else REJECT
    else:
        state = DIMENSION_BELOW
        disposition = REVIEW if _at_least(value, review_lower) else REJECT

    if state == DIMENSION_WITHIN:
        margin = min(value - lower, upper - value)
    elif state == DIMENSION_ABOVE:
        margin = upper - value
    else:
        margin = value - lower

    return {
        "name": name,
        "measured": value,
        "nominal": checked["nominal"],
        "lower_limit": lower,
        "upper_limit": upper,
        "deviation": value - checked["nominal"],
        "margin": margin,
        "state": state,
        "disposition": disposition,
    }


def positional_deviation_mm(measured_xy, nominal_xy):
    """Radial distance between a measured point and its nominal."""
    if not isinstance(measured_xy, (list, tuple)) or len(measured_xy) != 2:
        raise ValueError(
            "measured position must be an (x, y) pair, got %r" % (measured_xy,)
        )
    if not isinstance(nominal_xy, (list, tuple)) or len(nominal_xy) != 2:
        raise ValueError(
            "nominal position must be an (x, y) pair, got %r" % (nominal_xy,)
        )
    dx = _require_number("measured x_mm", measured_xy[0]) - _require_number(
        "nominal x_mm", nominal_xy[0]
    )
    dy = _require_number("measured y_mm", measured_xy[1]) - _require_number(
        "nominal y_mm", nominal_xy[1]
    )
    return math.hypot(dx, dy)


def areal_density_mg_per_cm2(mass_g, length_mm, width_mm):
    """Mass per unit of cell outline area, in milligrams per square centimetre."""
    mass = _require_positive("mass_g", mass_g)
    length = _require_positive("length_mm", length_mm)
    width = _require_positive("width_mm", width_mm)
    area_cm2 = (length * width) / 100.0
    return (mass * 1000.0) / area_cm2


def assess_interconnector_positions(measured, checked_spec):
    """True-position check of every interconnector attachment point."""
    if not isinstance(measured, (list, tuple)):
        raise ValueError("measured positions must be a list, got %r" % (measured,))
    nominal_positions = checked_spec["positions"]
    tolerance = checked_spec["position_tolerance_mm"]
    factor = checked_spec["review_band_factor"]
    if not nominal_positions:
        if measured:
            raise ValueError(
                "positions were measured but the specification declares none; "
                "there is nothing to judge them against"
            )
        return {"positions": [], "disposition": ACCEPT, "worst_deviation_mm": 0.0}
    tolerance = _require_positive("position_tolerance_mm", tolerance)

    seen = set()
    results = []
    for point in measured:
        if not isinstance(point, dict):
            raise ValueError("each measured position must be a mapping")
        point_id = point.get("id")
        if point_id not in nominal_positions:
            raise ValueError(
                "measured position %r is not in the specification; an extra "
                "attachment point is a drawing mismatch, not a deviation"
                % (point_id,)
            )
        if point_id in seen:
            raise ValueError("duplicate measured position id %r" % (point_id,))
        seen.add(point_id)
        deviation = positional_deviation_mm(
            (point.get("x_mm"), point.get("y_mm")), nominal_positions[point_id]
        )
        if _at_most(deviation, tolerance):
            disposition = ACCEPT
        elif _at_most(deviation, tolerance * factor):
            disposition = REVIEW
        else:
            disposition = REJECT
        results.append(
            {
                "id": point_id,
                "deviation_mm": deviation,
                "tolerance_mm": tolerance,
                "disposition": disposition,
            }
        )

    missing = sorted(set(nominal_positions) - seen)
    if missing:
        raise ValueError(
            "no measurement for interconnector position(s) %s; an unmeasured "
            "point is unknown, not conforming" % ", ".join(missing)
        )

    worst = max((item["deviation_mm"] for item in results), default=0.0)
    return {
        "positions": results,
        "disposition": _worst([item["disposition"] for item in results]),
        "worst_deviation_mm": worst,
    }


def assess_bare_cell_dimensions(cell, spec):
    """Full clause 7.5.2 dimensional and mass check of one bare cell."""
    checked = validate_cell_specification(spec)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("cell needs a non-empty cell_id for traceability")

    factor = checked["review_band_factor"]
    dimensions = []
    for name in REQUIRED_BANDS:
        if name not in cell:
            raise ValueError(
                "cell record is missing the %s measurement; an unmeasured "
                "feature is unknown, not conforming" % name
            )
        dimensions.append(
            evaluate_dimension(name, cell[name], checked["bands"][name], factor)
        )

    measured_contacts = cell.get("contacts", [])
    if not isinstance(measured_contacts, (list, tuple)):
        raise ValueError("cell contacts must be a list")
    contact_results = []
    seen_contacts = set()
    for contact in measured_contacts:
        if not isinstance(contact, dict):
            raise ValueError("each measured contact must be a mapping")
        contact_id = contact.get("id")
        if contact_id not in checked["contacts"]:
            raise ValueError(
                "measured contact %r is not in the specification" % (contact_id,)
            )
        if contact_id in seen_contacts:
            raise ValueError("duplicate measured contact id %r" % (contact_id,))
        seen_contacts.add(contact_id)
        for feature, band in checked["contacts"][contact_id].items():
            if feature not in contact:
                raise ValueError(
                    "contact %s is missing its %s measurement"
                    % (contact_id, feature)
                )
            result = evaluate_dimension(
                "%s %s" % (contact_id, feature), contact[feature], band, factor
            )
            result["contact_id"] = contact_id
            contact_results.append(result)
    missing_contacts = sorted(set(checked["contacts"]) - seen_contacts)
    if missing_contacts:
        raise ValueError(
            "no measurement for contact(s) %s; an unmeasured contact is "
            "unknown, not conforming" % ", ".join(missing_contacts)
        )

    positions = assess_interconnector_positions(
        cell.get("interconnector_positions", []), checked
    )

    density = areal_density_mg_per_cm2(
        cell["mass_g"], cell["length_mm"], cell["width_mm"]
    )
    nominal_density = areal_density_mg_per_cm2(
        checked["bands"]["mass_g"]["nominal"],
        checked["bands"]["length_mm"]["nominal"],
        checked["bands"]["width_mm"]["nominal"],
    )
    density_tolerance = checked["areal_density_tolerance"]
    density_ratio = density / nominal_density
    density_consistent = _at_most(
        abs(density_ratio - 1.0), density_tolerance
    )

    findings = []
    calls = [item["disposition"] for item in dimensions]
    calls.extend(item["disposition"] for item in contact_results)
    calls.append(positions["disposition"])

    for item in dimensions + contact_results:
        if item["state"] != DIMENSION_WITHIN:
            findings.append(
                "%s measures %.4f against the %.4f to %.4f band (%s)"
                % (
                    item["name"],
                    item["measured"],
                    item["lower_limit"],
                    item["upper_limit"],
                    item["state"],
                )
            )
    for item in positions["positions"]:
        if item["disposition"] != ACCEPT:
            findings.append(
                "interconnector position %s deviates %.4f mm from nominal "
                "against a %.4f mm true-position tolerance"
                % (item["id"], item["deviation_mm"], item["tolerance_mm"])
            )
    if not density_consistent:
        calls.append(REVIEW)
        findings.append(
            "measured areal density %.2f mg/cm2 departs from the %.2f mg/cm2 "
            "the nominal drawing implies by more than %.3f; the mass and the "
            "outline disagree and one of the two measurements is suspect"
            % (density, nominal_density, density_tolerance)
        )

    verdict = _worst(calls)
    if verdict == ACCEPT and not findings:
        findings.append(
            "every measured feature sits inside its band and the mass and "
            "outline agree; the record stands as the conformity evidence"
        )

    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "dimensions": dimensions,
        "contacts": contact_results,
        "interconnector_positions": positions["positions"],
        "worst_position_deviation_mm": positions["worst_deviation_mm"],
        "areal_density_mg_per_cm2": density,
        "nominal_areal_density_mg_per_cm2": nominal_density,
        "areal_density_consistent": density_consistent,
        "out_of_tolerance_names": [
            item["name"]
            for item in dimensions + contact_results
            if item["state"] != DIMENSION_WITHIN
        ],
        "nonconformance_review_required": verdict == REVIEW,
        "findings": findings,
    }
