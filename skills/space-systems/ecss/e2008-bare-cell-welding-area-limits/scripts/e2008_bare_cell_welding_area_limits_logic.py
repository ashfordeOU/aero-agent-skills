#!/usr/bin/env python3
"""Void and bubble diameter limits inside the contact welding areas.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause fixes a maximum permitted diameter for a void or a bubble
lying inside a contact welding area. It reads like a one-line
comparison and it is not, because three things have to be settled
before there is anything to compare.

The first is where the limit comes from. It is fixed for the part, so a
verdict quoted without the drawing that fixes it is not a verdict
against this clause; an unreferenced limit closes the assessment rather
than passing it.

The second is which number counts as the diameter. A void is rarely
round. Recording a major and a minor axis and then reporting the
area-equivalent diameter makes an elongated void look smaller than it
is, and it is the long chord that decides whether a weld nugget can
find sound metal to sit on. So the governing diameter is the major
axis when one is recorded, and the area-equivalent diameter only when
the record has nothing but an area -- which is a weaker figure and is
flagged as one.

The third is the margin. A void measured a hair inside the limit is
inside it only if the measurement was better than the hair. The
comparison therefore runs twice: once on the nominal value, which
decides the rejection, and once with the measurement uncertainty
added, which decides whether the acceptance is safe to make without a
second look.

Location still matters. A bubble outside the welding areas is not this
clause's business, and it is carried as an advisory so it reaches the
clause that owns it rather than being silently dropped.

Finally, a scatter of individually admissible bubbles is still a bad
weld zone. The void area fraction and the void count per welding area
catch the zone where every single bubble passed and there is not enough
sound metal left to put a nugget on.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VOID = "void"
BUBBLE = "bubble"
VOID_KINDS = (VOID, BUBBLE)

MAJOR_AXIS = "major-axis"
STATED_DIAMETER = "stated-diameter"
AREA_EQUIVALENT = "area-equivalent"
DIAMETER_SOURCES = (MAJOR_AXIS, STATED_DIAMETER, AREA_EQUIVALENT)

OUTSIDE_WELDING_AREA = "outside-welding-area"
ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
REJECT = "reject"
VOID_DISPOSITIONS = (OUTSIDE_WELDING_AREA, ACCEPT, REFER_FOR_REVIEW, REJECT)

LIMIT_NOT_ESTABLISHED = "void-diameter-limit-not-established"

_SEVERITY_ORDER = {
    OUTSIDE_WELDING_AREA: 0,
    ACCEPT: 1,
    REFER_FOR_REVIEW: 2,
    REJECT: 3,
}

DEFAULT_WELDING_AREA_CRITERIA = {
    "measurement_uncertainty_mm": 0.01,
    "max_void_area_fraction": 0.10,
    "max_voids_per_welding_area": 5,
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_welding_area_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_non_negative(
        "measurement_uncertainty_mm", criteria.get("measurement_uncertainty_mm")
    )
    _require_fraction(
        "max_void_area_fraction", criteria.get("max_void_area_fraction")
    )
    _require_count(
        "max_voids_per_welding_area", criteria.get("max_voids_per_welding_area")
    )
    return criteria


def equivalent_diameter_mm(area_mm2):
    """Diameter of the circle with the same area as the measured void."""
    area = _require_positive("area_mm2", area_mm2)
    return math.sqrt(4.0 * area / math.pi)


def circle_area_mm2(diameter_mm):
    """Area of a round void of the given diameter."""
    diameter = _require_positive("diameter_mm", diameter_mm)
    return math.pi * diameter * diameter / 4.0


def ellipse_area_mm2(major_axis_mm, minor_axis_mm):
    """Area of an elongated void from its two axes."""
    major = _require_positive("major_axis_mm", major_axis_mm)
    minor = _require_positive("minor_axis_mm", minor_axis_mm)
    if minor > major:
        raise ValueError(
            "the minor axis %g mm exceeds the major axis %g mm; the axes are "
            "the wrong way round" % (minor, major)
        )
    return math.pi * major * minor / 4.0


def validate_welding_area(area):
    """Normalise one welding area and the limit fixed for it."""
    if not isinstance(area, dict):
        raise ValueError("welding area must be a mapping, got %r" % (area,))
    identifier = _require_label("welding area id", area.get("id"))
    if not identifier:
        raise ValueError("welding area id must not be blank")
    x = _require_number("welding area x_mm", area.get("x_mm"))
    y = _require_number("welding area y_mm", area.get("y_mm"))
    width = _require_positive("welding area width_mm", area.get("width_mm"))
    length = _require_positive("welding area length_mm", area.get("length_mm"))
    limit = area.get("max_permitted_void_diameter_mm")
    reference = area.get("drawing_reference")
    normalised = {
        "id": identifier,
        "x_mm": x,
        "y_mm": y,
        "width_mm": width,
        "length_mm": length,
        "max_permitted_void_diameter_mm": None,
        "drawing_reference": None,
    }
    if limit is None and reference is None:
        return normalised
    normalised["max_permitted_void_diameter_mm"] = _require_positive(
        "max_permitted_void_diameter_mm", limit
    )
    normalised["drawing_reference"] = _require_label(
        "drawing_reference", reference
    )
    if normalised["max_permitted_void_diameter_mm"] > min(width, length):
        raise ValueError(
            "welding area %s permits a void of %g mm inside a zone only %g mm "
            "across; the limit cannot exceed the area it applies to"
            % (
                identifier,
                normalised["max_permitted_void_diameter_mm"],
                min(width, length),
            )
        )
    return normalised


def welding_area_mm2(area):
    """Footprint of one welding area."""
    normalised = validate_welding_area(area)
    return normalised["width_mm"] * normalised["length_mm"]


def validate_void(void):
    """Check one recorded void carries enough to yield a governing diameter."""
    if not isinstance(void, dict):
        raise ValueError("void must be a mapping, got %r" % (void,))
    kind = void.get("kind")
    if kind not in VOID_KINDS:
        raise ValueError(
            "void kind must be one of %s, got %r" % (", ".join(VOID_KINDS), kind)
        )
    normalised = {
        "kind": kind,
        "x_mm": _require_number("void x_mm", void.get("x_mm")),
        "y_mm": _require_number("void y_mm", void.get("y_mm")),
        "major_axis_mm": None,
        "minor_axis_mm": None,
        "diameter_mm": None,
        "area_mm2": None,
    }
    if void.get("major_axis_mm") is not None:
        normalised["major_axis_mm"] = _require_positive(
            "major_axis_mm", void.get("major_axis_mm")
        )
        minor = void.get("minor_axis_mm")
        if minor is None:
            raise ValueError(
                "a void recorded with a major axis must record the minor axis "
                "too; one axis alone does not describe an elongated void"
            )
        normalised["minor_axis_mm"] = _require_positive("minor_axis_mm", minor)
        if normalised["minor_axis_mm"] > normalised["major_axis_mm"]:
            raise ValueError(
                "the minor axis exceeds the major axis on a %s; the axes are "
                "the wrong way round" % kind
            )
        return normalised
    if void.get("diameter_mm") is not None:
        normalised["diameter_mm"] = _require_positive(
            "diameter_mm", void.get("diameter_mm")
        )
        return normalised
    if void.get("area_mm2") is not None:
        normalised["area_mm2"] = _require_positive("area_mm2", void.get("area_mm2"))
        return normalised
    raise ValueError(
        "a %s must record axes, a diameter or an area; none of the three is "
        "present so no diameter can be derived" % kind
    )


def governing_void_diameter_mm(void):
    """The diameter the limit is applied to, and where it came from.

    The long chord governs. An area-equivalent diameter is used only
    when the record offers nothing else, and it is reported as the
    weaker figure it is.
    """
    normalised = validate_void(void)
    if normalised["major_axis_mm"] is not None:
        return normalised["major_axis_mm"], MAJOR_AXIS
    if normalised["diameter_mm"] is not None:
        return normalised["diameter_mm"], STATED_DIAMETER
    return equivalent_diameter_mm(normalised["area_mm2"]), AREA_EQUIVALENT


def void_area_mm2(void):
    """Footprint of one void, from whichever description it carries."""
    normalised = validate_void(void)
    if normalised["area_mm2"] is not None:
        return normalised["area_mm2"]
    if normalised["major_axis_mm"] is not None:
        return ellipse_area_mm2(
            normalised["major_axis_mm"], normalised["minor_axis_mm"]
        )
    return circle_area_mm2(normalised["diameter_mm"])


def void_inside_welding_area(void, area):
    """True when any part of the void body lies in the welding area."""
    normalised = validate_void(void)
    pad = validate_welding_area(area)
    diameter, _source = governing_void_diameter_mm(void)
    radius = diameter / 2.0
    left = pad["x_mm"]
    right = pad["x_mm"] + pad["width_mm"]
    bottom = pad["y_mm"]
    top = pad["y_mm"] + pad["length_mm"]
    return (
        normalised["x_mm"] + radius > left
        and normalised["x_mm"] - radius < right
        and normalised["y_mm"] + radius > bottom
        and normalised["y_mm"] - radius < top
    )


def within_diameter_limit(diameter_mm, max_permitted_mm):
    """True when the void reaches no further than the limit; a tie passes."""
    diameter = _require_positive("diameter_mm", diameter_mm)
    limit = _require_positive("max_permitted_mm", max_permitted_mm)
    return _at_most(diameter, limit)


def categorize_void(void, area, criteria=DEFAULT_WELDING_AREA_CRITERIA):
    """Disposition one void against the limit fixed for a welding area."""
    validate_welding_area_criteria(criteria)
    normalised = validate_void(void)
    pad = validate_welding_area(area)
    if pad["max_permitted_void_diameter_mm"] is None or not pad["drawing_reference"]:
        raise ValueError(
            "welding area %s carries no drawing-fixed void diameter, so a void "
            "cannot be dispositioned against it" % pad["id"]
        )
    if not void_inside_welding_area(void, area):
        return (
            OUTSIDE_WELDING_AREA,
            "the %s lies clear of welding area %s; a bubble away from the weld "
            "zone belongs to another clause" % (normalised["kind"], pad["id"]),
        )
    diameter, source = governing_void_diameter_mm(void)
    limit = pad["max_permitted_void_diameter_mm"]
    if not within_diameter_limit(diameter, limit):
        return (
            REJECT,
            "the %s spans %.4g mm on its %s, past the %.4g mm fixed in drawing "
            "%s for welding area %s"
            % (
                normalised["kind"],
                diameter,
                source,
                limit,
                pad["drawing_reference"],
                pad["id"],
            ),
        )
    uncertainty = float(criteria["measurement_uncertainty_mm"])
    if uncertainty > 0.0 and not within_diameter_limit(
        diameter + uncertainty, limit
    ):
        return (
            REFER_FOR_REVIEW,
            "the %s spans %.4g mm against a %.4g mm limit, inside it by less "
            "than the %.4g mm the measurement is good to; the acceptance needs "
            "a better look before it is made"
            % (normalised["kind"], diameter, limit, uncertainty),
        )
    if source == AREA_EQUIVALENT:
        return (
            REFER_FOR_REVIEW,
            "the %s is described by an area alone, so its %.4g mm figure "
            "assumes a round void; an elongated void of the same area reaches "
            "further and the long chord is what the weld has to cross"
            % (normalised["kind"], diameter),
        )
    return (
        ACCEPT,
        "the %s spans %.4g mm on its %s, inside the %.4g mm fixed for welding "
        "area %s" % (normalised["kind"], diameter, source, limit, pad["id"]),
    )


def voids_in_welding_area(voids, area):
    """The recorded voids whose body reaches into one welding area."""
    if not isinstance(voids, (list, tuple)):
        raise ValueError("voids must be a sequence of void records")
    return tuple(void for void in voids if void_inside_welding_area(void, area))


def void_area_fraction(voids, area):
    """Total void footprint as a fraction of the welding area."""
    contained = voids_in_welding_area(voids, area)
    return sum(void_area_mm2(void) for void in contained) / welding_area_mm2(area)


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


def assess_welding_area(area, voids, criteria=DEFAULT_WELDING_AREA_CRITERIA):
    """Clause 7.5.1.5.2 disposition for one contact welding area."""
    validate_welding_area_criteria(criteria)
    pad = validate_welding_area(area)
    if not isinstance(voids, (list, tuple)):
        raise ValueError("voids must be a sequence of void records")

    findings = []
    advisories = []
    result = {
        "welding_area_id": pad["id"],
        "drawing_reference": pad["drawing_reference"],
        "max_permitted_void_diameter_mm": pad["max_permitted_void_diameter_mm"],
        "welding_area_mm2": pad["width_mm"] * pad["length_mm"],
        "voids_in_area": 0,
        "largest_void_diameter_mm": None,
        "void_area_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    if pad["max_permitted_void_diameter_mm"] is None or not pad["drawing_reference"]:
        findings.append(
            "welding area %s carries no drawing-fixed void diameter, so there "
            "is nothing for a void to be judged against" % pad["id"]
        )
        result["verdict"] = LIMIT_NOT_ESTABLISHED
        return result

    dispositions = []
    contained = []
    for void in voids:
        disposition, reason = categorize_void(void, area, criteria)
        if disposition == OUTSIDE_WELDING_AREA:
            advisories.append(reason)
            continue
        contained.append(void)
        dispositions.append(disposition)
        if disposition != ACCEPT:
            findings.append(reason)

    result["voids_in_area"] = len(contained)
    if contained:
        result["largest_void_diameter_mm"] = max(
            governing_void_diameter_mm(void)[0] for void in contained
        )
    fraction = void_area_fraction(voids, area)
    result["void_area_fraction"] = fraction

    if not _at_most(fraction, criteria["max_void_area_fraction"]):
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "voids cover %.1f per cent of welding area %s, past the %.1f per "
            "cent allowance; every bubble can be inside the diameter and still "
            "leave no sound metal for a nugget"
            % (
                fraction * 100.0,
                pad["id"],
                criteria["max_void_area_fraction"] * 100.0,
            )
        )
    if len(contained) > criteria["max_voids_per_welding_area"]:
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "%d voids in welding area %s, past the %d the criteria allow; a "
            "population that large is a process finding whatever each one "
            "measures"
            % (
                len(contained),
                pad["id"],
                criteria["max_voids_per_welding_area"],
            )
        )

    result["verdict"] = worst_disposition(dispositions)
    return result


def assess_bare_cell_welding_area_limits(
    case, criteria=DEFAULT_WELDING_AREA_CRITERIA
):
    """Roll the clause 7.5.1.5.2 screen up over the welding areas of one cell."""
    validate_welding_area_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    areas = case.get("welding_areas")
    if not isinstance(areas, (list, tuple)):
        raise ValueError("case must record welding_areas as a sequence")
    if not areas:
        raise ValueError(
            "a cell with no welding area declared cannot be screened against a "
            "clause about welding areas"
        )
    voids = case.get("voids", [])
    if not isinstance(voids, (list, tuple)):
        raise ValueError("case must record voids as a sequence")

    results = []
    seen = set()
    for area in areas:
        result = assess_welding_area(area, voids, criteria)
        if result["welding_area_id"] in seen:
            raise ValueError(
                "duplicate welding area id %r on the cell"
                % result["welding_area_id"]
            )
        seen.add(result["welding_area_id"])
        results.append(result)

    unestablished = tuple(
        result["welding_area_id"]
        for result in results
        if result["verdict"] == LIMIT_NOT_ESTABLISHED
    )
    if unestablished:
        verdict = LIMIT_NOT_ESTABLISHED
    else:
        verdict = worst_disposition([result["verdict"] for result in results])

    diameters = [
        result["largest_void_diameter_mm"]
        for result in results
        if result["largest_void_diameter_mm"] is not None
    ]
    return {
        "cell_id": _require_label("cell id", case.get("id", "unnamed-cell")),
        "verdict": verdict,
        "welding_areas_assessed": len(results),
        "welding_areas_without_a_limit": unestablished,
        "largest_void_diameter_mm": max(diameters) if diameters else None,
        "welding_areas_not_accepted": tuple(
            result["welding_area_id"]
            for result in results
            if result["verdict"] != ACCEPT
        ),
        "welding_area_results": tuple(results),
    }
