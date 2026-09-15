#!/usr/bin/env python3
"""The board route a part has to clear before it may be used.

Anchor: ECSS-Q-ST-60C clause 4.1.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

At the highest reliability class an electronic part is not selected by
the engineer who wants it. It is put to a standing board whose seats
represent the disciplines that carry the consequences -- product
assurance in the chair, part engineering, the design authority,
procurement quality, reliability and radiation, and the customer -- and
the part may be used when that board has said so on the record.

Four things follow, and each is a way a board meeting produces a
decision nobody is bound by.

A board is constituted or it is not. Every required seat has a named
member and a vote weight before the first meeting; a seat that exists
only on the day it agrees with the proposer is not a seat.

Quorum is attendance plus the chair. A meeting that loses the chair
loses the authority the chair carries, however many members attended,
so the chair presence is tested separately from the attendance share.

The approval threshold is weighted, and an abstention is not a vote in
favour. The share is taken over the weight of every seat present, so
abstaining lowers the share exactly as much as it removes support,
which is what stops a thin room from waving a part through.

Depth of approval follows the part, not the meeting. A standard
qualified part needs the board. An upgraded part needs part engineering
and the reliability and radiation seat to concur with it. A part outside
the standard route needs the customer to concur as well, because the
customer carries what that part does in orbit.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PRODUCT_ASSURANCE_CHAIR = "product-assurance-chair"
PARTS_ENGINEERING_MEMBER = "parts-engineering-member"
DESIGN_AUTHORITY_MEMBER = "design-authority-member"
PROCUREMENT_QUALITY_MEMBER = "procurement-quality-member"
RELIABILITY_AND_RADIATION_MEMBER = "reliability-and-radiation-member"
CUSTOMER_REPRESENTATIVE = "customer-representative"

REQUIRED_BOARD_ROLES = (
    PRODUCT_ASSURANCE_CHAIR,
    PARTS_ENGINEERING_MEMBER,
    DESIGN_AUTHORITY_MEMBER,
    PROCUREMENT_QUALITY_MEMBER,
    RELIABILITY_AND_RADIATION_MEMBER,
    CUSTOMER_REPRESENTATIVE,
)

STANDARD_QUALIFIED_PART = "standard-qualified-part"
UPGRADED_PART = "upgraded-part"
NON_STANDARD_PART = "non-standard-part"

RECOGNISED_PART_CATEGORIES = (
    STANDARD_QUALIFIED_PART,
    UPGRADED_PART,
    NON_STANDARD_PART,
)

CONCURRENCE_ROUTE = {
    STANDARD_QUALIFIED_PART: (),
    UPGRADED_PART: (PARTS_ENGINEERING_MEMBER, RELIABILITY_AND_RADIATION_MEMBER),
    NON_STANDARD_PART: (
        PARTS_ENGINEERING_MEMBER,
        RELIABILITY_AND_RADIATION_MEMBER,
        CUSTOMER_REPRESENTATIVE,
    ),
}

VOTE_FOR = "for"
VOTE_AGAINST = "against"
VOTE_ABSTAIN = "abstain"
RECOGNISED_VOTES = (VOTE_FOR, VOTE_AGAINST, VOTE_ABSTAIN)

BOARD_NOT_CONSTITUTED = "parts-control-board-not-constituted"
BOARD_QUORUM_NOT_MET = "parts-control-board-quorum-not-met"
DECISION_NOT_RECORDED = "parts-control-board-decision-not-recorded"
CONCURRENCE_MISSING = "parts-control-board-concurrence-missing"
PART_USE_REFUSED = "parts-control-board-refuses-part-use"
PART_USE_APPROVED = "parts-control-board-approves-part-use"

DEFAULT_BOARD_POLICY = {
    "min_attendance_share": 0.6,
    "min_approval_vote_share": 0.75,
    "marginal_vote_band": 0.05,
    "require_chair_present": True,
    "require_decision_record": True,
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
    """Check the board convening and approval policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_attendance_share", policy.get("min_attendance_share"))
    threshold = _require_positive(
        "min_approval_vote_share", policy.get("min_approval_vote_share")
    )
    if threshold > 1.0:
        raise ValueError(
            "min_approval_vote_share %g is above one; no room could ever reach "
            "it and every part would be refused" % threshold
        )
    band = _require_fraction("marginal_vote_band", policy.get("marginal_vote_band"))
    if band > threshold:
        raise ValueError(
            "marginal_vote_band %g is wider than the %g approval threshold; "
            "every approval would be flagged marginal" % (band, threshold)
        )
    _require_flag("require_chair_present", policy.get("require_chair_present"))
    _require_flag("require_decision_record", policy.get("require_decision_record"))
    return policy


def validate_seat_record(seat):
    """Read one board seat, its member, vote weight and attendance."""
    if not isinstance(seat, dict):
        raise ValueError("seat must be a mapping, got %r" % (seat,))
    role = _require_label("role", seat.get("role"))
    if role not in REQUIRED_BOARD_ROLES:
        raise ValueError(
            "unrecognised board role %r; the board seats are fixed" % role
        )
    member = _require_label("member on %s" % role, seat.get("member"))
    if not member:
        raise ValueError(
            "the %s seat names no member, so the seat exists only on paper" % role
        )
    weight = _require_positive("vote_weight on %s" % role, seat.get("vote_weight"))
    present = _require_flag("present on %s" % role, seat.get("present"))
    return {"role": role, "member": member, "vote_weight": weight, "present": present}


def validate_seats(seats):
    """Read every seat, refusing a role seated twice."""
    if not isinstance(seats, (list, tuple)):
        raise ValueError("seats must be a sequence of seat records")
    checked = []
    seen = set()
    for seat in seats:
        record = validate_seat_record(seat)
        if record["role"] in seen:
            raise ValueError("board role %r is seated twice" % record["role"])
        seen.add(record["role"])
        checked.append(record)
    return tuple(checked)


def seat_index(seats):
    """Map each seated role to its record."""
    return {record["role"]: record for record in validate_seats(seats)}


def unseated_roles(seats):
    """Required board roles that carry no seat at all."""
    index = seat_index(seats)
    return tuple(role for role in REQUIRED_BOARD_ROLES if role not in index)


def absent_roles(seats):
    """Seated roles whose member did not attend."""
    index = seat_index(seats)
    return tuple(
        role
        for role in REQUIRED_BOARD_ROLES
        if role in index and not index[role]["present"]
    )


def attendance_share(seats):
    """Share of the required board roles present at the meeting."""
    index = seat_index(seats)
    present = sum(
        1
        for role in REQUIRED_BOARD_ROLES
        if role in index and index[role]["present"]
    )
    return present / len(REQUIRED_BOARD_ROLES)


def present_vote_weight(seats):
    """Total vote weight in the room."""
    index = seat_index(seats)
    return sum(
        index[role]["vote_weight"]
        for role in REQUIRED_BOARD_ROLES
        if role in index and index[role]["present"]
    )


def chair_is_present(seats):
    """True when the product assurance chair attended."""
    index = seat_index(seats)
    record = index.get(PRODUCT_ASSURANCE_CHAIR)
    return bool(record is not None and record["present"])


def quorum_is_met(seats, policy=DEFAULT_BOARD_POLICY):
    """True when attendance reaches its share and the chair is in the room.

    An attendance share landing exactly on the declared minimum is
    quorate; the comparison tolerance absorbs representation error rather
    than lowering the minimum.
    """
    validate_board_policy(policy)
    if policy["require_chair_present"] and not chair_is_present(seats):
        return False
    return _at_least(
        attendance_share(seats), float(policy["min_attendance_share"])
    )


def validate_votes(votes, seats):
    """Read the votes cast, one per present seat and none from an empty chair."""
    if not isinstance(votes, dict):
        raise ValueError("votes must be a mapping of role to cast vote")
    index = seat_index(seats)
    checked = {}
    for role, vote in votes.items():
        name = _require_label("vote role", role)
        if name not in REQUIRED_BOARD_ROLES:
            raise ValueError("unrecognised board role %r in the votes" % name)
        record = index.get(name)
        if record is None:
            raise ValueError("a vote is recorded for the unseated role %r" % name)
        if not record["present"]:
            raise ValueError(
                "a vote is recorded for %r, whose member did not attend" % name
            )
        cast = _require_label("vote on %s" % name, vote)
        if cast not in RECOGNISED_VOTES:
            raise ValueError(
                "unrecognised vote %r on %s; a seat votes for, against or "
                "abstains" % (cast, name)
            )
        checked[name] = cast
    for role in REQUIRED_BOARD_ROLES:
        record = index.get(role)
        if record is not None and record["present"] and role not in checked:
            raise ValueError(
                "the %s seat attended and cast no vote, so the record is "
                "incomplete" % role
            )
    return checked


def approval_vote_share(votes, seats):
    """Weighted share of the room voting in favour.

    The denominator is the weight of every seat present, so an abstention
    lowers the share exactly as much as it withholds support. An empty
    room carries no support at all and returns zero.
    """
    checked = validate_votes(votes, seats)
    index = seat_index(seats)
    total = present_vote_weight(seats)
    if total <= 0.0:
        return 0.0
    favour = sum(
        index[role]["vote_weight"]
        for role, cast in checked.items()
        if cast == VOTE_FOR
    )
    return favour / total


def dissenting_roles(votes, seats):
    """Seats that voted against, in board order."""
    checked = validate_votes(votes, seats)
    return tuple(
        role for role in REQUIRED_BOARD_ROLES if checked.get(role) == VOTE_AGAINST
    )


def abstaining_roles(votes, seats):
    """Seats that attended and withheld support, in board order."""
    checked = validate_votes(votes, seats)
    return tuple(
        role for role in REQUIRED_BOARD_ROLES if checked.get(role) == VOTE_ABSTAIN
    )


def required_concurrences(category):
    """Roles whose explicit support the part category depends on."""
    name = _require_label("category", category)
    if name not in RECOGNISED_PART_CATEGORIES:
        raise ValueError(
            "unrecognised part category %r; the categories are fixed" % name
        )
    return CONCURRENCE_ROUTE[name]


def missing_concurrences(category, votes, seats):
    """Roles the category depends on that did not attend or did not support."""
    checked = validate_votes(votes, seats)
    missing = []
    for role in required_concurrences(category):
        if checked.get(role) != VOTE_FOR:
            missing.append(role)
    return tuple(missing)


def validate_part_request(request):
    """Read the part put to the board and how the meeting recorded it."""
    if not isinstance(request, dict):
        raise ValueError("part request must be a mapping, got %r" % (request,))
    reference = _require_label("part_reference", request.get("part_reference"))
    if not reference:
        raise ValueError(
            "the request names no part, so no board decision can attach to it"
        )
    category = _require_label("category", request.get("category"))
    if category not in RECOGNISED_PART_CATEGORIES:
        raise ValueError(
            "unrecognised part category %r; the categories are fixed" % category
        )
    decision = _require_label(
        "decision_reference", request.get("decision_reference", "")
    )
    dissent_recorded = _require_flag(
        "dissent_recorded", request.get("dissent_recorded")
    )
    votes = request.get("votes")
    if votes is None:
        raise ValueError("the request carries no votes mapping")
    return {
        "part_reference": reference,
        "category": category,
        "decision_reference": decision,
        "dissent_recorded": dissent_recorded,
        "votes": votes,
    }


def marginal_vote_advisory(votes, seats, policy=DEFAULT_BOARD_POLICY):
    """Say so when an approval clears its threshold by less than the band.

    This does not move the verdict -- an approval is an approval -- but a
    part carried by one weighted vote will not carry again if a seat is
    replaced, and that is worth saying once here rather than
    rediscovering it at the next board.
    """
    validate_board_policy(policy)
    share = approval_vote_share(votes, seats)
    threshold = float(policy["min_approval_vote_share"])
    band = float(policy["marginal_vote_band"])
    if not _at_least(share, threshold):
        return ()
    if not _at_most(share - threshold, band):
        return ()
    return (
        "the board carried the part on %.3g per cent of the weight present "
        "against a %.3g per cent threshold, inside the %.3g per cent marginal "
        "band; it carries today and would not carry with one seat changed"
        % (share * 100.0, threshold * 100.0, band * 100.0),
    )


def assess_parts_control_board(case, policy=DEFAULT_BOARD_POLICY):
    """Full clause 4.1.3 board route decision for one part request."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_board_policy(policy)

    findings = []
    advisories = []
    result = {
        "board_reference": None,
        "part_reference": None,
        "category": None,
        "attendance_share": None,
        "approval_vote_share": None,
        "unseated_roles": (),
        "absent_roles": (),
        "dissenting_roles": (),
        "abstaining_roles": (),
        "missing_concurrences": (),
        "findings": findings,
        "advisories": advisories,
    }

    board = case.get("board")
    if board is None:
        findings.append(
            "no parts control board is declared, so the part would be selected "
            "by whoever wants to use it"
        )
        result["verdict"] = BOARD_NOT_CONSTITUTED
        return result
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping, got %r" % (board,))

    board_reference = _require_label("board_reference", board.get("board_reference"))
    result["board_reference"] = board_reference
    seats = board.get("seats")
    if seats is None:
        raise ValueError("the board declares no seats sequence")
    checked_seats = validate_seats(seats)

    unseated = unseated_roles(checked_seats)
    result["unseated_roles"] = unseated
    if not board_reference or unseated:
        for role in unseated:
            findings.append("the board has no %s seat" % role)
        if not board_reference:
            findings.append(
                "the board carries no reference, so no reviewer can say which "
                "body took the decision"
            )
        result["verdict"] = BOARD_NOT_CONSTITUTED
        return result

    request = case.get("part_request")
    if request is None:
        raise ValueError("the case puts no part request to the board")
    checked_request = validate_part_request(request)
    result["part_reference"] = checked_request["part_reference"]
    result["category"] = checked_request["category"]

    attendance = attendance_share(checked_seats)
    result["attendance_share"] = attendance
    result["absent_roles"] = absent_roles(checked_seats)

    if not quorum_is_met(checked_seats, policy):
        if policy["require_chair_present"] and not chair_is_present(checked_seats):
            findings.append(
                "the chair did not attend, so the meeting carried none of the "
                "authority the chair holds"
            )
        findings.append(
            "attendance is %.3g per cent of the board against the %.3g per "
            "cent a quorum needs"
            % (
                attendance * 100.0,
                float(policy["min_attendance_share"]) * 100.0,
            )
        )
        result["verdict"] = BOARD_QUORUM_NOT_MET
        return result

    votes = checked_request["votes"]
    share = approval_vote_share(votes, checked_seats)
    dissent = dissenting_roles(votes, checked_seats)
    abstained = abstaining_roles(votes, checked_seats)
    result["approval_vote_share"] = share
    result["dissenting_roles"] = dissent
    result["abstaining_roles"] = abstained

    if policy["require_decision_record"]:
        if not checked_request["decision_reference"]:
            findings.append(
                "the meeting produced no decision reference, so the part has "
                "no board decision to be used under"
            )
            result["verdict"] = DECISION_NOT_RECORDED
            return result
        if dissent and not checked_request["dissent_recorded"]:
            findings.append(
                "%d seat(s) voted against and the dissent was not recorded, so "
                "the minute does not say what the board actually decided"
                % len(dissent)
            )
            result["verdict"] = DECISION_NOT_RECORDED
            return result

    missing = missing_concurrences(
        checked_request["category"], votes, checked_seats
    )
    result["missing_concurrences"] = missing
    if missing:
        for role in missing:
            findings.append(
                "a %s part depends on the %s seat concurring, and it did not"
                % (checked_request["category"], role)
            )
        result["verdict"] = CONCURRENCE_MISSING
        return result

    if not _at_least(share, float(policy["min_approval_vote_share"])):
        findings.append(
            "the board carried %.3g per cent of the weight present against a "
            "%.3g per cent threshold, so the part is not approved for use"
            % (
                share * 100.0,
                float(policy["min_approval_vote_share"]) * 100.0,
            )
        )
        result["verdict"] = PART_USE_REFUSED
        return result

    advisories.extend(marginal_vote_advisory(votes, checked_seats, policy))
    result["verdict"] = PART_USE_APPROVED
    return result
