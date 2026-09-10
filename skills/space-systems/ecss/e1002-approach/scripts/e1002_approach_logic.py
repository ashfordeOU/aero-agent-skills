#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.1 verification approach (paraphrase, not
copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): before
detailed verification planning, the programme defines an approach that
(a) identifies which requirements enter the verification programme at
all, (b) records a verification strategy for each of them -- a method
(test, analysis, review of design, inspection), a product-tree level
(equipment, subsystem, element, segment, system), and a stage
(qualification, acceptance, pre-launch, in-orbit, post-landing) -- and
(c) carries a documented risk assessment and mitigation for every
requirement not verified by test, since a non-test method accepts a
lower directness of evidence. This module implements requirement
applicability scoping, strategy-record completeness and method/stage
compatibility checks, the risk-assessment requirement for non-test
methods, and closure-status roll-up. It does not itself select a
method by precedence (see the sibling e10-req-verif-methods leaf),
assign a product-tree level (see the sibling e1002-levels leaf), or
determine stage applicability from a product's life profile (see the
sibling e1002-stages leaf).
"""

VERIFICATION_METHODS = frozenset(
    {"test", "analysis", "review_of_design", "inspection"}
)
VERIFICATION_LEVELS = ("equipment", "subsystem", "element", "segment", "system")
VERIFICATION_STAGES = (
    "qualification",
    "acceptance",
    "pre_launch",
    "in_orbit",
    "post_landing",
)
RISK_LEVELS = frozenset({"low", "medium", "high"})
STATUS_VALUES = frozenset({"open", "in_progress", "closed"})

# Requirement categories that enter the verification programme (clause
# 5.2.1 "requirements to be verified"). A goal, rationale note, or a
# withdrawn requirement carries no compliance obligation and is
# deliberately excluded.
VERIFIABLE_CATEGORIES = frozenset(
    {"performance", "functional", "design", "interface", "safety"}
)
NON_VERIFIABLE_CATEGORIES = frozenset({"informational", "rationale", "goal", "withdrawn"})

# Method/stage compatibility for the approach record. qualification
# precedes flight hardware and admits every method; acceptance protects
# the deliverable article and drops review of design (the design is
# already fixed); pre-launch and in-orbit are on integrated or flown
# hardware and drop inspection or review of design where physical or
# design-level access is no longer practical; post-landing covers
# recovered hardware and admits everything except review of design
# (the design question was already closed at qualification).
METHOD_APPLICABILITY_BY_STAGE = {
    "qualification": frozenset({"test", "analysis", "review_of_design", "inspection"}),
    "acceptance": frozenset({"test", "analysis", "inspection"}),
    "pre_launch": frozenset({"analysis", "inspection"}),
    "in_orbit": frozenset({"test", "analysis"}),
    "post_landing": frozenset({"test", "analysis", "inspection"}),
}


def requirement_needs_verification(category):
    """True if a requirement of this category enters the verification
    programme (clause 5.2.1 scoping). Raises ValueError for a category
    outside both the verifiable and non-verifiable sets."""
    if category in VERIFIABLE_CATEGORIES:
        return True
    if category in NON_VERIFIABLE_CATEGORIES:
        return False
    raise ValueError("unrecognized requirement category: %r" % (category,))


def is_method_applicable_at_stage(method, stage):
    """True if method is a valid choice for stage under the approach's
    method/stage compatibility rule. Raises ValueError for an
    unrecognized method or stage."""
    if method not in VERIFICATION_METHODS:
        raise ValueError("unrecognized verification method: %r" % (method,))
    if stage not in METHOD_APPLICABILITY_BY_STAGE:
        raise ValueError("unrecognized verification stage: %r" % (stage,))
    return method in METHOD_APPLICABILITY_BY_STAGE[stage]


def risk_assessment_violations(method, risk_assessment):
    """Violation list (empty if compliant) for the clause 5.2.1 risk
    assessment and mitigation required whenever a requirement is not
    verified by test. risk_assessment: {"risk_level", "mitigation"} or
    None. Raises ValueError for an unrecognized method."""
    if method not in VERIFICATION_METHODS:
        raise ValueError("unrecognized verification method: %r" % (method,))
    if method == "test":
        return []
    if risk_assessment is None:
        return [{"issue": "missing_risk_assessment", "method": method}]
    violations = []
    risk_level = risk_assessment.get("risk_level")
    if risk_level not in RISK_LEVELS:
        violations.append({"issue": "invalid_risk_level", "risk_level": risk_level})
    mitigation = risk_assessment.get("mitigation")
    if not isinstance(mitigation, str) or not mitigation.strip():
        violations.append({"issue": "missing_mitigation"})
    return violations


def verification_strategy_violations(entry):
    """Violation list (empty if compliant) for one requirement's
    verification-approach record.

    entry: {"requirement_id", "category", "level", "stage", "method",
    "risk_assessment", "status"}. Does not mutate entry. A requirement
    whose category is non-verifiable is checked only for the presence
    of a stray strategy assignment; a requirement that needs
    verification is checked for a complete, mutually consistent
    strategy plus the risk assessment required for a non-test method.
    """
    violations = []
    requirement_id = entry.get("requirement_id")
    if not isinstance(requirement_id, str) or not requirement_id.strip():
        violations.append({"issue": "missing_requirement_id"})

    category = entry.get("category")
    needs_verification = requirement_needs_verification(category)

    if not needs_verification:
        if entry.get("method") is not None:
            violations.append(
                {
                    "issue": "strategy_assigned_to_non_verifiable_requirement",
                    "requirement_id": requirement_id,
                }
            )
        return violations

    level = entry.get("level")
    if level not in VERIFICATION_LEVELS:
        violations.append(
            {"issue": "invalid_level", "level": level, "requirement_id": requirement_id}
        )

    stage = entry.get("stage")
    if stage not in VERIFICATION_STAGES:
        violations.append(
            {"issue": "invalid_stage", "stage": stage, "requirement_id": requirement_id}
        )

    method = entry.get("method")
    if method not in VERIFICATION_METHODS:
        violations.append(
            {"issue": "invalid_method", "method": method, "requirement_id": requirement_id}
        )
    else:
        if stage in VERIFICATION_STAGES and not is_method_applicable_at_stage(method, stage):
            violations.append(
                {
                    "issue": "method_not_applicable_at_stage",
                    "method": method,
                    "stage": stage,
                    "requirement_id": requirement_id,
                }
            )
        for risk_violation in risk_assessment_violations(method, entry.get("risk_assessment")):
            violations.append({"requirement_id": requirement_id, **risk_violation})

    status = entry.get("status")
    if status not in STATUS_VALUES:
        violations.append(
            {"issue": "invalid_status", "status": status, "requirement_id": requirement_id}
        )

    return violations


def rollup_status(entries):
    """Closure roll-up by verification level for a set of already-valid
    strategy entries. entries: iterable of {"level", "status"} dicts
    for requirements that need verification. Returns {level: {"total",
    "closed", "percent_closed"}, ..., "overall": {...}}. Raises
    ValueError for an entry with an unrecognized level or status."""
    counts = {level: {"total": 0, "closed": 0} for level in VERIFICATION_LEVELS}
    overall = {"total": 0, "closed": 0}
    for entry in entries:
        level = entry.get("level")
        status = entry.get("status")
        if level not in VERIFICATION_LEVELS:
            raise ValueError("unrecognized verification level: %r" % (level,))
        if status not in STATUS_VALUES:
            raise ValueError("unrecognized verification status: %r" % (status,))
        counts[level]["total"] += 1
        overall["total"] += 1
        if status == "closed":
            counts[level]["closed"] += 1
            overall["closed"] += 1

    result = {}
    for level, count in counts.items():
        total = count["total"]
        closed = count["closed"]
        percent = (closed / total * 100.0) if total else 0.0
        result[level] = {"total": total, "closed": closed, "percent_closed": percent}
    overall_total = overall["total"]
    overall_closed = overall["closed"]
    overall_percent = (overall_closed / overall_total * 100.0) if overall_total else 0.0
    result["overall"] = {
        "total": overall_total,
        "closed": overall_closed,
        "percent_closed": overall_percent,
    }
    return result


def is_verification_plan_complete(rollup):
    """True when the roll-up has at least one entry and every entry is
    closed -- the clause 5.2.1 approach is fully discharged."""
    return rollup["overall"]["total"] > 0 and rollup["overall"]["percent_closed"] == 100.0
