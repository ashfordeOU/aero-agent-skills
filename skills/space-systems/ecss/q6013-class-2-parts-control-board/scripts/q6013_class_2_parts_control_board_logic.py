#!/usr/bin/env python3
"""The board reviewing commercial EEE part choices at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.1.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A commercial part enters a design at this class through a board that
reviews the choice and approves it, and the board is a constitution
before it is a meeting. A required voting role that is absent does not
make the board smaller; it makes every decision unattributable to the
discipline that was missing, which is a constitution finding rather than
a decision finding.

The intermediate class permits a decision to be taken by written
procedure as well as in session, and that permission is the whole reason
this module is not the class above with softer numbers. A circulated
decision is sound only where the circulation reached every voting member
and enough of them answered; a member cannot respond to a circulation
they never received, and a response share taken over the members who
happened to reply is a share of nothing.

Participation is computed against the voting membership either way.
Observers and invited specialists are useful and they do not make a
quorum, and votes cast cannot exceed the members who took part -- folding
a later concurrence into the count of a session that did not hear it is
the commonest defect in a reconstructed minute.

The decision is about a part in a usage, not about a part. The same
device approved for a benign bay is a different decision from that device
in a hot, radiation-exposed one, so a decision carrying no usage
reference has approved nothing anyone can check later.

Customer concurrence is not required at this class. Informing the
customer is, above a declared usage criticality, because that is where
the residual risk the customer carries stops being theoretical.

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
)

RECOGNISED_ROLES = REQUIRED_VOTING_ROLES + (
    CUSTOMER_REPRESENTATIVE_MEMBER,
    TECHNICAL_OBSERVER,
)

IN_SESSION = "in-session"
BY_WRITTEN_PROCEDURE = "by-written-procedure"
RECOGNISED_MODES = (IN_SESSION, BY_WRITTEN_PROCEDURE)

BOARD_NOT_CONSTITUTED = "parts-control-board-not-constituted"
DECISION_NOT_QUORATE = "parts-control-board-decision-not-quorate"
DECISION_RECORD_INCOMPLETE = "parts-control-board-decision-record-incomplete"
BOARD_APPROVALS_SOUND = "parts-control-board-approvals-sound"

PARTICIPATION_SHORT = "participation-below-the-applicable-floor"
APPROVAL_SHARE_SHORT = "approval-share-below-floor"
CIRCULATION_INCOMPLETE = "circulation-missed-a-voting-member"
MISSING_DATA_PACKAGE = "missing-data-package-reference"
MISSING_CUSTOMER_NOTIFICATION = "customer-not-informed-of-a-critical-usage"
RECORDED_AFTER_COMMITMENT = "recorded-after-procurement-commitment"

DEFAULT_BOARD_POLICY = {
    "quorum_fraction": 0.6,
    "written_response_fraction": 0.75,
    "min_approval_fraction": 0.6,
    "marginal_participation_band": 0.05,
    "marginal_approval_band": 0.05,
    "customer_notification_threshold": 0.7,
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


def _require_id_list(name, value, allowed):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of member identifiers" % name)
    named = []
    for item in value:
        label = _require_label("identifier in %s" % name, item)
        if not label:
            raise ValueError("a blank member identifier appears in %s" % name)
        if label not in allowed:
            raise ValueError(
                "%r in %s is not a declared board member" % (label, name)
            )
        if label in named:
            raise ValueError("%r is listed twice in %s" % (label, name))
        named.append(label)
    return tuple(named)


def validate_board_policy(policy):
    """Check the board policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    quorum = _require_fraction("quorum_fraction", policy.get("quorum_fraction"))
    if quorum <= 0.0:
        raise ValueError("quorum_fraction must be greater than zero, got %r" % (quorum,))
    response = _require_fraction(
        "written_response_fraction", policy.get("written_response_fraction")
    )
    if response <= 0.0:
        raise ValueError(
            "written_response_fraction must be greater than zero, got %r" % (response,)
        )
    if response < quorum:
        raise ValueError(
            "written_response_fraction %g is below the quorum_fraction %g; a "
            "circulated decision cannot be easier to carry than a session"
            % (response, quorum)
        )
    approval = _require_fraction(
        "min_approval_fraction", policy.get("min_approval_fraction")
    )
    if approval <= 0.0:
        raise ValueError(
            "min_approval_fraction must be greater than zero, got %r" % (approval,)
        )
    participation_band = _require_fraction(
        "marginal_participation_band", policy.get("marginal_participation_band")
    )
    if participation_band > quorum:
        raise ValueError(
            "marginal_participation_band %g is wider than the %g quorum; every "
            "quorate decision would be flagged marginal"
            % (participation_band, quorum)
        )
    approval_band = _require_fraction(
        "marginal_approval_band", policy.get("marginal_approval_band")
    )
    if approval_band > approval:
        raise ValueError(
            "marginal_approval_band %g is wider than the %g approval floor; "
            "every approval would be flagged marginal" % (approval_band, approval)
        )
    _require_fraction(
        "customer_notification_threshold",
        policy.get("customer_notification_threshold"),
    )
    return policy


def validate_member_record(member):
    """Read one declared board member, their role and their voting right."""
    if not isinstance(member, dict):
        raise ValueError("member must be a mapping, got %r" % (member,))
    identifier = _require_label("member id", member.get("id"))
    if not identifier:
        raise ValueError("member id must not be blank")
    role = _require_label("role on %s" % identifier, member.get("role"))
    if role not in RECOGNISED_ROLES:
        raise ValueError(
            "unrecognised role %r on %s; the role names are fixed"
            % (role, identifier)
        )
    voting = _require_flag("voting on %s" % identifier, member.get("voting"))
    if role == TECHNICAL_OBSERVER and voting:
        raise ValueError(
            "%s is an observer and cannot hold a vote" % identifier
        )
    return {"id": identifier, "role": role, "voting": voting}


def validate_members(members):
    """Read the whole declared board, refusing an empty or voteless one."""
    if not isinstance(members, (list, tuple)):
        raise ValueError("members must be a sequence of member records")
    if not members:
        raise ValueError("no board member was declared, so no board exists")
    checked = []
    seen = set()
    for member in members:
        record = validate_member_record(member)
        if record["id"] in seen:
            raise ValueError("duplicate member id %r on the board" % record["id"])
        seen.add(record["id"])
        checked.append(record)
    if not any(record["voting"] for record in checked):
        raise ValueError("the declared board holds no voting member")
    return tuple(checked)


def voting_members(members):
    """The identifiers of the declared members who hold a vote."""
    checked = validate_members(members)
    return tuple(record["id"] for record in checked if record["voting"])


def missing_voting_roles(members):
    """Required voting roles no voting member carries."""
    checked = validate_members(members)
    held = {record["role"] for record in checked if record["voting"]}
    return tuple(role for role in REQUIRED_VOTING_ROLES if role not in held)


def board_is_constituted(members):
    """True when every required voting role is carried by a voting member."""
    return not missing_voting_roles(members)


def validate_decision_record(decision, members):
    """Read one board decision against the declared membership."""
    if not isinstance(decision, dict):
        raise ValueError("decision must be a mapping, got %r" % (decision,))
    checked = validate_members(members)
    known = {record["id"] for record in checked}
    voting = set(voting_members(checked))

    identifier = _require_label("decision id", decision.get("id"))
    if not identifier:
        raise ValueError("decision id must not be blank")
    part = _require_label("part_reference on %s" % identifier, decision.get("part_reference"))
    if not part:
        raise ValueError("decision %s names no part" % identifier)
    usage = _require_label(
        "usage_reference on %s" % identifier, decision.get("usage_reference")
    )
    if not usage:
        raise ValueError(
            "decision %s names no usage; a part approved for nothing in "
            "particular cannot be checked against the next board" % identifier
        )
    mode = _require_label("mode on %s" % identifier, decision.get("mode"))
    if mode not in RECOGNISED_MODES:
        raise ValueError(
            "unrecognised decision mode %r on %s" % (mode, identifier)
        )

    present = _require_id_list(
        "members_present on %s" % identifier, decision.get("members_present", ()), known
    )
    circulated = _require_id_list(
        "circulated_to on %s" % identifier, decision.get("circulated_to", ()), known
    )
    responding = _require_id_list(
        "members_responding on %s" % identifier,
        decision.get("members_responding", ()),
        known,
    )

    if mode == IN_SESSION:
        if circulated or responding:
            raise ValueError(
                "decision %s was taken in session and also carries a "
                "circulation; it is one or the other" % identifier
            )
        participants = present
    else:
        if present:
            raise ValueError(
                "decision %s was taken by written procedure and also carries a "
                "list of members present" % identifier
            )
        outside = [who for who in responding if who not in circulated]
        if outside:
            raise ValueError(
                "%s responded to the circulation of %s without being on it"
                % (", ".join(outside), identifier)
            )
        participants = responding

    in_favour = _require_count("votes_in_favour on %s" % identifier, decision.get("votes_in_favour"))
    against = _require_count("votes_against on %s" % identifier, decision.get("votes_against"))
    abstentions = _require_count(
        "abstentions on %s" % identifier, decision.get("abstentions")
    )
    cast = in_favour + against + abstentions
    if cast == 0:
        raise ValueError("decision %s records no vote at all" % identifier)
    participating_voters = [who for who in participants if who in voting]
    if cast > len(participating_voters):
        raise ValueError(
            "decision %s records %d votes from %d participating voting members"
            % (identifier, cast, len(participating_voters))
        )

    package = _require_label(
        "data_package_reference on %s" % identifier,
        decision.get("data_package_reference", ""),
    )
    criticality = _require_fraction(
        "usage_criticality on %s" % identifier, decision.get("usage_criticality")
    )
    informed = _require_flag(
        "customer_informed on %s" % identifier, decision.get("customer_informed", False)
    )
    in_time = _require_flag(
        "recorded_before_procurement_commitment on %s" % identifier,
        decision.get("recorded_before_procurement_commitment", False),
    )

    return {
        "id": identifier,
        "part_reference": part,
        "usage_reference": usage,
        "mode": mode,
        "members_present": present,
        "circulated_to": circulated,
        "members_responding": responding,
        "participating_voting_members": tuple(participating_voters),
        "votes_in_favour": in_favour,
        "votes_against": against,
        "abstentions": abstentions,
        "votes_cast": cast,
        "data_package_reference": package,
        "usage_criticality": criticality,
        "customer_informed": informed,
        "recorded_before_procurement_commitment": in_time,
    }


def validate_decisions(decisions, members):
    """Read every decision, refusing an empty or duplicated set."""
    if not isinstance(decisions, (list, tuple)):
        raise ValueError("decisions must be a sequence of decision records")
    if not decisions:
        raise ValueError("the board records no decision, so nothing was approved")
    checked = []
    seen = set()
    for decision in decisions:
        record = validate_decision_record(decision, members)
        if record["id"] in seen:
            raise ValueError("duplicate decision id %r" % record["id"])
        seen.add(record["id"])
        checked.append(record)
    return tuple(checked)


def applicable_participation_floor(record, policy=DEFAULT_BOARD_POLICY):
    """The floor a decision has to clear, which depends on how it was taken."""
    validate_board_policy(policy)
    if record["mode"] == IN_SESSION:
        return float(policy["quorum_fraction"])
    return float(policy["written_response_fraction"])


def participation_share(record, members):
    """Participating voting members over the whole voting membership."""
    voters = voting_members(members)
    return len(record["participating_voting_members"]) / len(voters)


def approval_share(record):
    """Votes in favour over votes cast."""
    return record["votes_in_favour"] / record["votes_cast"]


def decision_defects(record, members, policy=DEFAULT_BOARD_POLICY):
    """Everything wrong with one decision, in a fixed order, all of it."""
    validate_board_policy(policy)
    voters = set(voting_members(members))
    defects = []

    share = participation_share(record, members)
    if not _at_least(share, applicable_participation_floor(record, policy)):
        defects.append(PARTICIPATION_SHORT)

    if record["mode"] == BY_WRITTEN_PROCEDURE:
        missed = [who for who in voters if who not in record["circulated_to"]]
        if missed:
            defects.append(CIRCULATION_INCOMPLETE)

    if PARTICIPATION_SHORT not in defects:
        if not _at_least(
            approval_share(record), float(policy["min_approval_fraction"])
        ):
            defects.append(APPROVAL_SHARE_SHORT)

    if not record["data_package_reference"]:
        defects.append(MISSING_DATA_PACKAGE)

    threshold = float(policy["customer_notification_threshold"])
    if _at_least(record["usage_criticality"], threshold) and not record[
        "customer_informed"
    ]:
        defects.append(MISSING_CUSTOMER_NOTIFICATION)

    if not record["recorded_before_procurement_commitment"]:
        defects.append(RECORDED_AFTER_COMMITMENT)

    return tuple(defects)


def approval_advisories(record, members, policy=DEFAULT_BOARD_POLICY):
    """Say when an approval was carried on a bare participation or majority.

    These do not move the verdict -- a decision above both floors is
    approved -- but an approval carried on exactly the floor will not
    survive one absence, and the next board cannot see that from the word
    approved.
    """
    validate_board_policy(policy)
    advisories = []
    share = participation_share(record, members)
    floor = applicable_participation_floor(record, policy)
    if _at_least(share, floor) and _at_most(
        share - floor, float(policy["marginal_participation_band"])
    ):
        advisories.append(
            "decision %s carried on a participation of %.3g against a floor of "
            "%.3g; one further absence and it would not have been taken"
            % (record["id"], share, floor)
        )
    approval_floor = float(policy["min_approval_fraction"])
    approved = approval_share(record)
    if _at_least(approved, approval_floor) and _at_most(
        approved - approval_floor, float(policy["marginal_approval_band"])
    ):
        advisories.append(
            "decision %s carried on an approval share of %.3g against a floor "
            "of %.3g; one vote the other way reverses it"
            % (record["id"], approved, approval_floor)
        )
    return tuple(advisories)


def weakest_approved_decision(records, members, policy=DEFAULT_BOARD_POLICY):
    """The sound decision carrying the least approval, or None when none is."""
    validate_board_policy(policy)
    weakest = None
    for record in records:
        if decision_defects(record, members, policy):
            continue
        share = approval_share(record)
        if weakest is None or share < weakest[1]:
            weakest = (record["id"], share)
    return weakest


def assess_parts_control_board(case, policy=DEFAULT_BOARD_POLICY):
    """Full clause 5.1.3 decision for one board and its recorded decisions."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_board_policy(policy)

    findings = []
    advisories = []
    result = {
        "voting_member_count": None,
        "missing_voting_roles": (),
        "decisions": (),
        "weakest_approved_decision": None,
        "findings": findings,
        "advisories": advisories,
    }

    members = case.get("members")
    if members is None:
        findings.append(
            "no parts control board is declared, so no body reviewed the "
            "commercial parts this design carries"
        )
        result["verdict"] = BOARD_NOT_CONSTITUTED
        return result

    checked_members = validate_members(members)
    result["voting_member_count"] = len(voting_members(checked_members))

    missing = missing_voting_roles(checked_members)
    result["missing_voting_roles"] = missing
    if missing:
        for role in missing:
            findings.append(
                "no voting member carries %s, so every decision is "
                "unattributable to that discipline" % role
            )
        result["verdict"] = BOARD_NOT_CONSTITUTED
        return result

    records = validate_decisions(case.get("decisions"), checked_members)
    reported = []
    inquorate = False
    incomplete = False
    for record in records:
        defects = decision_defects(record, checked_members, policy)
        share = participation_share(record, checked_members)
        entry = {
            "id": record["id"],
            "mode": record["mode"],
            "participation_share": share,
            "participation_floor": applicable_participation_floor(record, policy),
            "approval_share": approval_share(record),
            "defects": defects,
        }
        reported.append(entry)
        if PARTICIPATION_SHORT in defects:
            inquorate = True
            findings.append(
                "decision %s reached a participation of %.3g against a floor of "
                "%.3g, so it approved nothing"
                % (record["id"], share, entry["participation_floor"])
            )
        for defect in defects:
            if defect == PARTICIPATION_SHORT:
                continue
            incomplete = True
            findings.append("decision %s: %s" % (record["id"], defect))
        advisories.extend(approval_advisories(record, checked_members, policy))

    result["decisions"] = tuple(reported)
    result["weakest_approved_decision"] = weakest_approved_decision(
        records, checked_members, policy
    )

    if inquorate:
        result["verdict"] = DECISION_NOT_QUORATE
        return result
    if incomplete:
        result["verdict"] = DECISION_RECORD_INCOMPLETE
        return result

    result["verdict"] = BOARD_APPROVALS_SOUND
    return result
