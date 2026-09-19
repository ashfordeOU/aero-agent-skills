---
name: q2007-planning
description: "Plan the quality and safety of a space test centre as ECSS-Q-ST-20-07 clause 5.3.2 asks, and say whether the plan in place can be run to. Use when a test centre's objectives, resourcing or management programmes are being set or audited: refuse a plan never established, name the objectives carrying no metric, no numeric target or no direction, name the ones nobody owns, take resource coverage against what the objectives require rather than against what the centre holds, find the objectives no approved programme carries, and read attainment in both directions with an exact equality settled by tolerance. Trigger: ecss, q-st-20-07-clause-5-3-2, test-centre-quality-objective-measurability, test-centre-objective-attainment-direction, test-centre-resource-planning-coverage, test-centre-management-programme-coverage."
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
  tags: [ecss, q-st-20-07-test-centre-quality-and-safety-scope, q2007-planning, q-st-20-07-clause-5-3-2, test-centre-quality-objective-measurability, test-centre-objective-attainment-direction, test-centre-resource-planning-coverage, test-centre-management-programme-coverage, test-centre-objective-ownership]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test-Centre Quality and Safety — Planning (space-systems/ecss/q2007-planning)

Use when the task is clause 5.3.2 of ECSS-Q-ST-20-07: the test centre
plans its quality and safety — the objectives it sets, the resources it
puts behind them, and the management programmes that carry them — and
the question is whether that plan is one the centre can actually be held
to.

## Domain quick reference

- An objective nobody can measure is an intention. A metric name, a
  finite numeric target and a direction saying which way is better are
  what make it checkable, and an objective missing any of the three is
  counted as unmeasurable rather than as merely unmet. The distinction
  matters because an unmet objective is a performance question and an
  unmeasurable one is a planning defect.
- Attainment depends on the direction. Two escapes against a target of
  five is attained; two on-time deliveries against a target of five is
  not. The comparison lives in one place so the direction cannot be
  applied inconsistently across a register.
- The equality case is the one that moves between hosts. An achieved
  value computed as a ratio can land a few units in the last place off
  its target, so the comparison carries a tolerance rather than a bare
  inequality on either side.
- Resource coverage is taken against what the objectives require, and
  over-planning one line does not pay for under-planning another. Each
  line is capped at its own requirement before the ratio is formed,
  otherwise a surplus of conductor hours hides a safety-officer gap.
- A programme is the vehicle an objective travels in. Only an approved
  programme carries anything, and by default a programme with no
  milestone is a title rather than a plan. An objective no programme
  carries has nobody driving it.
- A programme pointing at an objective that does not exist is a wrong
  entry, not a missing one. It is carried as an advisory so it cannot be
  confused with the objectives that genuinely have no vehicle.

## Workflow

1. Validate the planning policy first: the resource coverage and
   objective attainment the centre set itself, whether an owner is
   demanded per objective, and whether a programme needs milestones to
   count. An unrecognised key is refused rather than ignored.
2. Validate the plan: finite numeric targets where present, recognised
   directions and programme states, a positive requirement on every
   resource line, non-negative planned quantities, and nothing
   registered twice.
3. Name the unmeasurable objectives, and stop there if any exist —
   attainment across a register containing one of them is not a number
   worth reporting.
4. Name the objectives nobody owns, when the policy demands an owner.
5. Take resource coverage with each line capped at its own requirement,
   and name each under-planned line with the size of its shortfall.
6. Take the objectives no approved programme carries, and separately the
   programme references pointing at no objective.
7. Take attainment across the measurable objectives in each objective's
   own direction, comparing against the target with a tolerance.
8. Close on one verdict in order: plan absent, objectives unmeasurable,
   objectives unowned, resources under-planned, objectives uncovered, or
   plan established. Carry the dangling references and the attainment
   shortfall as advisories.

## Pitfalls

- Reading an unmet objective as an unmeasurable one, or the reverse.
  One needs management attention on the result, the other needs the
  objective rewritten before any result means anything.
- Applying one direction to a whole register. Defect counts and
  availability fractions sit in the same table and move opposite ways;
  a single comparison across both silently inverts half the verdicts.
- Summing planned units against summed requirements without capping. A
  surplus on the cheapest line pays for a gap on the one that actually
  binds, and the coverage ratio reports a plan that cannot be run.
- Counting a draft or milestone-free programme as coverage. Nothing is
  scheduled, so the objective has no vehicle whatever the register says.
- Treating a dangling programme reference as an uncovered objective.
  The objective does not exist; what needs correcting is the programme,
  and merging the two invents work nobody has to do.

## Behavior contract (gate 3)

The policy validation, objective, resource and programme validation, the
measurability and ownership gaps, attainment in both directions
including the exact-equality case, resource coverage with per-line
capping, the programme coverage and dangling references, and the ordered
verdict are exercised by the gate 3 contract test:
scripts/test_q2007_planning.py against scripts/q2007_planning_logic.py
(stdlib unittest, offline). Run: python3 scripts/test_q2007_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
