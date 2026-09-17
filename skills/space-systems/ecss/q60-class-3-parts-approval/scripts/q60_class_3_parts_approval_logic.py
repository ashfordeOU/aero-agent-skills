"""Customer-invoked review and approval of parts proposed for Class 3 use.

Anchor: ECSS-Q-ST-60C clause 6.2.4 (the review and approval the customer
invokes over components proposed for a Class 3 application).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Class 3 review is invoked, not universal. The first question is therefore
  never "is this part approved" but "did anything about this part invoke a
  customer review at all". A part that invoked nothing is usable on the
  project's own authority, and saying so is part of the answer.
* Where review is invoked the submission is what the decision is taken
  against. Each item the dossier owes is named separately when it is absent,
  because an approval granted on a submission nobody could read is not an
  approval anybody can audit afterwards.
* Customer silence is not consent. A submission with no decision stays
  pending however long it has been waiting; once the response window has
  elapsed that is an escalation, not an approval by default.
* A restriction attached to an approval releases nothing until it carries an
  implementation record. A refusal binds whatever else the file contains.
"""

from __future__ import annotations

import math

# Any one of these, declared true of a proposed part, invokes customer review.
INVOCATION_RULES = (
    "part-from-a-non-preferred-source",
    "part-type-new-to-the-project",
    "plastic-encapsulated-part-in-a-critical-function",
    "part-used-outside-its-published-derating-rules",
    "single-source-part-with-no-alternate",
)

# What an invoked submission has to put in front of the customer.
REQUIRED_SUBMISSION_ITEMS = (
    "application-and-circuit-function",
    "procurement-source-and-route",
    "reason-class-3-is-adequate-for-this-use",
    "available-quality-and-test-evidence",
)

# The decisions a customer file can carry.
CUSTOMER_DECISIONS = (
    "approved",
    "approved-with-restriction",
    "refused",
    "no-response",
)

# The assurance category this leaf reviews parts for.
TARGET_CATEGORY = "class-3"

# How long the customer has before an undecided submission is an escalation.
RESPONSE_WINDOW_WORKING_DAYS = 20.0

# Elapsed time is a declared quantity; a case meant to sit on the window edge
# can land a few units in the last place away from it.
RESPONSE_TOLERANCE = 1e-9

PART_STATUSES = (
    "class-3-part-usable-without-customer-review",
    "class-3-part-approved-for-use",
    "class-3-part-approval-pending-customer",
    "class-3-part-submission-incomplete",
    "class-3-part-restriction-not-implemented",
    "class-3-part-refused-by-customer",
)

USABLE_STATUSES = (
    "class-3-part-usable-without-customer-review",
    "class-3-part-approved-for-use",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _label(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _name_set(raw, allowed, label):
    """Validate a declared collection of names drawn from a closed set."""
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a list or tuple of names, got %r" % (label, raw))
    names = []
    for name in raw:
        if name not in allowed:
            raise ValueError(
                "unknown %s %r (known: %s)" % (label, name, ", ".join(allowed))
            )
        if name not in names:
            names.append(name)
    return tuple(names)


def invocation_reasons(declared_flags):
    """Rules a proposed part triggered, in the order the rules are published."""
    flagged = _name_set(declared_flags, INVOCATION_RULES, "invocation rule")
    return tuple(rule for rule in INVOCATION_RULES if rule in flagged)


def customer_review_invoked(declared_flags):
    """True when anything about the part puts it in front of the customer."""
    return bool(invocation_reasons(declared_flags))


def missing_submission_items(declared_items):
    """Submission items the dossier never supplied."""
    present = _name_set(declared_items, REQUIRED_SUBMISSION_ITEMS, "submission item")
    return tuple(item for item in REQUIRED_SUBMISSION_ITEMS if item not in present)


def response_window_elapsed(elapsed_working_days):
    """True when the customer has had longer than the response window."""
    elapsed = _real(elapsed_working_days, "elapsed_working_days")
    if elapsed < 0.0:
        raise ValueError("elapsed_working_days must not be negative, got %r" % (elapsed,))
    return elapsed > RESPONSE_WINDOW_WORKING_DAYS + RESPONSE_TOLERANCE


def normalize_restrictions(restrictions):
    """Validate the restrictions attached to a restricted approval."""
    if isinstance(restrictions, str) or not isinstance(restrictions, (list, tuple)):
        raise ValueError(
            "restrictions must be a list or tuple of mappings, got %r" % (restrictions,)
        )
    normalized = []
    seen = set()
    for restriction in restrictions:
        if not isinstance(restriction, dict):
            raise ValueError(
                "each restriction must be a mapping, got %r"
                % (type(restriction).__name__,)
            )
        restriction_id = _label(restriction.get("restriction_id"), "restriction_id")
        if restriction_id in seen:
            raise ValueError("duplicate restriction_id %r" % (restriction_id,))
        seen.add(restriction_id)
        normalized.append(
            {
                "restriction_id": restriction_id,
                "implementation_record_present": _flag(
                    restriction, "implementation_record_present"
                ),
            }
        )
    return normalized


def open_restrictions(restrictions):
    """Restrictions still without an implementation record."""
    return tuple(
        restriction["restriction_id"]
        for restriction in normalize_restrictions(restrictions)
        if not restriction["implementation_record_present"]
    )


def normalize_submission(submission):
    """Validate one customer submission file."""
    if not isinstance(submission, dict):
        raise ValueError(
            "submission must be a mapping, got %r" % (type(submission).__name__,)
        )
    decision = submission.get("customer_decision")
    if decision not in CUSTOMER_DECISIONS:
        raise ValueError(
            "unknown customer_decision %r (known: %s)"
            % (decision, ", ".join(CUSTOMER_DECISIONS))
        )
    elapsed = _real(
        submission.get("elapsed_working_days"), "elapsed_working_days"
    )
    if elapsed < 0.0:
        raise ValueError("elapsed_working_days must not be negative, got %r" % (elapsed,))
    restrictions = normalize_restrictions(submission.get("restrictions", []))
    if decision == "approved-with-restriction" and not restrictions:
        raise ValueError("a restricted approval must carry at least one restriction")
    if restrictions and decision != "approved-with-restriction":
        raise ValueError("restrictions were attached to an unrestricted decision")
    return {
        "customer_decision": decision,
        "elapsed_working_days": elapsed,
        "restrictions": restrictions,
        "items": _name_set(
            submission.get("items", []), REQUIRED_SUBMISSION_ITEMS, "submission item"
        ),
    }


def assess_proposed_part(part):
    """Read one proposed part and return its Class 3 use status with findings."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    part_number = _label(part.get("part_number"), "part_number")
    category = _label(part.get("declared_category"), "declared_category")
    reasons = invocation_reasons(part.get("invocation_flags", []))
    findings = []

    if category != TARGET_CATEGORY:
        findings.append(
            {
                "part_number": part_number,
                "finding": "declared-category-is-not-the-one-being-reviewed",
                "detail": category,
            }
        )
        return {
            "part_number": part_number,
            "declared_category": category,
            "invocation_reasons": list(reasons),
            "review_invoked": bool(reasons),
            "status": "class-3-part-submission-incomplete",
            "missing_submission_items": list(REQUIRED_SUBMISSION_ITEMS),
            "open_restrictions": [],
            "findings": findings,
            "usable": False,
        }

    if not reasons:
        return {
            "part_number": part_number,
            "declared_category": category,
            "invocation_reasons": [],
            "review_invoked": False,
            "status": "class-3-part-usable-without-customer-review",
            "missing_submission_items": [],
            "open_restrictions": [],
            "findings": findings,
            "usable": True,
        }

    submission = part.get("submission")
    if submission is None:
        findings.append(
            {
                "part_number": part_number,
                "finding": "customer-review-invoked-but-nothing-was-submitted",
                "detail": reasons[0],
            }
        )
        return {
            "part_number": part_number,
            "declared_category": category,
            "invocation_reasons": list(reasons),
            "review_invoked": True,
            "status": "class-3-part-submission-incomplete",
            "missing_submission_items": list(REQUIRED_SUBMISSION_ITEMS),
            "open_restrictions": [],
            "findings": findings,
            "usable": False,
        }

    record = normalize_submission(submission)
    missing_items = missing_submission_items(record["items"])
    still_open = open_restrictions(record["restrictions"])
    decision = record["customer_decision"]

    for item in missing_items:
        findings.append(
            {
                "part_number": part_number,
                "finding": "submission-dossier-incomplete",
                "detail": item,
            }
        )
    for restriction_id in still_open:
        findings.append(
            {
                "part_number": part_number,
                "finding": "approval-restriction-not-implemented",
                "detail": restriction_id,
            }
        )

    if decision == "refused":
        findings.append(
            {
                "part_number": part_number,
                "finding": "customer-refused-the-proposed-part",
                "detail": reasons[0],
            }
        )
        status = "class-3-part-refused-by-customer"
    elif decision == "no-response":
        if response_window_elapsed(record["elapsed_working_days"]):
            findings.append(
                {
                    "part_number": part_number,
                    "finding": "response-window-elapsed-without-a-decision",
                    "detail": "%.1f working days" % record["elapsed_working_days"],
                }
            )
        status = "class-3-part-approval-pending-customer"
    elif missing_items:
        status = "class-3-part-submission-incomplete"
    elif still_open:
        status = "class-3-part-restriction-not-implemented"
    else:
        status = "class-3-part-approved-for-use"

    return {
        "part_number": part_number,
        "declared_category": category,
        "invocation_reasons": list(reasons),
        "review_invoked": True,
        "customer_decision": decision,
        "elapsed_working_days": record["elapsed_working_days"],
        "status": status,
        "missing_submission_items": list(missing_items),
        "open_restrictions": list(still_open),
        "findings": findings,
        "usable": status in USABLE_STATUSES,
    }


def assess_class_3_parts_approval(programme_id, proposed_parts):
    """Turn a proposed Class 3 parts list into a usable list plus findings."""
    _label(programme_id, "programme_id")
    if isinstance(proposed_parts, str) or not isinstance(
        proposed_parts, (list, tuple)
    ):
        raise ValueError(
            "proposed_parts must be a list or tuple of mappings, got %r"
            % (proposed_parts,)
        )
    if not proposed_parts:
        raise ValueError("at least one proposed part is required")

    records = []
    seen = set()
    for part in proposed_parts:
        record = assess_proposed_part(part)
        if record["part_number"] in seen:
            raise ValueError("duplicate part_number %r" % (record["part_number"],))
        seen.add(record["part_number"])
        records.append(record)

    usable = [r["part_number"] for r in records if r["usable"]]
    blocked = [r["part_number"] for r in records if not r["usable"]]
    invoked = [r["part_number"] for r in records if r["review_invoked"]]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    counts = {status: 0 for status in PART_STATUSES}
    for record in records:
        counts[record["status"]] += 1

    return {
        "programme_id": programme_id,
        "part_records": records,
        "usable_parts": usable,
        "blocked_parts": blocked,
        "review_invoked_parts": invoked,
        "invoked_fraction": float(len(invoked)) / float(len(records)),
        "status_counts": counts,
        "findings": findings,
        "list_usable": not blocked,
    }
