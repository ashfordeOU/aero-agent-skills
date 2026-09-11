#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.2.3.9 requirements baseline management
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard calls for each
configuration item (CI) to have its requirement set reviewed and
frozen into a baseline at an agreed project milestone, and for every
change to a baselined requirement to be tracked and authorized rather
than made silently. This module implements the pre-baseline readiness
check for a requirement (approval status, requirement text,
verification method), duplicate-identifier detection across a CI's
requirement set, milestone baseline establishment gated on that
readiness check, and post-baseline change control (an addition,
modification, or deletion against an established baseline must carry
an approved change request). It does not define the CI's requirement
content itself or the change-request approval workflow.
"""

REQUIREMENT_STATUSES = frozenset({"draft", "in_review", "approved", "withdrawn"})

BASELINE_MILESTONES = frozenset({"SRR", "PDR", "CDR", "QR"})

CHANGE_TYPES = frozenset({"add", "modify", "delete"})


def classify_requirement_status(status):
    """Readiness category for a requirement status: "ready" only for
    "approved", otherwise "not_ready". Raises ValueError for a status
    outside REQUIREMENT_STATUSES."""
    if status not in REQUIREMENT_STATUSES:
        raise ValueError(
            "unrecognized requirement status %r under E-ST-10C clause "
            "5.2.3.9" % (status,)
        )
    return "ready" if status == "approved" else "not_ready"


def requirement_readiness_violations(requirement):
    """Violation list (empty if ready) for one requirement dict with
    keys "requirement_id", "status", and optionally "text" and
    "verification_method". Flags a non-approved status, missing
    requirement text, and a missing verification method independently
    so every gap is reported, not just the first one found."""
    requirement_id = requirement["requirement_id"]
    violations = []
    if classify_requirement_status(requirement["status"]) != "ready":
        violations.append(
            {
                "issue": "requirement_not_approved",
                "requirement_id": requirement_id,
                "status": requirement["status"],
            }
        )
    if not (requirement.get("text") or "").strip():
        violations.append(
            {"issue": "missing_requirement_text", "requirement_id": requirement_id}
        )
    if not requirement.get("verification_method"):
        violations.append(
            {
                "issue": "missing_verification_method",
                "requirement_id": requirement_id,
            }
        )
    return violations


def duplicate_requirement_ids(requirements):
    """Sorted list of requirement_id values that appear more than once
    in an iterable of requirement dicts. Does not mutate requirements."""
    seen = set()
    duplicates = set()
    for requirement in requirements:
        requirement_id = requirement["requirement_id"]
        if requirement_id in seen:
            duplicates.add(requirement_id)
        seen.add(requirement_id)
    return sorted(duplicates)


def milestone_baseline_review(ci_id, requirements, milestone):
    """Full clause 5.2.3.9 baseline-readiness review for one CI's
    requirement set at an agreed milestone. Raises ValueError for an
    unrecognized milestone. Returns a violation list: a CI with no
    requirements is itself flagged, then each duplicate identifier and
    each per-requirement readiness gap is reported."""
    if milestone not in BASELINE_MILESTONES:
        raise ValueError(
            "unrecognized baseline milestone %r under E-ST-10C clause "
            "5.2.3.9" % (milestone,)
        )
    if not requirements:
        return [{"issue": "no_requirements_for_baseline", "ci_id": ci_id}]
    violations = [
        {"issue": "duplicate_requirement_id", "ci_id": ci_id, "requirement_id": dup}
        for dup in duplicate_requirement_ids(requirements)
    ]
    for requirement in requirements:
        violations.extend(requirement_readiness_violations(requirement))
    return violations


def is_milestone_baseline_eligible(violations):
    """True when a milestone_baseline_review result has no blocking
    violations -- the CI's requirement set may be baselined."""
    return len(violations) == 0


def establish_baseline(ci_id, requirements, milestone, baseline_id):
    """Establish a requirements baseline record for one CI at an
    agreed milestone. Raises ValueError for an empty baseline_id or
    when the requirement set is not baseline-eligible (see
    milestone_baseline_review); an ineligible attempt is rejected
    rather than silently recorded. Returns the established baseline
    record on success."""
    if not baseline_id:
        raise ValueError("baseline_id must be a non-empty identifier")
    violations = milestone_baseline_review(ci_id, requirements, milestone)
    if not is_milestone_baseline_eligible(violations):
        raise ValueError(
            "cannot establish baseline %r for CI %r at %s milestone: "
            "%d blocking violation(s)"
            % (baseline_id, ci_id, milestone, len(violations))
        )
    return {
        "baseline_id": baseline_id,
        "ci_id": ci_id,
        "milestone": milestone,
        "status": "established",
        "requirement_ids": sorted(r["requirement_id"] for r in requirements),
    }


def baseline_change_violations(change):
    """Violation list (empty if authorized) for one change dict with
    keys "requirement_id", "change_type" ("add", "modify", or
    "delete"), and "has_approved_change_request". Raises ValueError
    for an unrecognized change_type."""
    change_type = change["change_type"]
    if change_type not in CHANGE_TYPES:
        raise ValueError(
            "unrecognized baseline change type %r under E-ST-10C clause "
            "5.2.3.9" % (change_type,)
        )
    if not change.get("has_approved_change_request"):
        return [
            {
                "issue": "baseline_change_without_approved_cr",
                "requirement_id": change["requirement_id"],
                "change_type": change_type,
            }
        ]
    return []


def baseline_control_review(baseline, changes):
    """Aggregated change-control violation list for a set of proposed
    changes against an established baseline record (see
    establish_baseline). Raises ValueError if the baseline itself is
    not in "established" status -- change control only applies once a
    baseline exists. Does not mutate baseline or changes."""
    if baseline.get("status") != "established":
        raise ValueError(
            "baseline %r is not established; cannot apply change control"
            % (baseline.get("baseline_id"),)
        )
    violations = []
    for change in changes:
        violations.extend(baseline_change_violations(change))
    return violations


def is_baseline_change_controlled(violations):
    """True when a baseline_control_review result has no violations --
    every proposed change carried an approved change request."""
    return len(violations) == 0
