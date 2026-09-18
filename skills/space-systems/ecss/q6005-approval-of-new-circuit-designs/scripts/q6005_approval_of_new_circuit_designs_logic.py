#!/usr/bin/env python3
"""Approval sequence for a hybrid circuit design with no predecessor.

Anchor: ECSS-Q-ST-60-05C clause 7.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

When a hybrid circuit design has no qualified predecessor to lean on,
none of the lighter clause 7.3 routes are open to it and the whole
approval sequence is owed. The sequence is a dependency graph, not a
checklist: several stages can be live at once, and a stage whose
prerequisites are not finished has not really started however it was
recorded.

The stage set below is ordered so that every prerequisite appears before
the stage that needs it, which makes the tuple order a valid topological
order and lets the critical path be computed in one forward pass.

Stage states

    not-started   no work booked against it yet
    in-progress   open, with an optional remaining-days override
    complete      finished and accepted
    failed        ran and did not pass; the grant is held, not delayed

Nominal durations are a declared planning policy rather than a property
of the standard, and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

STAGE_STATES = ("not-started", "in-progress", "complete", "failed")

NEW_DESIGN_STAGES = (
    {
        "id": "design-definition-review",
        "prerequisites": (),
        "nominal_days": 20,
    },
    {
        "id": "technology-and-parts-selection",
        "prerequisites": ("design-definition-review",),
        "nominal_days": 25,
    },
    {
        "id": "engineering-model-build",
        "prerequisites": ("technology-and-parts-selection",),
        "nominal_days": 40,
    },
    {
        "id": "design-verification-testing",
        "prerequisites": ("engineering-model-build",),
        "nominal_days": 35,
    },
    {
        "id": "manufacturing-process-identification",
        "prerequisites": ("technology-and-parts-selection",),
        "nominal_days": 30,
    },
    {
        "id": "qualification-lot-manufacture",
        "prerequisites": (
            "design-verification-testing",
            "manufacturing-process-identification",
        ),
        "nominal_days": 45,
    },
    {
        "id": "qualification-test-programme",
        "prerequisites": ("qualification-lot-manufacture",),
        "nominal_days": 60,
    },
    {
        "id": "qualification-results-evaluation",
        "prerequisites": ("qualification-test-programme",),
        "nominal_days": 20,
    },
    {
        "id": "circuit-type-approval-grant",
        "prerequisites": (
            "qualification-results-evaluation",
            "design-verification-testing",
        ),
        "nominal_days": 10,
    },
)

STAGE_IDS = tuple(stage["id"] for stage in NEW_DESIGN_STAGES)
STAGE_BY_ID = {stage["id"]: stage for stage in NEW_DESIGN_STAGES}
GRANT_STAGE = "circuit-type-approval-grant"

APPROVAL_GRANTED = "approval-granted"
APPROVAL_PENDING = "approval-pending"
APPROVAL_HELD_BY_FAILURE = "approval-held-by-failure"
APPROVAL_SEQUENCE_BROKEN = "approval-sequence-broken"


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_non_negative_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def validate_stage_order():
    """Confirm the stage tuple really is a topological order.

    Every prerequisite has to appear before the stage that needs it, or
    the single forward pass used for the critical path is wrong.
    """
    seen = []
    for stage in NEW_DESIGN_STAGES:
        for prerequisite in stage["prerequisites"]:
            if prerequisite not in STAGE_BY_ID:
                raise ValueError(
                    "stage %s names an unknown prerequisite %s"
                    % (stage["id"], prerequisite)
                )
            if prerequisite not in seen:
                raise ValueError(
                    "stage %s precedes its prerequisite %s"
                    % (stage["id"], prerequisite)
                )
        seen.append(stage["id"])
    return True


def validate_stage_states(states):
    """Check every stage is present and carries a known state."""
    _require_mapping("states", states)
    unknown = sorted(set(states) - set(STAGE_IDS))
    if unknown:
        raise ValueError("unknown stages: %s" % ", ".join(unknown))
    missing = [stage for stage in STAGE_IDS if stage not in states]
    if missing:
        raise ValueError(
            "no state declared for: %s; an undeclared stage is not started, "
            "not absent, so declare it" % ", ".join(missing)
        )
    for stage_id in STAGE_IDS:
        _require_choice("state of %s" % stage_id, states[stage_id], STAGE_STATES)
    return {stage_id: states[stage_id] for stage_id in STAGE_IDS}


def validate_remaining_days(remaining_days):
    """Check an optional remaining-days override table."""
    table = _require_mapping(
        "remaining_days", remaining_days if remaining_days is not None else {}
    )
    unknown = sorted(set(table) - set(STAGE_IDS))
    if unknown:
        raise ValueError(
            "remaining_days names unknown stages: %s" % ", ".join(unknown)
        )
    for stage_id, days in table.items():
        _require_non_negative_int("remaining_days[%s]" % stage_id, days)
    return dict(table)


def unmet_prerequisites(stage_id, states):
    """Prerequisites of one stage that are not complete."""
    _require_choice("stage_id", stage_id, STAGE_IDS)
    validated = validate_stage_states(states)
    return [
        prerequisite
        for prerequisite in STAGE_BY_ID[stage_id]["prerequisites"]
        if validated[prerequisite] != "complete"
    ]


def next_executable_stages(states):
    """Stages that may be worked now: open, with every prerequisite done."""
    validated = validate_stage_states(states)
    return [
        stage_id
        for stage_id in STAGE_IDS
        if validated[stage_id] in ("not-started", "in-progress")
        and not unmet_prerequisites(stage_id, validated)
    ]


def sequence_violations(states):
    """Stages recorded as done or running ahead of their prerequisites."""
    validated = validate_stage_states(states)
    violations = []
    for stage_id in STAGE_IDS:
        if validated[stage_id] not in ("complete", "in-progress"):
            continue
        unmet = unmet_prerequisites(stage_id, validated)
        if unmet:
            violations.append(
                {
                    "stage": stage_id,
                    "state": validated[stage_id],
                    "unmet_prerequisites": unmet,
                }
            )
    return violations


def failed_stages(states):
    """Stages that ran and did not pass."""
    validated = validate_stage_states(states)
    return [stage_id for stage_id in STAGE_IDS if validated[stage_id] == "failed"]


def stage_cost_days(stage_id, states, remaining_days=None):
    """Working days still owed by one stage."""
    _require_choice("stage_id", stage_id, STAGE_IDS)
    validated = validate_stage_states(states)
    table = validate_remaining_days(remaining_days)
    if validated[stage_id] == "complete":
        return 0
    if stage_id in table:
        return table[stage_id]
    return STAGE_BY_ID[stage_id]["nominal_days"]


def remaining_critical_path_days(states, remaining_days=None):
    """Longest remaining chain through the stage graph, in working days.

    One forward pass over the stage tuple is enough because the tuple is
    a topological order, which validate_stage_order() checks.
    """
    validate_stage_order()
    validated = validate_stage_states(states)
    table = validate_remaining_days(remaining_days)
    finish = {}
    for stage_id in STAGE_IDS:
        starts = [finish[p] for p in STAGE_BY_ID[stage_id]["prerequisites"]]
        earliest = max(starts) if starts else 0
        finish[stage_id] = earliest + stage_cost_days(stage_id, validated, table)
    return max(finish.values())


def completion_fraction(states):
    """Share of the total nominal effort already complete."""
    validated = validate_stage_states(states)
    total = sum(stage["nominal_days"] for stage in NEW_DESIGN_STAGES)
    done = sum(
        STAGE_BY_ID[stage_id]["nominal_days"]
        for stage_id in STAGE_IDS
        if validated[stage_id] == "complete"
    )
    return done / total


def approval_decision(states):
    """Verdict on the grant, in priority order."""
    validated = validate_stage_states(states)
    if sequence_violations(validated):
        return APPROVAL_SEQUENCE_BROKEN
    if failed_stages(validated):
        return APPROVAL_HELD_BY_FAILURE
    if all(validated[stage_id] == "complete" for stage_id in STAGE_IDS):
        return APPROVAL_GRANTED
    return APPROVAL_PENDING


def plan_new_design_approval(case):
    """Full clause 7.3.2 sequence position with a verdict and findings."""
    _require_mapping("case", case)
    states = validate_stage_states(case.get("states"))
    table = validate_remaining_days(case.get("remaining_days"))
    violations = sequence_violations(states)
    failures = failed_stages(states)
    verdict = approval_decision(states)
    findings = []
    for violation in violations:
        findings.append(
            "%s is recorded %s while %s is not complete"
            % (
                violation["stage"],
                violation["state"],
                ", ".join(violation["unmet_prerequisites"]),
            )
        )
    for stage_id in failures:
        findings.append(
            "%s failed; the grant is held until the failure is dispositioned "
            "and the stage is rerun" % stage_id
        )
    if states[GRANT_STAGE] == "complete" and verdict != APPROVAL_GRANTED:
        findings.append(
            "the grant stage is recorded complete but the sequence behind it "
            "is not; the approval does not stand on that record"
        )
    return {
        "verdict": verdict,
        "next_executable_stages": next_executable_stages(states),
        "sequence_violations": violations,
        "failed_stages": failures,
        "completion_fraction": completion_fraction(states),
        "remaining_critical_path_days": remaining_critical_path_days(states, table),
        "findings": findings,
    }
