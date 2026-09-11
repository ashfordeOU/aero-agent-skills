#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.2.3.7 requirements-specification agreement
loop (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system requirements engineering clause requires that each technical
requirements specification be brought to a recorded agreement between
the customer and every contributing supplier before it is used as a
baseline. This module implements the signatory-identification, review-
state, and outstanding-violation logic of that sign-off loop: who must
agree, whether each party's agreement is current against the
specification's baseline revision, and whether an outstanding comment
or an overdue review is blocking closure. It does not implement the
document-control or configuration-management mechanics of baselining
itself (see the M-ST-40 linked leaf for that).
"""

ROLES = frozenset({"customer", "supplier"})
REVIEW_STATUSES = frozenset({"agreed", "comment", "pending"})

STATE_AGREED = "agreed"
STATE_STALE_AGREEMENT = "stale_agreement"
STATE_OPEN_COMMENT = "open_comment"
STATE_PENDING = "pending"


def classify_party_role(role):
    """Signatory role for a party: "customer" or "supplier". Raises
    ValueError for a role outside both known values."""
    if role not in ROLES:
        raise ValueError(
            "unrecognized party role %r under E-ST-10C clause 5.2.3.7" % (role,)
        )
    return role


def required_signatories(parties):
    """Sorted list of unique party_id strings required to sign off on
    a specification: every party in `parties`, provided at least one
    of them holds the customer role. `parties`: iterable of
    {"party_id": str, "role": str}. Raises ValueError for a party with
    an unrecognized role, or if no customer party is present -- the
    agreement loop requires at least one customer signatory."""
    party_ids = []
    has_customer = False
    for party in parties:
        role = classify_party_role(party["role"])
        if role == "customer":
            has_customer = True
        party_ids.append(party["party_id"])
    if not has_customer:
        raise ValueError(
            "no customer party recorded; the agreement loop requires "
            "a customer signatory"
        )
    return sorted(set(party_ids))


def review_state(review, current_revision):
    """Effective agreement state of one party's review record against
    the specification's current baseline revision. `review`:
    {"status": "agreed"|"comment"|"pending", "reviewed_revision": ...}.
    Returns STATE_AGREED (status agreed and reviewed_revision matches
    current_revision), STATE_STALE_AGREEMENT (status agreed but
    reviewed_revision does not match -- the party must re-confirm),
    STATE_OPEN_COMMENT (status comment -- unresolved dissent), or
    STATE_PENDING (status pending, or no status recorded). Raises
    ValueError for an unrecognized status."""
    status = review.get("status", STATE_PENDING)
    if status not in REVIEW_STATUSES:
        raise ValueError("unrecognized review status %r" % (status,))
    if status == STATE_PENDING:
        return STATE_PENDING
    if status == "comment":
        return STATE_OPEN_COMMENT
    if review.get("reviewed_revision") != current_revision:
        return STATE_STALE_AGREEMENT
    return STATE_AGREED


def days_pending(review, current_day):
    """Elapsed days since a review was opened: current_day -
    review.get("opened_day", current_day) (0 when opened_day is
    absent). Raises ValueError if opened_day is after current_day."""
    opened_day = review.get("opened_day", current_day)
    elapsed = current_day - opened_day
    if elapsed < 0:
        raise ValueError("opened_day is after current_day")
    return elapsed


def signatory_violations(party_id, state, elapsed_days, review_period_days):
    """Violation list (empty if the party's agreement is clean) for
    one required signatory. STATE_STALE_AGREEMENT and
    STATE_OPEN_COMMENT and STATE_PENDING each yield their own issue;
    STATE_OPEN_COMMENT or STATE_PENDING additionally yields
    "overdue_review" once elapsed_days exceeds review_period_days.
    Raises ValueError for a negative review_period_days."""
    if review_period_days < 0:
        raise ValueError("review_period_days must be >= 0")
    violations = []
    if state == STATE_STALE_AGREEMENT:
        violations.append({"issue": "stale_agreement", "party": party_id})
    elif state == STATE_OPEN_COMMENT:
        violations.append({"issue": "open_comment", "party": party_id})
    elif state == STATE_PENDING:
        violations.append({"issue": "pending_agreement", "party": party_id})
    if state in (STATE_OPEN_COMMENT, STATE_PENDING) and elapsed_days > review_period_days:
        violations.append(
            {"issue": "overdue_review", "party": party_id, "elapsed_days": elapsed_days}
        )
    return violations


def agreement_review(spec, current_day, review_period_days=30):
    """Full clause 5.2.3.7 agreement review for one specification.

    spec: {"spec_id": str, "revision": int|str, "parties": [{"party_id",
    "role"}, ...], "reviews": {party_id: {"status", "reviewed_revision",
    "opened_day"}}}. A required signatory with no entry in "reviews" is
    treated as STATE_PENDING. Returns {"spec_id": str, "violations":
    [...], "party_states": {party_id: state}}. Raises ValueError from
    required_signatories, review_state, or days_pending on malformed
    input; does not mutate spec."""
    spec_id = spec["spec_id"]
    revision = spec["revision"]
    reviews = spec.get("reviews", {})
    party_states = {}
    violations = []
    for party_id in required_signatories(spec["parties"]):
        review = reviews.get(party_id, {})
        state = review_state(review, revision)
        elapsed_days = days_pending(review, current_day)
        party_states[party_id] = state
        violations.extend(
            signatory_violations(party_id, state, elapsed_days, review_period_days)
        )
    return {"spec_id": spec_id, "violations": violations, "party_states": party_states}


def is_spec_agreed(review):
    """True when an agreement_review result carries no violations --
    the specification's sign-off loop is closed for this assessment."""
    return len(review["violations"]) == 0
