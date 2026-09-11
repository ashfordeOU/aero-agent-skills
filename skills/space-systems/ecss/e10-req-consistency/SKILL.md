---
name: e10-req-consistency
description: "Use when identify and resolve internal inconsistencies inside a requirement baseline under ECSS-E-ST-10C clause 5.2.3.6: reduce each requirement that bounds a shared parameter to the feasible interval its constraint implies, intersect the intervals of a group to find a parameter no value can satisfy, and compare every requirement binding on a shared interface attribute to find the same attribute given two different values. Trigger: ecss, e-st-10-system-scope, requirement-consistency, conflicting-requirements, constraint-interval, feasible-range, interface-attribute, requirement-baseline."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-system-scope, requirement-consistency, conflicting-requirements, constraint-interval, interface-attribute, requirement-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Requirement Consistency (space-systems/ecss/e10-req-consistency)

Use when the task is to find and resolve contradictions *within* a
requirement baseline under ECSS-E-ST-10C clause 5.2.3.6 -- the same
parameter carrying irreconcilable value constraints, and a shared
interface described differently by the requirements that reference it.

## Domain quick reference

- Consistency is checked between requirements, not against a design.
  The question is whether any value at all could satisfy the set, so
  the check needs no implementation and no verification data.
- Each constraint reduces to a feasible interval: an exact constraint
  pins a single point, a maximum bounds the interval above, a minimum
  bounds it below. Reducing every kind to the same shape is what lets
  them be compared at all.
- A group of constraints on one parameter is inconsistent when the
  intersection of their intervals is empty -- the highest lower bound
  has risen above the lowest upper bound. That single test catches a
  minimum above a maximum, two conflicting exact values, and an exact
  value outside a bound, with no separate rule for each.
- The check is per group, and a group is defined by the parameter its
  requirements constrain. A group of zero or one requirement has
  nothing to conflict with and is consistent by construction.
- Units are a precondition, not a conversion step. A requirement in a
  multi-requirement group with no unit recorded is rejected, because
  comparing bare numbers across unrecorded units produces confident
  and wrong answers.
- Interface consistency is a separate check on a separate structure:
  requirement bindings grouped by the interface they describe. Two
  bindings naming the same attribute with different values conflict.
- An interface conflict is reported once per attribute, listing every
  requirement that bound it -- not once per pair. Three requirements
  disagreeing on one attribute is one thing to fix, not three.
- The requirement set is consistent only when both the value and the
  interface conflict lists are empty.

## Workflow

1. Group the requirements that constrain the same parameter, and the
   requirement bindings that describe the same interface.
2. For each value group with more than one requirement, confirm every
   requirement records a unit.
3. Reduce each constraint to its feasible interval by kind, then
   intersect the group's intervals.
4. Report an inconsistency for each group whose intersection is empty,
   naming the requirements involved.
5. For each interface, compare the bindings attribute by attribute and
   report one conflict per attribute given more than one value.
6. The requirement set is consistent only when both lists are empty.

## Pitfalls

- Writing a separate rule for each pairing of constraint kinds.
  Reducing every kind to an interval and intersecting covers them all,
  and hand-written pairings reliably miss a combination.
- Comparing constraint values whose units were never recorded. The
  arithmetic succeeds and the verdict is meaningless, which is why the
  missing unit is rejected rather than assumed.
- Reporting one conflict per conflicting pair on a shared interface
  attribute. Three requirements disagreeing generate three pairs but
  describe a single contradiction to resolve.
- Treating a single requirement bounding a parameter as a conflict
  risk. There is nothing to intersect it with, and flagging it buries
  the real conflicts in noise.
- Confusing an infeasible requirement set with an unmet one. Clause
  5.2.3.6 is about requirements that cannot all hold at once, whatever
  the design; a design failing to meet a consistent set is a
  verification finding instead.
- Silently widening an exact constraint to a tolerance band so the
  intersection becomes non-empty. That resolves the conflict on paper
  and leaves it in the baseline.

## Behavior contract (gate 3)

The constraint-interval, interval-intersection, value-conflict,
interface-attribute conflict and requirement-set aggregation logic is
exercised by the gate 3 contract test:
scripts/test_e10_req_consistency.py against
scripts/e10_req_consistency_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_consistency.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
