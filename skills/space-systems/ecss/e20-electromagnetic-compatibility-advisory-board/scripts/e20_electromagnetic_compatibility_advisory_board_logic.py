#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.2.3 electromagnetic compatibility advisory
board (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard expects a project to stand up an
advisory body that oversees the electromagnetic compatibility
decisions taken across the electrical architecture, and expects that
body's role and composition to be written down rather than left to
custom. This module implements the checkable part of that clause:
categorization of a nominated seat as core, contributing or observer,
the mandatory core-role list a constituted board has to fill,
representation of every electromagnetically relevant subsystem, the
voting membership and the quorum a sitting needs, and the disposition
of an agenda item as endorsed, rejected, deferred or escalated for
customer approval. It does not run an electromagnetic analysis, does
not set emission or susceptibility limits, and does not replace the
project configuration control board.
"""

import math

CORE_BOARD_ROLES = frozenset(
    {
        "chairperson",
        "system_engineering_representative",
        "customer_representative",
        "product_assurance_representative",
        "grounding_and_bonding_authority",
    }
)
CONTRIBUTING_BOARD_ROLES = frozenset(
    {
        "subsystem_emc_representative",
        "payload_emc_representative",
        "harness_design_representative",
        "launch_authority_representative",
    }
)
OBSERVER_BOARD_ROLES = frozenset(
    {
        "supplier_observer",
        "test_facility_observer",
        "secretariat",
    }
)

# Agenda item kind -> the class of decision it carries. The class, not
# the kind, decides whether the board may close the item itself.
IN_REMIT_AGENDA_ITEMS = {
    "emission_limit_tailoring": "requirement",
    "susceptibility_limit_tailoring": "requirement",
    "grounding_architecture_change": "architecture",
    "bonding_scheme_change": "architecture",
    "interference_margin_deviation": "deviation",
    "emc_nonconformance_disposition": "deviation",
    "emc_verification_plan_endorsement": "verification",
    "interference_critical_point_list_review": "verification",
}
OUT_OF_REMIT_AGENDA_ITEMS = frozenset(
    {
        "thermal_control_budget",
        "propellant_budget",
        "structural_load_case",
        "software_release_note",
    }
)

# A requirement change or a deviation leaves the project's agreed
# baseline, so the board recommends and the customer approves.
CUSTOMER_APPROVAL_ITEM_CLASSES = frozenset({"requirement", "deviation"})

DEFAULT_QUORUM_FRACTION = 0.6
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _ceil_with_tolerance(value):
    """Smallest integer not below value, absorbing binary floating
    point representation error.

    A quorum is a fraction of a head count, and a product such as
    0.56 * 25 evaluates to 14.000000000000002 rather than 14. A bare
    ceiling would demand a fifteenth seat that the stated requirement
    never asked for, so a product within tolerance of an integer is
    treated as that integer. The requirement itself is untouched.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number, got %r" % (value,))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("value must be finite, got %r" % (value,))
    nearest = round(value)
    if math.isclose(value, nearest, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return int(nearest)
    return int(math.ceil(value))


def categorize_board_role(role):
    """Seat category for a nominated board role: "core" (the seats the
    board cannot sit without), "contributing" (a technical seat that
    votes on the items touching its scope) or "observer" (attends, does
    not vote). Raises ValueError for a role that clause 6.2.3 does not
    place on the board."""
    if role in CORE_BOARD_ROLES:
        return "core"
    if role in CONTRIBUTING_BOARD_ROLES:
        return "contributing"
    if role in OBSERVER_BOARD_ROLES:
        return "observer"
    raise ValueError(
        "unrecognized advisory board role %r under "
        "E-ST-20C clause 6.2.3" % (role,)
    )


def validate_member(member):
    """Normalized member record: member_id, role, seat category,
    appointed flag and the subsystems the seat speaks for. Raises
    ValueError for a record that is not a mapping, carries an empty or
    non-string member_id, omits the role, marks appointed with a
    non-boolean, or lists a subsystem that is not a non-empty
    string."""
    if not isinstance(member, dict):
        raise ValueError("member record must be a mapping, got %r" % (member,))
    member_id = member.get("member_id")
    if not isinstance(member_id, str) or not member_id.strip():
        raise ValueError("member_id must be a non-empty string, got %r" % (member_id,))
    if "role" not in member:
        raise ValueError("member %s carries no role" % member_id)
    seat = categorize_board_role(member["role"])
    appointed = member.get("appointed", True)
    if not isinstance(appointed, bool):
        raise ValueError(
            "member %s: appointed must be a boolean, got %r" % (member_id, appointed)
        )
    raw_subsystems = member.get("subsystems", ())
    if isinstance(raw_subsystems, str) or not isinstance(raw_subsystems, (list, tuple)):
        raise ValueError(
            "member %s: subsystems must be a list or tuple of names" % member_id
        )
    subsystems = []
    for name in raw_subsystems:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "member %s: subsystem name must be a non-empty string, got %r"
                % (member_id, name)
            )
        subsystems.append(name)
    return {
        "member_id": member_id,
        "role": member["role"],
        "seat": seat,
        "appointed": appointed,
        "subsystems": tuple(sorted(subsystems)),
    }


def validate_membership(members):
    """Tuple of normalized member records. Raises ValueError when the
    membership is not a list or tuple, is empty, or repeats a
    member_id."""
    if isinstance(members, dict) or not isinstance(members, (list, tuple)):
        raise ValueError("members must be a list or tuple of member records")
    if not members:
        raise ValueError("the advisory board has no nominated members")
    normalized = []
    seen = set()
    for member in members:
        record = validate_member(member)
        if record["member_id"] in seen:
            raise ValueError("duplicate member_id %r on the board" % record["member_id"])
        seen.add(record["member_id"])
        normalized.append(record)
    return tuple(normalized)


def voting_member_ids(members):
    """Sorted tuple of the member ids that carry a vote: an appointed
    core or contributing seat. An observer never votes and an
    un-appointed nominee does not count towards the head count."""
    records = validate_membership(members)
    return tuple(
        sorted(
            record["member_id"]
            for record in records
            if record["appointed"] and record["seat"] in ("core", "contributing")
        )
    )


def missing_core_roles(members):
    """Sorted list of the core roles no appointed member fills. A
    board missing a core seat is not constituted, whatever its head
    count."""
    records = validate_membership(members)
    filled = {record["role"] for record in records if record["appointed"]}
    return sorted(CORE_BOARD_ROLES - filled)


def quorum_requirement(members, quorum_fraction=DEFAULT_QUORUM_FRACTION):
    """Number of voting members a sitting needs, the stated fraction of
    the voting membership rounded up, never below one. Raises
    ValueError for a fraction outside the half-open interval above zero
    up to one, or for a board with no voting member."""
    if isinstance(quorum_fraction, bool) or not isinstance(
        quorum_fraction, (int, float)
    ):
        raise ValueError("quorum_fraction must be a real number")
    if not 0.0 < quorum_fraction <= 1.0:
        raise ValueError(
            "quorum_fraction must be greater than 0 and at most 1, got %r"
            % (quorum_fraction,)
        )
    voting = voting_member_ids(members)
    if not voting:
        raise ValueError("the advisory board has no appointed voting member")
    return max(1, _ceil_with_tolerance(quorum_fraction * len(voting)))


def quorum_state(members, present_member_ids, quorum_fraction=DEFAULT_QUORUM_FRACTION):
    """Quorum picture for one sitting: the voting membership, the
    voting members present, the number required, whether the chair is
    in the room and whether the sitting is quorate. The chair must be
    present: the board advises with one voice and an unchaired sitting
    cannot issue that voice. Raises ValueError when an attendee is not
    on the board."""
    records = validate_membership(members)
    if isinstance(present_member_ids, str) or not isinstance(
        present_member_ids, (list, tuple, set, frozenset)
    ):
        raise ValueError("present_member_ids must be a collection of member ids")
    known = {record["member_id"]: record for record in records}
    present = set()
    for member_id in present_member_ids:
        if member_id not in known:
            raise ValueError("attendee %r is not a member of the board" % (member_id,))
        present.add(member_id)
    voting = set(voting_member_ids(members))
    present_voting = sorted(present & voting)
    required = quorum_requirement(members, quorum_fraction)
    chair_present = any(
        known[member_id]["role"] == "chairperson" and known[member_id]["appointed"]
        for member_id in present
    )
    return {
        "voting_members": tuple(sorted(voting)),
        "present_voting_members": tuple(present_voting),
        "required_voting_members": required,
        "chair_present": chair_present,
        "quorate": len(present_voting) >= required and chair_present,
    }


def subsystem_representation_findings(emc_relevant_subsystems, members):
    """Sorted findings for every electromagnetically relevant subsystem
    that no appointed member speaks for. Raises ValueError when the
    subsystem list is not a list or tuple of non-empty strings."""
    if isinstance(emc_relevant_subsystems, str) or not isinstance(
        emc_relevant_subsystems, (list, tuple)
    ):
        raise ValueError("emc_relevant_subsystems must be a list or tuple of names")
    records = validate_membership(members)
    represented = set()
    for record in records:
        if record["appointed"]:
            represented.update(record["subsystems"])
    findings = []
    for name in emc_relevant_subsystems:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("subsystem name must be a non-empty string, got %r" % (name,))
        if name not in represented:
            findings.append("subsystem %s has no representative on the board" % name)
    return sorted(set(findings))


def categorize_agenda_item(item_kind):
    """Decision class an agenda item carries: "requirement",
    "architecture", "deviation" or "verification". Raises ValueError
    for a topic outside the board's remit and for an unrecognized
    topic, so neither reaches the vote."""
    if item_kind in IN_REMIT_AGENDA_ITEMS:
        return IN_REMIT_AGENDA_ITEMS[item_kind]
    if item_kind in OUT_OF_REMIT_AGENDA_ITEMS:
        raise ValueError(
            "agenda item %r is outside the electromagnetic compatibility "
            "advisory board remit" % (item_kind,)
        )
    raise ValueError("unrecognized agenda item kind %r" % (item_kind,))


def item_needs_customer_approval(item_kind):
    """True when endorsing the item still leaves the customer to
    approve it, because the item moves the agreed baseline."""
    return categorize_agenda_item(item_kind) in CUSTOMER_APPROVAL_ITEM_CLASSES


def dispose_agenda_item(item, quorate):
    """Disposition of one agenda item: "deferred" when the sitting is
    not quorate or nobody cast a vote, "escalated_for_customer_approval"
    when a carried item moves the baseline, "endorsed" when a carried
    item stays inside the board's authority, otherwise "rejected". The
    majority is counted on votes cast, with abstentions excluded, in
    whole numbers so no rounding decides a vote. Raises ValueError for
    a malformed item record or a negative or non-integer tally."""
    if not isinstance(item, dict):
        raise ValueError("agenda item must be a mapping, got %r" % (item,))
    if not isinstance(quorate, bool):
        raise ValueError("quorate must be a boolean, got %r" % (quorate,))
    item_class = categorize_agenda_item(item.get("item_kind"))
    tallies = {}
    for key in ("votes_for", "votes_against", "abstentions"):
        value = item.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be a whole number, got %r" % (key, value))
        if value < 0:
            raise ValueError("%s must be >= 0, got %r" % (key, value))
        tallies[key] = value
    if not quorate:
        return "deferred"
    cast = tallies["votes_for"] + tallies["votes_against"]
    if cast == 0:
        return "deferred"
    if tallies["votes_for"] * 2 > cast:
        if item_class in CUSTOMER_APPROVAL_ITEM_CLASSES:
            return "escalated_for_customer_approval"
        return "endorsed"
    return "rejected"


def composition_findings(members):
    """Sorted findings against the board's composition: an unfilled
    core role, a second chairperson, a nominee left un-appointed and a
    board with no voting seat at all."""
    records = validate_membership(members)
    findings = ["core role %s is unfilled" % role for role in missing_core_roles(members)]
    chairs = [r["member_id"] for r in records if r["role"] == "chairperson" and r["appointed"]]
    if len(chairs) > 1:
        findings.append(
            "board carries %d appointed chairpersons (%s)"
            % (len(chairs), ", ".join(sorted(chairs)))
        )
    for record in records:
        if not record["appointed"]:
            findings.append("nominee %s is not appointed" % record["member_id"])
    if not voting_member_ids(members):
        findings.append("board carries no appointed voting seat")
    return sorted(set(findings))


def review_advisory_board(board):
    """Aggregate clause 6.2.3 review of one sitting.

    board: mapping with members, emc_relevant_subsystems,
    present_member_ids, optional quorum_fraction and an agenda of item
    records each carrying item_id and item_kind. Returns the
    composition and representation findings, the quorum picture, the
    disposition of every agenda item, the items left open and two
    verdicts: constituted (composition and representation clean) and
    compliant (constituted, quorate and nothing left deferred). Raises
    ValueError for a malformed board or a repeated item_id.
    """
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping, got %r" % (board,))
    members = board.get("members")
    comp = composition_findings(members)
    representation = subsystem_representation_findings(
        board.get("emc_relevant_subsystems", ()), members
    )
    quorum = quorum_state(
        members,
        board.get("present_member_ids", ()),
        board.get("quorum_fraction", DEFAULT_QUORUM_FRACTION),
    )
    agenda = board.get("agenda", ())
    if isinstance(agenda, dict) or not isinstance(agenda, (list, tuple)):
        raise ValueError("agenda must be a list or tuple of item records")
    dispositions = {}
    for item in agenda:
        if not isinstance(item, dict):
            raise ValueError("agenda item must be a mapping, got %r" % (item,))
        item_id = item.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("item_id must be a non-empty string, got %r" % (item_id,))
        if item_id in dispositions:
            raise ValueError("duplicate agenda item_id %r" % (item_id,))
        dispositions[item_id] = dispose_agenda_item(item, quorum["quorate"])
    open_items = sorted(
        item_id for item_id, verdict in dispositions.items() if verdict == "deferred"
    )
    constituted = not comp and not representation
    return {
        "composition_findings": comp,
        "representation_findings": representation,
        "quorum": quorum,
        "dispositions": dispositions,
        "open_items": open_items,
        "constituted": constituted,
        "compliant": constituted and quorum["quorate"] and not open_items,
    }
