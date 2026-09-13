#!/usr/bin/env python3
"""Visual inspection of solder joints at solar-array string terminations.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.13. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause does not carry the acceptance figures itself. It points at a
workmanship standard agreed between the supplier and the customer, and
the joints at the string terminations are examined against that. The
consequence for an implementation is unusual and is the whole point of
this module: the agreement is an input, and without a complete,
approved, in-force agreement there is no disposition to make. An
inspector who grades a joint against remembered numbers has produced an
opinion, not an inspection record.

So the screen runs in two steps. First the agreement is checked: it
needs a reference, an issue, customer approval and an effective date
that is not after the inspection date. Only then are the joints graded
against the criteria that agreement carries.

Joint attributes that carry no acceptance figure at all -- the joint is
refused on the attribute, whatever the geometry measures:

    cracked-joint       a fracture through the solidified solder
    disturbed-joint     movement while the solder was freezing
    cold-joint          the solder never reached wetting temperature
    dewetting           solder pulled back off the base metal

Graded geometry, each measured per joint:

    wetting_angle_deg           low angle means the solder wetted out
    fillet_coverage_fraction    wetted length over the joint length
    void_area_fraction          voids as a share of the joint footprint

Dispositions are accept, rework and reject. The limits below are a
declared example criteria set standing in for a project agreement; a
project substitutes the figures its own agreement carries.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TERMINATION_TYPES = (
    "string-positive-termination",
    "string-negative-termination",
    "string-to-string-interconnection",
    "string-to-harness-termination",
)

NOT_TOLERATED_ATTRIBUTES = (
    "cracked-joint",
    "disturbed-joint",
    "cold-joint",
    "dewetting",
)

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_SOLDER_CRITERIA = {
    "accept_wetting_angle_deg": 30.0,
    "rework_wetting_angle_deg": 55.0,
    "accept_fillet_coverage_fraction": 0.75,
    "rework_fillet_coverage_fraction": 0.50,
    "accept_void_area_fraction": 0.05,
    "rework_void_area_fraction": 0.25,
    "max_rework_cycles": 2,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage fraction is a quotient of two measured lengths, so a
    joint sitting exactly on the limit can evaluate a few units in the
    last place below it. The limit is never relaxed; only the
    comparison tolerates the representation error.
    """
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def _as_date_tuple(name, value):
    """Parse an ISO calendar date into a comparable tuple."""
    text = _require_text(name, value)
    parts = text.split("-")
    if len(parts) != 3:
        raise ValueError("%s must be an ISO date yyyy-mm-dd, got %r" % (name, value))
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        raise ValueError("%s must be an ISO date yyyy-mm-dd, got %r" % (name, value))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        raise ValueError("%s is not a calendar date: %r" % (name, value))
    return (year, month, day)


def validate_workmanship_agreement(agreement, inspection_date=None):
    """Check the customer-agreed workmanship standard is usable.

    The clause grades the joints against an agreed standard, so an
    agreement that is unnamed, unissued, unapproved or not yet in force
    leaves nothing to grade against. Every one of those is refused
    rather than defaulted.
    """
    if not isinstance(agreement, dict):
        raise ValueError("agreement must be a mapping, got %r" % (agreement,))
    reference = _require_text("agreement reference", agreement.get("reference"))
    issue = _require_text("agreement issue", agreement.get("issue"))
    if agreement.get("customer_approved") is not True:
        raise ValueError(
            "workmanship standard %s issue %s is not approved by the customer; "
            "the clause grades the joints against an agreed standard and there "
            "is none" % (reference, issue)
        )
    effective = _as_date_tuple(
        "agreement effective_date", agreement.get("effective_date")
    )
    if inspection_date is not None:
        inspected = _as_date_tuple("inspection_date", inspection_date)
        if inspected < effective:
            raise ValueError(
                "workmanship standard %s issue %s takes effect after the "
                "inspection date; the joints were graded against a standard "
                "that was not yet in force" % (reference, issue)
            )
    return {
        "reference": reference,
        "issue": issue,
        "effective_date": agreement.get("effective_date").strip(),
        "customer_approved": True,
    }


def validate_solder_criteria(criteria):
    """Check the criteria the agreement carries are ordered and complete."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    accept_angle = _require_positive(
        "accept_wetting_angle_deg", criteria.get("accept_wetting_angle_deg")
    )
    rework_angle = _require_positive(
        "rework_wetting_angle_deg", criteria.get("rework_wetting_angle_deg")
    )
    if rework_angle < accept_angle:
        raise ValueError(
            "criteria rework_wetting_angle_deg is below the accept angle"
        )
    if rework_angle > 180.0:
        raise ValueError(
            "criteria rework_wetting_angle_deg cannot exceed 180 degrees"
        )
    accept_coverage = _require_positive(
        "accept_fillet_coverage_fraction",
        criteria.get("accept_fillet_coverage_fraction"),
    )
    rework_coverage = _require_positive(
        "rework_fillet_coverage_fraction",
        criteria.get("rework_fillet_coverage_fraction"),
    )
    if accept_coverage > 1.0 and not _close(accept_coverage, 1.0):
        raise ValueError(
            "criteria accept_fillet_coverage_fraction cannot exceed one"
        )
    if rework_coverage > accept_coverage and not _close(
        rework_coverage, accept_coverage
    ):
        raise ValueError(
            "criteria rework_fillet_coverage_fraction is above the accept "
            "fraction; coverage limits run downward"
        )
    accept_void = _require_non_negative(
        "accept_void_area_fraction", criteria.get("accept_void_area_fraction")
    )
    rework_void = _require_non_negative(
        "rework_void_area_fraction", criteria.get("rework_void_area_fraction")
    )
    if rework_void < accept_void:
        raise ValueError(
            "criteria rework_void_area_fraction is below the accept fraction"
        )
    if rework_void > 1.0 and not _close(rework_void, 1.0):
        raise ValueError("criteria rework_void_area_fraction cannot exceed one")
    cycles = criteria.get("max_rework_cycles")
    if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 0:
        raise ValueError(
            "criteria max_rework_cycles must be a non-negative integer, got %r"
            % (cycles,)
        )
    return criteria


def fillet_coverage_fraction(wetted_length_mm, joint_length_mm):
    """Share of the joint length the solder fillet actually covers."""
    wetted = _require_non_negative("wetted_length_mm", wetted_length_mm)
    joint = _require_positive("joint_length_mm", joint_length_mm)
    if not _at_most(wetted, joint):
        raise ValueError(
            "wetted length %.3f mm exceeds the joint length %.3f mm; the "
            "measurement or the joint length is wrong" % (wetted, joint)
        )
    if wetted > joint:
        wetted = joint
    return wetted / joint


def void_area_fraction(void_area_mm2, joint_area_mm2):
    """Share of the joint footprint taken up by voids."""
    void = _require_non_negative("void_area_mm2", void_area_mm2)
    joint = _require_positive("joint_area_mm2", joint_area_mm2)
    if not _at_most(void, joint):
        raise ValueError(
            "void area %.3f mm2 exceeds the joint area %.3f mm2; the "
            "measurement or the joint area is wrong" % (void, joint)
        )
    if void > joint:
        void = joint
    return void / joint


def assess_solder_joint(joint, agreement, criteria=DEFAULT_SOLDER_CRITERIA):
    """Disposition one string-termination joint against the agreed standard."""
    approved = validate_workmanship_agreement(agreement)
    validate_solder_criteria(criteria)
    if not isinstance(joint, dict):
        raise ValueError("joint must be a mapping, got %r" % (joint,))
    termination = _require_choice(
        "termination_type", joint.get("termination_type"), TERMINATION_TYPES
    )
    attributes = joint.get("attributes", ())
    if not isinstance(attributes, (list, tuple)):
        raise ValueError("joint attributes must be a list, got %r" % (attributes,))
    for attribute in attributes:
        _require_choice("attribute", attribute, NOT_TOLERATED_ATTRIBUTES)

    angle = _require_non_negative("wetting_angle_deg", joint.get("wetting_angle_deg"))
    if angle > 180.0:
        raise ValueError(
            "wetting_angle_deg must not exceed 180 degrees, got %r" % (angle,)
        )
    coverage = fillet_coverage_fraction(
        joint.get("wetted_length_mm"), joint.get("joint_length_mm")
    )
    voids = void_area_fraction(
        joint.get("void_area_mm2"), joint.get("joint_area_mm2")
    )
    cycles = joint.get("rework_cycles", 0)
    if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 0:
        raise ValueError(
            "joint rework_cycles must be a non-negative integer, got %r" % (cycles,)
        )

    reasons = []
    calls = []

    if _at_most(angle, criteria["accept_wetting_angle_deg"]):
        calls.append(ACCEPT)
    elif _at_most(angle, criteria["rework_wetting_angle_deg"]):
        calls.append(REWORK)
        reasons.append(
            "wetting angle %.2f deg exceeds the %.2f deg accept angle in %s "
            "issue %s"
            % (
                angle,
                criteria["accept_wetting_angle_deg"],
                approved["reference"],
                approved["issue"],
            )
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "wetting angle %.2f deg exceeds the %.2f deg rework angle; the "
            "solder stood off the base metal rather than wetting it"
            % (angle, criteria["rework_wetting_angle_deg"])
        )

    if _at_least(coverage, criteria["accept_fillet_coverage_fraction"]):
        calls.append(ACCEPT)
    elif _at_least(coverage, criteria["rework_fillet_coverage_fraction"]):
        calls.append(REWORK)
        reasons.append(
            "fillet coverage %.3f is under the %.3f accept fraction"
            % (coverage, criteria["accept_fillet_coverage_fraction"])
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "fillet coverage %.3f is under the %.3f rework fraction; too little "
            "of the termination is joined to carry the string current"
            % (coverage, criteria["rework_fillet_coverage_fraction"])
        )

    if _at_most(voids, criteria["accept_void_area_fraction"]):
        calls.append(ACCEPT)
    elif _at_most(voids, criteria["rework_void_area_fraction"]):
        calls.append(REWORK)
        reasons.append(
            "void area fraction %.3f exceeds the %.3f accept fraction"
            % (voids, criteria["accept_void_area_fraction"])
        )
    else:
        calls.append(REJECT)
        reasons.append(
            "void area fraction %.3f exceeds the %.3f rework fraction"
            % (voids, criteria["rework_void_area_fraction"])
        )

    disposition = _worst(calls)
    blocking = [
        attribute for attribute in attributes if attribute in NOT_TOLERATED_ATTRIBUTES
    ]
    if blocking:
        disposition = REJECT
        reasons.append(
            "%s carries no acceptance figure in the agreed standard; the "
            "geometry does not reach it" % ", ".join(sorted(set(blocking)))
        )
    if disposition == REWORK and cycles >= criteria["max_rework_cycles"]:
        disposition = REJECT
        reasons.append(
            "the joint has already been reworked %d times against a limit of "
            "%d; another heat cycle is not available"
            % (cycles, criteria["max_rework_cycles"])
        )
    return {
        "id": joint.get("id"),
        "termination_type": termination,
        "workmanship_standard": "%s issue %s" % (approved["reference"], approved["issue"]),
        "wetting_angle_deg": angle,
        "fillet_coverage_fraction": coverage,
        "void_area_fraction": voids,
        "rework_cycles": cycles,
        "not_tolerated_attributes": sorted(set(blocking)),
        "disposition": disposition,
        "reasons": reasons,
    }


def group_joints_by_termination(joints):
    """Group the joints by the termination type they sit on."""
    if not isinstance(joints, (list, tuple)):
        raise ValueError("joints must be a list, got %r" % (joints,))
    counts = dict((termination, 0) for termination in TERMINATION_TYPES)
    for joint in joints:
        if not isinstance(joint, dict):
            raise ValueError("each joint must be a mapping, got %r" % (joint,))
        termination = _require_choice(
            "termination_type", joint.get("termination_type"), TERMINATION_TYPES
        )
        counts[termination] += 1
    return counts


def inspect_string_terminations(record, criteria=DEFAULT_SOLDER_CRITERIA):
    """Full clause 5.5.3.2.13 examination of one string's terminations."""
    validate_solder_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    string_id = record.get("string_id")
    if not isinstance(string_id, str) or not string_id.strip():
        raise ValueError("record needs a non-empty string_id for traceability")
    approved = validate_workmanship_agreement(
        record.get("workmanship_agreement"), record.get("inspection_date")
    )
    joints = record.get("joints")
    if not isinstance(joints, (list, tuple)):
        raise ValueError("record joints must be a list, got %r" % (joints,))

    seen = set()
    assessed = []
    for joint in joints:
        result = assess_solder_joint(
            joint, record.get("workmanship_agreement"), criteria
        )
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate joint id %r on string %s; traceability to the "
                    "rework record would be lost" % (marker, string_id)
                )
            seen.add(marker)
        assessed.append(result)

    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    findings = []
    if not assessed:
        findings.append(
            "no joints recorded against the string terminations; an empty "
            "survey is not an inspection and the string stays unverified"
        )
        verdict = REJECT
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    blocking_ids = [
        result["id"] for result in assessed if result["not_tolerated_attributes"]
    ]
    if blocking_ids:
        findings.append(
            "joints refused on attribute rather than geometry: %s"
            % ", ".join(str(marker) for marker in blocking_ids)
        )
    return {
        "string_id": string_id,
        "workmanship_standard": "%s issue %s"
        % (approved["reference"], approved["issue"]),
        "verdict": verdict,
        "joints": assessed,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "attribute_refused_ids": blocking_ids,
        "termination_counts": group_joints_by_termination(list(joints)),
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }
