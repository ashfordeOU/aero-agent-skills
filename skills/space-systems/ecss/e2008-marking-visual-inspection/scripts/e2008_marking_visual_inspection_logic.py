#!/usr/bin/env python3
"""Visual inspection of identification markings on a photovoltaic coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.18. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks three separate things of the identification markings on
a coupon, and a marking has to satisfy all three:

    presence    every marking the assembly drawing calls out is on the
                part. This is settled before anything is measured, by
                reconciling the drawing list against the observed list.
                A marking that is not there has no measurement to take.
    adhesion    the marking is well adhered. Two figures say so: the
                lifted share of the marking footprint, and the lifted
                share of its perimeter. A label can hold most of its
                area while one edge has peeled, so the two are graded
                apart and rolled up by the worse.
    location    the marking sits where the drawing put it. The
                tolerance on a rectangular marking is a rectangular
                zone, so the governing deviation is the larger of the
                two axis errors, not their root-sum-square. On top of
                the in-plane deviation the face has to match: a
                marking on the wrong face is not a large deviation, it
                is a different marking position entirely.

Legibility rides alongside as a minimum character height, because an
adhered, correctly placed marking that cannot be read identifies
nothing.

Condition kinds
    location-deviation          in-plane offset from the drawing spot
    adhesion-lift               lifted share of the footprint
    edge-lift                   lifted share of the perimeter
    character-height-shortfall  characters under the legibility minimum
    ink-smear                   transferred ink outside the marking
    surface-contamination       residue or particulate on the marking
    missing-marking             drawing calls it, part has none
    wrong-face-marking          applied to a face the drawing did not
    unbonded-marking            free to move, not adhered at all

Surfaces
    cell-stack-face        the illuminated face carrying the cells
    substrate-rear-face    the harness side of the substrate
    panel-edge-member      the edge closeout
    harness-bracket        a fitting the harness is dressed to

Dispositions are accept, rework and reject. The limits below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MARKING_TYPES = (
    "part-number-marking",
    "serial-number-marking",
    "lot-code-marking",
    "polarity-marking",
    "orientation-marking",
    "string-identifier-marking",
)

MARKING_CONDITION_KINDS = (
    "location-deviation",
    "adhesion-lift",
    "edge-lift",
    "character-height-shortfall",
    "ink-smear",
    "surface-contamination",
    "missing-marking",
    "wrong-face-marking",
    "unbonded-marking",
)

NOT_TOLERATED_KINDS = (
    "missing-marking",
    "wrong-face-marking",
    "unbonded-marking",
)

MARKING_SURFACES = (
    "cell-stack-face",
    "substrate-rear-face",
    "panel-edge-member",
    "harness-bracket",
)

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

_GRADED_AREA_KINDS = (
    "ink-smear",
    "surface-contamination",
)

_MEASURED_ON_THE_RECORD = (
    "location-deviation",
    "adhesion-lift",
    "edge-lift",
    "character-height-shortfall",
)

DEFAULT_MARKING_CRITERIA = {
    # Larger of the two axis errors against the drawing spot.
    "accept_location_deviation_mm": 1.00,
    "rework_location_deviation_mm": 4.00,
    # Lifted share of the marking footprint.
    "accept_lifted_area_fraction": 0.02,
    "rework_lifted_area_fraction": 0.15,
    # Lifted share of the marking perimeter.
    "accept_edge_lift_fraction": 0.05,
    "rework_edge_lift_fraction": 0.25,
    # Legibility. A minimum, never scaled by the surface factor.
    "min_character_height_mm": 1.50,
    "rework_character_height_mm": 1.20,
    "accept_area_mm2": {
        "ink-smear": 2.0,
        "surface-contamination": 5.0,
    },
    "rework_area_mm2": {
        "ink-smear": 12.0,
        "surface-contamination": 40.0,
    },
    # Applies to allowances only - deviations and areas. Never to a minimum.
    "surface_tolerance_factor": {
        "cell-stack-face": 0.5,
        "substrate-rear-face": 1.0,
        "panel-edge-member": 0.75,
        "harness-bracket": 1.0,
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

    A limit is a product of a criteria value and a surface factor, so a
    measurement sitting exactly on the limit can evaluate a few units in
    the last place above it. The limit is never raised; only the
    comparison tolerates the representation error.
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


def validate_marking_criteria(criteria):
    """Check a criteria set is complete and internally ordered."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    table_specs = (
        ("accept_area_mm2", _GRADED_AREA_KINDS),
        ("rework_area_mm2", _GRADED_AREA_KINDS),
        ("surface_tolerance_factor", MARKING_SURFACES),
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
    for surface in MARKING_SURFACES:
        _require_positive(
            "criteria surface_tolerance_factor[%s]" % surface,
            criteria["surface_tolerance_factor"][surface],
        )
    ordered_pairs = (
        ("accept_location_deviation_mm", "rework_location_deviation_mm"),
        ("accept_lifted_area_fraction", "rework_lifted_area_fraction"),
        ("accept_edge_lift_fraction", "rework_edge_lift_fraction"),
    )
    for accept_key, rework_key in ordered_pairs:
        accept_value = _require_non_negative(accept_key, criteria.get(accept_key))
        rework_value = _require_non_negative(rework_key, criteria.get(rework_key))
        if rework_value < accept_value and not _close(rework_value, accept_value):
            raise ValueError("criteria %s is below %s" % (rework_key, accept_key))
    for key in ("accept_lifted_area_fraction", "accept_edge_lift_fraction"):
        if criteria[key] > 1.0 and not _close(criteria[key], 1.0):
            raise ValueError("criteria %s cannot exceed one" % key)
    minimum_height = _require_positive(
        "min_character_height_mm", criteria.get("min_character_height_mm")
    )
    rework_height = _require_positive(
        "rework_character_height_mm", criteria.get("rework_character_height_mm")
    )
    if rework_height > minimum_height and not _close(rework_height, minimum_height):
        raise ValueError(
            "criteria rework_character_height_mm is above the legibility minimum"
        )
    return criteria


def surface_tolerance_factor(surface, criteria=DEFAULT_MARKING_CRITERIA):
    """Factor the surface applies to every allowance; below one is stricter."""
    _require_choice("surface", surface, MARKING_SURFACES)
    return float(criteria["surface_tolerance_factor"][surface])


def lifted_area_fraction(lifted_area_mm2, marking_area_mm2):
    """Share of the marking footprint that has lifted from the surface."""
    footprint = _require_positive("marking_area_mm2", marking_area_mm2)
    lifted = _require_non_negative("lifted_area_mm2", lifted_area_mm2)
    if not _at_most(lifted, footprint):
        raise ValueError(
            "lifted area %.3f mm2 exceeds the marking footprint %.3f mm2; the "
            "measurement or the footprint is wrong" % (lifted, footprint)
        )
    if lifted > footprint:
        lifted = footprint
    return lifted / footprint


def edge_lift_fraction(edge_lift_length_mm, marking_perimeter_mm):
    """Share of the marking perimeter that has lifted."""
    perimeter = _require_positive("marking_perimeter_mm", marking_perimeter_mm)
    lifted = _require_non_negative("edge_lift_length_mm", edge_lift_length_mm)
    if not _at_most(lifted, perimeter):
        raise ValueError(
            "edge lift %.3f mm exceeds the marking perimeter %.3f mm; the "
            "measurement or the perimeter is wrong" % (lifted, perimeter)
        )
    if lifted > perimeter:
        lifted = perimeter
    return lifted / perimeter


def axis_location_deviation_mm(nominal_position_mm, measured_position_mm):
    """Per-axis deviation from the drawing spot, and the governing one.

    A marking is placed inside a rectangular tolerance zone, so the
    deviation that governs is the larger of the two axis errors. Taking
    the root-sum-square instead reports a diagonal distance the drawing
    never toleranced, and rejects a marking that is inside its box.
    """
    nominal = _require_point("nominal_position_mm", nominal_position_mm)
    measured = _require_point("measured_position_mm", measured_position_mm)
    along = abs(measured[0] - nominal[0])
    across = abs(measured[1] - nominal[1])
    return {
        "x_mm": along,
        "y_mm": across,
        "governing_mm": along if along >= across else across,
    }


def character_height_margin_mm(
    character_height_mm, criteria=DEFAULT_MARKING_CRITERIA
):
    """Measured character height less the legibility minimum."""
    height = _require_positive("character_height_mm", character_height_mm)
    return height - float(criteria["min_character_height_mm"])


def reconcile_marking_inventory(required_ids, observed_ids):
    """Settle presence before anything is measured.

    A marking the drawing calls out and the part does not carry has no
    measurement to take, so it is reported apart from the graded ones.
    """
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
    present = [marker for marker in required_ids if marker in observed_ids]
    missing = [marker for marker in required_ids if marker not in observed_ids]
    unlisted = [marker for marker in observed_ids if marker not in required_ids]
    return {
        "present": present,
        "missing": missing,
        "unlisted": unlisted,
        "complete": not missing and not unlisted,
    }


def assess_marking_adhesion(
    lifted_area_mm2,
    marking_area_mm2,
    edge_lift_length_mm,
    marking_perimeter_mm,
    criteria=DEFAULT_MARKING_CRITERIA,
):
    """Disposition adhesion from the lifted footprint and the lifted edge."""
    validate_marking_criteria(criteria)
    area_share = lifted_area_fraction(lifted_area_mm2, marking_area_mm2)
    edge_share = edge_lift_fraction(edge_lift_length_mm, marking_perimeter_mm)
    measurements = {
        "lifted_area_fraction": area_share,
        "edge_lift_fraction": edge_share,
        "accept_lifted_area_fraction": criteria["accept_lifted_area_fraction"],
        "accept_edge_lift_fraction": criteria["accept_edge_lift_fraction"],
    }
    reasons = []
    calls = []

    if _at_most(area_share, criteria["accept_lifted_area_fraction"]):
        calls.append(ACCEPT)
    elif _at_most(area_share, criteria["rework_lifted_area_fraction"]):
        calls.append(REWORK)
        reasons.append(
            "%.3f of the marking footprint has lifted against the %.3f accept "
            "fraction; the marking can be re-applied"
            % (area_share, criteria["accept_lifted_area_fraction"])
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "%.3f of the marking footprint has lifted, past the %.3f rework "
            "fraction; the marking is no longer attached to the part it "
            "identifies"
            % (area_share, criteria["rework_lifted_area_fraction"])
        )

    if _at_most(edge_share, criteria["accept_edge_lift_fraction"]):
        calls.append(ACCEPT)
    elif _at_most(edge_share, criteria["rework_edge_lift_fraction"]):
        calls.append(REWORK)
        reasons.append(
            "%.3f of the marking perimeter has lifted against the %.3f accept "
            "fraction; the lift is still local to one edge"
            % (edge_share, criteria["accept_edge_lift_fraction"])
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "%.3f of the marking perimeter has lifted, past the %.3f rework "
            "fraction; the footprint figure stops describing an attached "
            "marking" % (edge_share, criteria["rework_edge_lift_fraction"])
        )

    return {
        "disposition": _worst(calls),
        "measurements": measurements,
        "reasons": reasons,
    }


def assess_marking_location(
    nominal_position_mm,
    measured_position_mm,
    surface,
    criteria=DEFAULT_MARKING_CRITERIA,
):
    """Disposition the in-plane placement against the surface-scaled box."""
    validate_marking_criteria(criteria)
    deviation = axis_location_deviation_mm(
        nominal_position_mm, measured_position_mm
    )
    factor = surface_tolerance_factor(surface, criteria)
    accept_limit = criteria["accept_location_deviation_mm"] * factor
    rework_limit = criteria["rework_location_deviation_mm"] * factor
    governing = deviation["governing_mm"]
    measurements = {
        "x_deviation_mm": deviation["x_mm"],
        "y_deviation_mm": deviation["y_mm"],
        "governing_deviation_mm": governing,
        "accept_location_deviation_mm": accept_limit,
        "rework_location_deviation_mm": rework_limit,
    }
    if _at_most(governing, accept_limit):
        return {"disposition": ACCEPT, "measurements": measurements, "reasons": []}
    if _at_most(governing, rework_limit):
        return {
            "disposition": REWORK,
            "measurements": measurements,
            "reasons": [
                "governing deviation %.3f mm exceeds the %.3f mm accept box on "
                "the %s; the marking can be lifted and re-applied"
                % (governing, accept_limit, surface)
            ],
        }
    return {
        "disposition": REJECT,
        "measurements": measurements,
        "reasons": [
            "governing deviation %.3f mm exceeds the %.3f mm rework box on the "
            "%s; the marking is not where the drawing identifies it"
            % (governing, rework_limit, surface)
        ],
    }


def assess_marking_legibility(
    character_height_mm, criteria=DEFAULT_MARKING_CRITERIA
):
    """Disposition the marking on whether it can still be read."""
    validate_marking_criteria(criteria)
    height = _require_positive("character_height_mm", character_height_mm)
    margin = character_height_margin_mm(height, criteria)
    measurements = {
        "character_height_mm": height,
        "min_character_height_mm": criteria["min_character_height_mm"],
        "character_height_margin_mm": margin,
    }
    if _at_least(height, criteria["min_character_height_mm"]):
        return {"disposition": ACCEPT, "measurements": measurements, "reasons": []}
    if _at_least(height, criteria["rework_character_height_mm"]):
        return {
            "disposition": REWORK,
            "measurements": measurements,
            "reasons": [
                "character height %.3f mm is under the %.3f mm legibility "
                "minimum; the marking can be over-marked"
                % (height, criteria["min_character_height_mm"])
            ],
        }
    return {
        "disposition": REJECT,
        "measurements": measurements,
        "reasons": [
            "character height %.3f mm is under the %.3f mm rework floor; an "
            "unreadable marking identifies nothing"
            % (height, criteria["rework_character_height_mm"])
        ],
    }


def assess_marking_condition(condition, criteria=DEFAULT_MARKING_CRITERIA):
    """Disposition one additional indication logged against a marking."""
    validate_marking_criteria(criteria)
    if not isinstance(condition, dict):
        raise ValueError("condition must be a mapping, got %r" % (condition,))
    kind = _require_choice(
        "kind", condition.get("kind"), MARKING_CONDITION_KINDS
    )
    surface = _require_choice(
        "surface", condition.get("surface"), MARKING_SURFACES
    )
    factor = surface_tolerance_factor(surface, criteria)
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
                "area %.3f mm2 exceeds the %.3f mm2 accept limit for %s on the "
                "%s" % (area, accept_area, kind, surface)
            )
        else:
            disposition = REJECT
            reasons.append(
                "area %.3f mm2 exceeds the %.3f mm2 rework limit for %s on the "
                "%s" % (area, rework_area, kind, surface)
            )
    else:
        raise ValueError(
            "%s is measured on the marking record itself, not logged as a "
            "separate condition; supply the adhesion, location or character "
            "height measurements" % kind
        )

    return {
        "id": condition.get("id"),
        "kind": kind,
        "surface": surface,
        "tolerated": tolerated,
        "disposition": disposition,
        "measurements": measurements,
        "reasons": reasons,
    }


def group_markings_by_type(markings):
    """Group marking records by the kind of identification they carry."""
    if isinstance(markings, (str, bytes)) or not isinstance(
        markings, (list, tuple)
    ):
        raise ValueError("markings must be a list, got %r" % (markings,))
    counts = dict((marking_type, 0) for marking_type in MARKING_TYPES)
    for marking in markings:
        if not isinstance(marking, dict):
            raise ValueError(
                "each marking must be a mapping, got %r" % (marking,)
            )
        marking_type = _require_choice(
            "marking_type", marking.get("marking_type"), MARKING_TYPES
        )
        counts[marking_type] += 1
    return {"counts": counts, "recorded": sum(counts.values())}


def assess_marking(marking, criteria=DEFAULT_MARKING_CRITERIA):
    """Roll the face, adhesion, location and legibility legs into one call."""
    validate_marking_criteria(criteria)
    if not isinstance(marking, dict):
        raise ValueError("marking record must be a mapping, got %r" % (marking,))
    marker = marking.get("marking_id")
    if not isinstance(marker, str) or not marker.strip():
        raise ValueError(
            "a marking record needs a non-empty marking_id so the rework "
            "record has something to attach to"
        )
    marking_type = _require_choice(
        "marking_type", marking.get("marking_type"), MARKING_TYPES
    )
    surface = _require_choice("surface", marking.get("surface"), MARKING_SURFACES)
    drawing_face = _require_label("drawing_face", marking.get("drawing_face"))
    observed_face = _require_label("observed_face", marking.get("observed_face"))

    adhesion = assess_marking_adhesion(
        marking.get("lifted_area_mm2", 0.0),
        marking.get("marking_area_mm2"),
        marking.get("edge_lift_length_mm", 0.0),
        marking.get("marking_perimeter_mm"),
        criteria,
    )
    location = assess_marking_location(
        marking.get("nominal_position_mm"),
        marking.get("measured_position_mm"),
        surface,
        criteria,
    )
    legibility = assess_marking_legibility(
        marking.get("character_height_mm"), criteria
    )

    conditions = marking.get("conditions", [])
    if isinstance(conditions, (str, bytes)) or not isinstance(
        conditions, (list, tuple)
    ):
        raise ValueError(
            "marking conditions must be a list, got %r" % (conditions,)
        )
    assessed = [
        assess_marking_condition(condition, criteria) for condition in conditions
    ]

    face_correct = drawing_face == observed_face
    reasons = (
        list(adhesion["reasons"])
        + list(location["reasons"])
        + list(legibility["reasons"])
    )
    calls = [
        adhesion["disposition"],
        location["disposition"],
        legibility["disposition"],
    ]
    if not face_correct:
        calls.append(REJECT)
        reasons.append(
            "the drawing places this marking on the %s face and it was found "
            "on the %s face; a wrong face is not an in-plane deviation and no "
            "tolerance reaches it" % (drawing_face, observed_face)
        )
    for result in assessed:
        calls.append(result["disposition"])
        for reason in result["reasons"]:
            reasons.append("%s: %s" % (result["id"], reason))

    blocking = [result["id"] for result in assessed if not result["tolerated"]]

    return {
        "marking_id": marker,
        "marking_type": marking_type,
        "surface": surface,
        "disposition": _worst(calls),
        "adhesion_disposition": adhesion["disposition"],
        "location_disposition": location["disposition"],
        "legibility_disposition": legibility["disposition"],
        "face_correct": face_correct,
        "well_adhered": adhesion["disposition"] == ACCEPT,
        "as_drawn": location["disposition"] == ACCEPT and face_correct,
        "legible": legibility["disposition"] == ACCEPT,
        "measurements": dict(
            list(adhesion["measurements"].items())
            + list(location["measurements"].items())
            + list(legibility["measurements"].items())
        ),
        "conditions": assessed,
        "not_tolerated_ids": blocking,
        "reasons": reasons,
    }


def inspect_coupon_markings(coupon, criteria=DEFAULT_MARKING_CRITERIA):
    """Full clause 5.5.3.2.18 screen with a coupon-level verdict."""
    validate_marking_criteria(criteria)
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    coupon_id = coupon.get("coupon_id")
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon needs a non-empty coupon_id for traceability")
    markings = coupon.get("markings")
    if isinstance(markings, (str, bytes)) or not isinstance(
        markings, (list, tuple)
    ):
        raise ValueError("coupon markings must be a list, got %r" % (markings,))

    observed = []
    assessed = []
    for marking in markings:
        result = assess_marking(marking, criteria)
        if result["marking_id"] in observed:
            raise ValueError(
                "duplicate marking_id %r on coupon %s; traceability to the "
                "rework record would be lost" % (result["marking_id"], coupon_id)
            )
        observed.append(result["marking_id"])
        assessed.append(result)

    required = coupon.get("drawing_marking_ids", [])
    if isinstance(required, (str, bytes)) or not isinstance(
        required, (list, tuple)
    ):
        raise ValueError(
            "drawing_marking_ids must be a list, got %r" % (required,)
        )
    if required:
        inventory = reconcile_marking_inventory(required, observed)
    else:
        inventory = {
            "present": list(observed),
            "missing": [],
            "unlisted": [],
            "complete": True,
        }
    grouping = group_markings_by_type(list(markings))

    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    findings = []

    if not assessed:
        findings.append(
            "no marking records on the coupon; an examined and clean coupon "
            "still carries the record that is the inspection evidence"
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["marking_id"], reason))

    blocking = [
        result["marking_id"] for result in assessed if result["not_tolerated_ids"]
    ]
    if blocking:
        findings.append(
            "not-tolerated conditions on %s; those markings cannot be "
            "dispositioned by size" % ", ".join(blocking)
        )
    if inventory["missing"]:
        verdict = REJECT
        findings.append(
            "the drawing calls out %s and the coupon carries no such marking; "
            "presence is settled before anything is measured"
            % ", ".join(inventory["missing"])
        )
    if inventory["unlisted"]:
        verdict = REJECT
        findings.append(
            "%s was found with no matching entry on the drawing"
            % ", ".join(inventory["unlisted"])
        )

    return {
        "coupon_id": coupon_id,
        "verdict": verdict,
        "markings": assessed,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "missing_marking_ids": inventory["missing"],
        "unlisted_marking_ids": inventory["unlisted"],
        "not_tolerated_marking_ids": blocking,
        "type_counts": grouping["counts"],
        "inventory_complete": inventory["complete"],
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }
