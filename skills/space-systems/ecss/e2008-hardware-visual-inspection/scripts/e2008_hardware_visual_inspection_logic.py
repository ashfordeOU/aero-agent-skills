#!/usr/bin/env python3
"""Visual inspection of terminal boards and other coupon hardware.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.19. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks whether the terminal boards and the other hardware on a
coupon are positioned the way the coupon assembly drawing requires.
Position here is four measurements, not one, because a piece of
hardware can be in the right spot and still be wrong:

    placement   the measured centre against the drawing centre, taken
                as a true-position radial offset.
    orientation the measured rotation against the drawing rotation,
                wrapped to the shorter way round. A board a few degrees
                out puts its terminals off the harness run even though
                its centre has not moved.
    retention   the fasteners actually installed against the fasteners
                the drawing calls for, as a completeness fraction.
                Hardware sitting in the right place and held by three
                of four fasteners is not positioned, it is resting.
    clearance   the measured gap to the nearest stay-out boundary
                against the minimum the drawing protects. A gap of zero
                or less is interference, and no tolerance reaches it.

A short list is decided by presence alone: an item the drawing calls
out and the coupon does not carry, an item interfering with a stay-out
boundary, and an item free to move. Measuring those more carefully
cannot change the answer.

Condition kinds
    placement-offset          centre off the drawing location
    angular-deviation         rotation off the drawing orientation
    retention-shortfall       fasteners short of the drawing count
    clearance-encroachment    gap under the protected minimum
    adhesive-fillet-void      gas pocket in a bonded fitting fillet
    surface-contamination     residue or particulate on the fitting
    missing-hardware-item     drawing calls it, coupon has none
    stay-out-interference     item inside a protected boundary
    unsecured-hardware-item   free to move, not tolerated

Zones
    cell-field-margin      the land next to the active cell field
    substrate-rear-face    the harness side of the substrate
    panel-edge-member      the edge closeout
    harness-run-corridor   the lane the harness is dressed along

Dispositions are accept, rework and reject. The limits below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HARDWARE_TYPES = (
    "terminal-board",
    "mounting-bracket",
    "standoff",
    "connector-shell",
    "cable-clamp",
    "tie-down-anchor",
)

HARDWARE_CONDITION_KINDS = (
    "placement-offset",
    "angular-deviation",
    "retention-shortfall",
    "clearance-encroachment",
    "adhesive-fillet-void",
    "surface-contamination",
    "missing-hardware-item",
    "stay-out-interference",
    "unsecured-hardware-item",
)

NOT_TOLERATED_KINDS = (
    "missing-hardware-item",
    "stay-out-interference",
    "unsecured-hardware-item",
)

HARDWARE_ZONES = (
    "cell-field-margin",
    "substrate-rear-face",
    "panel-edge-member",
    "harness-run-corridor",
)

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

_GRADED_AREA_KINDS = (
    "adhesive-fillet-void",
    "surface-contamination",
)

DEFAULT_HARDWARE_CRITERIA = {
    # True-position radial offset from the drawing centre.
    "accept_placement_offset_mm": 1.00,
    "rework_placement_offset_mm": 3.00,
    # Rotation off the drawing orientation, shorter way round.
    "accept_angular_deviation_deg": 1.00,
    "rework_angular_deviation_deg": 5.00,
    # Fasteners installed over fasteners the drawing calls for.
    # A minimum, never scaled by the zone factor.
    "accept_retention_fraction": 1.00,
    "rework_retention_fraction": 0.75,
    # Gap to the nearest stay-out boundary. Also a minimum.
    "min_clearance_mm": 2.00,
    "rework_clearance_mm": 1.00,
    "accept_area_mm2": {
        "adhesive-fillet-void": 2.0,
        "surface-contamination": 6.0,
    },
    "rework_area_mm2": {
        "adhesive-fillet-void": 10.0,
        "surface-contamination": 45.0,
    },
    # Applies to allowances only - offsets, angles and areas.
    "zone_tolerance_factor": {
        "cell-field-margin": 0.5,
        "substrate-rear-face": 1.0,
        "panel-edge-member": 0.75,
        "harness-run-corridor": 0.75,
    },
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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_point(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be an (x, y) pair, got %r" % (name, value))
    if len(value) != 2:
        raise ValueError("%s must hold exactly two coordinates" % name)
    return (
        _require_number("%s x" % name, value[0]),
        _require_number("%s y" % name, value[1]),
    )


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a product of a criteria value and a zone factor and a
    measurement is a root-sum-square or a wrapped angle, so a value
    sitting exactly on the limit can evaluate a few units in the last
    place above it. The limit is never raised; only the comparison
    tolerates the representation error.
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


def validate_hardware_criteria(criteria):
    """Check a criteria set is complete and internally ordered."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    table_specs = (
        ("accept_area_mm2", _GRADED_AREA_KINDS),
        ("rework_area_mm2", _GRADED_AREA_KINDS),
        ("zone_tolerance_factor", HARDWARE_ZONES),
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
    for kind in _GRADED_AREA_KINDS:
        if criteria["rework_area_mm2"][kind] < criteria["accept_area_mm2"][kind]:
            raise ValueError(
                "criteria rework_area_mm2[%s] is below the accept limit" % kind
            )
    for zone in HARDWARE_ZONES:
        _require_positive(
            "criteria zone_tolerance_factor[%s]" % zone,
            criteria["zone_tolerance_factor"][zone],
        )
    allowance_pairs = (
        ("accept_placement_offset_mm", "rework_placement_offset_mm"),
        ("accept_angular_deviation_deg", "rework_angular_deviation_deg"),
    )
    for accept_key, rework_key in allowance_pairs:
        accept_value = _require_positive(accept_key, criteria.get(accept_key))
        rework_value = _require_positive(rework_key, criteria.get(rework_key))
        if rework_value < accept_value and not _close(rework_value, accept_value):
            raise ValueError("criteria %s is below %s" % (rework_key, accept_key))
    minimum_pairs = (
        ("accept_retention_fraction", "rework_retention_fraction"),
        ("min_clearance_mm", "rework_clearance_mm"),
    )
    for minimum_key, floor_key in minimum_pairs:
        minimum_value = _require_positive(minimum_key, criteria.get(minimum_key))
        floor_value = _require_positive(floor_key, criteria.get(floor_key))
        if floor_value > minimum_value and not _close(floor_value, minimum_value):
            raise ValueError("criteria %s is above %s" % (floor_key, minimum_key))
    if criteria["accept_retention_fraction"] > 1.0 and not _close(
        criteria["accept_retention_fraction"], 1.0
    ):
        raise ValueError("criteria accept_retention_fraction cannot exceed one")
    return criteria


def zone_tolerance_factor(zone, criteria=DEFAULT_HARDWARE_CRITERIA):
    """Factor the zone applies to every allowance; below one is stricter."""
    _require_choice("zone", zone, HARDWARE_ZONES)
    return float(criteria["zone_tolerance_factor"][zone])


def placement_offset_mm(nominal_position_mm, measured_position_mm):
    """True-position radial offset of the item from its drawing centre."""
    nominal = _require_point("nominal_position_mm", nominal_position_mm)
    measured = _require_point("measured_position_mm", measured_position_mm)
    return math.hypot(measured[0] - nominal[0], measured[1] - nominal[1])


def angular_deviation_deg(nominal_orientation_deg, measured_orientation_deg):
    """Rotation error taken the shorter way round the circle.

    Orientations are reported on an open scale, so a board drawn at 359
    degrees and fitted at 1 degree is two degrees out, not 358. The
    difference is wrapped into a half turn and returned as a magnitude.
    """
    nominal = _require_number(
        "nominal_orientation_deg", nominal_orientation_deg
    )
    measured = _require_number(
        "measured_orientation_deg", measured_orientation_deg
    )
    wrapped = (measured - nominal + 180.0) % 360.0 - 180.0
    return abs(wrapped)


def retention_completeness_fraction(fasteners_installed, fasteners_required):
    """Share of the drawing fastener count that is actually installed."""
    required = _require_count("fasteners_required", fasteners_required)
    if required == 0:
        raise ValueError(
            "fasteners_required must be at least one; an item held by no "
            "fastener is graded on its bond, not on its retention"
        )
    installed = _require_count("fasteners_installed", fasteners_installed)
    if installed > required:
        raise ValueError(
            "%d fasteners installed against a drawing count of %d; the count "
            "or the drawing is wrong" % (installed, required)
        )
    return float(installed) / float(required)


def clearance_margin_mm(
    measured_clearance_mm, criteria=DEFAULT_HARDWARE_CRITERIA
):
    """Measured gap to the stay-out boundary less the protected minimum."""
    measured = _require_number("measured_clearance_mm", measured_clearance_mm)
    return measured - float(criteria["min_clearance_mm"])


def is_interfering(measured_clearance_mm):
    """True when the item has reached or crossed the stay-out boundary."""
    measured = _require_number("measured_clearance_mm", measured_clearance_mm)
    return measured < 0.0 or _close(measured, 0.0)


def reconcile_hardware_inventory(required_ids, observed_ids):
    """Split the drawing list and the observed list before grading anything."""
    for name, values in (
        ("required_ids", required_ids),
        ("observed_ids", observed_ids),
    ):
        if isinstance(values, (str, bytes)) or not isinstance(
            values, (list, tuple)
        ):
            raise ValueError("%s must be a list, got %r" % (name, values))
        seen = []
        for value in values:
            _require_label("%s entry" % name, value)
            if value in seen:
                raise ValueError("%s repeats %r" % (name, value))
            seen.append(value)
    fitted = [marker for marker in required_ids if marker in observed_ids]
    missing = [marker for marker in required_ids if marker not in observed_ids]
    undrawn = [marker for marker in observed_ids if marker not in required_ids]
    return {
        "fitted": fitted,
        "missing": missing,
        "undrawn": undrawn,
        "complete": not missing and not undrawn,
    }


def assess_placement(offset_mm, zone, criteria=DEFAULT_HARDWARE_CRITERIA):
    """Disposition a true-position offset against the zone-scaled limits."""
    validate_hardware_criteria(criteria)
    offset = _require_non_negative("offset_mm", offset_mm)
    factor = zone_tolerance_factor(zone, criteria)
    accept_limit = criteria["accept_placement_offset_mm"] * factor
    rework_limit = criteria["rework_placement_offset_mm"] * factor
    measurements = {
        "placement_offset_mm": offset,
        "accept_placement_offset_mm": accept_limit,
        "rework_placement_offset_mm": rework_limit,
    }
    if _at_most(offset, accept_limit):
        return {"disposition": ACCEPT, "measurements": measurements, "reasons": []}
    if _at_most(offset, rework_limit):
        return {
            "disposition": REWORK,
            "measurements": measurements,
            "reasons": [
                "placement offset %.3f mm exceeds the %.3f mm accept limit in "
                "the %s zone; the item can be released and reset"
                % (offset, accept_limit, zone)
            ],
        }
    return {
        "disposition": REJECT,
        "measurements": measurements,
        "reasons": [
            "placement offset %.3f mm exceeds the %.3f mm rework limit in the "
            "%s zone; the drawing location was not used"
            % (offset, rework_limit, zone)
        ],
    }


def assess_orientation(deviation_deg, zone, criteria=DEFAULT_HARDWARE_CRITERIA):
    """Disposition a wrapped rotation error against the zone-scaled limits."""
    validate_hardware_criteria(criteria)
    deviation = _require_non_negative("deviation_deg", deviation_deg)
    factor = zone_tolerance_factor(zone, criteria)
    accept_limit = criteria["accept_angular_deviation_deg"] * factor
    rework_limit = criteria["rework_angular_deviation_deg"] * factor
    measurements = {
        "angular_deviation_deg": deviation,
        "accept_angular_deviation_deg": accept_limit,
        "rework_angular_deviation_deg": rework_limit,
    }
    if _at_most(deviation, accept_limit):
        return {"disposition": ACCEPT, "measurements": measurements, "reasons": []}
    if _at_most(deviation, rework_limit):
        return {
            "disposition": REWORK,
            "measurements": measurements,
            "reasons": [
                "rotation %.3f deg exceeds the %.3f deg accept limit in the %s "
                "zone; the terminals are off the harness run"
                % (deviation, accept_limit, zone)
            ],
        }
    return {
        "disposition": REJECT,
        "measurements": measurements,
        "reasons": [
            "rotation %.3f deg exceeds the %.3f deg rework limit in the %s "
            "zone; the item is not on its drawing orientation"
            % (deviation, rework_limit, zone)
        ],
    }


def assess_retention(
    fasteners_installed, fasteners_required, criteria=DEFAULT_HARDWARE_CRITERIA
):
    """Disposition the item on how much of its retention was installed."""
    validate_hardware_criteria(criteria)
    fraction = retention_completeness_fraction(
        fasteners_installed, fasteners_required
    )
    measurements = {
        "retention_completeness_fraction": fraction,
        "fasteners_installed": fasteners_installed,
        "fasteners_required": fasteners_required,
        "accept_retention_fraction": criteria["accept_retention_fraction"],
    }
    if _at_least(fraction, criteria["accept_retention_fraction"]):
        return {"disposition": ACCEPT, "measurements": measurements, "reasons": []}
    if _at_least(fraction, criteria["rework_retention_fraction"]):
        return {
            "disposition": REWORK,
            "measurements": measurements,
            "reasons": [
                "%d of %d fasteners installed against a required fraction of "
                "%.3f; the item is resting rather than retained and the "
                "remainder can still be fitted"
                % (
                    fasteners_installed,
                    fasteners_required,
                    criteria["accept_retention_fraction"],
                )
            ],
        }
    return {
        "disposition": REJECT,
        "measurements": measurements,
        "reasons": [
            "%d of %d fasteners installed, under the %.3f rework floor; the "
            "item was not built to the drawing"
            % (
                fasteners_installed,
                fasteners_required,
                criteria["rework_retention_fraction"],
            )
        ],
    }


def assess_clearance(
    measured_clearance_mm, criteria=DEFAULT_HARDWARE_CRITERIA
):
    """Disposition the gap to the nearest protected stay-out boundary."""
    validate_hardware_criteria(criteria)
    measured = _require_number("measured_clearance_mm", measured_clearance_mm)
    margin = clearance_margin_mm(measured, criteria)
    interfering = is_interfering(measured)
    measurements = {
        "measured_clearance_mm": measured,
        "min_clearance_mm": criteria["min_clearance_mm"],
        "clearance_margin_mm": margin,
    }
    if interfering:
        return {
            "disposition": REJECT,
            "tolerated": False,
            "measurements": measurements,
            "reasons": [
                "the item has reached the stay-out boundary at %.3f mm; "
                "interference carries no allowance and no tolerance reaches it"
                % measured
            ],
        }
    if _at_least(measured, criteria["min_clearance_mm"]):
        return {
            "disposition": ACCEPT,
            "tolerated": True,
            "measurements": measurements,
            "reasons": [],
        }
    if _at_least(measured, criteria["rework_clearance_mm"]):
        return {
            "disposition": REWORK,
            "tolerated": True,
            "measurements": measurements,
            "reasons": [
                "clearance %.3f mm is under the %.3f mm protected minimum; the "
                "item can be shifted back off the boundary"
                % (measured, criteria["min_clearance_mm"])
            ],
        }
    return {
        "disposition": REJECT,
        "tolerated": True,
        "measurements": measurements,
        "reasons": [
            "clearance %.3f mm is under the %.3f mm rework floor; the item sits "
            "inside the lane the drawing protects"
            % (measured, criteria["rework_clearance_mm"])
        ],
    }


def assess_hardware_condition(condition, criteria=DEFAULT_HARDWARE_CRITERIA):
    """Disposition one additional indication logged against an item."""
    validate_hardware_criteria(criteria)
    if not isinstance(condition, dict):
        raise ValueError("condition must be a mapping, got %r" % (condition,))
    kind = _require_choice(
        "kind", condition.get("kind"), HARDWARE_CONDITION_KINDS
    )
    zone = _require_choice("zone", condition.get("zone"), HARDWARE_ZONES)
    factor = zone_tolerance_factor(zone, criteria)
    tolerated = kind not in NOT_TOLERATED_KINDS
    measurements = {}
    reasons = []

    if kind in NOT_TOLERATED_KINDS:
        disposition = REJECT
        reasons.append(
            "%s carries no allowance; presence alone decides and no "
            "measurement can bring it back" % kind
        )
    elif kind in _GRADED_AREA_KINDS:
        area = _require_non_negative("area_mm2", condition.get("area_mm2"))
        accept_area = criteria["accept_area_mm2"][kind] * factor
        rework_area = criteria["rework_area_mm2"][kind] * factor
        measurements["area_mm2"] = area
        measurements["accept_area_mm2"] = accept_area
        measurements["rework_area_mm2"] = rework_area
        if _at_most(area, accept_area):
            disposition = ACCEPT
        elif _at_most(area, rework_area):
            disposition = REWORK
            reasons.append(
                "area %.3f mm2 exceeds the %.3f mm2 accept limit for %s in the "
                "%s zone" % (area, accept_area, kind, zone)
            )
        else:
            disposition = REJECT
            reasons.append(
                "area %.3f mm2 exceeds the %.3f mm2 rework limit for %s in the "
                "%s zone" % (area, rework_area, kind, zone)
            )
    else:
        raise ValueError(
            "%s is measured on the hardware record itself, not logged as a "
            "separate condition; supply the placement, orientation, retention "
            "or clearance measurements" % kind
        )

    return {
        "id": condition.get("id"),
        "kind": kind,
        "zone": zone,
        "tolerated": tolerated,
        "disposition": disposition,
        "measurements": measurements,
        "reasons": reasons,
    }


def group_hardware_by_type(items):
    """Group hardware records by the kind of fitting they describe."""
    if isinstance(items, (str, bytes)) or not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list, got %r" % (items,))
    counts = dict((hardware_type, 0) for hardware_type in HARDWARE_TYPES)
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be a mapping, got %r" % (item,))
        hardware_type = _require_choice(
            "hardware_type", item.get("hardware_type"), HARDWARE_TYPES
        )
        counts[hardware_type] += 1
    return {"counts": counts, "recorded": sum(counts.values())}


def assess_hardware_item(item, criteria=DEFAULT_HARDWARE_CRITERIA):
    """Roll placement, orientation, retention and clearance into one call."""
    validate_hardware_criteria(criteria)
    if not isinstance(item, dict):
        raise ValueError("hardware record must be a mapping, got %r" % (item,))
    marker = item.get("hardware_id")
    if not isinstance(marker, str) or not marker.strip():
        raise ValueError(
            "a hardware record needs a non-empty hardware_id so the rework "
            "record has something to attach to"
        )
    hardware_type = _require_choice(
        "hardware_type", item.get("hardware_type"), HARDWARE_TYPES
    )
    zone = _require_choice("zone", item.get("zone"), HARDWARE_ZONES)

    offset = placement_offset_mm(
        item.get("nominal_position_mm"), item.get("measured_position_mm")
    )
    placement = assess_placement(offset, zone, criteria)
    rotation = angular_deviation_deg(
        item.get("nominal_orientation_deg", 0.0),
        item.get("measured_orientation_deg", 0.0),
    )
    orientation = assess_orientation(rotation, zone, criteria)
    retention = assess_retention(
        item.get("fasteners_installed"), item.get("fasteners_required"), criteria
    )
    clearance = assess_clearance(item.get("measured_clearance_mm"), criteria)

    conditions = item.get("conditions", [])
    if isinstance(conditions, (str, bytes)) or not isinstance(
        conditions, (list, tuple)
    ):
        raise ValueError(
            "hardware conditions must be a list, got %r" % (conditions,)
        )
    assessed = [
        assess_hardware_condition(condition, criteria)
        for condition in conditions
    ]

    reasons = (
        list(placement["reasons"])
        + list(orientation["reasons"])
        + list(retention["reasons"])
        + list(clearance["reasons"])
    )
    calls = [
        placement["disposition"],
        orientation["disposition"],
        retention["disposition"],
        clearance["disposition"],
    ]
    for result in assessed:
        calls.append(result["disposition"])
        for reason in result["reasons"]:
            reasons.append("%s: %s" % (result["id"], reason))

    blocking = [result["id"] for result in assessed if not result["tolerated"]]

    measurements = {}
    for leg in (placement, orientation, retention, clearance):
        measurements.update(leg["measurements"])

    return {
        "hardware_id": marker,
        "hardware_type": hardware_type,
        "zone": zone,
        "disposition": _worst(calls),
        "placement_disposition": placement["disposition"],
        "orientation_disposition": orientation["disposition"],
        "retention_disposition": retention["disposition"],
        "clearance_disposition": clearance["disposition"],
        "as_drawn": placement["disposition"] == ACCEPT
        and orientation["disposition"] == ACCEPT,
        "fully_retained": retention["disposition"] == ACCEPT,
        "interfering": not clearance["tolerated"],
        "measurements": measurements,
        "conditions": assessed,
        "not_tolerated_ids": blocking,
        "reasons": reasons,
    }


def inspect_coupon_hardware(coupon, criteria=DEFAULT_HARDWARE_CRITERIA):
    """Full clause 5.5.3.2.19 screen with a coupon-level verdict."""
    validate_hardware_criteria(criteria)
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    coupon_id = coupon.get("coupon_id")
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon needs a non-empty coupon_id for traceability")
    items = coupon.get("hardware")
    if isinstance(items, (str, bytes)) or not isinstance(items, (list, tuple)):
        raise ValueError("coupon hardware must be a list, got %r" % (items,))

    observed = []
    assessed = []
    for item in items:
        result = assess_hardware_item(item, criteria)
        if result["hardware_id"] in observed:
            raise ValueError(
                "duplicate hardware_id %r on coupon %s; traceability to the "
                "rework record would be lost"
                % (result["hardware_id"], coupon_id)
            )
        observed.append(result["hardware_id"])
        assessed.append(result)

    required = coupon.get("drawing_hardware_ids", [])
    if isinstance(required, (str, bytes)) or not isinstance(
        required, (list, tuple)
    ):
        raise ValueError(
            "drawing_hardware_ids must be a list, got %r" % (required,)
        )
    if required:
        inventory = reconcile_hardware_inventory(required, observed)
    else:
        inventory = {
            "fitted": list(observed),
            "missing": [],
            "undrawn": [],
            "complete": True,
        }

    grouping = group_hardware_by_type(list(items))
    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    findings = []

    if not assessed:
        findings.append(
            "no hardware records on the coupon; an examined and clean coupon "
            "still carries the record that is the inspection evidence"
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["hardware_id"], reason))

    blocking = [
        result["hardware_id"]
        for result in assessed
        if result["not_tolerated_ids"] or result["interfering"]
    ]
    if blocking:
        findings.append(
            "not-tolerated conditions on %s; those items cannot be "
            "dispositioned by size" % ", ".join(blocking)
        )
    if inventory["missing"]:
        verdict = REJECT
        findings.append(
            "the drawing calls out %s and the coupon carries no such item; a "
            "fitting that is not there has no position to measure"
            % ", ".join(inventory["missing"])
        )
    if inventory["undrawn"]:
        verdict = REJECT
        findings.append(
            "%s was fitted with no matching item on the drawing"
            % ", ".join(inventory["undrawn"])
        )

    return {
        "coupon_id": coupon_id,
        "verdict": verdict,
        "hardware": assessed,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "missing_hardware_ids": inventory["missing"],
        "undrawn_hardware_ids": inventory["undrawn"],
        "not_tolerated_hardware_ids": blocking,
        "type_counts": grouping["counts"],
        "inventory_complete": inventory["complete"],
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }
