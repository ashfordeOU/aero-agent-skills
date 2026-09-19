---
name: e2040-device-design-verification-tasks
description: "Structure the design and verification task set ECSS-E-ST-20-40C clause 5.4.3 puts on the supplier: separate the engineering tasks that produce a design item from the checking tasks that examine one, order the whole set by its prerequisites and refuse a cycle, find every design output no checking task looks at, flag a checking task aimed at an item nothing produces, refuse a task reported complete while a prerequisite is open or its evidence is absent, and compare verification coverage against the phase threshold so a value landing exactly on it passes. Use when the design and verification task list is planned, reviewed or tracked. Trigger: ecss, e-st-20-electrical-scope, device-design-verification-tasks, design-task-prerequisite-ordering, design-output-verification-coverage, verification-task-target-check, design-task-completion-evidence."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-design-verification-tasks, device-design-verification-tasks, design-task-prerequisite-ordering, design-output-verification-coverage, verification-task-target-check, design-task-completion-evidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Design and Verification Tasks (space-systems/ecss/e2040-device-design-verification-tasks)

Use when the task is the supplier duty of ECSS-E-ST-20-40C clause 5.4.3
-- saying whether the engineering and checking activities of the design
and verification phase form a set that can actually be run, and whether
what the engineering activities produce is what the checking activities
examine.

## Domain quick reference

- Two kinds of activity share the phase. An engineering task produces a
  named design item; a checking task examines one or more items some
  other task produced. A task doing both is a description of work, not
  a task, and it hides which half slipped when the phase runs late.
- The pairing between the two kinds is the whole point of the set. A
  design item produced and never examined is the defect this check
  exists for: the plan looks complete because every task has an owner
  and a date, and nothing in the task list says the item was never
  looked at.
- A checking task aimed at an item no engineering task produces is the
  mirror defect. It cannot start, it is invisible in a task-by-task
  read, and it is usually a renamed design item rather than a missing
  one.
- Prerequisites order the set. A set whose prerequisites close a loop
  has no order at all, so it is refused as an input defect rather than
  reported as a finding -- there is nothing to schedule and nothing to
  report against.
- Completion has two conditions, not one. A task reported complete
  while a prerequisite is still open has been closed against a
  precondition that never held, and a task reported complete with no
  evidence has recorded an opinion.
- Coverage is a fraction of the design items produced. A threshold met
  exactly is met, so the comparison absorbs representation error: a
  three-in-four landing on a 0.75 threshold is a pass, and a strict
  comparison against a computed division is what turns a compliant
  phase red.

## Workflow

1. Resolve every task: unique identifier, kind folded onto engineering
   or checking, the item it produces or the items it examines, its
   prerequisites, its evidence and its status. Refuse a repeated
   identifier or an unknown key as an input defect.
2. Refuse a task that both produces and examines an item, and a task
   whose kind carries neither.
3. Order the set by prerequisites and refuse a cycle or a prerequisite
   naming no task.
4. Collect the items the engineering tasks produce, and report each one
   no checking task examines.
5. Report each checking task naming an item nothing produces.
6. Report each task reported complete whose prerequisite is still open,
   and each one carrying no evidence.
7. Compute verification coverage over the produced items and compare it
   against the phase threshold, absorbing representation error and
   never widening the threshold itself.

## Pitfalls

- Reading task completion as phase progress. Every task can be closed
  and still leave a design item nobody examined, because the checking
  task for it was never written rather than left open.
- Letting one task both produce and examine. The set then reports one
  status for two activities, and the checking half is always the half
  assumed done.
- Dropping a checking task whose target does not exist. It is nearly
  always a renamed design item, and deleting the task deletes the only
  record that the item was meant to be examined.
- Closing a task ahead of its prerequisite. The precondition the work
  depended on never held, and the finding surfaces only when the item
  is examined much later in the phase.
- Comparing a computed coverage fraction against its threshold with a
  strict inequality. A three-in-four division landing on 0.75 can sit a
  unit in the last place below it and fail a phase that is exactly on
  target.

## Behavior contract (gate 3)

The task resolution, kind folding, prerequisite ordering with cycle
refusal, produced-item and examined-item pairing, completion-evidence
and prerequisite-order checks and the coverage-threshold comparison are
exercised by the gate 3 contract test:
scripts/test_e2040_device_design_verification_tasks.py against
scripts/e2040_device_design_verification_tasks_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_design_verification_tasks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
