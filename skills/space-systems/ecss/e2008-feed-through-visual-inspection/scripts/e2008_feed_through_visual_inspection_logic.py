#!/usr/bin/env python3
"""Visual inspection of panel feed-throughs for bond integrity and position.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.17. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks one question of every feed-through that passes through a
solar panel substrate: is it firmly bonded, and is it where the assembly
drawing put it. Those are two independent measurements and a feed-through
has to satisfy both, so the screen runs three legs that are rolled up
into a single item disposition:

    position    the measured centre against the drawing centre, taken as
                a radial offset. A feed-through inside its positional
                tolerance is where the harness routing expects it; one
                outside it drags the harness off its designed run.
    bond        the bonded footprint against the footprint the drawing
                requires, taken as a coverage fraction. Coverage is a
                minimum: a feed-through with too little bonded area is
                carrying its harness load on the remainder.
    perimeter   the debonded run around the bond line against the whole
                bond perimeter. A short debond is a local repair; a long
                one means the bond line has released and the coverage
                figure is about to stop meaning anything.

A short list of conditions carries no allowance at all. A feed-through
that is loose, a substrate cracked at the passage, and a feed-through
fitted in a position the drawing never called out are decided by
presence: no measurement taken more carefully changes the answer.

Condition kinds
    position-deviation             centre off the drawing location
    bond-coverage-shortfall        bonded footprint under the requirement
    perimeter-debond               bond line released over a run
    bond-fillet-void               gas pocket inside the fillet
    adhesive-contamination         residue or particulate on the bond
    unbonded-feed-through          free to move, not tolerated
    substrate-crack-at-feed-through fracture at the passage, not tolerated
    wrong-position-feed-through    fitted where no passage was drawn

Zones
    panel-front-face        the illuminated face of the substrate
    panel-rear-face         the harness side of the substrate
    substrate-core-interface where the passage meets the core
    harness-exit-margin     the land the harness leaves across

Dispositions are accept, rework and reject. The limits below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FEED_THROUGH_CONDITION_KINDS = (
    "position-deviation",
    "bond-coverage-shortfall",
    "perimeter-debond",
    "bond-fillet-void",
    "adhesive-contamination",
    "unbonded-feed-through",
    "substrate-crack-at-feed-through",
    "wrong-position-feed-through",
)

NOT_TOLERATED_KINDS = (
    "unbonded-feed-through",
    "substrate-crack-at-feed-through",
    "wrong-position-feed-through",
)

FEED_THROUGH_ZONES = (
    "panel-front-face",
    "panel-rear-face",
    "substrate-core-interface",
    "harness-exit-margin",
)

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

_GRADED_AREA_KINDS = (
    "bond-fillet-void",
    "adhesive-contamination",
)

DEFAULT_FEED_THROUGH_CRITERIA = {
    # Radial offset of the measured centre from the drawing centre.
    "accept_offset_mm": 0.50,
    "rework_offset_mm": 2.00,
    # Bonded footprint as a fraction of the footprint the drawing needs.
    "accept_bond_coverage_fraction": 0.90,
    "rework_bond_coverage_fraction": 0.70,
    # Released run as a fraction of the whole bond perimeter.
    "accept_debond_perimeter_fraction": 0.05,
    "rework_debond_perimeter_fraction": 0.25,
    "accept_area_mm2": {
        "bond-fillet-void": 1.0,
        "adhesive-contamination": 4.0,
    },
    "rework_area_mm2": {
        "bond-fillet-void": 6.0,
        "adhesive-contamination": 30.0,
    },
    # Applies to allowances only - offsets and areas. Never to a minimum.
    "zone_tolerance_factor": {
        "panel-front-face": 1.0,
        "panel-rear-face": 1.0,
        "substrate-core-interface": 0.5,
        "harness-exit-margin": 0.75,
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
    measurement is a root-sum-square, so a value sitting exactly on the
    limit can evaluate a few units in the last place above it. The limit
    is never raised; only the comparison tolerates the representation
    error.
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


def validate_feed_through_criteria(criteria):
    """Check a criteria set is complete and internally ordered."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    table_specs = (
        ("accept_area_mm2", _GRADED_AREA_KINDS),
        ("rework_area_mm2", _GRADED_AREA_KINDS),
        ("zone_tolerance_factor", FEED_THROUGH_ZONES),
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
    for zone in FEED_THROUGH_ZONES:
        _require_positive(
            "criteria zone_tolerance_factor[%s]" % zone,
            criteria["zone_tolerance_factor"][zone],
        )
    accept_offset = _require_positive(
        "accept_offset_mm", criteria.get("accept_offset_mm")
    )
    rework_offset = _require_positive(
        "rework_offset_mm", criteria.get("rework_offset_mm")
    )
    if rework_offset < accept_offset and not _close(rework_offset, accept_offset):
        raise ValueError("criteria rework_offset_mm is below the accept offset")
    accept_coverage = _require_positive(
        "accept_bond_coverage_fraction",
        criteria.get("accept_bond_coverage_fraction"),
    )
    rework_coverage = _require_positive(
        "rework_bond_coverage_fraction",
        criteria.get("rework_bond_coverage_fraction"),
    )
    if accept_coverage > 1.0 and not _close(accept_coverage, 1.0):
        raise ValueError(
            "criteria accept_bond_coverage_fraction cannot exceed one, got %r"
            % (accept_coverage,)
        )
    if rework_coverage > accept_coverage and not _close(
        rework_coverage, accept_coverage
    ):
        raise ValueError(
            "criteria rework_bond_coverage_fraction is above the accept fraction"
        )
    accept_debond = _require_non_negative(
        "accept_debond_perimeter_fraction",
        criteria.get("accept_debond_perimeter_fraction"),
    )
    rework_debond = _require_non_negative(
        "rework_debond_perimeter_fraction",
        criteria.get("rework_debond_perimeter_fraction"),
    )
    if rework_debond < accept_debond and not _close(rework_debond, accept_debond):
        raise ValueError(
            "criteria rework_debond_perimeter_fraction is below the accept "
            "fraction"
        )
    if rework_debond > 1.0 and not _close(rework_debond, 1.0):
        raise ValueError(
            "criteria rework_debond_perimeter_fraction cannot exceed one"
        )
    return criteria


def zone_tolerance_factor(zone, criteria=DEFAULT_FEED_THROUGH_CRITERIA):
    """Factor the zone applies to every allowance; below one is stricter."""
    _require_choice("zone", zone, FEED_THROUGH_ZONES)
    return float(criteria["zone_tolerance_factor"][zone])


def radial_position_offset_mm(nominal_position_mm, measured_position_mm):
    """Distance between the drawing centre and the measured centre.

    The offset is the root-sum-square of the two axis errors, because a
    feed-through is round and a tolerance on its position is a radial
    one; taking the larger axis error alone understates a diagonal miss.
    """
    nominal = _require_point("nominal_position_mm", nominal_position_mm)
    measured = _require_point("measured_position_mm", measured_position_mm)
    return math.hypot(measured[0] - nominal[0], measured[1] - nominal[1])


def bond_coverage_fraction(bonded_area_mm2, required_bond_area_mm2):
    """Share of the required bond footprint that is actually bonded."""
    required = _require_positive(
        "required_bond_area_mm2", required_bond_area_mm2
    )
    bonded = _require_non_negative("bonded_area_mm2", bonded_area_mm2)
    if not _at_most(bonded, required):
        raise ValueError(
            "bonded area %.3f mm2 exceeds the required footprint %.3f mm2; the "
            "measurement or the drawing footprint is wrong" % (bonded, required)
        )
    if bonded > required:
        bonded = required
    return bonded / required


def debond_perimeter_fraction(debonded_length_mm, bond_perimeter_mm):
    """Share of the bond perimeter that has released."""
    perimeter = _require_positive("bond_perimeter_mm", bond_perimeter_mm)
    debonded = _require_non_negative("debonded_length_mm", debonded_length_mm)
    if not _at_most(debonded, perimeter):
        raise ValueError(
            "debonded run %.3f mm exceeds the bond perimeter %.3f mm; the "
            "measurement or the perimeter is wrong" % (debonded, perimeter)
        )
    if debonded > perimeter:
        debonded = perimeter
    return debonded / perimeter


def is_firmly_bonded(
    bonded_area_mm2,
    required_bond_area_mm2,
    debonded_length_mm,
    bond_perimeter_mm,
    criteria=DEFAULT_FEED_THROUGH_CRITERIA,
):
    """True when coverage meets the minimum and the debond stays local."""
    coverage = bond_coverage_fraction(bonded_area_mm2, required_bond_area_mm2)
    released = debond_perimeter_fraction(debonded_length_mm, bond_perimeter_mm)
    return _at_least(
        coverage, criteria["accept_bond_coverage_fraction"]
    ) and _at_most(released, criteria["accept_debond_perimeter_fraction"])


def assess_position_offset(
    offset_mm, zone, criteria=DEFAULT_FEED_THROUGH_CRITERIA
):
    """Disposition a radial offset against the zone-scaled tolerances."""
    validate_feed_through_criteria(criteria)
    offset = _require_non_negative("offset_mm", offset_mm)
    factor = zone_tolerance_factor(zone, criteria)
    accept_limit = criteria["accept_offset_mm"] * factor
    rework_limit = criteria["rework_offset_mm"] * factor
    measurements = {
        "offset_mm": offset,
        "accept_offset_mm": accept_limit,
        "rework_offset_mm": rework_limit,
    }
    if _at_most(offset, accept_limit):
        return {"disposition": ACCEPT, "measurements": measurements, "reasons": []}
    if _at_most(offset, rework_limit):
        return {
            "disposition": REWORK,
            "measurements": measurements,
            "reasons": [
                "radial offset %.3f mm exceeds the %.3f mm accept tolerance in "
                "the %s zone; the feed-through can be released and reset"
                % (offset, accept_limit, zone)
            ],
        }
    return {
        "disposition": REJECT,
        "measurements": measurements,
        "reasons": [
            "radial offset %.3f mm exceeds the %.3f mm rework tolerance in the "
            "%s zone; the passage itself is in the wrong place"
            % (offset, rework_limit, zone)
        ],
    }


def assess_bond_state(
    bonded_area_mm2,
    required_bond_area_mm2,
    debonded_length_mm,
    bond_perimeter_mm,
    criteria=DEFAULT_FEED_THROUGH_CRITERIA,
):
    """Disposition the bond from its coverage and its released perimeter."""
    validate_feed_through_criteria(criteria)
    coverage = bond_coverage_fraction(bonded_area_mm2, required_bond_area_mm2)
    released = debond_perimeter_fraction(debonded_length_mm, bond_perimeter_mm)
    measurements = {
        "bond_coverage_fraction": coverage,
        "debond_perimeter_fraction": released,
        "accept_bond_coverage_fraction": criteria[
            "accept_bond_coverage_fraction"
        ],
        "accept_debond_perimeter_fraction": criteria[
            "accept_debond_perimeter_fraction"
        ],
    }
    reasons = []
    calls = []

    if _at_least(coverage, criteria["accept_bond_coverage_fraction"]):
        calls.append(ACCEPT)
    elif _at_least(coverage, criteria["rework_bond_coverage_fraction"]):
        calls.append(REWORK)
        reasons.append(
            "bond coverage %.3f is under the %.3f minimum; enough of the "
            "footprint is bonded that the fillet can be built back up"
            % (coverage, criteria["accept_bond_coverage_fraction"])
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "bond coverage %.3f is under the %.3f rework floor; the "
            "feed-through is carrying its harness load on the remainder"
            % (coverage, criteria["rework_bond_coverage_fraction"])
        )

    if _at_most(released, criteria["accept_debond_perimeter_fraction"]):
        calls.append(ACCEPT)
    elif _at_most(released, criteria["rework_debond_perimeter_fraction"]):
        calls.append(REWORK)
        reasons.append(
            "%.3f of the bond perimeter has released against the %.3f accept "
            "fraction; the release is still local"
            % (released, criteria["accept_debond_perimeter_fraction"])
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "%.3f of the bond perimeter has released, past the %.3f rework "
            "fraction; the bond line is no longer continuous and the coverage "
            "figure stops meaning anything"
            % (released, criteria["rework_debond_perimeter_fraction"])
        )

    return {
        "disposition": _worst(calls),
        "measurements": measurements,
        "reasons": reasons,
    }


def assess_feed_through_condition(
    condition, criteria=DEFAULT_FEED_THROUGH_CRITERIA
):
    """Disposition one additional indication logged against a feed-through."""
    validate_feed_through_criteria(criteria)
    if not isinstance(condition, dict):
        raise ValueError("condition must be a mapping, got %r" % (condition,))
    kind = _require_choice(
        "kind", condition.get("kind"), FEED_THROUGH_CONDITION_KINDS
    )
    zone = _require_choice("zone", condition.get("zone"), FEED_THROUGH_ZONES)
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
            "%s is measured on the feed-through record itself, not logged as a "
            "separate condition; supply the position or bond measurements"
            % kind
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


def group_conditions_by_kind(conditions):
    """Group logged conditions by kind and count the not-tolerated ones."""
    if not isinstance(conditions, (list, tuple)):
        raise ValueError("conditions must be a list, got %r" % (conditions,))
    counts = dict((kind, 0) for kind in FEED_THROUGH_CONDITION_KINDS)
    for condition in conditions:
        if not isinstance(condition, dict):
            raise ValueError(
                "each condition must be a mapping, got %r" % (condition,)
            )
        kind = _require_choice(
            "kind", condition.get("kind"), FEED_THROUGH_CONDITION_KINDS
        )
        counts[kind] += 1
    not_tolerated = sum(counts[kind] for kind in NOT_TOLERATED_KINDS)
    return {"counts": counts, "not_tolerated_count": not_tolerated}


def assess_feed_through(record, criteria=DEFAULT_FEED_THROUGH_CRITERIA):
    """Roll the position leg, the bond legs and any conditions into one call."""
    validate_feed_through_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("feed-through record must be a mapping, got %r" % (record,))
    marker = record.get("feed_through_id")
    if not isinstance(marker, str) or not marker.strip():
        raise ValueError(
            "a feed-through record needs a non-empty feed_through_id so the "
            "rework record has something to attach to"
        )
    zone = _require_choice("zone", record.get("zone"), FEED_THROUGH_ZONES)

    offset = radial_position_offset_mm(
        record.get("nominal_position_mm"), record.get("measured_position_mm")
    )
    position = assess_position_offset(offset, zone, criteria)
    bond = assess_bond_state(
        record.get("bonded_area_mm2"),
        record.get("required_bond_area_mm2"),
        record.get("debonded_perimeter_mm", 0.0),
        record.get("bond_perimeter_mm"),
        criteria,
    )

    conditions = record.get("conditions", [])
    if not isinstance(conditions, (list, tuple)):
        raise ValueError(
            "feed-through conditions must be a list, got %r" % (conditions,)
        )
    assessed = [
        assess_feed_through_condition(condition, criteria)
        for condition in conditions
    ]

    measurements = {}
    measurements.update(position["measurements"])
    measurements.update(bond["measurements"])

    reasons = list(position["reasons"]) + list(bond["reasons"])
    for result in assessed:
        for reason in result["reasons"]:
            reasons.append("%s: %s" % (result["id"], reason))

    calls = [position["disposition"], bond["disposition"]]
    calls.extend(result["disposition"] for result in assessed)
    blocking = [result["id"] for result in assessed if not result["tolerated"]]

    return {
        "feed_through_id": marker,
        "zone": zone,
        "disposition": _worst(calls),
        "position_disposition": position["disposition"],
        "bond_disposition": bond["disposition"],
        "firmly_bonded": bond["disposition"] == ACCEPT,
        "in_position": position["disposition"] == ACCEPT,
        "measurements": measurements,
        "conditions": assessed,
        "not_tolerated_ids": blocking,
        "reasons": reasons,
    }


def inspect_panel_feed_throughs(panel, criteria=DEFAULT_FEED_THROUGH_CRITERIA):
    """Full clause 5.5.3.2.17 screen with a panel-level verdict."""
    validate_feed_through_criteria(criteria)
    if not isinstance(panel, dict):
        raise ValueError("panel must be a mapping, got %r" % (panel,))
    panel_id = panel.get("panel_id")
    if not isinstance(panel_id, str) or not panel_id.strip():
        raise ValueError("panel needs a non-empty panel_id for traceability")
    records = panel.get("feed_throughs")
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "panel feed_throughs must be a list, got %r" % (records,)
        )

    seen = []
    assessed = []
    for record in records:
        result = assess_feed_through(record, criteria)
        if result["feed_through_id"] in seen:
            raise ValueError(
                "duplicate feed_through_id %r on panel %s; traceability to the "
                "rework record would be lost" % (result["feed_through_id"], panel_id)
            )
        seen.append(result["feed_through_id"])
        assessed.append(result)

    drawing_ids = panel.get("drawing_feed_through_ids", [])
    if not isinstance(drawing_ids, (list, tuple)):
        raise ValueError(
            "drawing_feed_through_ids must be a list, got %r" % (drawing_ids,)
        )
    unrecorded = [marker for marker in drawing_ids if marker not in seen]
    undrawn = (
        [marker for marker in seen if marker not in drawing_ids]
        if drawing_ids
        else []
    )

    every_condition = []
    for record in records:
        every_condition.extend(record.get("conditions", []))
    grouping = group_conditions_by_kind(every_condition)

    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    findings = []

    if not assessed:
        findings.append(
            "no feed-through records on the panel; an examined and clean panel "
            "still carries the record that is the inspection evidence"
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["feed_through_id"], reason))

    blocking = []
    for result in assessed:
        if result["not_tolerated_ids"]:
            blocking.append(result["feed_through_id"])
    if blocking:
        findings.append(
            "not-tolerated conditions on %s; those feed-throughs cannot be "
            "dispositioned by size" % ", ".join(blocking)
        )
    if unrecorded:
        verdict = REJECT
        findings.append(
            "the drawing calls out %s with no inspection record; an unexamined "
            "feed-through cannot be accepted" % ", ".join(unrecorded)
        )
    if undrawn:
        verdict = REJECT
        findings.append(
            "%s was found with no matching passage on the drawing"
            % ", ".join(undrawn)
        )

    return {
        "panel_id": panel_id,
        "verdict": verdict,
        "feed_throughs": assessed,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "unrecorded_ids": unrecorded,
        "undrawn_ids": undrawn,
        "not_tolerated_feed_through_ids": blocking,
        "condition_counts": grouping["counts"],
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }
