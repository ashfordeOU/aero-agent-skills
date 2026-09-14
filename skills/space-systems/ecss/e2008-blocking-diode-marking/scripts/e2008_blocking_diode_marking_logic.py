#!/usr/bin/env python3
"""Marking approaches for delivered planar blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause fixes no marking method. It says the approach used on
delivered planar blocking diodes is settled together with the customer,
which makes the agreement the first requirement rather than a formality
wrapped around a technical one. A scheme the supplier picked alone fails
the clause however legible and however permanent the mark is, because
nobody on the receiving side committed to reading it that way.

Once the agreement stands, three physical questions decide whether the
approach actually delivers an identity:

    fit         an identity code has a character count and a minimum
                legible character height, and the carrier it is put on
                has a finite face. A code that does not fit is not a
                marking approach, it is an aspiration.
    retention   a mark is only worth the handling stage it survives to.
                A label on a shipping carrier stops at incoming
                inspection; the diode leaves the bag and the identity
                stays behind.
    granularity a mark resolves a delivered diode to a population, not
                always to itself. A lot bag label resolves it to the
                whole lot, so a part pulled from the bag carries no
                identity of its own at all.

A planar blocking diode is a small part with a small face, which is why
the three questions pull against each other: the approach that survives
furthest is usually the one with the least room to write on.

The approach catalogue, the handling stages and the granularity limit
below are declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

AGREEMENT_RECORDED = "marking-agreement-recorded"
AGREEMENT_VERBAL = "marking-agreement-verbal"
AGREEMENT_SUPERSEDED = "marking-agreement-superseded"
AGREEMENT_PROPOSED = "marking-agreement-proposed"
AGREEMENT_ABSENT = "marking-agreement-absent"
AGREEMENT_STANDINGS = (
    AGREEMENT_RECORDED,
    AGREEMENT_VERBAL,
    AGREEMENT_SUPERSEDED,
    AGREEMENT_PROPOSED,
    AGREEMENT_ABSENT,
)

GRAIN_PART = "part-level-identity"
GRAIN_PACKAGE = "package-level-identity"
GRAIN_LOT = "lot-level-identity"
GRAINS = (GRAIN_PART, GRAIN_PACKAGE, GRAIN_LOT)

HANDLING_STAGES = (
    "diode-incoming-inspection",
    "diode-cleaning",
    "diode-mounting",
    "solar-array-integration",
    "solar-array-flight",
)

CARRIER_BODY = "planar-diode-body"
CARRIER_PACKAGE = "diode-shipping-carrier"
CARRIER_LOT_BAG = "diode-lot-bag"
CARRIERS = (CARRIER_BODY, CARRIER_PACKAGE, CARRIER_LOT_BAG)

MARKING_APPROACHES = {
    "planar-blocking-diode-laser-body-mark": {
        "carrier": CARRIER_BODY,
        "granularity": GRAIN_PART,
        "survives_through": "solar-array-flight",
        "min_character_height_mm": 0.25,
    },
    "planar-blocking-diode-ink-body-mark": {
        "carrier": CARRIER_BODY,
        "granularity": GRAIN_PART,
        "survives_through": "diode-mounting",
        "min_character_height_mm": 0.40,
    },
    "planar-blocking-diode-carrier-label": {
        "carrier": CARRIER_PACKAGE,
        "granularity": GRAIN_PACKAGE,
        "survives_through": "diode-incoming-inspection",
        "min_character_height_mm": 1.50,
    },
    "planar-blocking-diode-lot-bag-label": {
        "carrier": CARRIER_LOT_BAG,
        "granularity": GRAIN_LOT,
        "survives_through": "diode-incoming-inspection",
        "min_character_height_mm": 2.00,
    },
}

CHARACTER_ASPECT = 0.6
CHARACTER_GAP = 0.2

APPROACH_ACCEPTABLE = "marking-approach-acceptable"
APPROACH_NOT_AGREED = "marking-approach-not-agreed"
APPROACH_CODE_DOES_NOT_FIT = "marking-approach-code-does-not-fit"
APPROACH_RETENTION_SHORT = "marking-approach-retention-short"
APPROACH_GRANULARITY_SHORT = "marking-approach-granularity-short"

APPROACH_RANK = {
    APPROACH_NOT_AGREED: 0,
    APPROACH_CODE_DOES_NOT_FIT: 1,
    APPROACH_RETENTION_SHORT: 2,
    APPROACH_GRANULARITY_SHORT: 3,
    APPROACH_ACCEPTABLE: 4,
}

MARKING_ACCEPTED = "blocking-diode-marking-accepted"
MARKING_NOT_ACCEPTED = "blocking-diode-marking-not-accepted"

DEFAULT_MARKING_POLICY = {
    "accept_verbal_agreement": False,
    "required_identity_through": "solar-array-integration",
    "max_parts_per_mark": 1,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_positive(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must sit above zero, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A code footprint is a sum of products of a character height, so a
    code laid out to exactly fill its face can evaluate a unit in the
    last place above the face. The comparison absorbs that; the declared
    face is untouched.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_MARKING_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_flag(
        "accept_verbal_agreement", settings.get("accept_verbal_agreement")
    )
    _require_choice(
        "required_identity_through",
        settings.get("required_identity_through"),
        HANDLING_STAGES,
    )
    _require_count("max_parts_per_mark", settings.get("max_parts_per_mark"))
    return settings


def validate_agreement(agreement, policy=None):
    """Grade the standing of the marking agreement with the customer."""
    settings = resolve_policy(policy)
    block = _require_mapping("agreement", agreement)
    standing = _require_choice(
        "agreement standing", block.get("standing"), AGREEMENT_STANDINGS
    )
    approach = block.get("approach")
    if approach is not None:
        approach = _require_choice("approach", approach, tuple(MARKING_APPROACHES))
    reference = block.get("reference")
    reference = reference.strip() if isinstance(reference, str) else None

    findings = []
    binds = False
    if standing == AGREEMENT_RECORDED:
        if not reference:
            findings.append(
                "the agreement is claimed as recorded but names no document, "
                "so there is nothing for either side to read it back from"
            )
        else:
            binds = True
    elif standing == AGREEMENT_VERBAL:
        findings.append(
            "the agreement is verbal; it binds the delivery it was made for "
            "and nothing at the next one"
        )
        binds = settings["accept_verbal_agreement"]
    elif standing == AGREEMENT_SUPERSEDED:
        findings.append(
            "the agreement was superseded; the difference between the two "
            "schemes has to be dispositioned before either is delivered to"
        )
    elif standing == AGREEMENT_PROPOSED:
        findings.append(
            "the approach was proposed and never answered, so the customer "
            "committed to nothing"
        )
    else:
        findings.append(
            "no marking approach was settled with the customer at all; the "
            "clause is unmet whatever mark the delivery carries"
        )
    if approach is None:
        findings.append("the agreement names no marking approach")
        binds = False
    return {
        "standing": standing,
        "approach": approach,
        "reference": reference,
        "binds": binds,
        "findings": findings,
    }


def code_footprint_mm(code, character_height_mm):
    """Size the identity code laid out at a given character height."""
    text = _require_label("code", code)
    height = _require_positive("character_height_mm", character_height_mm)
    count = len(text)
    width = count * CHARACTER_ASPECT * height + (count - 1) * CHARACTER_GAP * height
    return {
        "characters": count,
        "character_height_mm": height,
        "width_mm": width,
        "height_mm": height,
    }


def assess_face_fit(approach_name, code, face_mm, character_height_mm=None):
    """Decide whether the identity code fits the face it is put on."""
    name = _require_choice("approach", approach_name, tuple(MARKING_APPROACHES))
    approach = MARKING_APPROACHES[name]
    if not isinstance(face_mm, (list, tuple)) or len(face_mm) != 2:
        raise ValueError(
            "face_mm must be a (width, height) pair in mm, got %r" % (face_mm,)
        )
    face_width = _require_positive("face width", face_mm[0])
    face_height = _require_positive("face height", face_mm[1])
    minimum = approach["min_character_height_mm"]
    height = minimum if character_height_mm is None else _require_positive(
        "character_height_mm", character_height_mm
    )
    legible = _at_least(height, minimum)
    footprint = code_footprint_mm(code, height)

    fits = (
        legible
        and _at_most(footprint["width_mm"], face_width)
        and _at_most(footprint["height_mm"], face_height)
    )
    findings = []
    if not legible:
        findings.append(
            "%s: a character height of %.4g mm sits below the %.4g mm this "
            "approach stays legible at" % (name, height, minimum)
        )
    if not _at_most(footprint["width_mm"], face_width):
        findings.append(
            "%s: the %d character code needs %.4g mm across a face %.4g mm wide"
            % (name, footprint["characters"], footprint["width_mm"], face_width)
        )
    if not _at_most(footprint["height_mm"], face_height):
        findings.append(
            "%s: a %.4g mm character will not sit on a face %.4g mm tall"
            % (name, footprint["height_mm"], face_height)
        )
    return {
        "approach": name,
        "carrier": approach["carrier"],
        "footprint": footprint,
        "face_width_mm": face_width,
        "face_height_mm": face_height,
        "legible": legible,
        "fits": fits,
        "findings": findings,
    }


def retention_reach(approach_name, required_stage):
    """Say how far down handling a mark on this carrier survives."""
    name = _require_choice("approach", approach_name, tuple(MARKING_APPROACHES))
    required = _require_choice(
        "required_identity_through", required_stage, HANDLING_STAGES
    )
    survives = MARKING_APPROACHES[name]["survives_through"]
    reach = HANDLING_STAGES.index(survives)
    needed = HANDLING_STAGES.index(required)
    findings = []
    if reach < needed:
        findings.append(
            "%s: the mark survives to %s, and identity is owed through %s"
            % (name, survives, required)
        )
    return {
        "approach": name,
        "survives_through": survives,
        "required_through": required,
        "reaches": reach >= needed,
        "findings": findings,
    }


def identity_granularity(approach_name, lot_size, package_size):
    """Count the diodes a single mark resolves a delivered part to."""
    name = _require_choice("approach", approach_name, tuple(MARKING_APPROACHES))
    lot = _require_count("lot_size", lot_size)
    package = _require_count("package_size", package_size)
    if package > lot:
        raise ValueError(
            "package_size %d cannot exceed lot_size %d" % (package, lot)
        )
    grain = MARKING_APPROACHES[name]["granularity"]
    if grain == GRAIN_PART:
        parts_per_mark = 1
    elif grain == GRAIN_PACKAGE:
        parts_per_mark = package
    else:
        parts_per_mark = lot
    return {
        "approach": name,
        "granularity": grain,
        "parts_per_mark": parts_per_mark,
    }


def assess_marking_approach(approach_name, case):
    """Grade one candidate approach against agreement, fit, reach and grain."""
    _require_mapping("case", case)
    settings = resolve_policy(case.get("policy"))
    name = _require_choice("approach", approach_name, tuple(MARKING_APPROACHES))
    faces = _require_mapping("faces_mm", case.get("faces_mm"))
    carrier = MARKING_APPROACHES[name]["carrier"]
    if carrier not in faces:
        raise ValueError(
            "no marking face declared for carrier %r, which %s writes on"
            % (carrier, name)
        )
    code = _require_label("identity_code", case.get("identity_code"))
    fit = assess_face_fit(
        name, code, faces[carrier], case.get("character_height_mm")
    )
    reach = retention_reach(name, settings["required_identity_through"])
    grain = identity_granularity(
        name, case.get("lot_size"), case.get("package_size")
    )
    grain_ok = grain["parts_per_mark"] <= settings["max_parts_per_mark"]

    findings = list(fit["findings"]) + list(reach["findings"])
    if not grain_ok:
        findings.append(
            "%s: one mark resolves a delivered diode only to %d parts, and "
            "policy asks for %d"
            % (name, grain["parts_per_mark"], settings["max_parts_per_mark"])
        )

    if not fit["fits"]:
        verdict = APPROACH_CODE_DOES_NOT_FIT
    elif not reach["reaches"]:
        verdict = APPROACH_RETENTION_SHORT
    elif not grain_ok:
        verdict = APPROACH_GRANULARITY_SHORT
    else:
        verdict = APPROACH_ACCEPTABLE
    return {
        "approach": name,
        "fit": fit,
        "retention": reach,
        "granularity": grain,
        "meets_granularity": grain_ok,
        "verdict": verdict,
        "findings": findings,
    }


def select_marking_approach(case):
    """Rank every catalogued approach and name the ones that would work."""
    _require_mapping("case", case)
    faces = _require_mapping("faces_mm", case.get("faces_mm"))
    _require_label("identity_code", case.get("identity_code"))
    graded = []
    for name in sorted(MARKING_APPROACHES):
        if MARKING_APPROACHES[name]["carrier"] not in faces:
            continue
        graded.append(assess_marking_approach(name, case))
    if not graded:
        raise ValueError(
            "no catalogued approach could be graded; declare a marking face "
            "for at least one carrier"
        )
    acceptable = [g for g in graded if g["verdict"] == APPROACH_ACCEPTABLE]
    acceptable.sort(
        key=lambda g: (
            -HANDLING_STAGES.index(g["retention"]["survives_through"]),
            g["granularity"]["parts_per_mark"],
            g["approach"],
        )
    )
    return {
        "graded": graded,
        "acceptable": [g["approach"] for g in acceptable],
        "recommended": acceptable[0]["approach"] if acceptable else None,
    }


def assess_blocking_diode_marking(case):
    """Full clause 12.2.3 roll-up over a planar blocking diode delivery."""
    _require_mapping("case", case)
    part_id = _require_label("part_id", case.get("part_id"))
    settings = resolve_policy(case.get("policy"))
    agreement = validate_agreement(case.get("agreement"), settings)
    options = select_marking_approach(case)

    findings = list(agreement["findings"])
    delivered = None
    if agreement["approach"] is not None:
        delivered = assess_marking_approach(agreement["approach"], case)
        findings.extend(delivered["findings"])

    if not agreement["binds"]:
        verdict = MARKING_NOT_ACCEPTED
        approach_verdict = APPROACH_NOT_AGREED
    elif delivered is not None and delivered["verdict"] == APPROACH_ACCEPTABLE:
        verdict = MARKING_ACCEPTED
        approach_verdict = APPROACH_ACCEPTABLE
    else:
        verdict = MARKING_NOT_ACCEPTED
        approach_verdict = delivered["verdict"] if delivered else APPROACH_NOT_AGREED

    if verdict == MARKING_NOT_ACCEPTED and options["recommended"]:
        findings.append(
            "%s would satisfy the fit, retention and granularity the delivery "
            "needs, and is the approach to settle with the customer"
            % options["recommended"]
        )
    return {
        "part_id": part_id,
        "agreement": agreement,
        "delivered_approach": delivered,
        "approach_verdict": approach_verdict,
        "approach_rank": APPROACH_RANK[approach_verdict],
        "acceptable_approaches": options["acceptable"],
        "recommended_approach": options["recommended"],
        "verdict": verdict,
        "findings": findings,
    }
