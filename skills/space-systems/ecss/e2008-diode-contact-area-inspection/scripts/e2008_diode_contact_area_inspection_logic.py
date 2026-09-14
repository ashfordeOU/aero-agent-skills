#!/usr/bin/env python3
"""Contact area inspection of a protection diode.

Anchor: ECSS-E-ST-20-08C clause 9.6.2.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause wants the contact areas of a protection diode free of digs,
scratches and probe marks. A protection diode has two of them, one per
polarity, and both are weld lands: the interconnect that carries the
string current is welded or bonded onto them. That is what makes this a
contact-area clause rather than a cosmetic one, and it drives three
rules that get dropped.

The first is placement. A mark has to be put against the contact
geometry before anybody dispositions it. A scratch on the diode body
away from either contact is a real finding under other clauses and it
is not this one, so rejecting the part on it here scraps a good diode
for the wrong reason. Placement is a containment test rather than a
judgement -- a mark lies inside a contact, straddles its edge, or misses
it -- and a straddling mark contributes only the part that overlaps.
Charging its whole footprint to the contact inflates every area figure
downstream of it.

The second is that the metallisation state decides the disposition and
the mark's own size does not. A dig that displaced metal and left a
continuous conductor has exposed nothing. The same dig that went
through has bared the semiconductor on the surface a weld is about to
be made on. Thinned metal is the middle case that gets waved through
because nothing is showing yet; a contact thinned past a working
fraction of its deposit is one probe landing away from bare, so it goes
to review.

The third is that the diode has two polarities and a verdict needs
both. A contact with no record is not a clean contact. A diode whose
cathode was never inspected cannot be accepted on its anode, and that
is the failure this rollup refuses to let through.

Two effects also survive a contact on which every individual mark was
admissible. Probe witnesses accumulate because the fixture lands on the
same sites, so they are counted per contact. And the weld land itself
gets used up: a contact can be fully metallised everywhere and still
have too little undisturbed surface left to put a sound weld on, so the
clear fraction is tracked rather than the defect count.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIG = "dig"
SCRATCH = "scratch"
PROBE_MARK = "probe-mark"
MARK_KINDS = (DIG, SCRATCH, PROBE_MARK)

INTACT = "intact"
THINNED = "thinned"
ABSENT = "absent"
METALLISATION_STATES = (INTACT, THINNED, ABSENT)

ANODE = "anode"
CATHODE = "cathode"
CONTACT_POLARITIES = (ANODE, CATHODE)

INSIDE = "inside"
STRADDLING = "straddling"
OUTSIDE = "outside"
PLACEMENTS = (INSIDE, STRADDLING, OUTSIDE)

OFF_CONTACT = "off-contact"
ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
NOT_ESTABLISHED = "not-established"
REJECT = "reject"
DISPOSITIONS = (OFF_CONTACT, ACCEPT, REFER_FOR_REVIEW, NOT_ESTABLISHED, REJECT)

_SEVERITY_ORDER = {
    OFF_CONTACT: 0,
    ACCEPT: 1,
    REFER_FOR_REVIEW: 2,
    NOT_ESTABLISHED: 3,
    REJECT: 4,
}

DEFAULT_DIODE_CONTACT_CRITERIA = {
    "min_remaining_metallisation_fraction": 0.5,
    "min_clear_weld_land_fraction": 0.9,
    "max_probe_witnesses_per_contact": 2,
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
        raise ValueError("%s must fall in the interval (0, 1], got %r" % (name, value))
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


def validate_diode_contact_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_fraction(
        "min_remaining_metallisation_fraction",
        criteria.get("min_remaining_metallisation_fraction"),
    )
    _require_fraction(
        "min_clear_weld_land_fraction",
        criteria.get("min_clear_weld_land_fraction"),
    )
    _require_count(
        "max_probe_witnesses_per_contact",
        criteria.get("max_probe_witnesses_per_contact"),
    )
    return criteria


def validate_diode_contact(contact):
    """Normalise one polarity contact footprint in the diode frame."""
    if not isinstance(contact, dict):
        raise ValueError("diode contact must be a mapping, got %r" % (contact,))
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
        "x_mm": _require_number("contact x_mm", contact.get("x_mm")),
        "y_mm": _require_number("contact y_mm", contact.get("y_mm")),
        "width_mm": _require_positive("contact width_mm", contact.get("width_mm")),
        "length_mm": _require_positive("contact length_mm", contact.get("length_mm")),
    }


def diode_contact_mm2(contact):
    """Weld-land footprint of one polarity contact."""
    normalised = validate_diode_contact(contact)
    return normalised["width_mm"] * normalised["length_mm"]


def validate_contact_mark(mark):
    """Check one recorded mark carries the fields its disposition needs."""
    if not isinstance(mark, dict):
        raise ValueError("mark must be a mapping, got %r" % (mark,))
    kind = mark.get("kind")
    if kind not in MARK_KINDS:
        raise ValueError(
            "mark kind must be one of %s, got %r" % (", ".join(MARK_KINDS), kind)
        )
    state = mark.get("metallisation")
    if state not in METALLISATION_STATES:
        raise ValueError(
            "metallisation must be one of %s, got %r"
            % (", ".join(METALLISATION_STATES), state)
        )
    normalised = {
        "kind": kind,
        "metallisation": state,
        "x_mm": _require_number("mark x_mm", mark.get("x_mm")),
        "y_mm": _require_number("mark y_mm", mark.get("y_mm")),
        "width_mm": _require_positive("mark width_mm", mark.get("width_mm")),
        "length_mm": _require_positive("mark length_mm", mark.get("length_mm")),
        "remaining_metallisation_fraction": None,
    }
    if state == THINNED:
        if "remaining_metallisation_fraction" not in mark:
            raise ValueError(
                "a thinned mark must record remaining_metallisation_fraction; "
                "without it the disposition has nothing to compare"
            )
        normalised["remaining_metallisation_fraction"] = _require_fraction(
            "remaining_metallisation_fraction",
            mark.get("remaining_metallisation_fraction"),
        )
    return normalised


def mark_footprint_mm2(mark):
    """Footprint of one mark, independent of where it sits."""
    normalised = validate_contact_mark(mark)
    return normalised["width_mm"] * normalised["length_mm"]


def overlap_mm2(mark, contact):
    """Footprint the mark and the polarity contact have in common."""
    defect = validate_contact_mark(mark)
    land = validate_diode_contact(contact)
    left = max(defect["x_mm"], land["x_mm"])
    right = min(defect["x_mm"] + defect["width_mm"], land["x_mm"] + land["width_mm"])
    bottom = max(defect["y_mm"], land["y_mm"])
    top = min(defect["y_mm"] + defect["length_mm"], land["y_mm"] + land["length_mm"])
    if right <= left or top <= bottom:
        return 0.0
    return (right - left) * (top - bottom)


def mark_placement(mark, contact):
    """Whether a mark sits inside a contact, straddles its edge, or misses it."""
    defect = validate_contact_mark(mark)
    overlap = overlap_mm2(mark, contact)
    if overlap <= 0.0:
        return OUTSIDE
    footprint = defect["width_mm"] * defect["length_mm"]
    if math.isclose(overlap, footprint, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return INSIDE
    return STRADDLING


def categorize_contact_mark(
    mark, contact, criteria=DEFAULT_DIODE_CONTACT_CRITERIA
):
    """Disposition one mark against one polarity contact."""
    validate_diode_contact_criteria(criteria)
    defect = validate_contact_mark(mark)
    land = validate_diode_contact(contact)
    if mark_placement(mark, contact) == OUTSIDE:
        return (
            OFF_CONTACT,
            "the %s misses the %s contact entirely; a mark on the diode body "
            "away from a weld land belongs to another clause"
            % (defect["kind"], land["polarity"]),
        )
    overlap = overlap_mm2(mark, contact)
    if defect["metallisation"] == ABSENT:
        return (
            REJECT,
            "the %s has bared the semiconductor over %.4g mm2 of the %s weld "
            "land, which is where the interconnect is about to be welded"
            % (defect["kind"], overlap, land["polarity"]),
        )
    if defect["metallisation"] == THINNED:
        remaining = defect["remaining_metallisation_fraction"]
        if not _at_least(
            remaining, criteria["min_remaining_metallisation_fraction"]
        ):
            return (
                REFER_FOR_REVIEW,
                "the %s leaves %.0f per cent of the deposit on the %s contact, "
                "under the %.0f per cent working fraction; nothing is showing "
                "through yet and one probe landing would change that"
                % (
                    defect["kind"],
                    remaining * 100.0,
                    land["polarity"],
                    criteria["min_remaining_metallisation_fraction"] * 100.0,
                ),
            )
        return (
            ACCEPT,
            "the %s has thinned the %s contact to %.0f per cent of the deposit "
            "and left a sound conductor behind"
            % (defect["kind"], land["polarity"], remaining * 100.0),
        )
    return (
        ACCEPT,
        "the %s has displaced metal on the %s contact without breaking the "
        "conductor" % (defect["kind"], land["polarity"]),
    )


def disturbed_mm2(marks, contact):
    """Weld-land footprint worked by marks of any kind.

    Overlapping marks are summed rather than unioned: the figure measures
    how much working the surface has taken, and a site worked twice has
    taken twice the working.
    """
    if not isinstance(marks, (list, tuple)):
        raise ValueError("marks must be a sequence of mark records")
    return sum(overlap_mm2(mark, contact) for mark in marks)


def bared_mm2(marks, contact):
    """Weld-land footprint over which the metallisation is gone."""
    if not isinstance(marks, (list, tuple)):
        raise ValueError("marks must be a sequence of mark records")
    total = 0.0
    for mark in marks:
        if validate_contact_mark(mark)["metallisation"] == ABSENT:
            total += overlap_mm2(mark, contact)
    return total


def clear_weld_land_fraction(marks, contact):
    """Share of the contact left undisturbed, floored at zero.

    A contact can be fully metallised everywhere and still have too
    little untouched surface left to put a sound weld on.
    """
    worked = disturbed_mm2(marks, contact) / diode_contact_mm2(contact)
    return max(0.0, 1.0 - worked)


def probe_witness_count(marks, contact):
    """Probe marks landing on one polarity contact."""
    if not isinstance(marks, (list, tuple)):
        raise ValueError("marks must be a sequence of mark records")
    count = 0
    for mark in marks:
        if (
            validate_contact_mark(mark)["kind"] == PROBE_MARK
            and mark_placement(mark, contact) != OUTSIDE
        ):
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


def assess_diode_contact(contact, marks, criteria=DEFAULT_DIODE_CONTACT_CRITERIA):
    """Clause 9.6.2.5.1 disposition for one polarity contact."""
    validate_diode_contact_criteria(criteria)
    land = validate_diode_contact(contact)
    if not isinstance(marks, (list, tuple)):
        raise ValueError("marks must be a sequence of mark records")

    findings = []
    advisories = []
    dispositions = []
    on_contact = 0
    for mark in marks:
        disposition, reason = categorize_contact_mark(mark, contact, criteria)
        if disposition == OFF_CONTACT:
            advisories.append(reason)
            continue
        on_contact += 1
        dispositions.append(disposition)
        if disposition != ACCEPT:
            findings.append(reason)

    footprint = diode_contact_mm2(contact)
    bared = bared_mm2(marks, contact)
    clear = clear_weld_land_fraction(marks, contact)
    witnesses = probe_witness_count(marks, contact)

    if not _at_least(clear, criteria["min_clear_weld_land_fraction"]):
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "only %.1f per cent of the %s weld land is undisturbed, under the "
            "%.1f per cent the criteria want; the metallisation can be sound "
            "everywhere and the weldable surface still be used up"
            % (
                clear * 100.0,
                land["polarity"],
                criteria["min_clear_weld_land_fraction"] * 100.0,
            )
        )
    if witnesses > criteria["max_probe_witnesses_per_contact"]:
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "%d probe witnesses on the %s contact, past the %d the criteria "
            "allow; the fixture lands on the same site and eventually one goes "
            "through"
            % (witnesses, land["polarity"], criteria["max_probe_witnesses_per_contact"])
        )

    return {
        "contact_id": land["id"],
        "polarity": land["polarity"],
        "verdict": worst_disposition(dispositions),
        "contact_mm2": footprint,
        "marks_on_contact": on_contact,
        "bared_mm2": bared,
        "bared_fraction": bared / footprint,
        "clear_weld_land_fraction": clear,
        "probe_witnesses": witnesses,
        "findings": findings,
        "advisories": advisories,
    }


def assess_protection_diode_contacts(
    case, criteria=DEFAULT_DIODE_CONTACT_CRITERIA
):
    """Roll the clause 9.6.2.5.1 screen up over both polarities of one diode."""
    validate_diode_contact_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    contacts = case.get("contacts")
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("case must record contacts as a sequence")
    if not contacts:
        raise ValueError(
            "a diode with no contact declared cannot be screened against a "
            "clause about contact areas"
        )
    marks = case.get("marks", [])
    if not isinstance(marks, (list, tuple)):
        raise ValueError("case must record marks as a sequence")

    results = []
    seen = set()
    for contact in contacts:
        result = assess_diode_contact(contact, marks, criteria)
        if result["contact_id"] in seen:
            raise ValueError("duplicate contact id %r on the diode" % result["contact_id"])
        seen.add(result["contact_id"])
        results.append(result)

    inspected = {result["polarity"] for result in results}
    uninspected = tuple(p for p in CONTACT_POLARITIES if p not in inspected)

    findings = []
    dispositions = [result["verdict"] for result in results]
    if uninspected:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "no record for the %s contact; a contact nobody looked at is not a "
            "clean contact, and the diode cannot be accepted on the other "
            "polarity alone" % " and ".join(uninspected)
        )

    unplaced = []
    for mark in marks:
        if all(mark_placement(mark, contact) == OUTSIDE for contact in contacts):
            unplaced.append(validate_contact_mark(mark)["kind"])

    return {
        "diode_id": _require_label("diode id", case.get("id", "unnamed-diode")),
        "verdict": worst_disposition(dispositions),
        "contacts_assessed": len(results),
        "polarities_without_a_record": uninspected,
        "total_bared_mm2": sum(result["bared_mm2"] for result in results),
        "contacts_not_accepted": tuple(
            result["contact_id"] for result in results if result["verdict"] != ACCEPT
        ),
        "marks_off_every_contact": tuple(unplaced),
        "rollup_findings": findings,
        "contact_results": tuple(results),
    }
