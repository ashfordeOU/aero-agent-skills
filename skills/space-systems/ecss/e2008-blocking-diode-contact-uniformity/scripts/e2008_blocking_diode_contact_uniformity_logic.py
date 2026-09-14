#!/usr/bin/env python3
"""Contact evenness on a blocking diode, judged for the weld that comes later.

Anchor: ECSS-E-ST-20-08C clause 12.6.13. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The evenness of the contact is not checked here for its own sake. It is
checked because an interconnector will be welded onto that contact later,
and a weld schedule is set once and then run on every joint. The question
the clause asks is therefore narrower than a general uniformity question: is
this contact even enough that one schedule will give the same, adequate weld
everywhere it is applied?

Two different evennesses follow from that, and a map reduced to a single
spread figure loses one of them.

Inside one weld footprint, the metal under the electrode has to stay inside
the band the schedule was set for. Too thin and the weld burns through to
the semiconductor; too thick and the energy never reaches the interface.
A footprint whose readings straddle the band fails even when its mean sits
comfortably in the middle of it, which is why the band is applied per
reading and the spread is taken against the footprint's own mean.

Between footprints, the means have to agree. One schedule runs on all of
them, so a contact whose first footprint sits near the floor and whose last
sits near the ceiling will weld reproducibly nowhere, even though every
individual footprint passed its own band. That is the reproducibility the
clause is after and it is invisible to a per-footprint check.

A footprint the map never reached is not a pass. Readings clustered away
from the weld sites describe metal nobody will put an electrode on, so a
footprint carrying fewer readings than the policy asks for is left unmapped
and closes the assessment rather than being averaged into the contact.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GRADE_WELDABLE = "weldable"
GRADE_BELOW_WELD_FLOOR = "below-weld-floor"
GRADE_ABOVE_WELD_CEILING = "above-weld-ceiling"
GRADE_UNEVEN_ACROSS_FOOTPRINT = "uneven-across-footprint"
GRADE_NOT_MAPPED = "not-mapped"

WELD_FOOTPRINTS_NOT_ESTABLISHED = "weld-footprints-not-established"
CONTACT_MAP_INCOMPLETE = "contact-map-incomplete"
CONTACT_NOT_WELD_READY = "contact-not-weld-ready"
CONTACT_READY_FOR_WELDING = "contact-ready-for-interconnector-welding"

DEFAULT_WELD_POLICY = {
    "min_weldable_thickness_um": 4.0,
    "max_weldable_thickness_um": 12.0,
    "max_footprint_spread_fraction": 0.20,
    "advisory_spread_fraction": 0.16,
    "max_footprint_mean_spread_fraction": 0.15,
    "min_readings_per_footprint": 3,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def validate_weld_policy(policy):
    """Check the declared weld readiness policy is complete and consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    floor = _require_positive(
        "min_weldable_thickness_um", policy.get("min_weldable_thickness_um")
    )
    ceiling = _require_positive(
        "max_weldable_thickness_um", policy.get("max_weldable_thickness_um")
    )
    if not floor < ceiling:
        raise ValueError(
            "the weldable band runs from %g um up to %g um, which admits no "
            "thickness" % (floor, ceiling)
        )
    spread = _require_positive(
        "max_footprint_spread_fraction",
        policy.get("max_footprint_spread_fraction"),
    )
    if spread > 1.0:
        raise ValueError(
            "max_footprint_spread_fraction %g is above one; a footprint "
            "varying by more than its own mean is not a weld site" % spread
        )
    advisory = _require_positive(
        "advisory_spread_fraction", policy.get("advisory_spread_fraction")
    )
    if not _at_most(advisory, spread):
        raise ValueError(
            "the advisory spread of %g sits above the %g the policy allows, so "
            "no weldable footprint could ever raise it" % (advisory, spread)
        )
    mean_spread = _require_positive(
        "max_footprint_mean_spread_fraction",
        policy.get("max_footprint_mean_spread_fraction"),
    )
    if mean_spread > 1.0:
        raise ValueError(
            "max_footprint_mean_spread_fraction %g is above one; one weld "
            "schedule cannot serve that contact" % mean_spread
        )
    _require_count(
        "min_readings_per_footprint", policy.get("min_readings_per_footprint")
    )
    return policy


def validate_thickness_reading(reading):
    """Read one mapped thickness reading: where it was taken and what it read."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    identifier = _require_label("reading id", reading.get("id"))
    if not identifier:
        raise ValueError("reading id must not be blank")
    return {
        "id": identifier,
        "position_mm": _require_number(
            "position_mm on %s" % identifier, reading.get("position_mm")
        ),
        "thickness_um": _require_positive(
            "thickness_um on %s" % identifier, reading.get("thickness_um")
        ),
    }


def validate_weld_footprint(footprint):
    """Read one interconnector weld footprint: its identifier and its span."""
    if not isinstance(footprint, dict):
        raise ValueError("footprint must be a mapping, got %r" % (footprint,))
    identifier = _require_label("footprint id", footprint.get("id"))
    if not identifier:
        raise ValueError("footprint id must not be blank")
    start = _require_number("start_mm on %s" % identifier, footprint.get("start_mm"))
    end = _require_number("end_mm on %s" % identifier, footprint.get("end_mm"))
    if not end > start:
        raise ValueError(
            "footprint %s ends at %g mm having started at %g mm, which is not "
            "a weld site" % (identifier, end, start)
        )
    return {"id": identifier, "start_mm": start, "end_mm": end}


def readings_in_footprint(readings, footprint):
    """The mapped readings that fall inside one weld footprint, edges included."""
    if not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a sequence of mapped readings")
    span = validate_weld_footprint(footprint)
    inside = []
    for reading in readings:
        checked = validate_thickness_reading(reading)
        if _at_least(checked["position_mm"], span["start_mm"]) and _at_most(
            checked["position_mm"], span["end_mm"]
        ):
            inside.append(checked)
    return tuple(inside)


def footprint_statistics(readings):
    """Mean, extremes and spread against the footprint's own mean."""
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("a footprint with no reading has no statistics")
    thicknesses = [reading["thickness_um"] for reading in readings]
    mean = sum(thicknesses) / len(thicknesses)
    if mean <= 0.0:
        raise ValueError("a footprint mean thickness of %g um is not metal" % mean)
    return {
        "count": len(thicknesses),
        "mean_um": mean,
        "min_um": min(thicknesses),
        "max_um": max(thicknesses),
        "spread_fraction": (max(thicknesses) - min(thicknesses)) / mean,
    }


def grade_weld_footprint(footprint, readings, policy=DEFAULT_WELD_POLICY):
    """Grade one weld footprint for the schedule that will be run on it."""
    validate_weld_policy(policy)
    span = validate_weld_footprint(footprint)
    inside = readings_in_footprint(readings, footprint)
    graded = {
        "id": span["id"],
        "count": len(inside),
        "mean_um": None,
        "min_um": None,
        "max_um": None,
        "spread_fraction": None,
        "reasons": (),
        "grade": GRADE_NOT_MAPPED,
        "weldable": False,
    }
    if len(inside) < int(policy["min_readings_per_footprint"]):
        return graded

    stats = footprint_statistics(inside)
    graded.update(
        {
            "mean_um": stats["mean_um"],
            "min_um": stats["min_um"],
            "max_um": stats["max_um"],
            "spread_fraction": stats["spread_fraction"],
        }
    )
    reasons = []
    if not _at_least(stats["min_um"], float(policy["min_weldable_thickness_um"])):
        reasons.append(GRADE_BELOW_WELD_FLOOR)
    if not _at_most(stats["max_um"], float(policy["max_weldable_thickness_um"])):
        reasons.append(GRADE_ABOVE_WELD_CEILING)
    if not _at_most(
        stats["spread_fraction"], float(policy["max_footprint_spread_fraction"])
    ):
        reasons.append(GRADE_UNEVEN_ACROSS_FOOTPRINT)
    graded["reasons"] = tuple(reasons)
    graded["grade"] = reasons[0] if reasons else GRADE_WELDABLE
    graded["weldable"] = not reasons
    return graded


def grade_weld_footprints(footprints, readings, policy=DEFAULT_WELD_POLICY):
    """Grade every declared weld footprint, in declaration order."""
    if not isinstance(footprints, (list, tuple)):
        raise ValueError("footprints must be a sequence of weld footprints")
    if not footprints:
        raise ValueError(
            "no weld footprint is declared, so there is nowhere to judge the "
            "contact for welding"
        )
    graded = []
    seen = set()
    for footprint in footprints:
        one = grade_weld_footprint(footprint, readings, policy)
        if one["id"] in seen:
            raise ValueError("duplicate footprint id %r in the map" % one["id"])
        seen.add(one["id"])
        graded.append(one)
    return tuple(graded)


def footprint_mean_spread_fraction(graded):
    """How far the mapped footprint means sit apart, against their own average.

    This is the reproducibility figure: one weld schedule runs on all of
    them, so it is the disagreement between footprints, not inside one, that
    decides whether the schedule can serve the whole contact.
    """
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded footprints")
    means = [one["mean_um"] for one in graded if one["mean_um"] is not None]
    if not means:
        raise ValueError("no footprint carries a mean, so no spread exists")
    average = sum(means) / len(means)
    if average <= 0.0:
        raise ValueError("an average footprint mean of %g um is not metal" % average)
    return (max(means) - min(means)) / average


def unmapped_footprints(graded):
    """Footprints the thickness map never covered densely enough to judge."""
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded footprints")
    return tuple(one["id"] for one in graded if one["grade"] == GRADE_NOT_MAPPED)


def marginal_footprint_advisories(graded, policy=DEFAULT_WELD_POLICY):
    """Name weldable footprints already close to the spread the policy allows.

    These do not move the verdict -- a weldable footprint is weldable -- but
    a contact that is even enough only by a hair will not stay that way
    across a production run, and that is worth saying once here.
    """
    validate_weld_policy(policy)
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded footprints")
    band = float(policy["advisory_spread_fraction"])
    advisories = []
    for one in graded:
        if not one["weldable"] or one["spread_fraction"] is None:
            continue
        if _at_least(one["spread_fraction"], band):
            advisories.append(
                "footprint %s is weldable at a spread of %.3g per cent, already "
                "at or past the %.3g per cent advisory band; one schedule will "
                "not hold this evenness across a production run"
                % (one["id"], one["spread_fraction"] * 100.0, band * 100.0)
            )
    return tuple(advisories)


def assess_blocking_diode_contact_uniformity(case, policy=DEFAULT_WELD_POLICY):
    """Full clause 12.6.13 weld readiness decision for one mapped contact."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_weld_policy(policy)

    findings = []
    advisories = []
    result = {
        "footprint_grades": (),
        "weldable_footprints": (),
        "rejected_footprints": (),
        "unmapped_footprints": (),
        "footprint_mean_spread_fraction": None,
        "worst_footprint_id": None,
        "worst_footprint_spread_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    footprints = case.get("weld_footprints")
    if not footprints:
        findings.append(
            "no interconnector weld footprint is declared, so an evenness "
            "figure has nowhere to be applied"
        )
        result["verdict"] = WELD_FOOTPRINTS_NOT_ESTABLISHED
        return result

    readings = case.get("thickness_readings")
    if not readings:
        findings.append(
            "the contact carries no thickness reading, so its evenness is "
            "unknown rather than adequate"
        )
        result["verdict"] = CONTACT_MAP_INCOMPLETE
        return result

    graded = grade_weld_footprints(footprints, readings, policy)
    result["footprint_grades"] = graded
    result["unmapped_footprints"] = unmapped_footprints(graded)
    result["weldable_footprints"] = tuple(
        one["id"] for one in graded if one["weldable"]
    )
    result["rejected_footprints"] = tuple(
        one["id"]
        for one in graded
        if not one["weldable"] and one["grade"] != GRADE_NOT_MAPPED
    )

    if result["unmapped_footprints"]:
        findings.append(
            "the map never reached %s densely enough to judge; readings taken "
            "away from a weld site describe metal no electrode will touch"
            % ", ".join(result["unmapped_footprints"])
        )
        result["verdict"] = CONTACT_MAP_INCOMPLETE
        return result

    result["footprint_mean_spread_fraction"] = footprint_mean_spread_fraction(graded)
    worst = max(graded, key=lambda one: one["spread_fraction"])
    result["worst_footprint_id"] = worst["id"]
    result["worst_footprint_spread_fraction"] = worst["spread_fraction"]

    for one in graded:
        if one["weldable"]:
            continue
        findings.append(
            "footprint %s is not weld ready: %s; mean %.3g um over %d readings "
            "spanning %.3g to %.3g um"
            % (
                one["id"],
                " and ".join(one["reasons"]),
                one["mean_um"],
                one["count"],
                one["min_um"],
                one["max_um"],
            )
        )

    advisories.extend(marginal_footprint_advisories(graded, policy))

    if not _at_most(
        result["footprint_mean_spread_fraction"],
        float(policy["max_footprint_mean_spread_fraction"]),
    ):
        findings.append(
            "the footprint means sit %.3g per cent apart, past the %.3g per "
            "cent one weld schedule can serve; each footprint passes its own "
            "band and no single schedule welds them alike"
            % (
                result["footprint_mean_spread_fraction"] * 100.0,
                float(policy["max_footprint_mean_spread_fraction"]) * 100.0,
            )
        )

    if findings:
        result["verdict"] = CONTACT_NOT_WELD_READY
        return result

    result["verdict"] = CONTACT_READY_FOR_WELDING
    return result
