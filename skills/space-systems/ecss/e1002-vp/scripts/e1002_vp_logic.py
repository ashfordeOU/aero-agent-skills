#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.8.1 and Annex A verification plan (VP)
assembly (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
Verification Plan records, for every requirement in scope, the
verification method, level, and stage already selected by the
method-selection and stage/level-planning activities elsewhere in the
E-ST-10-02C process, plus -- per Annex A -- the model or tool that will
be used to close out an analysis or test entry. Not every method makes
sense at every stage: qualification is the only stage broad enough to
exercise all four methods; acceptance and pre-launch (checking a
delivered/flight article rather than re-deriving design margin) allow
only inspection and test; in-orbit (no physical access) allows only
analysis and test. Each entry also carries a closure status, and the
plan as a whole is not closed until no entry is left open. This module
implements the VP entry completeness/consistency check, the stage/
method applicability check, and the plan-level closure roll-up; it
does not implement the method-selection decision itself (see the
method-selection leaves) or the level/stage definitions (see the
level/stage leaves).
"""

VERIFICATION_METHODS = frozenset(
    {"review_of_design", "analysis", "inspection", "test"}
)
VERIFICATION_LEVELS = frozenset({"equipment", "subsystem", "system"})
VERIFICATION_STAGES = frozenset(
    {"qualification", "acceptance", "pre_launch", "in_orbit"}
)
CLOSURE_STATUSES = frozenset({"open", "in_work", "closed"})

# Which methods a given stage can meaningfully carry. Qualification
# establishes design margin so it can carry all four; acceptance and
# pre-launch check a delivered/flight article rather than re-derive
# margin so they are restricted to inspection and test; in-orbit has no
# physical access so it is restricted to analysis and test.
STAGE_METHOD_APPLICABILITY = {
    "qualification": frozenset({"review_of_design", "analysis", "inspection", "test"}),
    "acceptance": frozenset({"inspection", "test"}),
    "pre_launch": frozenset({"inspection", "test"}),
    "in_orbit": frozenset({"analysis", "test"}),
}

# Methods whose closure evidence, per Annex A, must be tied to a named
# model (analysis) or tool/rig (test); review of design and inspection
# close out on design data or physical examination and need neither.
MODEL_OR_TOOL_REQUIRED_METHODS = frozenset({"analysis", "test"})


def method_applicable_at_stage(method, stage):
    """True if the verification stage can carry the given method.
    Raises ValueError for an unrecognized method or stage."""
    if method not in VERIFICATION_METHODS:
        raise ValueError("unrecognized verification method %r" % (method,))
    if stage not in VERIFICATION_STAGES:
        raise ValueError("unrecognized verification stage %r" % (stage,))
    return method in STAGE_METHOD_APPLICABILITY[stage]


def vp_entry_completeness(entry):
    """Completeness/consistency issues for one VP entry (a single
    requirement's row in the verification plan).

    entry: {"requirement_id", "method", "level", "stage",
    "model_or_tool", "closure_status"}. Returns a list of issue dicts,
    empty when the entry is complete and consistent. Raises ValueError
    for a method/level/stage/closure_status value outside the
    recognized sets -- those are malformed input, not VP findings."""
    requirement_id = entry["requirement_id"]
    method = entry["method"]
    level = entry["level"]
    stage = entry["stage"]
    closure_status = entry["closure_status"]

    if method not in VERIFICATION_METHODS:
        raise ValueError("unrecognized verification method %r" % (method,))
    if level not in VERIFICATION_LEVELS:
        raise ValueError("unrecognized verification level %r" % (level,))
    if stage not in VERIFICATION_STAGES:
        raise ValueError("unrecognized verification stage %r" % (stage,))
    if closure_status not in CLOSURE_STATUSES:
        raise ValueError("unrecognized closure status %r" % (closure_status,))

    issues = []
    if not method_applicable_at_stage(method, stage):
        issues.append(
            {
                "issue": "method_not_applicable_at_stage",
                "requirement": requirement_id,
                "method": method,
                "stage": stage,
            }
        )
    if method in MODEL_OR_TOOL_REQUIRED_METHODS and not entry.get("model_or_tool"):
        issues.append(
            {
                "issue": "missing_model_or_tool",
                "requirement": requirement_id,
                "method": method,
            }
        )
    return issues


def verification_plan_completeness(entries):
    """Completeness issues for every entry in a verification plan,
    keyed by requirement_id. Raises ValueError for an empty plan or for
    two entries sharing a requirement_id (the VP must carry exactly one
    entry per requirement)."""
    if not entries:
        raise ValueError("verification plan has no entries to review")
    seen = set()
    review = {}
    for entry in entries:
        requirement_id = entry["requirement_id"]
        if requirement_id in seen:
            raise ValueError(
                "duplicate verification plan entry for requirement %r"
                % (requirement_id,)
            )
        seen.add(requirement_id)
        review[requirement_id] = vp_entry_completeness(entry)
    return review


def rollup_closure_status(entries):
    """Overall VP closure status from a list of entries' closure_status
    values, in priority order open > in_work > closed -- a single open
    entry keeps the whole plan open regardless of the rest. Raises
    ValueError for an empty entry list or an unrecognized
    closure_status."""
    if not entries:
        raise ValueError("cannot roll up closure status of an empty verification plan")
    statuses = set()
    for entry in entries:
        status = entry["closure_status"]
        if status not in CLOSURE_STATUSES:
            raise ValueError("unrecognized closure status %r" % (status,))
        statuses.add(status)
    if "open" in statuses:
        return "open"
    if "in_work" in statuses:
        return "in_work"
    return "closed"


def verification_plan_review(entries):
    """Full clause 5.2.8.1 / Annex A VP review: per-entry completeness
    plus the overall closure roll-up. Raises ValueError as per
    verification_plan_completeness and rollup_closure_status."""
    return {
        "completeness": verification_plan_completeness(entries),
        "overall_closure_status": rollup_closure_status(entries),
    }


def is_verification_plan_ready(review):
    """True when every entry is complete/consistent (no issues) and the
    plan's overall closure status is "closed" -- the VP is ready to
    support sign-off."""
    all_complete = all(
        len(issues) == 0 for issues in review["completeness"].values()
    )
    return all_complete and review["overall_closure_status"] == "closed"
