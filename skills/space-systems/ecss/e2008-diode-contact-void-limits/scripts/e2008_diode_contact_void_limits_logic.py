#!/usr/bin/env python3
"""Void and bubble limits on the contacts of a protection diode.

Anchor: ECSS-E-ST-20-08C clause 9.6.2.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause puts a diameter ceiling of a quarter of a millimetre on the
voids and bubbles found on the contacts of a protection diode, and it
puts it on either polarity. Three things about that sentence decide
whether an implementation of it is honest.

The first is what diameter means for something that is not round. A
void is recorded as a major and a minor extent, and there are two
diameters that can be computed from them. The area-equivalent diameter
is the one a spreadsheet reaches for, and it is the wrong one: an
elongated bubble half a millimetre long and a tenth wide returns an
equivalent diameter of a fifth of a millimetre and passes, while the
defect itself runs twice the ceiling along the direction the weld has
to bridge. The governing figure is the maximum extent. The equivalent
diameter is still worth computing, because the gap between the two is
how you find the elongated ones.

The second is that voids do not stay separate. Two bubbles whose edges
have closed to within a coalescence gap behave as one cavity under a
weld pulse, and the span across the pair is what the ceiling has to be
applied to. Sentencing each one alone lets a pair that is plainly over
the ceiling through as two passes. Coalescence is per polarity: a void
on the anode does not merge with one on the cathode, whatever the
coordinates say.

The third is that either polarity means both of them have a record. A
contact nobody surveyed is not a contact with no voids, and a diode
accepted on its anode survey while the cathode was never looked at has
not been shown to meet anything.

A void exactly on the ceiling is inside it, not over it. The ceiling is
a limit the void must stay within, so the comparison has to absorb the
representation error a computed span carries rather than rejecting a
part on a difference in the last place of a float.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VOID = "void"
BUBBLE = "bubble"
CAVITY_KINDS = (VOID, BUBBLE)

ANODE = "anode"
CATHODE = "cathode"
CONTACT_POLARITIES = (ANODE, CATHODE)

ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
NOT_ESTABLISHED = "not-established"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REFER_FOR_REVIEW, NOT_ESTABLISHED, REJECT)

_SEVERITY_ORDER = {
    ACCEPT: 0,
    REFER_FOR_REVIEW: 1,
    NOT_ESTABLISHED: 2,
    REJECT: 3,
}

DEFAULT_VOID_CRITERIA = {
    "max_void_extent_mm": 0.25,
    "coalescence_gap_mm": 0.05,
    "review_extent_fraction": 0.8,
    "max_voided_area_fraction": 0.10,
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
        raise ValueError("%s must fall in the interval (0, 1], got %r" % (name, value))
    return number


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


def validate_void_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive("max_void_extent_mm", criteria.get("max_void_extent_mm"))
    _require_non_negative("coalescence_gap_mm", criteria.get("coalescence_gap_mm"))
    _require_fraction(
        "review_extent_fraction", criteria.get("review_extent_fraction")
    )
    _require_fraction(
        "max_voided_area_fraction", criteria.get("max_voided_area_fraction")
    )
    return criteria


def validate_void_contact(contact):
    """Normalise one polarity contact the survey was made on."""
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping, got %r" % (contact,))
    identifier = _require_label("contact id", contact.get("id"))
    if not identifier:
        raise ValueError("contact id must not be blank")
    polarity = contact.get("polarity")
    if polarity not in CONTACT_POLARITIES:
        raise ValueError(
            "contact polarity must be one of %s, got %r"
            % (", ".join(CONTACT_POLARITIES), polarity)
        )
    return {
        "id": identifier,
        "polarity": polarity,
        "area_mm2": _require_positive("contact area_mm2", contact.get("area_mm2")),
    }


def validate_void(cavity):
    """Normalise one recorded void or bubble."""
    if not isinstance(cavity, dict):
        raise ValueError("void must be a mapping, got %r" % (cavity,))
    kind = cavity.get("kind")
    if kind not in CAVITY_KINDS:
        raise ValueError(
            "void kind must be one of %s, got %r" % (", ".join(CAVITY_KINDS), kind)
        )
    polarity = cavity.get("polarity")
    if polarity not in CONTACT_POLARITIES:
        raise ValueError(
            "void polarity must be one of %s, got %r"
            % (", ".join(CONTACT_POLARITIES), polarity)
        )
    major = _require_positive("void major_mm", cavity.get("major_mm"))
    minor = _require_positive("void minor_mm", cavity.get("minor_mm"))
    if minor > major and not math.isclose(
        minor, major, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "void minor_mm must not exceed major_mm; the major extent is the "
            "longest one measured, got %r against %r" % (minor, major)
        )
    identifier = _require_label("void id", cavity.get("id", "unnamed-void"))
    if not identifier:
        raise ValueError("void id must not be blank")
    return {
        "id": identifier,
        "kind": kind,
        "polarity": polarity,
        "x_mm": _require_number("void x_mm", cavity.get("x_mm")),
        "y_mm": _require_number("void y_mm", cavity.get("y_mm")),
        "major_mm": major,
        "minor_mm": minor,
    }


def void_max_extent_mm(cavity):
    """Governing extent: the longest dimension measured across the cavity."""
    return validate_void(cavity)["major_mm"]


def void_equivalent_diameter_mm(cavity):
    """Diameter of a circle of the same area.

    Reported, never compared against the ceiling: an elongated bubble
    passes on this figure while running well past the ceiling along the
    direction the weld has to bridge.
    """
    normalised = validate_void(cavity)
    return math.sqrt(normalised["major_mm"] * normalised["minor_mm"])


def void_area_mm2(cavity):
    """Area of the cavity taken as an ellipse of the measured extents."""
    normalised = validate_void(cavity)
    return math.pi / 4.0 * normalised["major_mm"] * normalised["minor_mm"]


def void_elongation(cavity):
    """Major over minor; how far the cavity is from round."""
    normalised = validate_void(cavity)
    return normalised["major_mm"] / normalised["minor_mm"]


def centre_separation_mm(first, second):
    """Distance between the centres of two recorded cavities."""
    left = validate_void(first)
    right = validate_void(second)
    return math.hypot(left["x_mm"] - right["x_mm"], left["y_mm"] - right["y_mm"])


def voids_coalesce(first, second, criteria=DEFAULT_VOID_CRITERIA):
    """Whether two cavities have closed to within the coalescence gap.

    Cavities on opposite polarities never merge, whatever the
    coordinates say.
    """
    validate_void_criteria(criteria)
    left = validate_void(first)
    right = validate_void(second)
    if left["polarity"] != right["polarity"]:
        return False
    reach = (left["major_mm"] + right["major_mm"]) / 2.0 + criteria[
        "coalescence_gap_mm"
    ]
    return _at_most(centre_separation_mm(first, second), reach)


def coalesced_groups(cavities, criteria=DEFAULT_VOID_CRITERIA):
    """Group cavities that have closed on one another into single findings."""
    validate_void_criteria(criteria)
    if not isinstance(cavities, (list, tuple)):
        raise ValueError("voids must be a sequence of cavity records")
    for cavity in cavities:
        validate_void(cavity)
    remaining = list(range(len(cavities)))
    groups = []
    while remaining:
        seed = remaining.pop(0)
        group = [seed]
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            joined = [
                index
                for index in remaining
                if voids_coalesce(cavities[current], cavities[index], criteria)
            ]
            for index in joined:
                remaining.remove(index)
                group.append(index)
                frontier.append(index)
        groups.append(tuple(cavities[index] for index in sorted(group)))
    return tuple(groups)


def group_extent_mm(group, criteria=DEFAULT_VOID_CRITERIA):
    """Span the ceiling has to be applied to across a coalesced group."""
    validate_void_criteria(criteria)
    if not isinstance(group, (list, tuple)) or not group:
        raise ValueError("a group must be a non-empty sequence of cavity records")
    normalised = [validate_void(cavity) for cavity in group]
    widest = max(cavity["major_mm"] for cavity in normalised)
    span = widest
    for index, left in enumerate(normalised):
        for right in normalised[index + 1:]:
            reach = (
                math.hypot(left["x_mm"] - right["x_mm"], left["y_mm"] - right["y_mm"])
                + left["major_mm"] / 2.0
                + right["major_mm"] / 2.0
            )
            if reach > span:
                span = reach
    return span


def categorize_void_group(group, criteria=DEFAULT_VOID_CRITERIA):
    """Disposition one cavity or one coalesced group of them."""
    validate_void_criteria(criteria)
    span = group_extent_mm(group, criteria)
    ceiling = criteria["max_void_extent_mm"]
    names = ", ".join(validate_void(cavity)["id"] for cavity in group)
    if not _at_most(span, ceiling):
        if len(group) > 1:
            return (
                REJECT,
                "%s have closed on one another and span %.4g mm together, past "
                "the %.4g mm ceiling; each one alone would have passed"
                % (names, span, ceiling),
            )
        return (
            REJECT,
            "%s runs %.4g mm across, past the %.4g mm ceiling"
            % (names, span, ceiling),
        )
    if _at_least(span, criteria["review_extent_fraction"] * ceiling):
        return (
            REFER_FOR_REVIEW,
            "%s spans %.4g mm, inside the %.4g mm ceiling but above the review "
            "band; the next survey is where it goes over"
            % (names, span, ceiling),
        )
    return (ACCEPT, "%s spans %.4g mm, well inside the ceiling" % (names, span))


def voided_area_mm2(cavities):
    """Total cavity area on a contact."""
    if not isinstance(cavities, (list, tuple)):
        raise ValueError("voids must be a sequence of cavity records")
    return sum(void_area_mm2(cavity) for cavity in cavities)


def voided_area_fraction(cavities, contact):
    """Share of a polarity contact given over to cavities."""
    return voided_area_mm2(cavities) / validate_void_contact(contact)["area_mm2"]


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


def assess_contact_voids(contact, cavities, criteria=DEFAULT_VOID_CRITERIA):
    """Clause 9.6.2.5.2 disposition for one polarity contact."""
    validate_void_criteria(criteria)
    land = validate_void_contact(contact)
    if not isinstance(cavities, (list, tuple)):
        raise ValueError("voids must be a sequence of cavity records")
    mine = [
        cavity
        for cavity in cavities
        if validate_void(cavity)["polarity"] == land["polarity"]
    ]

    findings = []
    dispositions = []
    groups = coalesced_groups(mine, criteria)
    for group in groups:
        disposition, reason = categorize_void_group(group, criteria)
        dispositions.append(disposition)
        if disposition != ACCEPT:
            findings.append(reason)

    fraction = voided_area_fraction(mine, contact) if mine else 0.0
    if not _at_most(fraction, criteria["max_voided_area_fraction"]):
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "cavities take %.2f per cent of the %s contact, past the %.2f per "
            "cent the criteria allow; every one of them can be inside the "
            "ceiling and the land still be mostly cavity"
            % (
                fraction * 100.0,
                land["polarity"],
                criteria["max_voided_area_fraction"] * 100.0,
            )
        )

    elongated = tuple(
        validate_void(cavity)["id"]
        for cavity in mine
        if not _at_most(void_max_extent_mm(cavity), criteria["max_void_extent_mm"])
        and _at_most(
            void_equivalent_diameter_mm(cavity), criteria["max_void_extent_mm"]
        )
    )

    return {
        "contact_id": land["id"],
        "polarity": land["polarity"],
        "verdict": worst_disposition(dispositions),
        "contact_area_mm2": land["area_mm2"],
        "cavities_surveyed": len(mine),
        "groups_formed": len(groups),
        "largest_extent_mm": (
            max(group_extent_mm(group, criteria) for group in groups)
            if groups
            else 0.0
        ),
        "voided_area_mm2": voided_area_mm2(mine),
        "voided_area_fraction": fraction,
        "cavities_an_equivalent_diameter_would_have_passed": elongated,
        "findings": findings,
    }


def assess_diode_contact_voids(case, criteria=DEFAULT_VOID_CRITERIA):
    """Roll the clause 9.6.2.5.2 screen up over both polarities of one diode."""
    validate_void_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    contacts = case.get("contacts")
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("case must record contacts as a sequence")
    if not contacts:
        raise ValueError(
            "a diode with no contact declared cannot be screened against a "
            "clause about contact voids"
        )
    cavities = case.get("voids", [])
    if not isinstance(cavities, (list, tuple)):
        raise ValueError("case must record voids as a sequence")

    results = []
    seen = set()
    for contact in contacts:
        result = assess_contact_voids(contact, cavities, criteria)
        if result["contact_id"] in seen:
            raise ValueError("duplicate contact id %r on the diode" % result["contact_id"])
        seen.add(result["contact_id"])
        results.append(result)

    surveyed = {result["polarity"] for result in results}
    unsurveyed = tuple(p for p in CONTACT_POLARITIES if p not in surveyed)

    findings = []
    dispositions = [result["verdict"] for result in results]
    if unsurveyed:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "no void survey for the %s contact; the clause covers either "
            "polarity, and a contact nobody surveyed is not a contact without "
            "cavities" % " and ".join(unsurveyed)
        )

    orphaned = tuple(
        validate_void(cavity)["id"]
        for cavity in cavities
        if validate_void(cavity)["polarity"] not in surveyed
    )
    if orphaned:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "cavities %s are recorded against a polarity the diode does not "
            "declare, so they were never sentenced" % ", ".join(orphaned)
        )

    return {
        "diode_id": _require_label("diode id", case.get("id", "unnamed-diode")),
        "verdict": worst_disposition(dispositions),
        "contacts_assessed": len(results),
        "polarities_without_a_survey": unsurveyed,
        "cavities_on_an_undeclared_polarity": orphaned,
        "largest_extent_mm": (
            max(result["largest_extent_mm"] for result in results) if results else 0.0
        ),
        "contacts_not_accepted": tuple(
            result["contact_id"] for result in results if result["verdict"] != ACCEPT
        ),
        "rollup_findings": findings,
        "contact_results": tuple(results),
    }
