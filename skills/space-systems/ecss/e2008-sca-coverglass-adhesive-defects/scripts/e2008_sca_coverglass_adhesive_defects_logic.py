#!/usr/bin/env python3
"""Coverglass adhesive: delamination and discolouration outside the weld zones.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The adhesive under a coverglass is asked to be free of delamination and
of discolouration, with one carve-out: the zones sitting behind the rear
welds, where the welding heat is put into the cell from the other face
and some separation and darkening is the expected consequence of a
process the design asked for.

That carve-out is positional, not a size allowance. It does not say a
certain area of delamination is tolerated; it says the area behind a
weld is not the adhesive's fault. So the screen is a containment
problem: each indication footprint is intersected with the exempt zones
and only the part that falls outside them is charged against the bond.
An indication that straddles the edge of a zone is charged for its
overhanging part and credited for the rest, and an indication whose
centre happens to sit behind a weld is not thereby exempt in full.

Overlapping exempt zones are never summed. The credit is taken from the
single zone that covers the most of the indication, because adding the
overlaps back together would exempt area twice and turn two adjacent
welds into a licence for a delamination neither of them caused.

Nothing here is reworkable. The adhesive is under a bonded glass, so any
recovery means taking the glass off, which is a new build rather than a
rework; the dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INDICATION_KINDS = ("delamination", "discolouration")

DISCOLOURATION_GRADES = {"light": 0.25, "medium": 0.6, "dark": 1.0}

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
ADHESIVE_DISPOSITIONS = (ACCEPT, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

DEFAULT_ADHESIVE_CRITERIA = {
    "negligible_area_mm2": 0.2,
    "max_indication_area_fraction": 0.002,
    "delamination_limit_factor": 0.25,
    "max_total_counted_fraction": 0.005,
    "max_transmission_loss_fraction": 0.003,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_finite(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_finite(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_finite(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The exempt area comes out of an inverse-cosine geometry and every
    limit is a product of a criteria fraction and a measured area, so a
    value sitting exactly on a limit can evaluate a few units in the
    last place above it. The limit is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing the same representation error."""
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def _clamp_cosine(value):
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return value


def validate_adhesive_criteria(criteria):
    """Check an adhesive criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive(
        "criteria negligible_area_mm2", criteria.get("negligible_area_mm2")
    )
    for key in (
        "max_indication_area_fraction",
        "delamination_limit_factor",
        "max_total_counted_fraction",
        "max_transmission_loss_fraction",
    ):
        value = _require_positive("criteria %s" % key, criteria.get(key))
        if value > 1.0:
            raise ValueError(
                "criteria %s is a fraction and must not exceed one, got %r"
                % (key, value)
            )
    if (
        criteria["max_indication_area_fraction"]
        > criteria["max_total_counted_fraction"]
    ):
        raise ValueError(
            "a single indication may not be allowed more area than the whole "
            "bond line is allowed to lose"
        )
    return criteria


def circle_intersection_area_mm2(radius_a_mm, radius_b_mm, centre_distance_mm):
    """Area common to two circular footprints a given distance apart.

    The two limiting cases are handled before the general one because
    the general expression divides by the centre distance and the
    inverse cosines run off the end of their domain there.
    """
    radius_a = _require_positive("radius_a_mm", radius_a_mm)
    radius_b = _require_positive("radius_b_mm", radius_b_mm)
    distance = _require_non_negative("centre_distance_mm", centre_distance_mm)
    if _at_least(distance, radius_a + radius_b):
        return 0.0
    if _at_most(distance, abs(radius_a - radius_b)):
        smaller = min(radius_a, radius_b)
        return math.pi * smaller * smaller
    cos_a = _clamp_cosine(
        (distance * distance + radius_a * radius_a - radius_b * radius_b)
        / (2.0 * distance * radius_a)
    )
    cos_b = _clamp_cosine(
        (distance * distance + radius_b * radius_b - radius_a * radius_a)
        / (2.0 * distance * radius_b)
    )
    lens = (
        radius_a * radius_a * math.acos(cos_a)
        + radius_b * radius_b * math.acos(cos_b)
    )
    wedge = (
        (-distance + radius_a + radius_b)
        * (distance + radius_a - radius_b)
        * (distance - radius_a + radius_b)
        * (distance + radius_a + radius_b)
    )
    if wedge < 0.0:
        wedge = 0.0
    return lens - 0.5 * math.sqrt(wedge)


def validate_weld_zone(zone):
    """Check one exempt zone behind a rear weld."""
    if not isinstance(zone, dict):
        raise ValueError("weld zone must be a mapping, got %r" % (zone,))
    zone_id = zone.get("id")
    if not isinstance(zone_id, str) or not zone_id.strip():
        raise ValueError("each weld zone needs a non-empty id")
    return {
        "id": zone_id,
        "centre_x_mm": _require_finite("weld centre_x_mm", zone.get("centre_x_mm")),
        "centre_y_mm": _require_finite("weld centre_y_mm", zone.get("centre_y_mm")),
        "radius_mm": _require_positive("weld radius_mm", zone.get("radius_mm")),
    }


def exempt_area_mm2(indication, weld_zones):
    """Largest single-zone credit the indication can take, never a sum.

    Two exempt zones that overlap each other would each credit the area
    they share, so summing them exempts it twice. The credit taken here
    is the one from the zone that covers the most of the indication,
    which can only understate the exemption and never invent one.
    """
    radius = _require_positive("indication radius_mm", indication.get("radius_mm"))
    centre_x = _require_finite("indication centre_x_mm", indication.get("centre_x_mm"))
    centre_y = _require_finite("indication centre_y_mm", indication.get("centre_y_mm"))
    best = 0.0
    best_zone = None
    for zone in weld_zones:
        checked = validate_weld_zone(zone)
        offset_x = centre_x - checked["centre_x_mm"]
        offset_y = centre_y - checked["centre_y_mm"]
        distance = math.sqrt(offset_x * offset_x + offset_y * offset_y)
        overlap = circle_intersection_area_mm2(
            radius, checked["radius_mm"], distance
        )
        if overlap > best:
            best = overlap
            best_zone = checked["id"]
    return {"exempt_area_mm2": best, "zone_id": best_zone}


def assess_adhesive_indication(
    indication, weld_zones, bonded_area_mm2, criteria=DEFAULT_ADHESIVE_CRITERIA
):
    """Charge one indication for the part of it outside every weld zone."""
    validate_adhesive_criteria(criteria)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    if not isinstance(weld_zones, (list, tuple)):
        raise ValueError("weld_zones must be a list, got %r" % (weld_zones,))
    kind = _require_choice("kind", indication.get("kind"), INDICATION_KINDS)
    bonded = _require_positive("bonded_area_mm2", bonded_area_mm2)
    radius = _require_positive("radius_mm", indication.get("radius_mm"))
    footprint = math.pi * radius * radius
    if not _at_most(footprint, bonded):
        raise ValueError(
            "indication %r claims %.3f mm2 of a %.3f mm2 bond line"
            % (indication.get("id"), footprint, bonded)
        )

    weight = 1.0
    grade = None
    if kind == "discolouration":
        grade = _require_choice(
            "grade", indication.get("grade"), tuple(DISCOLOURATION_GRADES)
        )
        weight = DISCOLOURATION_GRADES[grade]

    credit = exempt_area_mm2(indication, weld_zones)
    exempt = credit["exempt_area_mm2"]
    counted = footprint - exempt
    wholly_exempt = _at_most(counted, 0.0)
    if wholly_exempt:
        counted = 0.0
    straddles = exempt > 0.0 and not wholly_exempt
    effective = counted * weight

    limit = bonded * criteria["max_indication_area_fraction"]
    if kind == "delamination":
        limit = limit * criteria["delamination_limit_factor"]

    reasons = []
    if wholly_exempt:
        disposition = ACCEPT
        reasons.append(
            "the indication sits wholly inside the zone behind weld %s, which "
            "the clause carves out; the carve-out is positional, so its size "
            "was never the question" % (credit["zone_id"],)
        )
    elif _at_most(effective, criteria["negligible_area_mm2"]):
        disposition = ACCEPT
        reasons.append(
            "%.4f mm2 falls outside every weld zone, at or under the %.4f mm2 "
            "the examination can call a real separation"
            % (effective, criteria["negligible_area_mm2"])
        )
    elif _at_most(effective, limit):
        disposition = REFER
        reasons.append(
            "%.4f mm2 of %s sits outside every weld zone against a %.4f mm2 "
            "limit; the bond is not free of it, so the call is a review"
            % (effective, kind, limit)
        )
    else:
        disposition = REJECT
        reasons.append(
            "%.4f mm2 of %s outside the weld zones is past the %.4f mm2 limit"
            % (effective, kind, limit)
        )
    if straddles:
        reasons.append(
            "it straddles the edge of weld zone %s, so only the %.4f mm2 behind "
            "the weld was credited" % (credit["zone_id"], exempt)
        )

    return {
        "id": indication.get("id"),
        "kind": kind,
        "grade": grade,
        "footprint_mm2": footprint,
        "exempt_area_mm2": exempt,
        "exempt_zone_id": credit["zone_id"],
        "counted_area_mm2": counted,
        "effective_area_mm2": effective,
        "limit_mm2": limit,
        "wholly_behind_weld": wholly_exempt,
        "straddles_weld_zone": straddles,
        "disposition": disposition,
        "reasons": reasons,
    }


def inspect_coverglass_adhesive(item, criteria=DEFAULT_ADHESIVE_CRITERIA):
    """Clause 6.4.3.1.6 adhesive screen over one coverglassed cell."""
    validate_adhesive_criteria(criteria)
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    item_id = item.get("assembly_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item needs a non-empty assembly_id")
    bonded = _require_positive("bonded_area_mm2", item.get("bonded_area_mm2"))

    zones = item.get("weld_zones", [])
    if not isinstance(zones, (list, tuple)):
        raise ValueError("weld_zones must be a list, got %r" % (zones,))
    seen_zones = set()
    for zone in zones:
        checked = validate_weld_zone(zone)
        if checked["id"] in seen_zones:
            raise ValueError("duplicate weld zone id %r" % (checked["id"],))
        seen_zones.add(checked["id"])
    declared_welds = item.get("declared_rear_weld_count", len(zones))
    _require_count("declared_rear_weld_count", declared_welds)
    if len(zones) > declared_welds:
        raise ValueError(
            "%d exempt zones against %d declared rear welds on %s"
            % (len(zones), declared_welds, item_id)
        )
    unmapped_welds = declared_welds - len(zones)

    indications = item.get("indications", [])
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))

    seen = set()
    assessed = []
    for indication in indications:
        result = assess_adhesive_indication(indication, zones, bonded, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate indication id %r on %s" % (marker, item_id)
                )
            seen.add(marker)
        assessed.append(result)

    counted_total = sum(result["counted_area_mm2"] for result in assessed)
    exempt_total = sum(result["exempt_area_mm2"] for result in assessed)
    if not _at_most(counted_total, bonded):
        raise ValueError(
            "indications charge %.3f mm2 against a %.3f mm2 bond line"
            % (counted_total, bonded)
        )
    counted_fraction = counted_total / bonded
    transmission_loss = (
        sum(
            result["effective_area_mm2"]
            for result in assessed
            if result["kind"] == "discolouration"
        )
        / bonded
    )

    findings = []
    counts = dict((state, 0) for state in ADHESIVE_DISPOSITIONS)
    for result in assessed:
        counts[result["disposition"]] += 1
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])
    if not _at_most(counted_fraction, criteria["max_total_counted_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "indications outside the weld zones take %.5f of the bond line "
            "together against a %.5f allowance, even though no single one did"
            % (counted_fraction, criteria["max_total_counted_fraction"])
        )
    if not _at_most(transmission_loss, criteria["max_transmission_loss_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "graded discolouration outside the weld zones costs %.5f of the "
            "bonded area in transmission against a %.5f allowance"
            % (transmission_loss, criteria["max_transmission_loss_fraction"])
        )

    complete = unmapped_welds == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d rear welds carry no exempt zone; without the map an "
            "indication behind one of them is charged to the adhesive"
            % (unmapped_welds, declared_welds)
        )

    return {
        "assembly_id": item_id,
        "verdict": verdict,
        "exemption_map_complete": complete,
        "unmapped_weld_count": unmapped_welds,
        "bonded_area_mm2": bonded,
        "counted_area_mm2": counted_total,
        "exempt_area_mm2": exempt_total,
        "counted_area_fraction": counted_fraction,
        "transmission_loss_fraction": transmission_loss,
        "disposition_counts": counts,
        "wholly_exempt_ids": [
            result["id"] for result in assessed if result["wholly_behind_weld"]
        ],
        "straddling_ids": [
            result["id"] for result in assessed if result["straddles_weld_zone"]
        ],
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "indications": assessed,
        "findings": findings,
    }
