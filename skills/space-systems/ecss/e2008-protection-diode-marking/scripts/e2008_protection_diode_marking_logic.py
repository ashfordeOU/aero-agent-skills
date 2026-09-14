#!/usr/bin/env python3
"""Marking of delivered external protection diodes.

Anchor: ECSS-E-ST-20-08C clause 9.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An external protection diode is delivered as a discrete part and is
fitted into the spacecraft wiring later, by somebody who was not in the
room when the marking scheme was picked. The clause does not fix a
method; it makes the method a thing the supplier and the customer agree.
So the first question is never what the mark says, it is whether anyone
agreed to it and whether that agreement can be produced.

Agreement standing
    agreed-and-recorded  the customer agreed and the agreement is on file
    agreed-verbally      the customer agreed and nothing records it
    superseded           agreed against an earlier scheme since replaced
    proposed-not-agreed  the supplier put it forward and nobody answered
    not-sought           the supplier simply chose

What the mark is carried on
    diode-body     on the part itself
    diode-lead     on a lead that is later trimmed and formed
    unit-package   on the bag or blister the part is shipped in
    shipping-tray  on the tray the bags travel in
    none           nothing carries a mark

How far down the handling chain identity survives
    sealed-package      still in the shipper
    incoming-inspection the shipper is open, the part is beside its bag
    kitted-loose        picked into a kit with nothing around it
    mounted-on-panel    fitted into the wiring

Identity granularity
    item          this part
    package       the parts that shared one bag
    delivery-lot  the parts that shared one delivery
    none          nothing

Two numbers do real work. A code only exists if the characters fit the
face they are put on, so the code length times the character pitch is
held against the available face length. And a granularity coarser than
the item resolves a part to a set rather than to a part, so the
resolution share is one over the size of that set.

The required retention stage, the resolution floor and the carrier
retention table below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

AGREEMENT_STANDINGS = (
    "agreed-and-recorded",
    "agreed-verbally",
    "superseded",
    "proposed-not-agreed",
    "not-sought",
)

MARK_CARRIERS = (
    "diode-body",
    "diode-lead",
    "unit-package",
    "shipping-tray",
    "none",
)

HANDLING_STAGES = (
    "sealed-package",
    "incoming-inspection",
    "kitted-loose",
    "mounted-on-panel",
)

STAGE_RANK = {stage: index for index, stage in enumerate(HANDLING_STAGES)}

CARRIER_RETENTION = {
    "diode-body": "mounted-on-panel",
    "diode-lead": "kitted-loose",
    "unit-package": "incoming-inspection",
    "shipping-tray": "sealed-package",
    "none": None,
}

GRANULARITY_ITEM = "item"
GRANULARITY_PACKAGE = "package"
GRANULARITY_LOT = "delivery-lot"
GRANULARITY_NONE = "none"

GRANULARITIES = (
    GRANULARITY_ITEM,
    GRANULARITY_PACKAGE,
    GRANULARITY_LOT,
    GRANULARITY_NONE,
)

MARKING_AGREED = "marking-agreed-and-adequate"
MARKING_SHORT = "marking-agreed-but-short"
MARKING_NOT_AGREED = "marking-not-agreed"

MARKING_RANK = {
    MARKING_NOT_AGREED: 0,
    MARKING_SHORT: 1,
    MARKING_AGREED: 2,
}

DEFAULT_MARKING_POLICY = {
    "required_retention_stage": "mounted-on-panel",
    "min_resolution_share": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_positive(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_positive_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A code cut exactly to the width of the face it is put on is a
    product of measured lengths against another measured length, so it
    can evaluate a unit in the last place over. The comparison absorbs
    that; the face length itself stays as measured.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def agreement_standing(standing, agreed_carrier=None, delivered_carrier=None):
    """Decide whether the marking approach was agreed, and still is.

    The clause makes the approach a bilateral choice, so a scheme the
    supplier picked alone fails however good the mark is, and a scheme
    agreed against a carrier the delivery did not use is an agreement
    about something else.
    """
    where = _require_choice("standing", standing, AGREEMENT_STANDINGS)
    findings = []
    binding = where in ("agreed-and-recorded", "agreed-verbally", "superseded")
    concession = False

    if where == "proposed-not-agreed":
        findings.append(
            "the approach was put forward and never answered, so nothing the "
            "customer agreed to is being delivered against"
        )
    elif where == "not-sought":
        findings.append(
            "the supplier chose the approach alone; the clause makes the choice "
            "one the customer takes part in"
        )
    elif where == "agreed-verbally":
        concession = True
        findings.append(
            "the agreement exists only as a conversation; nothing on file holds "
            "either party to it at the next delivery"
        )
    elif where == "superseded":
        concession = True
        findings.append(
            "the agreement in force was replaced; the difference between the "
            "two schemes has to be dispositioned before it carries a delivery"
        )

    if agreed_carrier is not None and delivered_carrier is not None:
        promised = _require_choice("agreed_carrier", agreed_carrier, MARK_CARRIERS)
        used = _require_choice(
            "delivered_carrier", delivered_carrier, MARK_CARRIERS
        )
        if promised != used:
            concession = True
            findings.append(
                "the agreement covers a mark on the %s and the delivery carries "
                "it on the %s, which is a change the customer has not seen"
                % (promised, used)
            )
    return {
        "standing": where,
        "binding": binding,
        "needs_concession": concession,
        "findings": findings,
    }


def carrier_retention_stage(mark_carrier):
    """How far down the handling chain a mark on this carrier survives."""
    carrier = _require_choice("mark_carrier", mark_carrier, MARK_CARRIERS)
    stage = CARRIER_RETENTION[carrier]
    findings = []
    if stage is None:
        findings.append(
            "nothing on the delivery carries a mark, so identity rests on the "
            "order of the parts in the box"
        )
    elif carrier == "diode-lead":
        findings.append(
            "a mark on a lead is gone once the lead is trimmed and formed for "
            "mounting"
        )
    elif carrier in ("unit-package", "shipping-tray"):
        findings.append(
            "the mark is on packaging rather than on the part; identity ends "
            "when the part leaves it"
        )
    return {
        "mark_carrier": carrier,
        "retention_stage": stage,
        "retention_rank": -1 if stage is None else STAGE_RANK[stage],
        "findings": findings,
    }


def retention_shortfall(required_stage, reached_stage):
    """Handling steps between the stage reached and the stage required."""
    required = _require_choice(
        "required_stage", required_stage, HANDLING_STAGES
    )
    if reached_stage is None:
        reached_rank = -1
    else:
        reached_rank = STAGE_RANK[
            _require_choice("reached_stage", reached_stage, HANDLING_STAGES)
        ]
    gap = STAGE_RANK[required] - reached_rank
    return {
        "required_stage": required,
        "reached_stage": reached_stage,
        "steps_short": max(gap, 0),
        "meets_requirement": gap <= 0,
    }


def code_fits_marking_face(code_characters, character_pitch_mm, face_length_mm):
    """Check the code physically fits the face it is put on.

    A scheme that does not fit is not a marking scheme, it is a marking
    intention, and it shows up at the marking bench rather than at the
    review that approved it.
    """
    characters = _require_positive_count("code_characters", code_characters)
    pitch = _require_positive("character_pitch_mm", character_pitch_mm)
    face = _require_positive("face_length_mm", face_length_mm)
    needed = characters * pitch
    fits = _at_most(needed, face)
    findings = []
    if not fits:
        findings.append(
            "a %d character code at %.4g mm pitch needs %.4g mm and the face "
            "offers %.4g mm" % (characters, pitch, needed, face)
        )
    return {
        "code_characters": characters,
        "required_length_mm": needed,
        "face_length_mm": face,
        "margin_mm": face - needed,
        "fits": fits,
        "findings": findings,
    }


def identity_resolution(granularity, items_delivered, items_per_package=1):
    """Share of a delivered part's identity the granularity actually resolves.

    Item granularity resolves a part to itself. Package granularity
    resolves it to the parts that shared a bag, lot granularity to the
    whole delivery, and none resolves nothing at all.
    """
    level = _require_choice("granularity", granularity, GRANULARITIES)
    delivered = _require_positive_count("items_delivered", items_delivered)
    per_package = _require_positive_count("items_per_package", items_per_package)
    if per_package > delivered:
        raise ValueError(
            "a package of %d parts cannot come out of a delivery of %d"
            % (per_package, delivered)
        )

    if level == GRANULARITY_ITEM:
        set_size = 1
    elif level == GRANULARITY_PACKAGE:
        set_size = per_package
    elif level == GRANULARITY_LOT:
        set_size = delivered
    else:
        set_size = 0

    findings = []
    if set_size == 0:
        share = 0.0
        findings.append("the scheme resolves a delivered part to nothing")
    else:
        share = 1.0 / set_size
        if set_size > 1:
            findings.append(
                "a delivered part resolves to the %d parts that shared its %s, "
                "not to the part" % (set_size, level)
            )
    return {
        "granularity": level,
        "resolved_set_size": set_size,
        "resolution_share": share,
        "findings": findings,
    }


def assess_diode_marking(record, policy=None):
    """Grade the marking approach of one delivered external diode type."""
    _require_mapping("record", record)
    settings = dict(DEFAULT_MARKING_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    required_stage = _require_choice(
        "required_retention_stage",
        settings.get("required_retention_stage"),
        HANDLING_STAGES,
    )
    floor = settings.get("min_resolution_share")
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        raise ValueError(
            "min_resolution_share must be a number, got %r" % (floor,)
        )
    floor = float(floor)

    part_type = _require_label("part_type", record.get("part_type"))
    agreement = agreement_standing(
        record.get("agreement_standing"),
        record.get("agreed_carrier"),
        record.get("mark_carrier") if record.get("agreed_carrier") else None,
    )
    retention = carrier_retention_stage(record.get("mark_carrier"))
    shortfall = retention_shortfall(required_stage, retention["retention_stage"])
    resolution = identity_resolution(
        record.get("granularity"),
        record.get("items_delivered"),
        record.get("items_per_package", 1),
    )

    findings = ["%s: %s" % (part_type, f) for f in agreement["findings"]]
    findings.extend("%s: %s" % (part_type, f) for f in retention["findings"])
    findings.extend("%s: %s" % (part_type, f) for f in resolution["findings"])

    fit = None
    if retention["retention_stage"] is not None:
        fit = code_fits_marking_face(
            record.get("code_characters"),
            record.get("character_pitch_mm"),
            record.get("face_length_mm"),
        )
        findings.extend("%s: %s" % (part_type, f) for f in fit["findings"])

    resolves_enough = _at_least(resolution["resolution_share"], floor)
    if not resolves_enough:
        findings.append(
            "%s: the scheme resolves %.4g of a part against a %.4g floor"
            % (part_type, resolution["resolution_share"], floor)
        )
    if not shortfall["meets_requirement"]:
        findings.append(
            "%s: identity is owed as far as %s and survives only to %s, %d "
            "step(s) short"
            % (
                part_type,
                shortfall["required_stage"],
                shortfall["reached_stage"] or "no stage at all",
                shortfall["steps_short"],
            )
        )

    if not agreement["binding"] or retention["retention_stage"] is None:
        verdict = MARKING_NOT_AGREED
    elif (
        not shortfall["meets_requirement"]
        or not resolves_enough
        or (fit is not None and not fit["fits"])
        or agreement["needs_concession"]
    ):
        verdict = MARKING_SHORT
    else:
        verdict = MARKING_AGREED

    return {
        "part_type": part_type,
        "agreement": agreement,
        "mark_carrier": retention["mark_carrier"],
        "retention_stage": retention["retention_stage"],
        "shortfall": shortfall,
        "resolution": resolution,
        "resolves_enough": resolves_enough,
        "code_fit": fit,
        "verdict": verdict,
        "findings": findings,
    }


def assess_diode_marking_scheme(case):
    """Full clause 9.2.3 roll-up over the external diode types in a delivery."""
    _require_mapping("case", case)
    delivery_id = _require_label("delivery_id", case.get("delivery_id"))
    records = case.get("diode_types")
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("case must carry a non-empty diode_types sequence")

    assessments = [
        assess_diode_marking(record, case.get("policy")) for record in records
    ]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    seen = []
    for assessment in assessments:
        if assessment["part_type"] in seen:
            raise ValueError(
                "part type %r appears twice in one delivery"
                % assessment["part_type"]
            )
        seen.append(assessment["part_type"])

    adequate = [a for a in assessments if a["verdict"] == MARKING_AGREED]
    unmarked = sorted(
        a["part_type"] for a in assessments if a["verdict"] == MARKING_NOT_AGREED
    )
    adequate_share = len(adequate) / len(assessments)
    worst = min(MARKING_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in MARKING_RANK.items() if v == worst)
    weakest = min(
        assessments,
        key=lambda a: (
            MARKING_RANK[a["verdict"]],
            -a["shortfall"]["steps_short"],
            a["part_type"],
        ),
    )
    return {
        "delivery_id": delivery_id,
        "assessments": assessments,
        "verdict": verdict,
        "adequate_share": adequate_share,
        "fully_adequate": _at_least(adequate_share, 1.0),
        "unmarked_types": unmarked,
        "weakest_type": weakest["part_type"],
        "findings": findings,
    }
