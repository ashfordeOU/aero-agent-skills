#!/usr/bin/env python3
"""Visual inspection of a solar-array substrate for induced damage.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause looks at the substrate itself rather than the cells on it:
the panel is examined for damage that the assembly, handling or test
operations put there. Each indication is categorized by kind, measured
(depth into the facesheet and damaged area), placed in a panel zone and
attributed to the operation that produced it, then dispositioned.

Indication kinds
    facesheet-scratch        a gouge along the facesheet surface
    facesheet-dent           a local depression with no fibre break
    facesheet-puncture       a hole driven through the facesheet
    honeycomb-core-crush     core cells collapsed under a point load
    facesheet-core-disbond   facesheet no longer bonded to the core
    insulation-layer-tear    torn dielectric layer under the cell field
    edge-closeout-damage     damage to the panel edge member
    insert-damage            a bonded insert pulled, spun or cracked

Zones
    cell-bonding-footprint   under the cells: bond line and dielectric
    free-facesheet-area      open facesheet carrying no cells
    panel-edge-closeout      the edge member and its bond
    insert-region            around a bonded insert

Source operations
    assembly, handling, test -- attribution is mandatory, because the
    corrective action lands on the operation, not on the panel.

Dispositions are accept, repair and reject. The limits below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SUBSTRATE_INDICATION_KINDS = (
    "facesheet-scratch",
    "facesheet-dent",
    "facesheet-puncture",
    "honeycomb-core-crush",
    "facesheet-core-disbond",
    "insulation-layer-tear",
    "edge-closeout-damage",
    "insert-damage",
)

SUBSTRATE_ZONES = (
    "cell-bonding-footprint",
    "free-facesheet-area",
    "panel-edge-closeout",
    "insert-region",
)

SOURCE_OPERATIONS = ("assembly", "handling", "test")

ACCEPT = "accept"
REPAIR = "repair"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REPAIR, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REPAIR: 1, REJECT: 2}

DEFAULT_SUBSTRATE_CRITERIA = {
    "accept_depth_fraction": {
        "facesheet-scratch": 0.10,
        "facesheet-dent": 0.08,
        "facesheet-puncture": 0.0,
        "honeycomb-core-crush": 0.0,
        "facesheet-core-disbond": 0.0,
        "insulation-layer-tear": 0.0,
        "edge-closeout-damage": 0.15,
        "insert-damage": 0.0,
    },
    "repair_depth_fraction": {
        "facesheet-scratch": 0.30,
        "facesheet-dent": 0.25,
        "facesheet-puncture": 1.50,
        "honeycomb-core-crush": 3.00,
        "facesheet-core-disbond": 1.00,
        "insulation-layer-tear": 1.00,
        "edge-closeout-damage": 1.00,
        "insert-damage": 1.00,
    },
    "accept_area_mm2": {
        "facesheet-scratch": 50.0,
        "facesheet-dent": 25.0,
        "facesheet-puncture": 0.0,
        "honeycomb-core-crush": 0.0,
        "facesheet-core-disbond": 0.0,
        "insulation-layer-tear": 0.0,
        "edge-closeout-damage": 100.0,
        "insert-damage": 0.0,
    },
    "repair_area_mm2": {
        "facesheet-scratch": 400.0,
        "facesheet-dent": 300.0,
        "facesheet-puncture": 100.0,
        "honeycomb-core-crush": 600.0,
        "facesheet-core-disbond": 800.0,
        "insulation-layer-tear": 200.0,
        "edge-closeout-damage": 1000.0,
        "insert-damage": 150.0,
    },
    "zone_severity_factor": {
        "cell-bonding-footprint": 0.5,
        "free-facesheet-area": 1.0,
        "panel-edge-closeout": 1.0,
        "insert-region": 0.5,
    },
    "through_facesheet_under_cells_rejects": True,
    "panel_repair_area_fraction": 0.02,
    "panel_reject_area_fraction": 0.05,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a product of a measured size and a severity factor, so a
    measurement that sits exactly on the limit can evaluate a few units
    in the last place above it. The limit itself is never raised; only
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


def validate_substrate_criteria(criteria):
    """Check an inspection criteria set covers every kind and zone."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    table_specs = (
        ("accept_depth_fraction", SUBSTRATE_INDICATION_KINDS),
        ("repair_depth_fraction", SUBSTRATE_INDICATION_KINDS),
        ("accept_area_mm2", SUBSTRATE_INDICATION_KINDS),
        ("repair_area_mm2", SUBSTRATE_INDICATION_KINDS),
        ("zone_severity_factor", SUBSTRATE_ZONES),
    )
    for key, keys_needed in table_specs:
        table = criteria.get(key)
        if not isinstance(table, dict):
            raise ValueError("criteria %s must be a mapping" % key)
        missing = set(keys_needed) - set(table)
        if missing:
            raise ValueError(
                "criteria %s is missing entries: %s"
                % (key, ", ".join(sorted(missing)))
            )
        for entry in keys_needed:
            _require_non_negative("criteria %s[%s]" % (key, entry), table[entry])
    for kind in SUBSTRATE_INDICATION_KINDS:
        if criteria["repair_depth_fraction"][kind] < criteria["accept_depth_fraction"][kind]:
            raise ValueError(
                "criteria repair_depth_fraction[%s] is below the accept limit" % kind
            )
        if criteria["repair_area_mm2"][kind] < criteria["accept_area_mm2"][kind]:
            raise ValueError(
                "criteria repair_area_mm2[%s] is below the accept limit" % kind
            )
    for zone in SUBSTRATE_ZONES:
        _require_positive(
            "criteria zone_severity_factor[%s]" % zone,
            criteria["zone_severity_factor"][zone],
        )
    repair_fraction = _require_positive(
        "panel_repair_area_fraction", criteria.get("panel_repair_area_fraction")
    )
    reject_fraction = _require_positive(
        "panel_reject_area_fraction", criteria.get("panel_reject_area_fraction")
    )
    if reject_fraction < repair_fraction:
        raise ValueError(
            "criteria panel_reject_area_fraction is below panel_repair_area_fraction"
        )
    return criteria


def depth_fraction(depth_mm, facesheet_thickness_mm):
    """Depth of an indication as a fraction of the facesheet thickness."""
    depth = _require_non_negative("depth_mm", depth_mm)
    thickness = _require_positive("facesheet_thickness_mm", facesheet_thickness_mm)
    return depth / thickness


def zone_severity_factor(zone, criteria=DEFAULT_SUBSTRATE_CRITERIA):
    """Factor the zone applies to every limit; below one means stricter."""
    _require_choice("zone", zone, SUBSTRATE_ZONES)
    return float(criteria["zone_severity_factor"][zone])


def assess_indication(
    indication, facesheet_thickness_mm, criteria=DEFAULT_SUBSTRATE_CRITERIA
):
    """Disposition one substrate indication against the criteria set."""
    validate_substrate_criteria(criteria)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    kind = _require_choice(
        "kind", indication.get("kind"), SUBSTRATE_INDICATION_KINDS
    )
    zone = _require_choice("zone", indication.get("zone"), SUBSTRATE_ZONES)
    operation = _require_choice(
        "operation", indication.get("operation"), SOURCE_OPERATIONS
    )
    depth = _require_non_negative("depth_mm", indication.get("depth_mm"))
    area = _require_non_negative("area_mm2", indication.get("area_mm2"))
    if depth <= 0.0 and area <= 0.0:
        raise ValueError(
            "an indication needs a depth or an area; both are zero for %r"
            % (indication.get("id"),)
        )
    fraction = depth_fraction(depth, facesheet_thickness_mm)
    factor = zone_severity_factor(zone, criteria)

    accept_depth = criteria["accept_depth_fraction"][kind] * factor
    repair_depth = criteria["repair_depth_fraction"][kind] * factor
    accept_area = criteria["accept_area_mm2"][kind] * factor
    repair_area = criteria["repair_area_mm2"][kind] * factor

    reasons = []
    if _at_most(fraction, accept_depth):
        depth_call = ACCEPT
    elif _at_most(fraction, repair_depth):
        depth_call = REPAIR
        reasons.append(
            "depth %.4f of the facesheet exceeds the %.4f accept limit for %s"
            % (fraction, accept_depth, kind)
        )
    else:
        depth_call = REJECT
        reasons.append(
            "depth %.4f of the facesheet exceeds the %.4f repair limit for %s"
            % (fraction, repair_depth, kind)
        )

    if _at_most(area, accept_area):
        area_call = ACCEPT
    elif _at_most(area, repair_area):
        area_call = REPAIR
        reasons.append(
            "area %.1f mm2 exceeds the %.1f mm2 accept limit for %s"
            % (area, accept_area, kind)
        )
    else:
        area_call = REJECT
        reasons.append(
            "area %.1f mm2 exceeds the %.1f mm2 repair limit for %s"
            % (area, repair_area, kind)
        )

    disposition = _worst((depth_call, area_call))
    through = fraction >= 1.0 and not math.isclose(
        fraction, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    if (
        through
        and zone == "cell-bonding-footprint"
        and criteria.get("through_facesheet_under_cells_rejects", True)
    ):
        disposition = REJECT
        reasons.append(
            "damage passes through the facesheet under the cell field, where the "
            "bond line and the dielectric cannot be restored by a surface repair"
        )
    return {
        "id": indication.get("id"),
        "kind": kind,
        "zone": zone,
        "operation": operation,
        "depth_fraction": fraction,
        "area_mm2": area,
        "accept_depth_fraction": accept_depth,
        "repair_depth_fraction": repair_depth,
        "accept_area_mm2": accept_area,
        "repair_area_mm2": repair_area,
        "through_facesheet": through,
        "disposition": disposition,
        "reasons": reasons,
    }


def attribute_damage_operations(indications):
    """Group the indications by the operation that produced them."""
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))
    counts = dict((operation, 0) for operation in SOURCE_OPERATIONS)
    for indication in indications:
        if not isinstance(indication, dict):
            raise ValueError("each indication must be a mapping, got %r" % (indication,))
        operation = _require_choice(
            "operation", indication.get("operation"), SOURCE_OPERATIONS
        )
        counts[operation] += 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    dominant = None
    if ranked[0][1] > 0 and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
        dominant = ranked[0][0]
    return {"counts": counts, "dominant_operation": dominant}


def damaged_area_fraction(indications, panel_area_mm2):
    """Damaged area of the substrate as a fraction of the panel area."""
    panel_area = _require_positive("panel_area_mm2", panel_area_mm2)
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))
    total = 0.0
    for indication in indications:
        if not isinstance(indication, dict):
            raise ValueError("each indication must be a mapping, got %r" % (indication,))
        total += _require_non_negative("area_mm2", indication.get("area_mm2"))
    if not _at_most(total, panel_area):
        raise ValueError(
            "damaged area %.1f mm2 exceeds the panel area %.1f mm2; the survey "
            "or the panel area is wrong" % (total, panel_area)
        )
    return total / panel_area


def inspect_substrate(panel, criteria=DEFAULT_SUBSTRATE_CRITERIA):
    """Full clause 5.5.3.2.5 substrate examination with a panel verdict."""
    validate_substrate_criteria(criteria)
    if not isinstance(panel, dict):
        raise ValueError("panel must be a mapping, got %r" % (panel,))
    substrate_id = panel.get("substrate_id")
    if not isinstance(substrate_id, str) or not substrate_id.strip():
        raise ValueError("panel needs a non-empty substrate_id for traceability")
    panel_area = _require_positive("panel_area_mm2", panel.get("panel_area_mm2"))
    thickness = _require_positive(
        "facesheet_thickness_mm", panel.get("facesheet_thickness_mm")
    )
    indications = panel.get("indications")
    if not isinstance(indications, (list, tuple)):
        raise ValueError("panel indications must be a list, got %r" % (indications,))

    seen = set()
    assessed = []
    for indication in indications:
        result = assess_indication(indication, thickness, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate indication id %r on substrate %s; traceability to "
                    "the repair record would be lost" % (marker, substrate_id)
                )
            seen.add(marker)
        assessed.append(result)

    fraction = damaged_area_fraction(list(indications), panel_area)
    attribution = attribute_damage_operations(list(indications))

    findings = []
    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    if not assessed:
        findings.append(
            "no indications recorded; the substrate is examined and clean, and "
            "the record still stands as the inspection evidence"
        )
    if not _at_most(fraction, criteria["panel_reject_area_fraction"]):
        verdict = REJECT
        findings.append(
            "damaged area fraction %.4f exceeds the panel reject fraction %.4f"
            % (fraction, criteria["panel_reject_area_fraction"])
        )
    elif not _at_most(fraction, criteria["panel_repair_area_fraction"]):
        verdict = _worst((verdict, REPAIR))
        findings.append(
            "damaged area fraction %.4f exceeds the panel repair fraction %.4f"
            % (fraction, criteria["panel_repair_area_fraction"])
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    if attribution["dominant_operation"] is not None and len(assessed) >= 2:
        findings.append(
            "most indications came from the %s operation; the corrective action "
            "belongs there" % attribution["dominant_operation"]
        )
    return {
        "substrate_id": substrate_id,
        "verdict": verdict,
        "indications": assessed,
        "reject_count": calls.count(REJECT),
        "repair_count": calls.count(REPAIR),
        "accept_count": calls.count(ACCEPT),
        "damaged_area_fraction": fraction,
        "operation_counts": attribution["counts"],
        "corrective_action_focus": (
            attribution["dominant_operation"] if len(assessed) >= 2 else None
        ),
        "reinspection_required": verdict == REPAIR,
        "findings": findings,
    }
