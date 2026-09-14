#!/usr/bin/env python3
"""Surface finish examination of protection diode contact surfaces.

Anchor: ECSS-E-ST-20-08C clause 9.6.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks what finish the contact surfaces of a protection diode
show. It reads like a cosmetic clause and it is not one: the finish is
the surface an interconnect is welded or bonded onto, so every attribute
it names is a weldability attribute wearing an appearance word.

The first thing that has to be established is the examination itself. A
finish is described at a magnification and over an area, and a record
that names neither describes whatever the operator happened to notice.
An examination carried out below the declared magnification has not
looked hard enough to see the things the clause lists, and one that
covered part of the land has described that part. Both close the
contact as not established rather than clean -- a clean page can be a
missing page, and accepting on it is how an unexamined land reaches a
welding head.

Roughness is then taken against two ceilings and not one. Past the
working ceiling the surface is rougher than the process was qualified
for, which is a review: the weld may still be sound and the process has
moved. Past the second ceiling the asperities are deeper than the weld
can consume and the joint would sit on the peaks, which is a rejection.
Carrying only the working ceiling turns every rough land into a review
queue entry, and carrying only the far one accepts a process that has
visibly drifted.

Each finish anomaly is then dispositioned on what it is, how deep it
goes and how much it covers -- never on how bad it looks. A blister is
the clearest case: the finish over it is intact and the adhesion under
it is already gone, so it rejects at any coverage at all, and a rule
written on coverage alone would wave a small one through. A pit is
dispositioned on its depth first, because a pit through the deposit has
reached what the deposit was protecting, and only then on how much of
the land it covers. Oxidation and residue are coverage questions:
neither hurts a weld in a small patch and both starve one when they
spread. A nodule is a height question, because a protrusion holds the
weld head off the surface around it.

Finally the accumulation. A contact on which every single anomaly was
admissible can still be mostly covered in admissible anomalies, so the
total coverage is carried separately and is summed rather than unioned:
overlapping findings describe a surface that has taken the working
twice.

And a diode has two contact surfaces. A polarity with no examination is
not a clean polarity.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANODE = "anode"
CATHODE = "cathode"
CONTACT_POLARITIES = (ANODE, CATHODE)

PITTING = "pitting"
OXIDATION = "oxidation"
RESIDUE = "residue"
NODULE = "nodule"
BLISTER = "blister"
ANOMALY_KINDS = (PITTING, OXIDATION, RESIDUE, NODULE, BLISTER)

_DEPTH_BEARING_KINDS = (PITTING, NODULE)

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

DEFAULT_SURFACE_FINISH_CRITERIA = {
    "min_magnification_x": 10.0,
    "min_examined_fraction": 0.95,
    "max_roughness_ra_um": 1.6,
    "max_weldable_roughness_ra_um": 3.2,
    "max_pit_depth_fraction": 0.30,
    "max_pit_coverage_fraction": 0.05,
    "max_oxidation_coverage_fraction": 0.10,
    "max_residue_coverage_fraction": 0.02,
    "max_nodule_height_fraction": 0.50,
    "max_total_anomaly_coverage_fraction": 0.20,
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


def validate_surface_finish_criteria(criteria):
    """Check a finish criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    _require_positive("min_magnification_x", criteria.get("min_magnification_x"))
    _require_fraction("min_examined_fraction", criteria.get("min_examined_fraction"))
    working = _require_positive(
        "max_roughness_ra_um", criteria.get("max_roughness_ra_um")
    )
    weldable = _require_positive(
        "max_weldable_roughness_ra_um", criteria.get("max_weldable_roughness_ra_um")
    )
    if _at_most(weldable, working):
        raise ValueError(
            "max_weldable_roughness_ra_um must sit above max_roughness_ra_um; "
            "with the two ceilings on top of each other there is no review "
            "band and every rough land is scrap"
        )
    for key in (
        "max_pit_depth_fraction",
        "max_pit_coverage_fraction",
        "max_oxidation_coverage_fraction",
        "max_residue_coverage_fraction",
        "max_nodule_height_fraction",
        "max_total_anomaly_coverage_fraction",
    ):
        _require_fraction(key, criteria.get(key))
    return criteria


def validate_finish_examination(examination):
    """Normalise the examination a finish record was taken under."""
    if not isinstance(examination, dict):
        raise ValueError("examination must be a mapping, got %r" % (examination,))
    return {
        "magnification_x": _require_positive(
            "magnification_x", examination.get("magnification_x")
        ),
        "examined_fraction": _require_fraction(
            "examined_fraction", examination.get("examined_fraction")
        ),
        "roughness_ra_um": _require_positive(
            "roughness_ra_um", examination.get("roughness_ra_um")
        ),
    }


def examination_shortfalls(
    examination, criteria=DEFAULT_SURFACE_FINISH_CRITERIA
):
    """Reasons the examination cannot support a verdict, in order."""
    validate_surface_finish_criteria(criteria)
    record = validate_finish_examination(examination)
    shortfalls = []
    if not _at_least(record["magnification_x"], criteria["min_magnification_x"]):
        shortfalls.append(
            "examined at %.3gx, under the %.3gx the criteria want; the clause "
            "lists things that are not visible at this magnification"
            % (record["magnification_x"], criteria["min_magnification_x"])
        )
    if not _at_least(record["examined_fraction"], criteria["min_examined_fraction"]):
        shortfalls.append(
            "%.1f per cent of the land was examined, under the %.1f per cent "
            "the criteria want; a record covering part of a contact describes "
            "that part"
            % (
                record["examined_fraction"] * 100.0,
                criteria["min_examined_fraction"] * 100.0,
            )
        )
    return tuple(shortfalls)


def examination_is_adequate(examination, criteria=DEFAULT_SURFACE_FINISH_CRITERIA):
    """Whether the examination looked hard enough, and at enough of the land."""
    return not examination_shortfalls(examination, criteria)


def categorize_roughness(
    roughness_ra_um, criteria=DEFAULT_SURFACE_FINISH_CRITERIA
):
    """Disposition a measured roughness against the two ceilings."""
    validate_surface_finish_criteria(criteria)
    roughness = _require_positive("roughness_ra_um", roughness_ra_um)
    if _at_most(roughness, criteria["max_roughness_ra_um"]):
        return (
            ACCEPT,
            "the surface measures Ra %.3g um, inside the %.3g um the process "
            "was qualified for"
            % (roughness, criteria["max_roughness_ra_um"]),
        )
    if _at_most(roughness, criteria["max_weldable_roughness_ra_um"]):
        return (
            REFER_FOR_REVIEW,
            "the surface measures Ra %.3g um, past the %.3g um working ceiling "
            "and inside the %.3g um a weld can still consume; the joint may be "
            "sound and the process has moved"
            % (
                roughness,
                criteria["max_roughness_ra_um"],
                criteria["max_weldable_roughness_ra_um"],
            ),
        )
    return (
        REJECT,
        "the surface measures Ra %.3g um, past the %.3g um a weld can consume; "
        "the joint would sit on the asperity peaks"
        % (roughness, criteria["max_weldable_roughness_ra_um"]),
    )


def validate_finish_anomaly(anomaly):
    """Check one recorded finish anomaly carries what its rule needs."""
    if not isinstance(anomaly, dict):
        raise ValueError("finish anomaly must be a mapping, got %r" % (anomaly,))
    kind = anomaly.get("kind")
    if kind not in ANOMALY_KINDS:
        raise ValueError(
            "anomaly kind must be one of %s, got %r" % (", ".join(ANOMALY_KINDS), kind)
        )
    normalised = {
        "kind": kind,
        "coverage_fraction": _require_fraction(
            "coverage_fraction", anomaly.get("coverage_fraction")
        ),
        "depth_fraction": None,
    }
    if kind in _DEPTH_BEARING_KINDS:
        if "depth_fraction" not in anomaly:
            raise ValueError(
                "a %s must record depth_fraction; its disposition is a depth "
                "question before it is a coverage question" % kind
            )
        normalised["depth_fraction"] = _require_fraction(
            "depth_fraction", anomaly.get("depth_fraction")
        )
    return normalised


def categorize_finish_anomaly(
    anomaly, criteria=DEFAULT_SURFACE_FINISH_CRITERIA
):
    """Disposition one finish anomaly on its kind, depth and coverage."""
    validate_surface_finish_criteria(criteria)
    finding = validate_finish_anomaly(anomaly)
    kind = finding["kind"]
    coverage = finding["coverage_fraction"]

    if kind == BLISTER:
        return (
            REJECT,
            "a blister over %.2f per cent of the land; the finish above it is "
            "intact and the adhesion under it is already gone, so coverage "
            "does not enter into it" % (coverage * 100.0),
        )
    if kind == PITTING:
        depth = finding["depth_fraction"]
        if not _at_most(depth, criteria["max_pit_depth_fraction"]):
            return (
                REJECT,
                "pitting %.0f per cent through the deposit, past the %.0f per "
                "cent allowed; a pit through the finish has reached what the "
                "finish was protecting"
                % (depth * 100.0, criteria["max_pit_depth_fraction"] * 100.0),
            )
        if not _at_most(coverage, criteria["max_pit_coverage_fraction"]):
            return (
                REFER_FOR_REVIEW,
                "shallow pitting over %.2f per cent of the land, past the %.2f "
                "per cent allowed"
                % (coverage * 100.0, criteria["max_pit_coverage_fraction"] * 100.0),
            )
        return (
            ACCEPT,
            "pitting %.0f per cent deep over %.2f per cent of the land, inside "
            "both allowances" % (depth * 100.0, coverage * 100.0),
        )
    if kind == NODULE:
        height = finding["depth_fraction"]
        if not _at_most(height, criteria["max_nodule_height_fraction"]):
            return (
                REFER_FOR_REVIEW,
                "a nodule standing %.0f per cent of the deposit proud, past the "
                "%.0f per cent allowed; a protrusion holds the weld head off "
                "the surface around it"
                % (height * 100.0, criteria["max_nodule_height_fraction"] * 100.0),
            )
        return (
            ACCEPT,
            "a nodule standing %.0f per cent of the deposit proud, inside the "
            "allowance" % (height * 100.0),
        )
    if kind == OXIDATION:
        if not _at_most(coverage, criteria["max_oxidation_coverage_fraction"]):
            return (
                REFER_FOR_REVIEW,
                "oxidation over %.2f per cent of the land, past the %.2f per "
                "cent allowed; a small patch does not hurt a weld and a spread "
                "one starves it"
                % (
                    coverage * 100.0,
                    criteria["max_oxidation_coverage_fraction"] * 100.0,
                ),
            )
        return (
            ACCEPT,
            "oxidation over %.2f per cent of the land, inside the allowance"
            % (coverage * 100.0),
        )
    if not _at_most(coverage, criteria["max_residue_coverage_fraction"]):
        return (
            REFER_FOR_REVIEW,
            "residue over %.2f per cent of the land, past the %.2f per cent "
            "allowed; the weld would be made through it"
            % (coverage * 100.0, criteria["max_residue_coverage_fraction"] * 100.0),
        )
    return (
        ACCEPT,
        "residue over %.2f per cent of the land, inside the allowance"
        % (coverage * 100.0),
    )


def total_anomaly_coverage(anomalies):
    """Share of the land carrying a finding, summed rather than unioned."""
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError("anomalies must be a sequence of finish records")
    return sum(
        validate_finish_anomaly(anomaly)["coverage_fraction"] for anomaly in anomalies
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


def validate_finish_contact(contact):
    """Normalise one polarity contact surface and its finish record."""
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
    anomalies = contact.get("anomalies", [])
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError("contact must record anomalies as a sequence")
    return {
        "id": identifier,
        "polarity": polarity,
        "examination": validate_finish_examination(contact.get("examination")),
        "anomalies": tuple(validate_finish_anomaly(a) for a in anomalies),
    }


def assess_contact_finish(contact, criteria=DEFAULT_SURFACE_FINISH_CRITERIA):
    """Clause 9.6.9 finish verdict for one polarity contact surface."""
    validate_surface_finish_criteria(criteria)
    land = validate_finish_contact(contact)

    findings = []
    dispositions = []
    governing_attribute = None
    governing_rank = _SEVERITY_ORDER[ACCEPT]

    def _record(disposition, attribute, reason=None):
        """Carry a disposition, and let severity pick what governs."""
        dispositions.append(disposition)
        if reason is not None:
            findings.append(reason)
        rank = _SEVERITY_ORDER[disposition]
        if rank > governing_rank:
            return disposition, attribute, rank
        return None, governing_attribute, governing_rank

    shortfalls = examination_shortfalls(land["examination"], criteria)
    for shortfall in shortfalls:
        _, governing_attribute, governing_rank = _record(
            NOT_ESTABLISHED,
            "examination",
            "the %s contact was %s" % (land["polarity"], shortfall),
        )

    roughness_disposition, roughness_reason = categorize_roughness(
        land["examination"]["roughness_ra_um"], criteria
    )
    _, governing_attribute, governing_rank = _record(
        roughness_disposition,
        "roughness",
        None if roughness_disposition == ACCEPT else roughness_reason,
    )

    graded = []
    for anomaly in land["anomalies"]:
        disposition, reason = categorize_finish_anomaly(anomaly, criteria)
        graded.append((anomaly["kind"], disposition))
        _, governing_attribute, governing_rank = _record(
            disposition,
            anomaly["kind"],
            None if disposition == ACCEPT else reason,
        )

    coverage = total_anomaly_coverage(land["anomalies"])
    if not _at_most(coverage, criteria["max_total_anomaly_coverage_fraction"]):
        _, governing_attribute, governing_rank = _record(
            REFER_FOR_REVIEW,
            "accumulated-coverage",
            "%.1f per cent of the %s contact carries a finding, past the %.1f "
            "per cent allowed in total; a land whose every anomaly passed can "
            "still be covered in them"
            % (
                coverage * 100.0,
                land["polarity"],
                criteria["max_total_anomaly_coverage_fraction"] * 100.0,
            ),
        )

    verdict = worst_disposition(dispositions)
    return {
        "contact_id": land["id"],
        "polarity": land["polarity"],
        "verdict": verdict,
        "examination_adequate": not shortfalls,
        "magnification_x": land["examination"]["magnification_x"],
        "examined_fraction": land["examination"]["examined_fraction"],
        "roughness_ra_um": land["examination"]["roughness_ra_um"],
        "roughness_disposition": roughness_disposition,
        "anomalies_recorded": len(land["anomalies"]),
        "anomaly_grades": tuple(graded),
        "total_anomaly_coverage_fraction": coverage,
        "governing_attribute": governing_attribute,
        "findings": findings,
    }


def assess_diode_surface_finish(case, criteria=DEFAULT_SURFACE_FINISH_CRITERIA):
    """Roll the clause 9.6.9 examination up over both contact surfaces."""
    validate_surface_finish_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    contacts = case.get("contacts")
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("case must record contacts as a sequence")
    if not contacts:
        raise ValueError(
            "a diode with no contact surface declared cannot be examined "
            "against a clause about contact surfaces"
        )

    results = []
    seen = set()
    for contact in contacts:
        result = assess_contact_finish(contact, criteria)
        if result["contact_id"] in seen:
            raise ValueError(
                "duplicate contact id %r on the diode" % result["contact_id"]
            )
        seen.add(result["contact_id"])
        results.append(result)

    examined = {result["polarity"] for result in results}
    unexamined = tuple(p for p in CONTACT_POLARITIES if p not in examined)

    findings = []
    dispositions = [result["verdict"] for result in results]
    if unexamined:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "no finish examination for the %s contact; a surface nobody looked "
            "at is not a clean surface" % " and ".join(unexamined)
        )

    return {
        "diode_id": _require_label("diode id", case.get("id", "unnamed-diode")),
        "verdict": worst_disposition(dispositions),
        "contacts_examined": len(results),
        "polarities_without_an_examination": unexamined,
        "roughest_contact_ra_um": max(
            result["roughness_ra_um"] for result in results
        ),
        "contacts_not_accepted": tuple(
            result["contact_id"] for result in results if result["verdict"] != ACCEPT
        ),
        "governing_attributes": tuple(
            result["governing_attribute"]
            for result in results
            if result["governing_attribute"] is not None
        ),
        "rollup_findings": findings,
        "contact_results": tuple(results),
    }
