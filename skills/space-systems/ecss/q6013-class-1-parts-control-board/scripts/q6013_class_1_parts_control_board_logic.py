#!/usr/bin/env python3
"""The board approving commercial EEE part selection and usage.

Anchor: ECSS-Q-ST-60-13C clause 4.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

At the highest assurance class a commercial part enters a design through
a board, and the board is a constitution before it is a meeting. Four
things follow from that, and each is a way a minute reads sound and
proves nothing.

A required voting role that is absent does not make the board smaller.
It makes every decision unattributable to the discipline that was
missing, so a missing role closes the assessment rather than reducing
the quorum.

Attendance is computed against the voting membership, not against
whoever appeared. Observers and invited specialists are useful and they
do not make a quorum, and votes cast cannot exceed the voting members
present -- folding a later written concurrence into the count of a
meeting that did not hear it is the commonest defect in a reconstructed
minute.

The decision is about a part in a usage. The same device approved for a
benign bay is a different decision from that device in a hot,
radiation-exposed one, so a decision carrying no usage reference has
approved nothing anyone can check later.

The record has to be reconstructable: a submitted data package, customer
concurrence at this class, and a record raised before the procurement
commitment, because an approval minuted after the order describes a
decision the purchase had already taken.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BOARD_CHAIR = "board-chair"
COMPONENT_ENGINEERING_MEMBER = "component-engineering-member"
DESIGN_AUTHORITY_MEMBER = "design-authority-member"
PRODUCT_ASSURANCE_MEMBER = "product-assurance-member"
CUSTOMER_REPRESENTATIVE_MEMBER = "customer-representative-member"
TECHNICAL_OBSERVER = "technical-observer"

REQUIRED_VOTING_ROLES = (
    BOARD_CHAIR,
    COMPONENT_ENGINEERING_MEMBER,
    DESIGN_AUTHORITY_MEMBER,
    PRODUCT_ASSURANCE_MEMBER,
    CUSTOMER_REPRESENTATIVE_MEMBER,
)

RECOGNISED_ROLES = REQUIRED_VOTING_ROLES + (TECHNICAL_OBSERVER,)

BOARD_NOT_CONSTITUTED = "parts-control-board-not-constituted"
DECISION_NOT_QUORATE = "parts-control-board-decision-not-quorate"
DECISION_RECORD_INCOMPLETE = "parts-control-board-decision-record-incomplete"
BOARD_APPROVALS_SOUND = "parts-control-board-approvals-sound"

MISSING_DATA_PACKAGE = "missing-data-package-reference"
MISSING_CUSTOMER_CONCURRENCE = "missing-customer-concurrence"
RECORDED_AFTER_COMMITMENT = "recorded-after-procurement-commitment"
APPROVAL_SHARE_SHORT = "approval-share-below-floor"

DEFAULT_BOARD_POLICY = {
    "quorum_fraction": 0.75,
    "min_approval_fraction": 0.6,
    "marginal_approval_band": 0.05,
    "require_customer_concurrence": True,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


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


def validate_board_policy(policy):
    """Check the board policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    quorum = _require_positive("quorum_fraction", policy.get("quorum_fraction"))
    if quorum > 1.0:
        raise ValueError(
            "quorum_fraction %g is above one; no meeting can seat more voting "
            "members than the board has" % quorum
        )
    approval = _require_positive(
        "min_approval_fraction", policy.get("min_approval_fraction")
    )
    if approval > 1.0:
        raise ValueError("min_approval_fraction %g is above one" % approval)
    band = _require_fraction(
        "marginal_approval_band", policy.get("marginal_approval_band")
    )
    if band > approval:
        raise ValueError(
            "marginal_approval_band %g is wider than the %g approval floor; "
            "every approval would be flagged marginal" % (band, approval)
        )
    _require_flag(
        "require_customer_concurrence", policy.get("require_customer_concurrence")
    )
    return policy


def validate_member_record(member):
    """Read one declared board member, the role held and the voting right."""
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping, got %r" % (member,))
    identifier = _require_label("member id", member.get("id"))
    if not identifier:
        raise ValueError("member id must not be blank")
    role = _require_label("role on %s" % identifier, member.get("role"))
    if role not in RECOGNISED_ROLES:
        raise ValueError(
            "unrecognised board role %r on %s; the role names are fixed"
            % (role, identifier)
        )
    voting = _require_flag("voting on %s" % identifier, member.get("voting"))
    return {"id": identifier, "role": role, "voting": voting}


def validate_membership(members):
    """Read the whole declared membership, refusing an empty or voteless board."""
    if not isinstance(members, (list, tuple)):
        raise ValueError("members must be a sequence of member records")
    if not members:
        raise ValueError("no board member was declared, so no board sits")
    checked = []
    seen = set()
    for member in members:
        record = validate_member_record(member)
        if record["id"] in seen:
            raise ValueError("duplicate member id %r on the board" % record["id"])
        seen.add(record["id"])
        checked.append(record)
    if not any(record["voting"] for record in checked):
        raise ValueError("the board has no voting member, so it can decide nothing")
    return tuple(checked)


def voting_members(members):
    """The declared members who carry a vote."""
    return tuple(record for record in validate_membership(members) if record["voting"])


def missing_voting_roles(members):
    """Required voting roles no declared voting member holds."""
    held = {record["role"] for record in voting_members(members)}
    return tuple(role for role in REQUIRED_VOTING_ROLES if role not in held)


def board_is_constituted(members):
    """True when every required voting role is held by a voting member."""
    return not missing_voting_roles(members)


def validate_decision_record(decision, members):
    """Read one part decision against the declared membership."""
    checked_members = validate_membership(members)
    known = {record["id"]: record for record in checked_members}
    if not isinstance(decision, dict):
        raise ValueError("decision must be a mapping, got %r" % (decision,))
    identifier = _require_label("decision id", decision.get("id"))
    if not identifier:
        raise ValueError("decision id must not be blank")
    part = _require_label("part_reference on %s" % identifier, decision.get("part_reference"))
    usage = _require_label("usage_reference on %s" % identifier, decision.get("usage_reference"))
    if not part:
        raise ValueError("decision %s names no part" % identifier)
    if not usage:
        raise ValueError(
            "decision %s names no usage; the same device in another bay is "
            "another decision" % identifier
        )
    present = decision.get("members_present")
    if not isinstance(present, (list, tuple)):
        raise ValueError(
            "members_present on %s must be a sequence of member ids" % identifier
        )
    attendees = []
    for entry in present:
        label = _require_label("attendee on %s" % identifier, entry)
        if label not in known:
            raise ValueError(
                "attendee %r on %s is not a declared board member" % (label, identifier)
            )
        if label in attendees:
            raise ValueError("attendee %r is listed twice on %s" % (label, identifier))
        attendees.append(label)
    votes_for = _require_count("votes_for on %s" % identifier, decision.get("votes_for"))
    votes_against = _require_count(
        "votes_against on %s" % identifier, decision.get("votes_against")
    )
    present_voters = sum(1 for label in attendees if known[label]["voting"])
    if votes_for + votes_against > present_voters:
        raise ValueError(
            "decision %s records %d votes against %d voting members present; a "
            "concurrence collected later is a separate record"
            % (identifier, votes_for + votes_against, present_voters)
        )
    package = _require_label(
        "data_package_reference on %s" % identifier,
        decision.get("data_package_reference", ""),
    )
    concurrence = _require_flag(
        "customer_concurrence on %s" % identifier, decision.get("customer_concurrence")
    )
    before = _require_flag(
        "recorded_before_commitment on %s" % identifier,
        decision.get("recorded_before_commitment"),
    )
    return {
        "id": identifier,
        "part_reference": part,
        "usage_reference": usage,
        "members_present": tuple(attendees),
        "present_voting_members": present_voters,
        "votes_for": votes_for,
        "votes_against": votes_against,
        "data_package_reference": package,
        "customer_concurrence": concurrence,
        "recorded_before_commitment": before,
    }


def attendance_fraction(decision, members):
    """Share of the voting membership present for one decision."""
    checked = validate_decision_record(decision, members)
    seated = len(voting_members(members))
    return checked["present_voting_members"] / seated


def decision_is_quorate(decision, members, policy=DEFAULT_BOARD_POLICY):
    """True when the attendance share reaches the declared quorum."""
    validate_board_policy(policy)
    return _at_least(
        attendance_fraction(decision, members), float(policy["quorum_fraction"])
    )


def approval_fraction(decision, members):
    """Share of the votes cast that were in favour, zero when none were cast."""
    checked = validate_decision_record(decision, members)
    cast = checked["votes_for"] + checked["votes_against"]
    if cast == 0:
        return 0.0
    return checked["votes_for"] / cast


def decision_record_shortfalls(decision, members, policy=DEFAULT_BOARD_POLICY):
    """Name everything a decision record is missing, not only the first thing."""
    validate_board_policy(policy)
    checked = validate_decision_record(decision, members)
    shortfalls = []
    if not _at_least(
        approval_fraction(decision, members), float(policy["min_approval_fraction"])
    ):
        shortfalls.append(APPROVAL_SHARE_SHORT)
    if not checked["data_package_reference"]:
        shortfalls.append(MISSING_DATA_PACKAGE)
    if policy["require_customer_concurrence"] and not checked["customer_concurrence"]:
        shortfalls.append(MISSING_CUSTOMER_CONCURRENCE)
    if not checked["recorded_before_commitment"]:
        shortfalls.append(RECORDED_AFTER_COMMITMENT)
    return tuple(shortfalls)


def decision_verdicts(decisions, members, policy=DEFAULT_BOARD_POLICY):
    """Judge every decision in record order, refusing a duplicate identifier."""
    validate_board_policy(policy)
    if not isinstance(decisions, (list, tuple)):
        raise ValueError("decisions must be a sequence of decision records")
    if not decisions:
        raise ValueError("the board recorded no decision, so there is nothing to judge")
    verdicts = []
    seen = set()
    for decision in decisions:
        checked = validate_decision_record(decision, members)
        if checked["id"] in seen:
            raise ValueError("duplicate decision id %r in the minutes" % checked["id"])
        seen.add(checked["id"])
        quorate = decision_is_quorate(decision, members, policy)
        shortfalls = decision_record_shortfalls(decision, members, policy) if quorate else ()
        verdicts.append(
            {
                "id": checked["id"],
                "part_reference": checked["part_reference"],
                "usage_reference": checked["usage_reference"],
                "attendance_fraction": attendance_fraction(decision, members),
                "approval_fraction": approval_fraction(decision, members),
                "quorate": quorate,
                "shortfalls": shortfalls,
                "sound": quorate and not shortfalls,
            }
        )
    return tuple(verdicts)


def record_completeness(verdicts):
    """Share of the judged decisions that are quorate and completely recorded."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    sound = sum(1 for verdict in verdicts if verdict["sound"])
    return sound / len(verdicts)


def weakest_sound_decision(verdicts):
    """The soundly recorded decision carried on the smallest approval share."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    sound = [verdict for verdict in verdicts if verdict["sound"]]
    if not sound:
        return None
    return min(sound, key=lambda verdict: verdict["approval_fraction"])


def bare_quorum_advisories(verdicts, policy=DEFAULT_BOARD_POLICY):
    """Name sound decisions carried on an approval share inside the band.

    These do not move the verdict -- a sound decision is sound -- but an
    approval standing on the floor will not stand again after one absence,
    and that is worth saying once here rather than rediscovering it when
    the part is quoted to the next board.
    """
    validate_board_policy(policy)
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    floor = float(policy["min_approval_fraction"])
    band = float(policy["marginal_approval_band"])
    advisories = []
    for verdict in verdicts:
        if not verdict["sound"]:
            continue
        if _at_most(verdict["approval_fraction"] - floor, band):
            advisories.append(
                "decision %s on %s carries an approval share of %.3g per cent "
                "against a %.3g per cent floor, inside the %.3g per cent "
                "marginal band; it stands today and would not stand after one "
                "absence"
                % (
                    verdict["id"],
                    verdict["part_reference"],
                    verdict["approval_fraction"] * 100.0,
                    floor * 100.0,
                    band * 100.0,
                )
            )
    return tuple(advisories)


def assess_parts_control_board(case, policy=DEFAULT_BOARD_POLICY):
    """Full clause 4.1.3 decision for one parts control board and its minutes."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_board_policy(policy)

    findings = []
    advisories = []
    result = {
        "voting_member_count": None,
        "missing_voting_roles": (),
        "decision_verdicts": (),
        "record_completeness": None,
        "weakest_sound_decision_id": None,
        "weakest_sound_approval_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    members = case.get("members")
    if members is None:
        findings.append(
            "no parts control board is declared, so no body may approve a "
            "commercial part for a usage"
        )
        result["verdict"] = BOARD_NOT_CONSTITUTED
        return result

    seated = voting_members(members)
    result["voting_member_count"] = len(seated)
    missing = missing_voting_roles(members)
    result["missing_voting_roles"] = missing
    if missing:
        for role in missing:
            findings.append(
                "no voting member holds %s, so every decision is unattributable "
                "to that discipline" % role
            )
        result["verdict"] = BOARD_NOT_CONSTITUTED
        return result

    verdicts = decision_verdicts(case.get("decisions"), members, policy)
    result["decision_verdicts"] = verdicts
    result["record_completeness"] = record_completeness(verdicts)

    weakest = weakest_sound_decision(verdicts)
    if weakest is not None:
        result["weakest_sound_decision_id"] = weakest["id"]
        result["weakest_sound_approval_fraction"] = weakest["approval_fraction"]

    inquorate = tuple(verdict for verdict in verdicts if not verdict["quorate"])
    for verdict in inquorate:
        findings.append(
            "decision %s on %s was taken with %.3g per cent of the voting "
            "membership present against a %.3g per cent quorum"
            % (
                verdict["id"],
                verdict["part_reference"],
                verdict["attendance_fraction"] * 100.0,
                float(policy["quorum_fraction"]) * 100.0,
            )
        )
    advisories.extend(bare_quorum_advisories(verdicts, policy))

    if inquorate:
        result["verdict"] = DECISION_NOT_QUORATE
        return result

    incomplete = tuple(verdict for verdict in verdicts if verdict["shortfalls"])
    for verdict in incomplete:
        findings.append(
            "decision %s on %s in usage %s is short of %s"
            % (
                verdict["id"],
                verdict["part_reference"],
                verdict["usage_reference"],
                " and ".join(verdict["shortfalls"]),
            )
        )
    if incomplete:
        result["verdict"] = DECISION_RECORD_INCOMPLETE
        return result

    result["verdict"] = BOARD_APPROVALS_SOUND
    return result
