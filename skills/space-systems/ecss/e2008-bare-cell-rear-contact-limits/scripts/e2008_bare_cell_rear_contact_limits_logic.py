#!/usr/bin/env python3
"""Size ceilings for drops and spatter outside the rear welding zone.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.5.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The rear contact of a bare cell carries a designated welding zone: the
area the interconnector is joined in, where molten metal is expected.
The clause is about everything that landed anywhere else. A drop of
solder or a particle of weld spatter sitting outside that zone is not
refused on sight -- it is held to a size ceiling, and where it landed
changes the ceiling it is held to.

Three questions decide a deposit, and they are geometric before they
are dispositional:

    in zone or out    the welding zone is the rectangle the joint is
                      made in. A deposit inside it is the process, not
                      a finding, and no ceiling applies to it. The
                      distance a deposit sits outside the zone is the
                      straight-line distance from the deposit to the
                      nearest point of the rectangle.
    how big across    the footprint diameter against the ceiling. A
                      deposit that exceeds it but stays inside the
                      rework band can be dressed back; past that band
                      there is too much metal to remove without
                      putting heat into the cell.
    how far up        a deposit stands proud of the rear contact plane.
                      Below the declared bond line it disappears into
                      the adhesive; above it the cell no longer seats,
                      and that is refused whatever its diameter.

Where a deposit landed matters twice. Near the cell perimeter the
junction comes close to the rear surface, so a deposit inside the edge
exclusion band is held to a tightened ceiling. And the rear as a whole
carries a budget: enough small deposits, each individually acceptable,
still add to a total footprint area and a count that the assembly
cannot carry.

Deposit kinds
    solder-drop                  a discrete bead of solder
    solder-spatter               solder thrown clear of the joint
    weld-spatter                 expelled metal from the weld itself
    resolidified-metal-bead      contact metal melted and re-frozen

Coordinates are millimetres in the rear-face frame, with the origin at
one corner of the cell outline. Dispositions are accept, rework and
reject. The limits below are a declared project criteria set, not a
physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEPOSIT_KINDS = (
    "solder-drop",
    "solder-spatter",
    "weld-spatter",
    "resolidified-metal-bead",
)

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_REAR_CONTACT_CRITERIA = {
    # Footprint diameter ceilings for a deposit outside the welding zone.
    "accept_deposit_diameter_mm": 0.30,
    "rework_deposit_diameter_mm": 0.60,
    # A deposit standing this far proud is dressed back; past the bond
    # line thickness the cell cannot seat and it is refused.
    "accept_protrusion_height_mm": 0.04,
    "bond_line_thickness_mm": 0.10,
    # Band along the cell perimeter where the ceilings tighten.
    "edge_exclusion_mm": 0.50,
    "edge_zone_ceiling_factor": 0.5,
    # Budget across the whole rear face, outside the welding zone.
    "max_total_deposit_area_mm2": 0.60,
    "max_deposit_count_outside_zone": 6,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A ceiling is a product of a criteria value and an edge factor, and a
    footprint area comes out of a squared diameter, so a measurement
    meant to sit exactly on a limit can evaluate a few units in the last
    place above it. The limit is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_rear_contact_criteria(criteria):
    """Check a criteria set is complete and internally ordered."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    positive_keys = (
        "accept_deposit_diameter_mm",
        "rework_deposit_diameter_mm",
        "accept_protrusion_height_mm",
        "bond_line_thickness_mm",
        "edge_exclusion_mm",
        "edge_zone_ceiling_factor",
        "max_total_deposit_area_mm2",
    )
    for key in positive_keys:
        _require_positive("criteria %s" % key, criteria.get(key))
    factor = criteria["edge_zone_ceiling_factor"]
    if factor > 1.0 and not _close(factor, 1.0):
        raise ValueError(
            "criteria edge_zone_ceiling_factor cannot exceed one; the edge "
            "band tightens a ceiling, it never loosens one"
        )
    accept_diameter = criteria["accept_deposit_diameter_mm"]
    rework_diameter = criteria["rework_deposit_diameter_mm"]
    if rework_diameter < accept_diameter and not _close(
        rework_diameter, accept_diameter
    ):
        raise ValueError(
            "criteria rework_deposit_diameter_mm is below the accept ceiling; "
            "the rework band has to be the looser one"
        )
    accept_height = criteria["accept_protrusion_height_mm"]
    bond_line = criteria["bond_line_thickness_mm"]
    if bond_line < accept_height and not _close(bond_line, accept_height):
        raise ValueError(
            "criteria bond_line_thickness_mm is below the accept protrusion "
            "height; a deposit could then be accepted and still hold the cell "
            "off the substrate"
        )
    count = criteria.get("max_deposit_count_outside_zone")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError(
            "criteria max_deposit_count_outside_zone must be a positive "
            "integer, got %r" % (count,)
        )
    return criteria


def validate_welding_zone(zone):
    """Check a welding zone rectangle is ordered and has real area."""
    if not isinstance(zone, dict):
        raise ValueError("welding_zone must be a mapping, got %r" % (zone,))
    bounds = {}
    for key in ("x_min", "x_max", "y_min", "y_max"):
        bounds[key] = _require_number("welding_zone %s" % key, zone.get(key))
    if bounds["x_max"] <= bounds["x_min"] or bounds["y_max"] <= bounds["y_min"]:
        raise ValueError(
            "welding_zone has no area; x_max and y_max must exceed x_min and "
            "y_min"
        )
    return bounds


def validate_cell_outline(outline):
    """Check a rear-face outline carries a real length and width."""
    if not isinstance(outline, dict):
        raise ValueError("outline must be a mapping, got %r" % (outline,))
    length = _require_positive("outline length_mm", outline.get("length_mm"))
    width = _require_positive("outline width_mm", outline.get("width_mm"))
    return {"length_mm": length, "width_mm": width}


def distance_outside_welding_zone_mm(x_mm, y_mm, zone):
    """Straight-line distance from a point to the welding zone rectangle.

    Zero when the point lies on or inside the rectangle.
    """
    bounds = validate_welding_zone(zone)
    x = _require_number("x_mm", x_mm)
    y = _require_number("y_mm", y_mm)
    dx = max(bounds["x_min"] - x, 0.0, x - bounds["x_max"])
    dy = max(bounds["y_min"] - y, 0.0, y - bounds["y_max"])
    return math.hypot(dx, dy)


def distance_to_cell_edge_mm(x_mm, y_mm, outline):
    """Shortest distance from a point to the cell perimeter."""
    box = validate_cell_outline(outline)
    x = _require_number("x_mm", x_mm)
    y = _require_number("y_mm", y_mm)
    if x < 0.0 or y < 0.0 or x > box["length_mm"] or y > box["width_mm"]:
        raise ValueError(
            "point (%.3f, %.3f) lies off the cell outline; the survey frame "
            "or the outline is wrong" % (x, y)
        )
    return min(x, y, box["length_mm"] - x, box["width_mm"] - y)


def deposit_footprint_area_mm2(diameter_mm):
    """Footprint area of a deposit taken as a circle of that diameter."""
    diameter = _require_non_negative("diameter_mm", diameter_mm)
    radius = diameter / 2.0
    return math.pi * radius * radius


def effective_diameter_ceilings_mm(
    edge_distance_mm, criteria=DEFAULT_REAR_CONTACT_CRITERIA
):
    """Accept and rework diameter ceilings once the edge band is applied."""
    validate_rear_contact_criteria(criteria)
    edge_distance = _require_non_negative("edge_distance_mm", edge_distance_mm)
    factor = 1.0
    if edge_distance < criteria["edge_exclusion_mm"] and not _close(
        edge_distance, criteria["edge_exclusion_mm"]
    ):
        factor = criteria["edge_zone_ceiling_factor"]
    return {
        "factor": factor,
        "accept_diameter_mm": criteria["accept_deposit_diameter_mm"] * factor,
        "rework_diameter_mm": criteria["rework_deposit_diameter_mm"] * factor,
    }


def assess_rear_deposit(deposit, cell, criteria=DEFAULT_REAR_CONTACT_CRITERIA):
    """Disposition one deposit against the ceilings that govern where it sits."""
    validate_rear_contact_criteria(criteria)
    if not isinstance(deposit, dict):
        raise ValueError("deposit must be a mapping, got %r" % (deposit,))
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    outline = validate_cell_outline(cell.get("outline"))
    zone = validate_welding_zone(cell.get("welding_zone"))

    kind = _require_choice("kind", deposit.get("kind"), DEPOSIT_KINDS)
    x = _require_number("x_mm", deposit.get("x_mm"))
    y = _require_number("y_mm", deposit.get("y_mm"))
    diameter = _require_non_negative("diameter_mm", deposit.get("diameter_mm"))
    height = _require_non_negative("height_mm", deposit.get("height_mm"))

    zone_distance = distance_outside_welding_zone_mm(x, y, zone)
    edge_distance = distance_to_cell_edge_mm(x, y, outline)
    area = deposit_footprint_area_mm2(diameter)
    in_zone = zone_distance <= 0.0 or _close(zone_distance, 0.0)

    measurements = {
        "distance_outside_welding_zone_mm": zone_distance,
        "distance_to_cell_edge_mm": edge_distance,
        "footprint_area_mm2": area,
        "diameter_mm": diameter,
        "height_mm": height,
    }
    reasons = []

    if in_zone:
        return {
            "id": deposit.get("id"),
            "kind": kind,
            "in_welding_zone": True,
            "in_edge_band": False,
            "disposition": ACCEPT,
            "measurements": measurements,
            "reasons": [],
        }

    ceilings = effective_diameter_ceilings_mm(edge_distance, criteria)
    measurements["accept_diameter_mm"] = ceilings["accept_diameter_mm"]
    measurements["rework_diameter_mm"] = ceilings["rework_diameter_mm"]
    in_edge_band = ceilings["factor"] < 1.0

    if _at_most(diameter, ceilings["accept_diameter_mm"]):
        diameter_call = ACCEPT
    elif _at_most(diameter, ceilings["rework_diameter_mm"]):
        diameter_call = REWORK
        reasons.append(
            "diameter %.3f mm is over the %.3f mm ceiling for a deposit "
            "%.3f mm outside the welding zone; it can be dressed back"
            % (diameter, ceilings["accept_diameter_mm"], zone_distance)
        )
    else:
        diameter_call = REJECT
        reasons.append(
            "diameter %.3f mm is over the %.3f mm rework ceiling; removing "
            "that much metal puts more heat into the cell than the rear "
            "contact survives" % (diameter, ceilings["rework_diameter_mm"])
        )

    if _at_most(height, criteria["accept_protrusion_height_mm"]):
        height_call = ACCEPT
    elif _at_most(height, criteria["bond_line_thickness_mm"]):
        height_call = REWORK
        reasons.append(
            "the deposit stands %.3f mm proud, over the %.3f mm accept height"
            % (height, criteria["accept_protrusion_height_mm"])
        )
    else:
        height_call = REJECT
        reasons.append(
            "the deposit stands %.3f mm proud, past the %.3f mm bond line; the "
            "cell cannot seat on the substrate whatever its diameter"
            % (height, criteria["bond_line_thickness_mm"])
        )

    if in_edge_band:
        reasons.append(
            "the deposit sits %.3f mm from the cell edge, inside the edge "
            "exclusion band, so its ceilings are the tightened ones"
            % edge_distance
        )

    return {
        "id": deposit.get("id"),
        "kind": kind,
        "in_welding_zone": False,
        "in_edge_band": in_edge_band,
        "disposition": _worst([diameter_call, height_call]),
        "measurements": measurements,
        "reasons": reasons,
    }


def group_deposits_by_kind(deposits):
    """Group a rear survey by deposit kind."""
    if not isinstance(deposits, (list, tuple)):
        raise ValueError("deposits must be a list, got %r" % (deposits,))
    counts = dict((kind, 0) for kind in DEPOSIT_KINDS)
    for deposit in deposits:
        if not isinstance(deposit, dict):
            raise ValueError("each deposit must be a mapping, got %r" % (deposit,))
        kind = _require_choice("kind", deposit.get("kind"), DEPOSIT_KINDS)
        counts[kind] += 1
    return {"counts": counts, "total": sum(counts.values())}


def assess_rear_contact(cell, criteria=DEFAULT_REAR_CONTACT_CRITERIA):
    """Full clause 7.5.1.5.4 rear contact screen with a cell-level verdict."""
    validate_rear_contact_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("cell needs a non-empty cell_id for traceability")
    deposits = cell.get("deposits")
    if not isinstance(deposits, (list, tuple)):
        raise ValueError("cell deposits must be a list, got %r" % (deposits,))

    seen = set()
    assessed = []
    for deposit in deposits:
        result = assess_rear_deposit(deposit, cell, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate deposit id %r on cell %s; traceability to the "
                    "rework record would be lost" % (marker, cell_id)
                )
            seen.add(marker)
        assessed.append(result)

    outside = [result for result in assessed if not result["in_welding_zone"]]
    total_area = sum(
        result["measurements"]["footprint_area_mm2"] for result in outside
    )
    calls = [result["disposition"] for result in assessed]
    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    budget_calls = []
    if not _at_most(total_area, criteria["max_total_deposit_area_mm2"]):
        budget_calls.append(REWORK)
        findings.append(
            "total deposit footprint outside the welding zone is %.4f mm2, "
            "over the %.4f mm2 budget; individually acceptable deposits still "
            "add up" % (total_area, criteria["max_total_deposit_area_mm2"])
        )
    if len(outside) > criteria["max_deposit_count_outside_zone"]:
        budget_calls.append(REWORK)
        findings.append(
            "%d deposits sit outside the welding zone, over the limit of %d"
            % (len(outside), criteria["max_deposit_count_outside_zone"])
        )

    verdict = _worst(calls + budget_calls) if (calls or budget_calls) else ACCEPT
    if not assessed:
        findings.append(
            "no deposits recorded; the rear contact was surveyed and is clear "
            "outside the welding zone, and the record stands as the evidence"
        )

    grouping = group_deposits_by_kind(list(deposits))
    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "deposits": assessed,
        "outside_zone_count": len(outside),
        "in_zone_count": len(assessed) - len(outside),
        "total_outside_area_mm2": total_area,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "edge_band_ids": [
            result["id"] for result in assessed if result["in_edge_band"]
        ],
        "kind_counts": grouping["counts"],
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }
