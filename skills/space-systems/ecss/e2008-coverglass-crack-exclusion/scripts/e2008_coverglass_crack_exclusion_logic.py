#!/usr/bin/env python3
"""Crack exclusion for a delivered solar cell coverglass.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Every other coverglass defect clause is a dimension with an allowance
against it. This one has no allowance. Cracking on the surface, along an
edge or at a corner is not permitted on a delivered coverglass at all, so
there is no length below which a crack becomes acceptable and no zone in
which one is tolerated.

That changes what the screen has to do. A clause with a limit is answered
by measuring; a clause with no limit is answered by categorizing, and then
by proving the look was good enough for an empty result to mean anything.
So this leaf does three things.

It sorts every recorded indication into a crack family, a non-crack family
or neither. A crack-family indication rejects the glass wherever it sits
and whatever it measures. A non-crack indication is not this clause's work
and is routed to the clause that does bound it, rather than being absorbed
here. An indication whose kind is not recognised is neither: it is referred
for re-examination, because an unrecognised mark is an open question and an
open question is not an absence.

Then it grades the inspection itself. A record that covered two of the
three zones cannot certify the third. A record taken below the declared
magnification, or under too little light, is not evidence that nothing was
there; it is evidence that nothing was seen. An empty finding list on such
a record is inconclusive, not a pass, and that is the distinction this
screen exists to hold.

A crack found under a poor inspection is still a crack. Weak evidence never
softens a rejection; it only blocks an acceptance.

Dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ZONE_SURFACE = "coverglass-surface"
ZONE_EDGE = "coverglass-edge"
ZONE_CORNER = "coverglass-corner"
COVERGLASS_ZONES = (ZONE_SURFACE, ZONE_EDGE, ZONE_CORNER)

FAMILY_CRACK = "crack-family"
FAMILY_OTHER = "non-crack-family"
FAMILY_UNRESOLVED = "unresolved-family"

CRACK_KINDS = frozenset(
    {
        "crack",
        "hairline-crack",
        "star-crack",
        "edge-crack",
        "corner-crack",
        "fracture",
        "fissure",
        "check",
        "split",
        "craze",
    }
)

NON_CRACK_KINDS = frozenset(
    {
        "chip",
        "nick",
        "scratch",
        "dig",
        "inclusion",
        "bubble",
        "stain",
        "coating-blemish",
        "handling-mark",
    }
)

CHIP_CLAUSE_ROUTE = "coverglass-chip-clauses"
SURFACE_QUALITY_ROUTE = "coverglass-surface-quality-clauses"
ADHESIVE_ROUTE = "coverglass-adhesive-clauses"

_ROUTE_BY_KIND = {
    "chip": CHIP_CLAUSE_ROUTE,
    "nick": CHIP_CLAUSE_ROUTE,
    "scratch": SURFACE_QUALITY_ROUTE,
    "dig": SURFACE_QUALITY_ROUTE,
    "inclusion": SURFACE_QUALITY_ROUTE,
    "bubble": ADHESIVE_ROUTE,
    "stain": ADHESIVE_ROUTE,
    "coating-blemish": SURFACE_QUALITY_ROUTE,
    "handling-mark": SURFACE_QUALITY_ROUTE,
}

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
CRACK_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

GLASS_CRACK_FREE = "coverglass-free-of-cracking"
GLASS_INCONCLUSIVE = "coverglass-crack-screen-inconclusive"
GLASS_CRACKED = "coverglass-cracked"

_ROLLUP_BY_SEVERITY = {
    ACCEPT: GLASS_CRACK_FREE,
    REFER: GLASS_INCONCLUSIVE,
    REJECT: GLASS_CRACKED,
}

DEFAULT_CRACK_CRITERIA = {
    # the clause has no size allowance, so the criteria bound the LOOK
    "required_zones": COVERGLASS_ZONES,
    "min_magnification_x": 10.0,
    "min_illumination_lux": 500.0,
    "max_unresolved_indications": 0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, floor):
    """value >= floor, absorbing floating-point representation error.

    A magnification or an illumination reading entered as a decimal can
    evaluate a few units in the last place below the figure it was meant
    to be. The floor is never lowered; only the comparison tolerates the
    representation error.
    """
    return value >= floor or math.isclose(
        value, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def normalize_kind(kind):
    """Reduce a recorded indication kind to its comparable form."""
    text = _require_text("kind", kind)
    return text.lower().replace("_", "-").replace(" ", "-")


def categorize_indication(kind):
    """Sort one indication kind into a crack, non-crack or open family.

    An unrecognised kind is deliberately not forced into the non-crack
    family. The clause tolerates no cracking, so the safe default for a
    mark nobody has named is a question, not an acceptance.
    """
    normalized = normalize_kind(kind)
    if normalized in CRACK_KINDS:
        return FAMILY_CRACK
    if normalized in NON_CRACK_KINDS:
        return FAMILY_OTHER
    return FAMILY_UNRESOLVED


def is_crack_family(kind):
    """True when this kind of indication is cracking by any of its names."""
    return categorize_indication(kind) == FAMILY_CRACK


def route_for_kind(kind):
    """The clause a non-crack indication belongs to, or None."""
    return _ROUTE_BY_KIND.get(normalize_kind(kind))


def validate_crack_criteria(criteria):
    """Check the inspection adequacy criteria are complete and consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    zones = criteria.get("required_zones")
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError(
            "criteria required_zones must be a non-empty sequence, got %r"
            % (zones,)
        )
    for zone in zones:
        if zone not in COVERGLASS_ZONES:
            raise ValueError(
                "criteria required_zones names %r, which is not one of %s"
                % (zone, ", ".join(COVERGLASS_ZONES))
            )
    if len(set(zones)) != len(zones):
        raise ValueError("criteria required_zones repeats a zone: %r" % (zones,))
    _require_positive(
        "criteria min_magnification_x", criteria.get("min_magnification_x")
    )
    _require_positive(
        "criteria min_illumination_lux", criteria.get("min_illumination_lux")
    )
    _require_count(
        "criteria max_unresolved_indications",
        criteria.get("max_unresolved_indications"),
    )
    return criteria


def validate_inspection_record(record):
    """Check one coverglass inspection record before anything is read from it."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    glass_id = _require_text("coverglass_id", record.get("coverglass_id"))
    inspector = _require_text("inspector", record.get("inspector"))
    magnification = _require_positive(
        "magnification_x", record.get("magnification_x")
    )
    illumination = _require_non_negative(
        "illumination_lux", record.get("illumination_lux")
    )
    zones = record.get("zones_inspected")
    if not isinstance(zones, (list, tuple)):
        raise ValueError("zones_inspected must be a list, got %r" % (zones,))
    for zone in zones:
        if zone not in COVERGLASS_ZONES:
            raise ValueError(
                "zones_inspected names %r, which is not one of %s"
                % (zone, ", ".join(COVERGLASS_ZONES))
            )
    if len(set(zones)) != len(zones):
        raise ValueError("zones_inspected repeats a zone: %r" % (zones,))
    indications = record.get("indications", [])
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))
    return {
        "coverglass_id": glass_id,
        "inspector": inspector,
        "magnification_x": magnification,
        "illumination_lux": illumination,
        "zones_inspected": tuple(zones),
        "indication_count": len(indications),
    }


def evidence_coverage(record, criteria=DEFAULT_CRACK_CRITERIA):
    """Decide whether this record can support a statement of absence.

    A zero-tolerance clause is only satisfied by positive evidence that
    the look was complete and good enough. Missing zones, thin
    magnification and poor light are each enough on their own to make an
    empty finding list inconclusive rather than clean.
    """
    validate_crack_criteria(criteria)
    resolved = validate_inspection_record(record)
    covered = set(resolved["zones_inspected"])
    required = set(criteria["required_zones"])
    missing = sorted(required - covered)
    magnification_ok = _at_least(
        resolved["magnification_x"], criteria["min_magnification_x"]
    )
    illumination_ok = _at_least(
        resolved["illumination_lux"], criteria["min_illumination_lux"]
    )
    gaps = []
    if missing:
        gaps.append(
            "no examination is recorded for %s, so nothing can be stated about "
            "cracking there" % (", ".join(missing),)
        )
    if not magnification_ok:
        gaps.append(
            "examined at %.1fx against a %.1fx minimum; a hairline crack is not "
            "resolved at that magnification"
            % (resolved["magnification_x"], criteria["min_magnification_x"])
        )
    if not illumination_ok:
        gaps.append(
            "examined under %.0f lux against a %.0f lux minimum; the light was "
            "not enough to call the surface clean"
            % (resolved["illumination_lux"], criteria["min_illumination_lux"])
        )
    return {
        "coverglass_id": resolved["coverglass_id"],
        "zones_covered": sorted(covered),
        "zones_missing": missing,
        "magnification_x": resolved["magnification_x"],
        "magnification_sufficient": magnification_ok,
        "illumination_lux": resolved["illumination_lux"],
        "illumination_sufficient": illumination_ok,
        "sufficient": not gaps,
        "gaps": gaps,
    }


def assess_indication(indication, criteria=DEFAULT_CRACK_CRITERIA):
    """Disposition one recorded indication under the crack exclusion.

    Length is recorded for the nonconformance paperwork and plays no part
    in the disposition. There is no length at which cracking becomes
    acceptable, so a hairline and a run across the whole face come out of
    this screen with the same answer.
    """
    validate_crack_criteria(criteria)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    kind = normalize_kind(indication.get("kind"))
    zone = indication.get("zone")
    if zone not in COVERGLASS_ZONES:
        raise ValueError(
            "indication zone must be one of %s, got %r"
            % (", ".join(COVERGLASS_ZONES), zone)
        )
    length = indication.get("length_mm")
    if length is not None:
        length = _require_positive("length_mm", length)
    family = categorize_indication(kind)

    if family == FAMILY_CRACK:
        disposition = REJECT
        reason = (
            "cracking of type %s on the %s; the clause allows none anywhere on "
            "a delivered coverglass, at any length" % (kind, zone)
        )
        routed_to = None
    elif family == FAMILY_UNRESOLVED:
        disposition = REFER
        reason = (
            "an indication recorded as %s on the %s has not been resolved into "
            "cracking or not; re-examine it before the glass is dispositioned"
            % (kind, zone)
        )
        routed_to = None
    else:
        disposition = ACCEPT
        reason = None
        routed_to = route_for_kind(kind)

    return {
        "id": indication.get("id"),
        "kind": kind,
        "zone": zone,
        "family": family,
        "length_mm": length,
        "graded_on_length": False,
        "routed_to": routed_to,
        "disposition": disposition,
        "reasons": [reason] if reason else [],
    }


def assess_coverglass_crack_exclusion(record, criteria=DEFAULT_CRACK_CRITERIA):
    """Clause 8.7.1.3.6 screen of one coverglass inspection record."""
    validate_crack_criteria(criteria)
    resolved = validate_inspection_record(record)
    coverage = evidence_coverage(record, criteria)
    glass_id = resolved["coverglass_id"]
    indications = record.get("indications", [])

    seen = set()
    assessed = []
    for indication in indications:
        result = assess_indication(indication, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate indication id %r on coverglass %s"
                    % (marker, glass_id)
                )
            seen.add(marker)
        if result["zone"] not in resolved["zones_inspected"]:
            raise ValueError(
                "indication %r sits on the %s, which the record says was not "
                "inspected on coverglass %s" % (marker, result["zone"], glass_id)
            )
        assessed.append(result)

    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])

    by_family = {FAMILY_CRACK: 0, FAMILY_OTHER: 0, FAMILY_UNRESOLVED: 0}
    by_zone = {}
    for result in assessed:
        by_family[result["family"]] += 1
        if result["family"] == FAMILY_CRACK:
            by_zone[result["zone"]] = by_zone.get(result["zone"], 0) + 1

    if by_family[FAMILY_UNRESOLVED] > criteria["max_unresolved_indications"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d indications are still unresolved, past the %d this clause "
            "leaves open"
            % (
                by_family[FAMILY_UNRESOLVED],
                criteria["max_unresolved_indications"],
            )
        )

    if not coverage["sufficient"]:
        verdict = _worst((verdict, REFER))
        for gap in coverage["gaps"]:
            findings.append("%s: %s" % (glass_id, gap))

    crack_lengths = [
        result["length_mm"]
        for result in assessed
        if result["family"] == FAMILY_CRACK and result["length_mm"] is not None
    ]

    return {
        "coverglass_id": glass_id,
        "inspector": resolved["inspector"],
        "verdict": _ROLLUP_BY_SEVERITY[verdict],
        "disposition": verdict,
        "indications": assessed,
        "indications_by_family": by_family,
        "cracked_zones": sorted(by_zone),
        "crack_count": by_family[FAMILY_CRACK],
        "unresolved_count": by_family[FAMILY_UNRESOLVED],
        "longest_recorded_crack_mm": max(crack_lengths, default=None),
        "evidence": coverage,
        "evidence_sufficient": coverage["sufficient"],
        "routed_elsewhere": [
            result["id"] for result in assessed if result["routed_to"]
        ],
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "findings": findings,
    }
