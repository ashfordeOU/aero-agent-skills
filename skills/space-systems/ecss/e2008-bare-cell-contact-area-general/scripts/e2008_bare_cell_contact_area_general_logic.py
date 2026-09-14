#!/usr/bin/env python3
"""General condition of the contact areas of a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause wants the contact areas of a bare cell kept clear of digs,
scratches and probe marks in the places where the metallisation is
absent. Two qualifiers carry the whole requirement and both are dropped
routinely.

The first is the location. The requirement is about contact areas, not
about the cell face at large. A scratch in the middle of an active
region is a real finding under other clauses and it is simply not this
one, so a mark has to be placed against the contact geometry before it
is dispositioned at all. Placing it is a containment test, not a
judgement: a mark sits inside a contact area, straddles its edge, or
lies outside it, and a straddling mark contributes only the part that
overlaps.

The second qualifier is the condition of the metallisation. A dig that
has displaced metal but left a continuous conductor behind has not
exposed anything; the same dig that has gone through has bared the
semiconductor inside the area a weld is going to be made on, and that
is what the clause refuses. So the metallisation state -- intact,
thinned, absent -- decides the disposition and the mark's own size does
not.

Thinned metal is the interesting middle. It is not bare and it is not
sound; a contact thinned past a working fraction of its deposit is one
probe landing or one weld pulse away from being bare, so it goes to
review rather than being accepted on the grounds that nothing is
showing through yet.

Two area-level effects survive an area where every individual mark was
admissible. Probe witnesses accumulate at the same sites because that
is where the fixture puts them, so a witness count is tracked per
contact area. And the disturbed footprint accumulates too: an area can
be fully metallised and still have had most of its weldable surface
worked over.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIG = "dig"
SCRATCH = "scratch"
PROBE_MARK = "probe-mark"
DEFECT_KINDS = (DIG, SCRATCH, PROBE_MARK)

INTACT = "intact"
THINNED = "thinned"
ABSENT = "absent"
METALLISATION_STATES = (INTACT, THINNED, ABSENT)

OUTSIDE_CONTACT_AREA = "outside-contact-area"
ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
REJECT = "reject"
CONTACT_DISPOSITIONS = (OUTSIDE_CONTACT_AREA, ACCEPT, REFER_FOR_REVIEW, REJECT)

INSIDE = "inside"
STRADDLING = "straddling"
OUTSIDE = "outside"
PLACEMENTS = (INSIDE, STRADDLING, OUTSIDE)

_SEVERITY_ORDER = {
    OUTSIDE_CONTACT_AREA: 0,
    ACCEPT: 1,
    REFER_FOR_REVIEW: 2,
    REJECT: 3,
}

DEFAULT_CONTACT_AREA_CRITERIA = {
    "min_remaining_metallisation_fraction": 0.5,
    "max_probe_witnesses_per_contact_area": 3,
    "max_disturbed_area_fraction": 0.05,
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
    if number <= 0.0 or number > 1.0:
        raise ValueError(
            "%s must fall in the interval (0, 1], got %r" % (name, value)
        )
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
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


def validate_contact_area_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_fraction(
        "min_remaining_metallisation_fraction",
        criteria.get("min_remaining_metallisation_fraction"),
    )
    _require_count(
        "max_probe_witnesses_per_contact_area",
        criteria.get("max_probe_witnesses_per_contact_area"),
    )
    _require_fraction(
        "max_disturbed_area_fraction", criteria.get("max_disturbed_area_fraction")
    )
    return criteria


def validate_contact_area(area):
    """Normalise one contact area footprint in the cell coordinate frame."""
    if not isinstance(area, dict):
        raise ValueError("contact area must be a mapping, got %r" % (area,))
    identifier = _require_label("contact area id", area.get("id"))
    if not identifier:
        raise ValueError("contact area id must not be blank")
    x = _require_number("contact area x_mm", area.get("x_mm"))
    y = _require_number("contact area y_mm", area.get("y_mm"))
    width = _require_positive("contact area width_mm", area.get("width_mm"))
    length = _require_positive("contact area length_mm", area.get("length_mm"))
    return {
        "id": identifier,
        "x_mm": x,
        "y_mm": y,
        "width_mm": width,
        "length_mm": length,
    }


def contact_area_mm2(area):
    """Footprint of one contact area."""
    normalised = validate_contact_area(area)
    return normalised["width_mm"] * normalised["length_mm"]


def validate_defect(defect):
    """Check one recorded mark carries the fields its disposition needs."""
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    kind = defect.get("kind")
    if kind not in DEFECT_KINDS:
        raise ValueError(
            "defect kind must be one of %s, got %r"
            % (", ".join(DEFECT_KINDS), kind)
        )
    state = defect.get("metallisation")
    if state not in METALLISATION_STATES:
        raise ValueError(
            "metallisation must be one of %s, got %r"
            % (", ".join(METALLISATION_STATES), state)
        )
    normalised = {
        "kind": kind,
        "metallisation": state,
        "x_mm": _require_number("defect x_mm", defect.get("x_mm")),
        "y_mm": _require_number("defect y_mm", defect.get("y_mm")),
        "width_mm": _require_positive("defect width_mm", defect.get("width_mm")),
        "length_mm": _require_positive("defect length_mm", defect.get("length_mm")),
        "remaining_metallisation_fraction": None,
    }
    if state == THINNED:
        if "remaining_metallisation_fraction" not in defect:
            raise ValueError(
                "a thinned mark must record remaining_metallisation_fraction; "
                "without it the disposition has nothing to compare"
            )
        normalised["remaining_metallisation_fraction"] = _require_fraction(
            "remaining_metallisation_fraction",
            defect.get("remaining_metallisation_fraction"),
        )
    return normalised


def defect_footprint_mm2(defect):
    """Footprint of one mark, independent of where it sits."""
    normalised = validate_defect(defect)
    return normalised["width_mm"] * normalised["length_mm"]


def overlap_area_mm2(defect, area):
    """Footprint the mark and the contact area have in common."""
    mark = validate_defect(defect)
    pad = validate_contact_area(area)
    left = max(mark["x_mm"], pad["x_mm"])
    right = min(mark["x_mm"] + mark["width_mm"], pad["x_mm"] + pad["width_mm"])
    bottom = max(mark["y_mm"], pad["y_mm"])
    top = min(mark["y_mm"] + mark["length_mm"], pad["y_mm"] + pad["length_mm"])
    if right <= left or top <= bottom:
        return 0.0
    return (right - left) * (top - bottom)


def defect_placement(defect, area):
    """Whether a mark sits inside a contact area, straddles it, or misses it."""
    mark = validate_defect(defect)
    overlap = overlap_area_mm2(defect, area)
    if overlap <= 0.0:
        return OUTSIDE
    footprint = mark["width_mm"] * mark["length_mm"]
    if math.isclose(overlap, footprint, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return INSIDE
    return STRADDLING


def categorize_contact_defect(
    defect, area, criteria=DEFAULT_CONTACT_AREA_CRITERIA
):
    """Disposition one mark against one contact area."""
    validate_contact_area_criteria(criteria)
    mark = validate_defect(defect)
    pad = validate_contact_area(area)
    placement = defect_placement(defect, area)
    if placement == OUTSIDE:
        return (
            OUTSIDE_CONTACT_AREA,
            "the %s misses contact area %s entirely; the cell face at large is "
            "not what this clause is about" % (mark["kind"], pad["id"]),
        )
    overlap = overlap_area_mm2(defect, area)
    if mark["metallisation"] == ABSENT:
        return (
            REJECT,
            "the %s bares the semiconductor over %.4g mm2 of contact area %s, "
            "which is the surface a weld is going to be made on"
            % (mark["kind"], overlap, pad["id"]),
        )
    if mark["metallisation"] == THINNED:
        remaining = mark["remaining_metallisation_fraction"]
        if not _at_least(
            remaining, criteria["min_remaining_metallisation_fraction"]
        ):
            return (
                REFER_FOR_REVIEW,
                "the %s leaves %.0f per cent of the deposit on contact area %s, "
                "under the %.0f per cent working fraction; nothing is showing "
                "through yet and one probe landing would change that"
                % (
                    mark["kind"],
                    remaining * 100.0,
                    pad["id"],
                    criteria["min_remaining_metallisation_fraction"] * 100.0,
                ),
            )
        return (
            ACCEPT,
            "the %s has thinned contact area %s to %.0f per cent of the deposit "
            "and left a sound conductor behind"
            % (mark["kind"], pad["id"], remaining * 100.0),
        )
    return (
        ACCEPT,
        "the %s has displaced metal on contact area %s without breaking the "
        "conductor" % (mark["kind"], pad["id"]),
    )


def disturbed_area_mm2(defects, area):
    """Total contact-area footprint touched by marks of any kind.

    Overlapping marks are summed rather than unioned: the count is a
    measure of how much working the surface has taken, and a site worked
    twice has taken twice the working.
    """
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a sequence of mark records")
    return sum(overlap_area_mm2(defect, area) for defect in defects)


def exposed_area_mm2(defects, area):
    """Contact-area footprint over which the metallisation is gone."""
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a sequence of mark records")
    total = 0.0
    for defect in defects:
        mark = validate_defect(defect)
        if mark["metallisation"] == ABSENT:
            total += overlap_area_mm2(defect, area)
    return total


def disturbed_area_fraction(defects, area):
    """Disturbed footprint as a fraction of the contact area."""
    return disturbed_area_mm2(defects, area) / contact_area_mm2(area)


def probe_witness_count(defects, area):
    """Probe marks landing on one contact area."""
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a sequence of mark records")
    count = 0
    for defect in defects:
        mark = validate_defect(defect)
        if mark["kind"] == PROBE_MARK and defect_placement(defect, area) != OUTSIDE:
            count += 1
    return count


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


def assess_contact_area(area, defects, criteria=DEFAULT_CONTACT_AREA_CRITERIA):
    """Clause 7.5.1.5.1 disposition for one contact area."""
    validate_contact_area_criteria(criteria)
    pad = validate_contact_area(area)
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a sequence of mark records")

    findings = []
    advisories = []
    dispositions = []
    in_area = 0
    for defect in defects:
        disposition, reason = categorize_contact_defect(defect, area, criteria)
        if disposition == OUTSIDE_CONTACT_AREA:
            advisories.append(reason)
            continue
        in_area += 1
        dispositions.append(disposition)
        if disposition != ACCEPT:
            findings.append(reason)

    footprint = contact_area_mm2(area)
    exposed = exposed_area_mm2(defects, area)
    disturbed = disturbed_area_mm2(defects, area)
    witnesses = probe_witness_count(defects, area)

    if not _at_most(
        disturbed / footprint, criteria["max_disturbed_area_fraction"]
    ):
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "marks have worked %.1f per cent of contact area %s, past the %.1f "
            "per cent allowance; the metallisation can be sound everywhere and "
            "the weldable surface still be used up"
            % (
                disturbed / footprint * 100.0,
                pad["id"],
                criteria["max_disturbed_area_fraction"] * 100.0,
            )
        )
    if witnesses > criteria["max_probe_witnesses_per_contact_area"]:
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "%d probe witnesses on contact area %s, past the %d the criteria "
            "allow; the fixture lands on the same sites and eventually one goes "
            "through"
            % (
                witnesses,
                pad["id"],
                criteria["max_probe_witnesses_per_contact_area"],
            )
        )

    return {
        "contact_area_id": pad["id"],
        "verdict": worst_disposition(dispositions),
        "contact_area_mm2": footprint,
        "marks_in_area": in_area,
        "exposed_area_mm2": exposed,
        "exposed_area_fraction": exposed / footprint,
        "disturbed_area_mm2": disturbed,
        "disturbed_area_fraction": disturbed / footprint,
        "probe_witnesses": witnesses,
        "findings": findings,
        "advisories": advisories,
    }


def assess_bare_cell_contact_area(case, criteria=DEFAULT_CONTACT_AREA_CRITERIA):
    """Roll the clause 7.5.1.5.1 screen up over the contact areas of one cell."""
    validate_contact_area_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    areas = case.get("contact_areas")
    if not isinstance(areas, (list, tuple)):
        raise ValueError("case must record contact_areas as a sequence")
    if not areas:
        raise ValueError(
            "a cell with no contact area declared cannot be screened against a "
            "clause about contact areas"
        )
    defects = case.get("defects", [])
    if not isinstance(defects, (list, tuple)):
        raise ValueError("case must record defects as a sequence")

    results = []
    seen = set()
    for area in areas:
        result = assess_contact_area(area, defects, criteria)
        if result["contact_area_id"] in seen:
            raise ValueError(
                "duplicate contact area id %r on the cell" % result["contact_area_id"]
            )
        seen.add(result["contact_area_id"])
        results.append(result)

    unplaced = []
    for defect in defects:
        if all(
            defect_placement(defect, area) == OUTSIDE for area in areas
        ):
            unplaced.append(validate_defect(defect)["kind"])

    return {
        "cell_id": _require_label("cell id", case.get("id", "unnamed-cell")),
        "verdict": worst_disposition(
            [result["verdict"] for result in results]
        ),
        "contact_areas_assessed": len(results),
        "total_exposed_area_mm2": sum(
            result["exposed_area_mm2"] for result in results
        ),
        "contact_areas_not_accepted": tuple(
            result["contact_area_id"]
            for result in results
            if result["verdict"] != ACCEPT
        ),
        "marks_outside_every_contact_area": tuple(unplaced),
        "contact_area_results": tuple(results),
    }
