#!/usr/bin/env python3
"""Welds at string terminations and terminals checked against the drawing.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.14. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The welds that join a solar-array string to its termination hardware and
to the terminals are the points where the whole string's current leaves
the cell field. The inspection of this clause is not a free-standing
judgement of weld quality: the assembly control drawing is the
authority. The drawing says which locations carry welds, how many welds
each one carries, where each weld sits and how large its nugget has to
be, and the inspection answers the drawing.

Three comparisons are made at every welded location:

    population   the welds present against the count the drawing calls
                 for, and the sound welds left once the unsound ones
                 are taken out
    placement    each weld's offset from its drawn position against the
                 position tolerance the drawing carries
    nugget       each weld's measured diameter against the drawing band

A weld found at a location the drawing does not declare is an undeclared
weld. It is refused rather than graded, because there is no drawn
position or nugget band to grade it against, and an extra current path
nobody designed is a configuration question, not a workmanship one.

Dispositions are accept, rework and reject. The allowance set below is a
declared project allowance set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
WELD_DISPOSITIONS = (ACCEPT, REWORK, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

STRING_TERMINATION = "string-termination"
TERMINAL = "terminal"
LOCATION_TYPES = (STRING_TERMINATION, TERMINAL)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

NUGGET_CONDITIONS = ("cracked", "expelled", "discoloured")

DEFAULT_WELDING_ALLOWANCES = {
    "max_cracked_weld_fraction": 0.0,
    "max_expelled_weld_fraction": 0.10,
    "max_discoloured_weld_fraction": 0.25,
    "min_sound_welds": 2,
    "max_affected_location_fraction": 0.05,
    "rework_margin_factor": 2.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero" % name)
    return count


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An allowance is a product of a declared fraction and a counted
    number of welds or locations, and an offset is a root-sum-square of
    two measured components, so a value sitting exactly on its limit can
    evaluate a few units in the last place above it. The limit is never
    raised; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit under the same representation tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_welding_allowances(allowances):
    """Check a welding allowance set is complete and self-consistent."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping, got %r" % (allowances,))
    for key in (
        "max_cracked_weld_fraction",
        "max_expelled_weld_fraction",
        "max_discoloured_weld_fraction",
        "max_affected_location_fraction",
    ):
        _require_fraction("allowances %s" % key, allowances.get(key))
    _require_positive_count(
        "allowances min_sound_welds", allowances.get("min_sound_welds")
    )
    factor = allowances.get("rework_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "allowances rework_margin_factor must be at least one, got %r" % (factor,)
        )
    if (
        allowances["max_cracked_weld_fraction"]
        > allowances["max_expelled_weld_fraction"]
    ):
        raise ValueError(
            "allowances permit a larger fraction of cracked nuggets than of "
            "expelled ones; a cracked nugget is the worse of the pair, so the "
            "two allowances contradict each other"
        )
    return allowances


def validate_control_drawing(drawing):
    """Check the assembly control drawing the inspection answers to.

    The drawing is the authority for this clause, so it is validated
    before any weld is looked at. An unidentified or unrevised drawing
    cannot be the authority for anything.
    """
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    _require_text("drawing_id", drawing.get("drawing_id"))
    _require_text("drawing revision", drawing.get("revision"))
    locations = drawing.get("locations")
    if not isinstance(locations, (list, tuple)) or not locations:
        raise ValueError(
            "the control drawing must declare at least one welded location, "
            "got %r" % (locations,)
        )
    seen = {}
    for entry in locations:
        if not isinstance(entry, dict):
            raise ValueError("each drawing location must be a mapping, got %r" % (entry,))
        location_id = _require_text("location_id", entry.get("location_id"))
        if location_id in seen:
            raise ValueError(
                "the control drawing declares location %r twice" % location_id
            )
        location_type = entry.get("location_type")
        if location_type not in LOCATION_TYPES:
            raise ValueError(
                "location %s has location_type %r; the clause covers %s"
                % (location_id, location_type, " and ".join(LOCATION_TYPES))
            )
        _require_positive_count(
            "required_weld_count on %s" % location_id,
            entry.get("required_weld_count"),
        )
        _require_positive(
            "position_tolerance_mm on %s" % location_id,
            entry.get("position_tolerance_mm"),
        )
        low = _require_positive(
            "nugget_diameter_min_mm on %s" % location_id,
            entry.get("nugget_diameter_min_mm"),
        )
        high = _require_positive(
            "nugget_diameter_max_mm on %s" % location_id,
            entry.get("nugget_diameter_max_mm"),
        )
        if low > high:
            raise ValueError(
                "nugget diameter band on %s runs from %r down to %r"
                % (location_id, low, high)
            )
        seen[location_id] = entry
    return seen


def weld_geometry(weld, spec):
    """Offset from the drawn position and standing against the nugget band."""
    if not isinstance(weld, dict):
        raise ValueError("weld must be a mapping, got %r" % (weld,))
    weld_id = _require_text("weld_id", weld.get("weld_id"))
    offset_x = _require_number("offset_x_mm on %s" % weld_id, weld.get("offset_x_mm", 0.0))
    offset_y = _require_number("offset_y_mm on %s" % weld_id, weld.get("offset_y_mm", 0.0))
    diameter = _require_positive(
        "nugget_diameter_mm on %s" % weld_id, weld.get("nugget_diameter_mm")
    )
    tolerance = spec["position_tolerance_mm"]
    low = spec["nugget_diameter_min_mm"]
    high = spec["nugget_diameter_max_mm"]
    offset = math.hypot(offset_x, offset_y)
    return {
        "weld_id": weld_id,
        "position_offset_mm": offset,
        "position_tolerance_mm": float(tolerance),
        "offset_ratio": offset / float(tolerance),
        "within_position_tolerance": _at_most(offset, float(tolerance)),
        "nugget_diameter_mm": diameter,
        "nugget_band_mm": (float(low), float(high)),
        "undersized": not _at_least(diameter, float(low)),
        "oversized": not _at_most(diameter, float(high)),
    }


def assess_weld(weld, spec, allowances=DEFAULT_WELDING_ALLOWANCES):
    """Grade one weld against its drawing entry."""
    validate_welding_allowances(allowances)
    geometry = weld_geometry(weld, spec)
    weld_id = geometry["weld_id"]
    conditions = []
    for condition in NUGGET_CONDITIONS:
        flag = weld.get(condition, False)
        if not isinstance(flag, bool):
            raise ValueError(
                "%s on %s must be true or false, got %r" % (condition, weld_id, flag)
            )
        if flag:
            conditions.append(condition)

    findings = []
    dispositions = [ACCEPT]
    factor = allowances["rework_margin_factor"]

    if geometry["undersized"]:
        dispositions.append(REJECT)
        findings.append(
            "nugget diameter %.3f mm is under the %.3f mm the drawing calls for; "
            "an undersized nugget carries less current than the joint was drawn to"
            % (geometry["nugget_diameter_mm"], geometry["nugget_band_mm"][0])
        )
    elif geometry["oversized"]:
        dispositions.append(REWORK)
        findings.append(
            "nugget diameter %.3f mm is over the %.3f mm band top"
            % (geometry["nugget_diameter_mm"], geometry["nugget_band_mm"][1])
        )

    if not geometry["within_position_tolerance"]:
        if _at_most(geometry["position_offset_mm"], geometry["position_tolerance_mm"] * factor):
            dispositions.append(REWORK)
            findings.append(
                "sits %.3f mm from its drawn position, past the %.3f mm tolerance"
                % (geometry["position_offset_mm"], geometry["position_tolerance_mm"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "sits %.3f mm from its drawn position, past the %.3f mm rework margin"
                % (
                    geometry["position_offset_mm"],
                    geometry["position_tolerance_mm"] * factor,
                )
            )

    if "cracked" in conditions:
        dispositions.append(REJECT)
        findings.append("the nugget is cracked")
    if "expelled" in conditions:
        dispositions.append(REWORK)
        findings.append("the nugget shows expulsion")

    verdict = _worst(dispositions)
    return {
        "weld_id": weld_id,
        "verdict": verdict,
        "sound": verdict != REJECT and "cracked" not in conditions,
        "conditions": conditions,
        "geometry": geometry,
        "findings": findings,
    }


def assess_weld_location(record, spec, allowances=DEFAULT_WELDING_ALLOWANCES):
    """Apply the drawing entry for one location to the welds found there."""
    validate_welding_allowances(allowances)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    location_id = _require_text("location_id", record.get("location_id"))
    welds = record.get("welds")
    if not isinstance(welds, (list, tuple)):
        raise ValueError(
            "welds on %s must be a list, got %r" % (location_id, welds)
        )

    required = spec["required_weld_count"]
    seen = set()
    graded = []
    for weld in welds:
        result = assess_weld(weld, spec, allowances)
        if result["weld_id"] in seen:
            raise ValueError(
                "duplicate weld id %r at location %s" % (result["weld_id"], location_id)
            )
        seen.add(result["weld_id"])
        graded.append(result)

    present = len(graded)
    sound = sum(1 for result in graded if result["sound"])
    condition_counts = dict((name, 0) for name in NUGGET_CONDITIONS)
    for result in graded:
        for condition in result["conditions"]:
            condition_counts[condition] += 1

    findings = []
    dispositions = [ACCEPT] + [result["verdict"] for result in graded]
    for result in graded:
        for finding in result["findings"]:
            findings.append("%s %s" % (result["weld_id"], finding))

    if present > required:
        raise ValueError(
            "%d welds recorded at %s against the %d the drawing calls for; welds "
            "the drawing does not carry are a configuration question"
            % (present, location_id, required)
        )
    if present < required:
        dispositions.append(REWORK)
        findings.append(
            "%d welds of the %d the drawing calls for" % (present, required)
        )

    fractions = {}
    for condition, key in (
        ("cracked", "max_cracked_weld_fraction"),
        ("expelled", "max_expelled_weld_fraction"),
        ("discoloured", "max_discoloured_weld_fraction"),
    ):
        allowed = allowances[key] * required
        fractions[condition] = condition_counts[condition] / float(required)
        if _at_most(condition_counts[condition], allowed):
            continue
        if _at_most(condition_counts[condition], allowed * allowances["rework_margin_factor"]):
            dispositions.append(REWORK)
            findings.append(
                "%d %s nuggets of %d, past the %.2f the allowance permits"
                % (condition_counts[condition], condition, required, allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d %s nuggets of %d, past the rework margin of %.2f"
                % (
                    condition_counts[condition],
                    condition,
                    required,
                    allowed * allowances["rework_margin_factor"],
                )
            )

    reserve = min(allowances["min_sound_welds"], required)
    if sound == 0:
        dispositions.append(REJECT)
        findings.append(
            "no sound weld is left; the string termination carries no current path"
        )
    elif sound < reserve:
        dispositions.append(REJECT)
        findings.append(
            "%d sound welds against the %d the allowance keeps in reserve"
            % (sound, reserve)
        )

    return {
        "location_id": location_id,
        "location_type": spec["location_type"],
        "verdict": _worst(dispositions),
        "required_weld_count": required,
        "welds_present": present,
        "missing_weld_count": required - present,
        "sound_weld_count": sound,
        "condition_counts": condition_counts,
        "condition_fractions": fractions,
        "welds": graded,
        "not_accepted_weld_ids": [
            result["weld_id"] for result in graded if result["verdict"] != ACCEPT
        ],
        "findings": findings,
    }


def inspect_welding(assembly, drawing, allowances=DEFAULT_WELDING_ALLOWANCES):
    """Clause 5.5.3.2.14 weld inspection over one assembly, drawing-led."""
    validate_welding_allowances(allowances)
    specs = validate_control_drawing(drawing)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = _require_text("assembly_id", assembly.get("assembly_id"))
    cited = _require_text("drawing_revision", assembly.get("drawing_revision"))
    if cited != drawing["revision"]:
        raise ValueError(
            "assembly %s was inspected against drawing revision %r while the "
            "drawing in hand is revision %r; the inspection answers a drawing "
            "that is not this one" % (assembly_id, cited, drawing["revision"])
        )
    records = assembly.get("locations")
    if not isinstance(records, (list, tuple)):
        raise ValueError("locations must be a list, got %r" % (records,))

    screened = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each location record must be a mapping, got %r" % (record,))
        location_id = _require_text("location_id", record.get("location_id"))
        if location_id not in specs:
            raise ValueError(
                "location %r was inspected but the control drawing does not "
                "declare it; an undeclared welded location is refused, not graded"
                % location_id
            )
        if location_id in seen:
            raise ValueError("duplicate location record %r on %s" % (location_id, assembly_id))
        seen.add(location_id)
        screened.append(assess_weld_location(record, specs[location_id], allowances))

    inspected = len(screened)
    declared = len(specs)
    missing_ids = sorted(set(specs) - seen)
    counts = dict((state, 0) for state in WELD_DISPOSITIONS)
    findings = []
    dispositions = [ACCEPT]
    affected = 0
    weld_total = 0
    sound_total = 0
    for result in screened:
        counts[result["verdict"]] += 1
        dispositions.append(result["verdict"])
        weld_total += result["welds_present"]
        sound_total += result["sound_weld_count"]
        if result["verdict"] != ACCEPT or result["findings"]:
            affected += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["location_id"], finding))

    affected_allowed = allowances["max_affected_location_fraction"] * inspected
    factor = allowances["rework_margin_factor"]
    if inspected and not _at_most(affected, affected_allowed):
        if _at_most(affected, affected_allowed * factor):
            dispositions.append(REWORK)
            findings.append(
                "%d of %d welded locations carry a finding, past the %.2f the "
                "assembly allowance permits" % (affected, inspected, affected_allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d welded locations carry a finding, past the rework "
                "margin of %.2f" % (affected, inspected, affected_allowed * factor)
            )

    verdict = _worst(dispositions)
    complete = not missing_ids
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of the %d welded locations the drawing declares carry no "
            "inspection record; an allowance applied to a short set is applied "
            "to the wrong population" % (len(missing_ids), declared)
        )
    return {
        "assembly_id": assembly_id,
        "drawing_id": drawing["drawing_id"],
        "drawing_revision": drawing["revision"],
        "verdict": verdict,
        "inspection_complete": complete,
        "declared_location_count": declared,
        "inspected_location_count": inspected,
        "uninspected_location_ids": missing_ids,
        "disposition_counts": counts,
        "weld_count": weld_total,
        "sound_weld_count": sound_total,
        "affected_location_count": affected,
        "affected_location_fraction": affected / float(inspected) if inspected else 0.0,
        "affected_location_allowance": affected_allowed,
        "remaining_affected_allowance": affected_allowed - affected,
        "not_accepted_location_ids": [
            result["location_id"] for result in screened if result["verdict"] != ACCEPT
        ],
        "locations": screened,
        "findings": findings,
    }
