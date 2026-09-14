#!/usr/bin/env python3
"""Bare solar cell acceptance against cracks and fingerprint contamination.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.4.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause names two conditions and admits neither of them: a bare cell
is acceptable only when it carries no crack and no fingerprint. Both
halves read as absolutes, and both are routinely softened in practice
into something the clause never said.

A crack has no permitted length. There is no band below which a short
fracture becomes cosmetic, because the mechanism is not the fracture as
found -- it is the fracture after a few hundred thermal cycles, and the
cell has not been cycled yet at the point somebody is looking at it. So
the disposition of a confirmed crack is a rejection at any length, and
the only question a length answers is whether the examination could
have seen it at all.

That second question is the real content of the assessment. An
examination has a detection floor set by the angular resolution of the
eye, the working distance and any magnification, and a cell declared
free of cracks is only free of cracks down to that floor. An indication
recorded below the floor of the examination that supposedly produced it
did not come from that examination, so it goes to review rather than
being credited either way.

Magnification runs one way only here. Because the clause admits no
crack, a more sensitive instrument can add rejections and can never
withdraw one, so a magnified finding stands while a magnified acceptance
is simply a stronger statement than an unaided one.

A fingerprint is a contamination finding rather than a fracture, and it
separates on whether it can be taken off. A print on a bare area of the
cell is cleaned and looked at again; a print sitting on a contact area
is a rejection because the ionic residue ends up inside a weld zone and
the cleaning that would remove it attacks the metallisation. Cleaning
cycles are finite, so a cell that has already spent its allowance has no
cleaning route left and is rejected instead.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CRACK = "crack"
FINGERPRINT = "fingerprint"
INDICATION_KINDS = (CRACK, FINGERPRINT)

ACCEPT = "accept"
CLEAN_AND_REINSPECT = "clean-and-reinspect"
REFER_FOR_REVIEW = "refer-for-review"
REJECT = "reject"
CELL_DISPOSITIONS = (ACCEPT, CLEAN_AND_REINSPECT, REFER_FOR_REVIEW, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {
    ACCEPT: 0,
    CLEAN_AND_REINSPECT: 1,
    REFER_FOR_REVIEW: 2,
    REJECT: 3,
    INSPECTION_INCOMPLETE: 4,
}

REQUIRED_INDICATION_FIELDS = {
    CRACK: ("length_mm", "confirmed"),
    FINGERPRINT: ("area_mm2", "removable", "on_contact_area"),
}

DEFAULT_BARE_CELL_CRITERIA = {
    "unaided_acuity_arcmin": 1.0,
    "max_working_distance_mm": 400.0,
    "min_illuminance_lux": 1000.0,
    "max_cleanable_fingerprint_area_mm2": 25.0,
    "max_cleaning_cycles": 2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_ARCMIN_PER_DEGREE = 60.0


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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_bare_cell_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive(
        "unaided_acuity_arcmin", criteria.get("unaided_acuity_arcmin")
    )
    _require_positive(
        "max_working_distance_mm", criteria.get("max_working_distance_mm")
    )
    _require_positive(
        "min_illuminance_lux", criteria.get("min_illuminance_lux")
    )
    _require_positive(
        "max_cleanable_fingerprint_area_mm2",
        criteria.get("max_cleanable_fingerprint_area_mm2"),
    )
    cycles = _require_count(
        "max_cleaning_cycles", criteria.get("max_cleaning_cycles")
    )
    if cycles < 1:
        raise ValueError(
            "max_cleaning_cycles must allow at least one cleaning, got %r"
            % (cycles,)
        )
    return criteria


def crack_detection_floor_mm(
    working_distance_mm, acuity_arcmin=1.0, magnification=1.0
):
    """Smallest crack length the examination could have reported.

    The eye subtends its acuity angle at the working distance; a
    magnifier divides the angle the feature has to fill. Below the floor
    the examination reports nothing, so a cell declared crack free is
    crack free only down to this length.
    """
    distance = _require_positive("working_distance_mm", working_distance_mm)
    acuity = _require_positive("acuity_arcmin", acuity_arcmin)
    power = _require_positive("magnification", magnification)
    half_angle_rad = math.radians(acuity / _ARCMIN_PER_DEGREE) / 2.0
    return 2.0 * distance * math.tan(half_angle_rad) / power


def validate_inspection_conditions(conditions, criteria=DEFAULT_BARE_CELL_CRITERIA):
    """Normalise the examination conditions recorded for one cell."""
    validate_bare_cell_criteria(criteria)
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping, got %r" % (conditions,))
    distance = _require_positive(
        "working_distance_mm", conditions.get("working_distance_mm")
    )
    power = _require_positive("magnification", conditions.get("magnification", 1.0))
    illuminance = _require_non_negative(
        "illuminance_lux", conditions.get("illuminance_lux")
    )
    return {
        "working_distance_mm": distance,
        "magnification": power,
        "illuminance_lux": illuminance,
    }


def condition_findings(conditions, criteria=DEFAULT_BARE_CELL_CRITERIA):
    """Conditions that stop the examination from supporting an acceptance."""
    validate_bare_cell_criteria(criteria)
    normalised = validate_inspection_conditions(conditions, criteria)
    findings = []
    if not _at_most(
        normalised["working_distance_mm"], criteria["max_working_distance_mm"]
    ):
        findings.append(
            "the cell was looked at from %.0f mm, beyond the %.0f mm the "
            "criteria allow; the crack detection floor grows with the distance"
            % (
                normalised["working_distance_mm"],
                criteria["max_working_distance_mm"],
            )
        )
    if not _at_least(
        normalised["illuminance_lux"], criteria["min_illuminance_lux"]
    ):
        findings.append(
            "the examination ran at %.0f lux, below the %.0f lux floor; finding "
            "no crack is the expected result of looking in the dark"
            % (normalised["illuminance_lux"], criteria["min_illuminance_lux"])
        )
    return tuple(findings)


def validate_indication(indication):
    """Check one recorded indication carries the fields its kind needs."""
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    kind = indication.get("kind")
    if kind not in INDICATION_KINDS:
        raise ValueError(
            "indication kind must be one of %s, got %r"
            % (", ".join(INDICATION_KINDS), kind)
        )
    missing = [
        field
        for field in REQUIRED_INDICATION_FIELDS[kind]
        if field not in indication
    ]
    if missing:
        raise ValueError(
            "a %s indication needs %s; missing %s"
            % (kind, ", ".join(REQUIRED_INDICATION_FIELDS[kind]), ", ".join(missing))
        )
    if kind == CRACK:
        _require_positive("length_mm", indication.get("length_mm"))
        _require_bool("confirmed", indication.get("confirmed"))
    else:
        _require_positive("area_mm2", indication.get("area_mm2"))
        _require_bool("removable", indication.get("removable"))
        _require_bool("on_contact_area", indication.get("on_contact_area"))
    return kind


def categorize_crack_indication(
    indication, detection_floor_mm, criteria=DEFAULT_BARE_CELL_CRITERIA
):
    """Disposition one crack indication. Length never earns an acceptance."""
    validate_bare_cell_criteria(criteria)
    kind = validate_indication(indication)
    if kind != CRACK:
        raise ValueError("categorize_crack_indication was handed a %s" % kind)
    floor = _require_positive("detection_floor_mm", detection_floor_mm)
    length = float(indication["length_mm"])
    if indication["confirmed"]:
        return (
            REJECT,
            "a confirmed crack %.3g mm long is a rejection; the clause admits "
            "no crack and the fracture grows over the thermal cycles the cell "
            "has not yet seen" % length,
        )
    if not _at_least(length, floor):
        return (
            REFER_FOR_REVIEW,
            "an unconfirmed %.3g mm indication sits under the %.3g mm floor of "
            "the examination that recorded it, so its provenance is the first "
            "thing to settle" % (length, floor),
        )
    return (
        REFER_FOR_REVIEW,
        "an unconfirmed %.3g mm indication is above the %.3g mm floor and needs "
        "a confirming look before the cell moves either way" % (length, floor),
    )


def categorize_fingerprint_indication(
    indication, cleaning_cycles_used=0, criteria=DEFAULT_BARE_CELL_CRITERIA
):
    """Disposition one fingerprint indication on a bare cell."""
    validate_bare_cell_criteria(criteria)
    kind = validate_indication(indication)
    if kind != FINGERPRINT:
        raise ValueError("categorize_fingerprint_indication was handed a %s" % kind)
    used = _require_count("cleaning_cycles_used", cleaning_cycles_used)
    area = float(indication["area_mm2"])
    if indication["on_contact_area"]:
        return (
            REJECT,
            "a print of %.3g mm2 sits on a contact area; the ionic residue ends "
            "up inside a weld zone and the cleaning that would lift it attacks "
            "the metallisation" % area,
        )
    if not indication["removable"]:
        return (
            REJECT,
            "a print of %.3g mm2 recorded as not removable leaves hygroscopic "
            "residue on the cell for the life of the article" % area,
        )
    if used >= criteria["max_cleaning_cycles"]:
        return (
            REJECT,
            "the cell has already spent its %d cleaning cycles, so no cleaning "
            "route remains for a print of %.3g mm2"
            % (criteria["max_cleaning_cycles"], area),
        )
    if not _at_most(area, criteria["max_cleanable_fingerprint_area_mm2"]):
        return (
            REFER_FOR_REVIEW,
            "a print of %.3g mm2 is beyond the %.3g mm2 a single cleaning cycle "
            "is credited with, so the cleaning plan is reviewed before it runs"
            % (area, criteria["max_cleanable_fingerprint_area_mm2"]),
        )
    return (
        CLEAN_AND_REINSPECT,
        "a removable print of %.3g mm2 away from the contact areas is cleaned "
        "and looked at again" % area,
    )


def worst_disposition(dispositions):
    """The governing disposition of a set; severity, not record order."""
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    if not dispositions:
        return ACCEPT
    unknown = [d for d in dispositions if d not in _SEVERITY_ORDER]
    if unknown:
        raise ValueError("unknown disposition %r" % (unknown[0],))
    return max(dispositions, key=lambda d: _SEVERITY_ORDER[d])


def assess_cell(cell, criteria=DEFAULT_BARE_CELL_CRITERIA):
    """Clause 7.5.1.4.3 disposition for one bare cell."""
    validate_bare_cell_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    identifier = _require_label("cell id", cell.get("id"))
    if not identifier:
        raise ValueError("cell id must not be blank")

    declared = _require_count("declared_faces", cell.get("declared_faces", 1))
    if declared < 1:
        raise ValueError("a cell must declare at least one face to examine")
    examined = _require_count("faces_examined", cell.get("faces_examined", declared))
    if examined > declared:
        raise ValueError(
            "cell %s records %d faces examined against %d declared"
            % (identifier, examined, declared)
        )
    used = _require_count(
        "cleaning_cycles_used", cell.get("cleaning_cycles_used", 0)
    )

    conditions = validate_inspection_conditions(cell.get("conditions"), criteria)
    floor = crack_detection_floor_mm(
        conditions["working_distance_mm"],
        criteria["unaided_acuity_arcmin"],
        conditions["magnification"],
    )
    unaided_floor = crack_detection_floor_mm(
        conditions["working_distance_mm"], criteria["unaided_acuity_arcmin"], 1.0
    )

    condition_problems = list(condition_findings(conditions, criteria))
    findings = list(condition_problems)
    advisories = []
    if conditions["magnification"] > 1.0:
        advisories.append(
            "the record was made at %.3gx, a more sensitive instrument than the "
            "unaided look; because no crack is admissible it can only add "
            "rejections, never withdraw one" % conditions["magnification"]
        )
    if examined < declared:
        findings.append(
            "%d of %d declared faces were examined; a cell is only as crack "
            "free as the face nobody looked at" % (examined, declared)
        )

    indications = cell.get("indications", [])
    if not isinstance(indications, (list, tuple)):
        raise ValueError("cell %s must record indications as a sequence" % identifier)

    dispositions = []
    crack_count = 0
    fingerprint_count = 0
    for indication in indications:
        kind = validate_indication(indication)
        if kind == CRACK:
            crack_count += 1
            disposition, reason = categorize_crack_indication(
                indication, floor, criteria
            )
        else:
            fingerprint_count += 1
            disposition, reason = categorize_fingerprint_indication(
                indication, used, criteria
            )
        dispositions.append(disposition)
        if disposition != ACCEPT:
            findings.append("%s: %s" % (kind, reason))

    verdict = worst_disposition(dispositions)
    examination_sound = not condition_problems and examined >= declared
    if verdict != REJECT and not examination_sound:
        # A positive finding survives a poor examination -- a crack that was
        # seen was seen. An acceptance does not: it rests on the examination
        # having been able to find something, which here it was not.
        verdict = INSPECTION_INCOMPLETE

    return {
        "cell_id": identifier,
        "verdict": verdict,
        "crack_detection_floor_mm": floor,
        "unaided_detection_floor_mm": unaided_floor,
        "crack_indications": crack_count,
        "fingerprint_indications": fingerprint_count,
        "faces_examined": examined,
        "declared_faces": declared,
        "examination_sound": examination_sound,
        "findings": findings,
        "advisories": advisories,
    }


def assess_bare_cell_cracks_and_fingerprints(lot, criteria=DEFAULT_BARE_CELL_CRITERIA):
    """Roll the clause 7.5.1.4.3 screen up over a lot of bare cells."""
    validate_bare_cell_criteria(criteria)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    cells = lot.get("cells")
    if not isinstance(cells, (list, tuple)):
        raise ValueError("lot must record cells as a sequence")
    if not cells:
        raise ValueError("an empty lot has nothing to disposition")

    results = []
    seen = set()
    for cell in cells:
        result = assess_cell(cell, criteria)
        if result["cell_id"] in seen:
            raise ValueError("duplicate cell id %r in the lot" % result["cell_id"])
        seen.add(result["cell_id"])
        results.append(result)

    counts = {name: 0 for name in CELL_DISPOSITIONS}
    counts[INSPECTION_INCOMPLETE] = 0
    for result in results:
        counts[result["verdict"]] += 1

    total = len(results)
    return {
        "lot_id": _require_label("lot id", lot.get("id", "unnamed-lot")),
        "cells_assessed": total,
        "counts": counts,
        "accepted_fraction": counts[ACCEPT] / float(total),
        "rejected_fraction": counts[REJECT] / float(total),
        "worst_detection_floor_mm": max(
            result["crack_detection_floor_mm"] for result in results
        ),
        "cells_not_accepted": tuple(
            result["cell_id"] for result in results if result["verdict"] != ACCEPT
        ),
        "cell_results": tuple(results),
    }
