#!/usr/bin/env python3
"""Evaluation test flow that earns a die its application approval.

Anchor: ECSS-Q-ST-60-12C clause 8.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

An application approval is granted on the strength of an ordered set of
evaluation tests, not on the set alone. Order carries evidence: a
characterisation taken before a stress means nothing unless the same
samples are characterised again after it, and a step that consumes its
samples can have nothing downstream of it on those samples.

A step declares
    id              unique name of the evaluation step
    predecessors    steps whose result this step needs first
    destructive     whether the step consumes the samples it runs on
    sample_demand   how many samples the step needs at once
    duration_h      elapsed hours the step occupies
    sequence        declared preference used only to break ties in order

Sample groups
    The flow is cut into groups. A group runs its steps in order on one
    set of samples and ends at the destructive step that consumes them, so
    the samples a group needs is the largest single demand inside it and
    the demands of separate groups add.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import heapq
import math

# Evaluation steps an application approval flow has to contain before it
# can be run at all. Naming is the flow's own, not a catalogue reference.
MANDATORY_EVALUATION_STEPS = (
    "incoming-electrical-characterisation",
    "construction-analysis",
    "environmental-evaluation",
    "endurance-life-test",
    "post-test-electrical-verification",
)

# Order the evidence itself demands, independent of what a flow declares.
MANDATORY_ORDER_PAIRS = (
    ("incoming-electrical-characterisation", "environmental-evaluation"),
    ("incoming-electrical-characterisation", "endurance-life-test"),
    ("endurance-life-test", "post-test-electrical-verification"),
    ("environmental-evaluation", "post-test-electrical-verification"),
)

FLOW_EXECUTABLE = "flow-executable"
FLOW_BLOCKED = "flow-blocked"

_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def validate_test_step(step, position=0):
    """Normalise one declared evaluation step, raising on bad input."""
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping, got %r" % (step,))
    step_id = step.get("id")
    if not isinstance(step_id, str) or not step_id.strip():
        raise ValueError("step id must be a non-empty string, got %r" % (step_id,))
    predecessors = step.get("predecessors", ())
    if isinstance(predecessors, (str, bytes)) or not hasattr(predecessors, "__iter__"):
        raise ValueError("step %s predecessors must be a sequence" % step_id)
    predecessors = tuple(predecessors)
    for name in predecessors:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("step %s has a non-string predecessor" % step_id)
    if step_id in predecessors:
        raise ValueError("step %s lists itself as a predecessor" % step_id)
    if len(set(predecessors)) != len(predecessors):
        raise ValueError("step %s repeats a predecessor" % step_id)
    destructive = step.get("destructive", False)
    if not isinstance(destructive, bool):
        raise ValueError("step %s destructive flag must be a boolean" % step_id)
    sequence = step.get("sequence", position)
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise ValueError("step %s sequence must be an integer" % step_id)
    return {
        "id": step_id,
        "predecessors": predecessors,
        "destructive": destructive,
        "sample_demand": _require_positive_int(
            "step %s sample_demand" % step_id, step.get("sample_demand")
        ),
        "duration_h": _require_non_negative(
            "step %s duration_h" % step_id, step.get("duration_h", 0.0)
        ),
        "sequence": sequence,
    }


def validate_test_flow(steps):
    """Normalise a declared flow: unique ids, resolvable predecessors."""
    if isinstance(steps, dict) or not hasattr(steps, "__iter__"):
        raise ValueError("steps must be a sequence of mappings, got %r" % (steps,))
    normalised = [validate_test_step(step, i) for i, step in enumerate(steps)]
    if not normalised:
        raise ValueError("a flow must declare at least one evaluation step")
    seen = set()
    for step in normalised:
        if step["id"] in seen:
            raise ValueError("step id %s is declared twice" % step["id"])
        seen.add(step["id"])
    for step in normalised:
        for name in step["predecessors"]:
            if name not in seen:
                raise ValueError(
                    "step %s depends on %s, which the flow never declares"
                    % (step["id"], name)
                )
    return normalised


def order_test_flow(steps):
    """Deterministic execution order honouring every declared dependency."""
    normalised = validate_test_flow(steps)
    by_id = {step["id"]: step for step in normalised}
    remaining = {
        step["id"]: set(step["predecessors"]) for step in normalised
    }
    successors = {step["id"]: [] for step in normalised}
    for step in normalised:
        for name in step["predecessors"]:
            successors[name].append(step["id"])
    ready = [
        (by_id[sid]["sequence"], sid)
        for sid, preds in remaining.items()
        if not preds
    ]
    heapq.heapify(ready)
    order = []
    while ready:
        _, sid = heapq.heappop(ready)
        order.append(sid)
        for nxt in sorted(successors[sid]):
            remaining[nxt].discard(sid)
            if not remaining[nxt]:
                heapq.heappush(ready, (by_id[nxt]["sequence"], nxt))
    if len(order) != len(normalised):
        stuck = sorted(set(by_id) - set(order))
        raise ValueError(
            "the declared dependencies form a cycle through: %s" % ", ".join(stuck)
        )
    return order


def destructive_conflicts(steps):
    """Steps that need samples an earlier destructive step has consumed."""
    normalised = validate_test_flow(steps)
    by_id = {step["id"]: step for step in normalised}
    order = order_test_flow(steps)
    reachable = {sid: set() for sid in by_id}
    for sid in reversed(order):
        for pred in by_id[sid]["predecessors"]:
            reachable[pred].add(sid)
            reachable[pred].update(reachable[sid])
    conflicts = []
    for sid in order:
        if not by_id[sid]["destructive"]:
            continue
        for downstream in sorted(reachable[sid]):
            conflicts.append({"destructive_step": sid, "blocked_step": downstream})
    return conflicts


def allocate_sample_groups(steps):
    """Cut the ordered flow into sample groups and size each one."""
    normalised = validate_test_flow(steps)
    by_id = {step["id"]: step for step in normalised}
    groups = []
    current = []
    for sid in order_test_flow(steps):
        current.append(sid)
        if by_id[sid]["destructive"]:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    allocated = []
    for index, members in enumerate(groups):
        allocated.append(
            {
                "group": index,
                "steps": list(members),
                "sample_demand": max(by_id[sid]["sample_demand"] for sid in members),
                "ends_destructively": by_id[members[-1]]["destructive"],
            }
        )
    return allocated


def total_sample_demand(steps):
    """Samples the whole flow consumes, adding the demand of each group."""
    return sum(group["sample_demand"] for group in allocate_sample_groups(steps))


def flow_duration_h(steps):
    """Elapsed hours on the longest dependency chain through the flow."""
    normalised = validate_test_flow(steps)
    by_id = {step["id"]: step for step in normalised}
    finish = {}
    for sid in order_test_flow(steps):
        start = 0.0
        for pred in by_id[sid]["predecessors"]:
            start = max(start, finish[pred])
        finish[sid] = start + by_id[sid]["duration_h"]
    return max(finish.values()) if finish else 0.0


def mandatory_coverage(steps):
    """Mandatory steps the flow omits and evidence order it does not honour."""
    normalised = validate_test_flow(steps)
    present = {step["id"] for step in normalised}
    missing = [name for name in MANDATORY_EVALUATION_STEPS if name not in present]
    order = order_test_flow(steps)
    rank = {sid: i for i, sid in enumerate(order)}
    violations = []
    for before, after in MANDATORY_ORDER_PAIRS:
        if before in rank and after in rank and rank[before] > rank[after]:
            violations.append(
                {"required_before": before, "required_after": after}
            )
    return {"missing_steps": missing, "order_violations": violations}


def plan_approval_test_flow(case):
    """Full clause 8.2 evaluation flow with a runnability disposition."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    steps = case.get("steps")
    order = order_test_flow(steps)
    groups = allocate_sample_groups(steps)
    conflicts = destructive_conflicts(steps)
    coverage = mandatory_coverage(steps)
    demand = total_sample_demand(steps)
    available = case.get("available_samples")
    if available is None:
        shortfall = None
    else:
        available = _require_positive_int("available_samples", available)
        shortfall = max(0, demand - available)
    findings = []
    for name in coverage["missing_steps"]:
        findings.append("the flow omits the mandatory step %s" % name)
    for pair in coverage["order_violations"]:
        findings.append(
            "%s is ordered after %s, so its evidence cannot be read"
            % (pair["required_before"], pair["required_after"])
        )
    for conflict in conflicts:
        findings.append(
            "%s needs samples that %s consumes"
            % (conflict["blocked_step"], conflict["destructive_step"])
        )
    if shortfall:
        findings.append(
            "the flow needs %d samples and only %d are available" % (demand, available)
        )
    return {
        "order": order,
        "sample_groups": groups,
        "total_sample_demand": demand,
        "sample_shortfall": shortfall,
        "flow_duration_h": flow_duration_h(steps),
        "destructive_conflicts": conflicts,
        "missing_steps": coverage["missing_steps"],
        "order_violations": coverage["order_violations"],
        "findings": findings,
        "verdict": FLOW_BLOCKED if findings else FLOW_EXECUTABLE,
    }
