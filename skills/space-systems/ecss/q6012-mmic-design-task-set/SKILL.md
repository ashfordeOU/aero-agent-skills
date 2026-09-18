---
name: q6012-mmic-design-task-set
description: "Determine whether the collected engineering activities declared for a microwave monolithic integrated circuit development actually cover the design effort, under ECSS-Q-ST-60-12 clause 7.2. Use when a project submits its MMIC design task set with owners, deliverables, effort and states and someone must authorise the work: refuse a duplicate task identifier, a free-text state or a non-positive declared effort, name the mandated design activities no task serves, separate a project extra from a genuine gap, list the tasks carrying no owner or no named deliverable, expose a single activity holding most of the effort, and weight the completion ratio by effort rather than task count. Trigger: ecss, q-st-60-12, mmic-design-task-set, mmic-design-activity-coverage, mmic-design-effort-weighting, mmic-design-task-ownership, mmic-design-deliverable-gap."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-mmic-design-task-set, mmic-design-activity-coverage, mmic-design-effort-weighting, mmic-design-task-ownership, mmic-design-deliverable-gap, mmic-design-task-authorisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMICs — Design Task Set (space-systems/ecss/q6012-mmic-design-task-set)

Use when the task is the design-task-set step of ECSS-Q-ST-60-12 clause 7.2 —
naming the engineering activities that together make up a microwave monolithic
integrated circuit development effort, and judging whether the set a project
declared is complete enough to authorise work against.

## Domain quick reference

- The task set is the definition of the effort, not a schedule of it. It
  answers what engineering has to happen for this circuit at all; the order,
  the durations and the critical path are a separate question asked of the same
  activities afterwards.
- The mandated activities are the electrical design specification, circuit
  design, layout design, electromagnetic simulation, thermal design,
  reliability and lifetime design, process design-rule verification, and design
  review. A project may serve one of these with several tasks and may add tasks
  of its own, but an activity nothing serves is a gap in the effort.
- Electromagnetic simulation and process design-rule verification are the two
  most often folded into circuit design and layout design respectively. On a
  monolithic part they are not sub-steps: the passive structures are
  distributed, so their behaviour comes from a field solution rather than the
  schematic, and the foundry rule deck is what decides whether the drawn layout
  can be made at all.
- A declared task without a responsible owner and a declared task without a
  named deliverable are the same defect in two forms: neither can be reviewed,
  so neither is evidence that the activity happened.
- Effort is the honest weight. A task set reported by task count says a
  development is two-thirds done when the two finished tasks were a week each
  and the open one is six months, so completion is taken against declared
  effort and the count-based figure is reported only alongside it.
- One activity holding most of the declared effort is a breakdown finding. It
  means the effort was never decomposed far enough to be tracked, and progress
  inside that activity is invisible until it finishes.

## Workflow

1. Validate every declared task: a unique identifier, an activity name
   normalised to canonical spelling, a state from the closed vocabulary, and a
   strictly positive declared effort. A free-text state and a zero effort are
   input errors, not degenerate cases to be absorbed.
2. Build the set, refusing a duplicate identifier outright so two tasks cannot
   both claim the same activity record.
3. Compare the declared activities against the mandated set. Report the
   activities no task serves as gaps in mandated order, and report activities
   outside the mandated set separately as project extras.
4. List the tasks that carry no owner and the tasks that name no deliverable,
   by identifier, so each can be repaired individually.
5. Sum the declared effort per activity and expose the share held by the single
   largest activity, comparing it with the breakdown limit and absorbing
   representation error at the equality with a named tolerance.
6. Derive the completion ratio by effort and, separately, by task count; report
   both so the difference between them is visible.
7. Return the authorisation verdict: the task set is authorised only when no
   mandated activity is unserved, every task has an owner and a deliverable,
   and no single activity exceeds the breakdown limit.

## Pitfalls

- Treating the task list as the schedule. The set says what has to be done;
  reading it top to bottom as an order invents a plan that nobody dependency-
  checked and that the durations were never applied to.
- Counting a mandated activity as covered because a neighbouring task mentions
  it. Coverage is a declared activity on a declared task; a sentence inside
  another task's deliverable is not an activity anybody owns.
- Reporting progress by task count. Small finished tasks and one large open
  task give a comfortable fraction and hide where the development actually is.
- Rejecting a project extra as a defect. A project may add activities of its
  own; the extras are reported so a reviewer sees the shape of the effort, and
  they neither fill a mandated gap nor create one.
- Accepting a single activity that carries most of the effort because the total
  looks right. The total is right and the plan is still untrackable, which is
  exactly the finding.
- Repairing an ownership gap by naming the project itself as the owner. An
  owner that is the whole project is the same as no owner when the deliverable
  is late.

## Behavior contract (gate 3)

The task validation, duplicate-identifier refusal, activity-coverage
comparison, project-extra separation, ownership and deliverable gap lists,
effort distribution and concentration limit, the two completion ratios and the
authorisation verdict are exercised by the gate 3 contract test:
scripts/test_q6012_mmic_design_task_set.py against
scripts/q6012_mmic_design_task_set_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6012_mmic_design_task_set.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
