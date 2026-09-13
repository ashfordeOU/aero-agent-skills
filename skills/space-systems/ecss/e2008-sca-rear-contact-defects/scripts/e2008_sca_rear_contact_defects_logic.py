#!/usr/bin/env python3
"""Size limits on weld drops and spatter outside the rear welding area.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The rear contact of a solar cell assembly carries designated welding
areas where the interconnectors are joined. Material thrown or run
outside those areas -- a drop of weld or solder that has flowed, a
scatter of fine spatter -- is governed by a size limit rather than by a
count: outside the welding area a deposit is permitted only while it
stays under the size allowed for its kind.

Two sizes matter and they fail differently:

    diameter        the footprint the deposit covers on the rear face,
                    which consumes area the cell needs for bonding
    standoff        how proud the deposit stands off the rear face,
                    which decides whether the cell still lies flat on
                    its substrate and whether it presses on anything

Where a deposit sits is decided by its own footprint, not by its centre.
A drop centred just inside a welding boundary but wide enough to reach
across it is partly outside, and the part outside is the part this
clause governs, so such a deposit is graded as an outside one.

A limit set whose welding areas cover the whole rear face leaves nothing
for the clause to govern and is refused rather than passed vacuously.

The limits below are a declared limit set, not a physical constant; a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REAR_DEPOSIT_KINDS = ("weld-drop", "weld-spatter")

WITHIN_WELDING_AREA = "within-welding-area"
STRADDLING_WELDING_BOUNDARY = "straddling-welding-boundary"
OUTSIDE_WELDING_AREA = "outside-welding-area"

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
REAR_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

DEFAULT_REAR_DEPOSIT_LIMITS = {
    "max_diameter_mm": {
        "weld-drop": 0.50,
        "weld-spatter": 0.20,
    },
    "max_standoff_height_mm": {
        "weld-drop": 0.15,
        "weld-spatter": 0.08,
    },
    "max_covered_fraction": 0.005,
    "review_margin_factor": 1.5,
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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError(
            "%s must lie between zero and one, got %r" % (name, value)
        )
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_rear_deposit_limits(limits):
    """Check a rear deposit limit set is complete and self-consistent."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    diameters = limits.get("max_diameter_mm")
    if not isinstance(diameters, dict):
        raise ValueError("limits max_diameter_mm must be a mapping")
    standoffs = limits.get("max_standoff_height_mm")
    if not isinstance(standoffs, dict):
        raise ValueError("limits max_standoff_height_mm must be a mapping")
    for kind in REAR_DEPOSIT_KINDS:
        if kind not in diameters:
            raise ValueError("limits max_diameter_mm is missing %s" % kind)
        if kind not in standoffs:
            raise ValueError("limits max_standoff_height_mm is missing %s" % kind)
        _require_non_negative("limits max_diameter_mm %s" % kind, diameters[kind])
        _require_non_negative(
            "limits max_standoff_height_mm %s" % kind, standoffs[kind]
        )
        if diameters[kind] == 0.0 and standoffs[kind] > 0.0:
            raise ValueError(
                "limits permit no %s of any diameter while allowing a standoff "
                "height for one; the two allowances contradict each other" % kind
            )
    _require_fraction("limits max_covered_fraction", limits.get("max_covered_fraction"))
    factor = limits.get("review_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "limits review_margin_factor must be at least one, got %r" % (factor,)
        )
    return limits


def _rectangle(area):
    if not isinstance(area, dict):
        raise ValueError("welding area must be a mapping, got %r" % (area,))
    area_id = _require_text("area_id", area.get("area_id"))
    x = _require_non_negative("welding area x_mm on %s" % area_id, area.get("x_mm"))
    y = _require_non_negative("welding area y_mm on %s" % area_id, area.get("y_mm"))
    width = _require_positive(
        "welding area width_mm on %s" % area_id, area.get("width_mm")
    )
    height = _require_positive(
        "welding area height_mm on %s" % area_id, area.get("height_mm")
    )
    return {
        "area_id": area_id,
        "x_mm": x,
        "y_mm": y,
        "width_mm": width,
        "height_mm": height,
        "area_mm2": width * height,
    }


def _rectangles_overlap(first, second):
    return (
        first["x_mm"] < second["x_mm"] + second["width_mm"]
        and second["x_mm"] < first["x_mm"] + first["width_mm"]
        and first["y_mm"] < second["y_mm"] + second["height_mm"]
        and second["y_mm"] < first["y_mm"] + first["height_mm"]
    )


def welding_area_layout(rear_face):
    """Read the rear face and its welding areas, and size what is governed."""
    if not isinstance(rear_face, dict):
        raise ValueError("rear_face must be a mapping, got %r" % (rear_face,))
    width = _require_positive("rear_face width_mm", rear_face.get("width_mm"))
    height = _require_positive("rear_face height_mm", rear_face.get("height_mm"))
    declared = rear_face.get("welding_areas")
    if not isinstance(declared, (list, tuple)):
        raise ValueError("welding_areas must be a list, got %r" % (declared,))
    areas = []
    seen = set()
    for entry in declared:
        rectangle = _rectangle(entry)
        if rectangle["area_id"] in seen:
            raise ValueError("duplicate welding area id %r" % rectangle["area_id"])
        seen.add(rectangle["area_id"])
        if not _at_most(
            rectangle["x_mm"] + rectangle["width_mm"], width
        ) or not _at_most(rectangle["y_mm"] + rectangle["height_mm"], height):
            raise ValueError(
                "welding area %s extends past the rear face" % rectangle["area_id"]
            )
        for other in areas:
            if _rectangles_overlap(rectangle, other):
                raise ValueError(
                    "welding areas %s and %s overlap, so the governed area "
                    "cannot be sized" % (rectangle["area_id"], other["area_id"])
                )
        areas.append(rectangle)
    rear_area = width * height
    welded_area = sum(area["area_mm2"] for area in areas)
    governed = rear_area - welded_area
    if not governed > 0.0 or math.isclose(
        governed, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "the declared welding areas cover the whole rear face, so the "
            "clause governs no area at all and grading it would be vacuous"
        )
    return {
        "width_mm": width,
        "height_mm": height,
        "rear_area_mm2": rear_area,
        "welding_area_mm2": welded_area,
        "governed_area_mm2": governed,
        "welding_areas": areas,
    }


def deposit_footprint(deposit):
    """Read one deposit record as a footprint on the rear face."""
    if not isinstance(deposit, dict):
        raise ValueError("deposit record must be a mapping, got %r" % (deposit,))
    deposit_id = _require_text("deposit_id", deposit.get("deposit_id"))
    kind = _require_choice("kind", deposit.get("kind"), REAR_DEPOSIT_KINDS)
    x = _require_non_negative("x_mm on %s" % deposit_id, deposit.get("x_mm"))
    y = _require_non_negative("y_mm on %s" % deposit_id, deposit.get("y_mm"))
    diameter = _require_positive(
        "diameter_mm on %s" % deposit_id, deposit.get("diameter_mm")
    )
    standoff = _require_non_negative(
        "standoff_height_mm on %s" % deposit_id,
        deposit.get("standoff_height_mm", 0.0),
    )
    radius = diameter / 2.0
    return {
        "deposit_id": deposit_id,
        "kind": kind,
        "x_mm": x,
        "y_mm": y,
        "radius_mm": radius,
        "diameter_mm": diameter,
        "standoff_height_mm": standoff,
        "covered_area_mm2": math.pi * radius * radius,
    }


def locate_deposit(footprint, welding_areas):
    """Place a deposit by its footprint rather than by its centre."""
    for area in welding_areas:
        inside = (
            _at_least(footprint["x_mm"] - footprint["radius_mm"], area["x_mm"])
            and _at_most(
                footprint["x_mm"] + footprint["radius_mm"],
                area["x_mm"] + area["width_mm"],
            )
            and _at_least(footprint["y_mm"] - footprint["radius_mm"], area["y_mm"])
            and _at_most(
                footprint["y_mm"] + footprint["radius_mm"],
                area["y_mm"] + area["height_mm"],
            )
        )
        if inside:
            return (WITHIN_WELDING_AREA, area["area_id"])
    for area in welding_areas:
        dx = max(
            area["x_mm"] - footprint["x_mm"],
            0.0,
            footprint["x_mm"] - (area["x_mm"] + area["width_mm"]),
        )
        dy = max(
            area["y_mm"] - footprint["y_mm"],
            0.0,
            footprint["y_mm"] - (area["y_mm"] + area["height_mm"]),
        )
        if dx * dx + dy * dy < footprint["radius_mm"] * footprint["radius_mm"]:
            return (STRADDLING_WELDING_BOUNDARY, area["area_id"])
    return (OUTSIDE_WELDING_AREA, None)


def assess_rear_deposit(deposit, welding_areas, limits=DEFAULT_REAR_DEPOSIT_LIMITS):
    """Grade one deposit against the size allowed for its kind."""
    validate_rear_deposit_limits(limits)
    footprint = deposit_footprint(deposit)
    placement, area_id = locate_deposit(footprint, welding_areas)
    result = dict(footprint)
    result["placement"] = placement
    result["welding_area_id"] = area_id
    result["findings"] = []
    result["governed"] = placement != WITHIN_WELDING_AREA
    if not result["governed"]:
        result["verdict"] = ACCEPT
        return result

    factor = float(limits["review_margin_factor"])
    dispositions = [ACCEPT]
    for label, measured, allowed in (
        (
            "diameter",
            footprint["diameter_mm"],
            float(limits["max_diameter_mm"][footprint["kind"]]),
        ),
        (
            "standoff height",
            footprint["standoff_height_mm"],
            float(limits["max_standoff_height_mm"][footprint["kind"]]),
        ),
    ):
        if _at_most(measured, allowed):
            continue
        if allowed == 0.0:
            dispositions.append(REJECT)
            result["findings"].append(
                "%s %s %.3f mm outside the welding area; no %s is permitted "
                "there at any size"
                % (footprint["kind"], label, measured, footprint["kind"])
            )
        elif _at_most(measured, allowed * factor):
            dispositions.append(REFER)
            result["findings"].append(
                "%s %s %.3f mm is past the %.3f mm allowed outside the welding "
                "area" % (footprint["kind"], label, measured, allowed)
            )
        else:
            dispositions.append(REJECT)
            result["findings"].append(
                "%s %s %.3f mm is past the %.3f mm review margin on an "
                "allowance of %.3f mm"
                % (footprint["kind"], label, measured, allowed * factor, allowed)
            )
    if placement == STRADDLING_WELDING_BOUNDARY:
        result["findings"].append(
            "the footprint reaches across the boundary of welding area %s, so "
            "it is graded as an outside deposit" % area_id
        )
    result["verdict"] = _worst(dispositions)
    return result


def inspect_rear_contact(assembly, limits=DEFAULT_REAR_DEPOSIT_LIMITS):
    """Clause 6.4.3.1.8 size screen for one solar cell assembly rear contact."""
    validate_rear_deposit_limits(limits)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = _require_text("assembly_id", assembly.get("assembly_id"))
    layout = welding_area_layout(assembly.get("rear_face"))
    records = assembly.get("deposits")
    if not isinstance(records, (list, tuple)):
        raise ValueError("deposits must be a list, got %r" % (records,))

    graded = []
    seen = set()
    findings = []
    for record in records:
        result = assess_rear_deposit(record, layout["welding_areas"], limits)
        if result["deposit_id"] in seen:
            raise ValueError(
                "duplicate deposit id %r on assembly %s"
                % (result["deposit_id"], assembly_id)
            )
        seen.add(result["deposit_id"])
        if not _at_most(
            result["x_mm"] + result["radius_mm"], layout["width_mm"]
        ) or not _at_most(
            result["y_mm"] + result["radius_mm"], layout["height_mm"]
        ):
            raise ValueError(
                "deposit %s reaches past the rear face of assembly %s"
                % (result["deposit_id"], assembly_id)
            )
        graded.append(result)
        for finding in result["findings"]:
            findings.append("%s %s" % (result["deposit_id"], finding))

    governed = [result for result in graded if result["governed"]]
    exempt = [result for result in graded if not result["governed"]]
    covered = sum(result["covered_area_mm2"] for result in governed)
    covered_fraction = covered / layout["governed_area_mm2"]

    dispositions = [result["verdict"] for result in graded] or [ACCEPT]
    allowed_fraction = float(limits["max_covered_fraction"])
    factor = float(limits["review_margin_factor"])
    if not _at_most(covered_fraction, allowed_fraction):
        if _at_most(covered_fraction, allowed_fraction * factor):
            dispositions.append(REFER)
            findings.append(
                "deposits outside the welding area cover %.5f of the governed "
                "rear area, past the %.5f allowed even though no single one "
                "was oversize" % (covered_fraction, allowed_fraction)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "deposits outside the welding area cover %.5f of the governed "
                "rear area, past the %.5f review margin"
                % (covered_fraction, allowed_fraction * factor)
            )

    counts = dict((state, 0) for state in REAR_DISPOSITIONS)
    for result in graded:
        counts[result["verdict"]] += 1

    return {
        "assembly_id": assembly_id,
        "verdict": _worst(dispositions),
        "rear_area_mm2": layout["rear_area_mm2"],
        "welding_area_mm2": layout["welding_area_mm2"],
        "governed_area_mm2": layout["governed_area_mm2"],
        "deposit_count": len(graded),
        "governed_deposit_count": len(governed),
        "within_welding_area_ids": [result["deposit_id"] for result in exempt],
        "straddling_ids": [
            result["deposit_id"]
            for result in graded
            if result["placement"] == STRADDLING_WELDING_BOUNDARY
        ],
        "covered_area_mm2": covered,
        "covered_fraction": covered_fraction,
        "disposition_counts": counts,
        "not_accepted_ids": [
            result["deposit_id"] for result in graded if result["verdict"] != ACCEPT
        ],
        "deposits": graded,
        "findings": findings,
    }
