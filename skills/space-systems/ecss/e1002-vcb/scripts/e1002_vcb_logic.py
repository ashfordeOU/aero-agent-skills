#!/usr/bin/env python3
"""ECSS-E-ST-10-02C §5.4.2 Verification Control Board (VCB) governance
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
verification standard's VCB clause establishes a formal governance board
that must include at least one customer representative and one supplier
representative; the board confirms quorum before deliberating, categorizes
agenda items as elevated-authority (closeout approval, exception approval,
discrepancy waiver) or routine (verification status change, action item
review), requires both required roles for elevated items and at least one
for routine items, records every decision with rationale, and is compliant
when composition, quorum, and decision-authority findings are all empty.
This module implements composition validation, quorum checking, agenda-item
authority categorization, decision recording with error paths, and the full
meeting review; it does not implement the verification matrix or DRB logic.
"""

VALID_MEMBER_ROLES = frozenset(
    {"customer", "supplier", "technical_expert", "observer"}
)
REQUIRED_BOARD_ROLES = frozenset({"customer", "supplier"})

AGENDA_ITEM_TYPES = frozenset(
    {
        "verification_status_change",
        "discrepancy_waiver",
        "closeout_approval",
        "exception_approval",
        "action_item_review",
    }
)

# Items where both customer and supplier authority must be present.
ELEVATED_AUTHORITY_ITEM_TYPES = frozenset(
    {"closeout_approval", "exception_approval", "discrepancy_waiver"}
)

VALID_DECISIONS = frozenset(
    {"approved", "rejected", "deferred", "conditionally_approved"}
)


def validate_member_role(role):
    """Confirm role is a recognised VCB member role. Raises ValueError for
    any role outside the known set."""
    if role not in VALID_MEMBER_ROLES:
        raise ValueError(
            "unrecognised VCB member role %r under E-ST-10-02C §5.4.2" % (role,)
        )


def validate_vcb_composition(members):
    """Composition violation list for the VCB board. Each element of members
    must be a dict with a 'role' key; an unrecognised role raises ValueError.
    Returns a list of dicts (empty when composition is valid) — one entry for
    each required role absent from the board. Does not mutate members."""
    roles = set()
    for member in members:
        validate_member_role(member["role"])
        roles.add(member["role"])
    violations = []
    for required_role in sorted(REQUIRED_BOARD_ROLES):
        if required_role not in roles:
            violations.append(
                {
                    "issue": "missing_required_vcb_role",
                    "missing_role": required_role,
                }
            )
    return violations


def check_quorum(roles_present):
    """True when both 'customer' and 'supplier' appear in roles_present.
    roles_present: iterable of role strings for the meeting attendees.
    A VCB meeting must confirm quorum before recording binding decisions."""
    return REQUIRED_BOARD_ROLES.issubset(set(roles_present))


def categorize_agenda_item(item_type):
    """Authority category for an agenda item type: 'elevated' for items
    that require both customer and supplier present (closeout_approval,
    exception_approval, discrepancy_waiver), 'routine' for items that
    require at least one required role present (verification_status_change,
    action_item_review). Raises ValueError for an unrecognised item type."""
    if item_type not in AGENDA_ITEM_TYPES:
        raise ValueError(
            "unrecognised VCB agenda item type %r under E-ST-10-02C §5.4.2"
            % (item_type,)
        )
    if item_type in ELEVATED_AUTHORITY_ITEM_TYPES:
        return "elevated"
    return "routine"


def authority_sufficient(item_type, roles_present):
    """True when the roles present satisfy the decision authority required
    for item_type. Elevated items require both 'customer' and 'supplier'
    present; routine items require at least one. Raises ValueError for an
    unrecognised item_type (via categorize_agenda_item)."""
    category = categorize_agenda_item(item_type)
    present = set(roles_present)
    if category == "elevated":
        return REQUIRED_BOARD_ROLES.issubset(present)
    return bool(present & REQUIRED_BOARD_ROLES)


def validate_vcb_decision(item_id, item_type, decision, roles_present, rationale):
    """Validate one VCB decision record. Raises ValueError for an
    unrecognised item_type, unrecognised decision outcome, or empty/missing
    rationale. Returns a list of authority violations (empty when authority is
    sufficient for the item). Does not mutate roles_present."""
    if item_type not in AGENDA_ITEM_TYPES:
        raise ValueError(
            "unrecognised VCB agenda item type %r for decision on item %r"
            % (item_type, item_id)
        )
    if decision not in VALID_DECISIONS:
        raise ValueError(
            "unrecognised VCB decision outcome %r for item %r"
            % (decision, item_id)
        )
    if not rationale or not str(rationale).strip():
        raise ValueError(
            "VCB decision for item %r has no rationale; rationale is mandatory"
            % (item_id,)
        )
    if not authority_sufficient(item_type, roles_present):
        return [
            {
                "issue": "insufficient_decision_authority",
                "item_id": item_id,
                "item_type": item_type,
                "category": categorize_agenda_item(item_type),
                "roles_present": sorted(set(roles_present)),
            }
        ]
    return []


def vcb_meeting_review(meeting):
    """Full VCB meeting compliance review.

    meeting: {
        "members": [{"role": str, ...}, ...],
        "roles_present": [str, ...],
        "decisions": [{"item_id": str, "item_type": str,
                       "decision": str, "rationale": str}, ...]
    }

    Returns {"composition": [...], "quorum": [...], "decisions": [...]},
    each a violation list. Raises ValueError for any unrecognised member
    role (via validate_vcb_composition), unrecognised item_type, unrecognised
    decision outcome, or missing rationale (via validate_vcb_decision)."""
    composition_violations = validate_vcb_composition(
        meeting.get("members", [])
    )

    roles_present = list(meeting.get("roles_present", []))
    for role in roles_present:
        validate_member_role(role)

    quorum_violations = []
    if not check_quorum(roles_present):
        missing = sorted(REQUIRED_BOARD_ROLES - set(roles_present))
        quorum_violations.append(
            {
                "issue": "quorum_not_met",
                "missing_required_roles": missing,
            }
        )

    decision_violations = []
    for dec in meeting.get("decisions", []):
        decision_violations.extend(
            validate_vcb_decision(
                dec["item_id"],
                dec["item_type"],
                dec["decision"],
                roles_present,
                dec.get("rationale", ""),
            )
        )

    return {
        "composition": composition_violations,
        "quorum": quorum_violations,
        "decisions": decision_violations,
    }


def is_vcb_meeting_compliant(review):
    """True when all three finding lists in a vcb_meeting_review result are
    empty — the meeting satisfies §5.4.2 for composition, quorum, and
    decision authority."""
    return all(len(findings) == 0 for findings in review.values())
