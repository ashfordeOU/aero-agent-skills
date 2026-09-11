#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.5.1 system-level product verification
management (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard requires product
verification to be planned and managed at system level consistently
with the verification process of ECSS-E-ST-10-02 and the testing
scope of ECSS-E-ST-10-03, per the verification policy recorded in the
project's System Engineering Plan (SEP). Each system-level requirement
is assigned one or more verification methods (test, analysis,
inspection, review of design); every assigned method is tracked to a
status (open, in progress, closed, closed with an accepted deviation,
or failed) with supporting evidence once closed; and a requirement is
verified only when every assigned method has reached a closed status
and none has failed. This module implements the method vocabulary,
per-requirement method assignment, status aggregation, evidence and
policy-linkage checks, and the overall verified/not-verified
determination; it does not perform the underlying test, analysis,
inspection, or review-of-design activity itself.
"""

VERIFICATION_METHODS = frozenset(
    {"test", "analysis", "inspection", "review_of_design"}
)

METHOD_STATUSES = frozenset(
    {"open", "in_progress", "closed", "closed_with_deviation", "failed"}
)

CLOSED_STATUSES = frozenset({"closed", "closed_with_deviation"})


def validate_verification_method(method):
    """Return method if it is one of the four E-ST-10C verification
    methods, else raise ValueError."""
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r under E-ST-10C clause "
            "5.5.1" % (method,)
        )
    return method


def validate_method_status(status):
    """Return status if it is a recognized verification action status,
    else raise ValueError."""
    if status not in METHOD_STATUSES:
        raise ValueError("unrecognized verification method status %r" % (status,))
    return status


def assign_verification_methods(requirement_id, methods):
    """Normalize and validate the verification methods assigned to one
    requirement. Raises ValueError if requirement_id is empty, no
    methods are given, a method is unrecognized, or a method is
    duplicated. Returns a tuple preserving input order."""
    if not requirement_id:
        raise ValueError("requirement_id is required")
    if not methods:
        raise ValueError(
            "requirement %r must be assigned at least one verification "
            "method under E-ST-10C clause 5.5.1" % (requirement_id,)
        )
    normalized = []
    seen = set()
    for method in methods:
        validate_verification_method(method)
        if method in seen:
            raise ValueError(
                "verification method %r assigned twice to requirement %r"
                % (method, requirement_id)
            )
        seen.add(method)
        normalized.append(method)
    return tuple(normalized)


def verification_policy_linkage_violations(requirement_id, sep_policy_ref):
    """Flag a requirement whose verification approach is not linked
    back to a System Engineering Plan verification policy reference.
    sep_policy_ref: str | None."""
    if not sep_policy_ref:
        return [
            {
                "issue": "missing_sep_verification_policy_linkage",
                "requirement": requirement_id,
            }
        ]
    return []


def method_assignment_violations(requirement_id, assigned_methods, method_status_map):
    """Flag an assigned method with no recorded status, and a recorded
    status for a method that was never assigned to the requirement."""
    violations = []
    assigned = set(assigned_methods)
    tracked = set(method_status_map)
    for method in sorted(assigned - tracked):
        violations.append(
            {
                "issue": "assigned_method_missing_status",
                "requirement": requirement_id,
                "method": method,
            }
        )
    for method in sorted(tracked - assigned):
        violations.append(
            {
                "issue": "status_for_unassigned_method",
                "requirement": requirement_id,
                "method": method,
            }
        )
    return violations


def closure_evidence_violations(requirement_id, method_status_map, evidence_map):
    """Flag a method whose status is closed (with or without a
    deviation) but has no supporting evidence reference on record.
    evidence_map: {method: evidence_ref | None}. Validates every
    status in method_status_map, raising ValueError for an
    unrecognized one."""
    violations = []
    for method, status in method_status_map.items():
        validate_method_status(status)
        if status in CLOSED_STATUSES and not evidence_map.get(method):
            violations.append(
                {
                    "issue": "closed_method_missing_evidence",
                    "requirement": requirement_id,
                    "method": method,
                }
            )
    return violations


def requirement_verification_status(method_status_map):
    """Aggregate verification status across every method in
    method_status_map ({method: status}). A single failed method makes
    the requirement "failed" regardless of the others. Otherwise the
    requirement is "closed_with_deviation" or "closed" only once every
    method has reached a closed status; while any method remains open
    it is "in_progress" if at least one method is in progress, else
    "open". Raises ValueError for an empty map or an unrecognized
    status."""
    if not method_status_map:
        raise ValueError("no verification methods to aggregate a status from")
    statuses = [validate_method_status(s) for s in method_status_map.values()]
    if "failed" in statuses:
        return "failed"
    if not all(s in CLOSED_STATUSES for s in statuses):
        return "in_progress" if "in_progress" in statuses else "open"
    return "closed_with_deviation" if "closed_with_deviation" in statuses else "closed"


def verification_review(requirement):
    """Full clause 5.5.1 system-level verification review for one
    requirement.

    requirement: {"requirement_id": str, "methods": [str, ...],
    "method_status": {method: status}, "evidence": {method: ref |
    None}, "sep_policy_ref": str | None}. Raises ValueError for an
    empty requirement_id, an empty/invalid methods list, a duplicate
    method, or an unrecognized status. Returns {"violations": [...],
    "status": str | None}; status is None whenever a method assigned
    to the requirement has no recorded status yet, since the
    aggregate cannot be computed until every method is tracked."""
    requirement_id = requirement["requirement_id"]
    methods = assign_verification_methods(requirement_id, requirement["methods"])
    method_status = requirement.get("method_status", {})
    evidence = requirement.get("evidence", {})

    violations = []
    violations.extend(
        verification_policy_linkage_violations(
            requirement_id, requirement.get("sep_policy_ref")
        )
    )
    violations.extend(
        method_assignment_violations(requirement_id, methods, method_status)
    )
    violations.extend(
        closure_evidence_violations(requirement_id, method_status, evidence)
    )

    status = None
    if set(methods) <= set(method_status):
        status = requirement_verification_status(
            {method: method_status[method] for method in methods}
        )
    return {"violations": violations, "status": status}


def is_requirement_verified(review):
    """True when a verification_review result has no violations and
    every assigned method reached a closed status (with or without an
    accepted deviation)."""
    return not review["violations"] and review["status"] in CLOSED_STATUSES
