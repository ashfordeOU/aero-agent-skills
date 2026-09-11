---
name: e1011-training-approach
description: "Use when defining the training approach for human operators as required by ECSS-E-ST-10-11C §4.3.5: categorize each operator task by criticality and worst-case error consequence, determine the minimum required training level (awareness, procedural, or expert), select admissible training means (simulation, CBT, classroom, on-the-job, handbook, or briefing), assign a training strategy (initial, recurrent, refresher, or qualification), set the recurrent interval for strategies that repeat, and verify every identified task has a training approach record so no task enters operation without a traceable HFE training provision. Trigger: ecss, e-st-10-system-scope, e-st-10-11c, training-approach, human-factors-engineering, hfe, operator-training, training-level, training-strategy, training-means."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, training-approach, human-factors-engineering, hfe, operator-training, training-level, training-strategy, training-means]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Training Approach (space-systems/ecss/e1011-training-approach)

Use when the task is to define the training approach for human operators
under ECSS-E-ST-10-11C §4.3.5 — categorizing operator tasks by criticality,
selecting required training levels, choosing admissible training means, and
assigning strategies with validated recurrent intervals so that every task
that enters operation has a traceable HFE training provision.

## Domain quick reference

- §4.3.5 requires the programme to define, for each operator task, three
  things: the training level needed (awareness, procedural, or expert), the
  training means to achieve it, and the training strategy (initial,
  recurrent, refresher, or qualification). All three must be on record before
  the task is declared operationally ready.
- Training level is driven by two factors: task criticality (how important
  the task is to mission or safety success) and worst-case error consequence
  (catastrophic, critical, marginal, or negligible). A high-criticality task
  with a catastrophic error consequence demands expert-level training; a
  low-criticality task with a negligible consequence may be handled at
  awareness level. The selection table is deterministic and must not be
  overridden informally.
- Training means are the delivery vehicles: simulation delivers hands-on
  fidelity for expert and procedural levels; computer-based training (CBT)
  suits procedural and awareness levels; classroom instruction is applicable
  at all levels; on-the-job training (OJT) suits procedural and expert work
  under qualified supervision; handbooks and briefings cover awareness-level
  needs. A chosen means must fall within the admissible set for its level.
- Training strategy governs scheduling: initial training qualifies the
  operator before first task performance; recurrent training refreshes at a
  fixed interval; refresher training is triggered by a specific event (e.g.
  a gap in currency, a system change, or an incident); qualification training
  achieves a formal competency certification. Recurrent and refresher
  strategies must specify a maximum interval; the maximum interval shortens as
  the training level rises (expert training must be repeated more frequently
  than awareness training).
- Coverage completeness: every task on the identified operator task list must
  have a training approach record. A task without a record is a coverage gap
  and blocks the HFE training-approach closure.

## Workflow

1. Obtain the operator task list from the HFE task analysis (§4.3.4 output).
   Each task entry must carry a criticality rating and a worst-case error
   consequence rating; flag any task missing either before proceeding.
2. For each task, apply the level-selection table to derive the required
   training level from its criticality and error-consequence pair. The table
   is non-negotiable: if the project requires a deviation, a formal waiver
   against §4.3.5 is needed.
3. For each task, select at least one training means from the admissible set
   for the required level. If cost or schedule constraints push toward a means
   outside the admissible set, escalate as a risk before recording it.
4. Assign a training strategy to each task. For recurrent or refresher
   strategies, set the recurrent interval in months and confirm it does not
   exceed the maximum for the training level.
5. Record each task as a TrainingApproachRecord (task_id, criticality,
   error_consequence, assigned_level, strategy, means, recurrent interval if
   applicable) and run validate_training_approach_record against it; all
   findings must be resolved.
6. Run check_coverage against the full task list; any task_id with no record
   is a coverage gap that must be resolved before the training approach is
   considered complete.
7. Compile the training approach document: include the level-selection
   rationale per task, the chosen means and strategy, the schedule of
   recurrent events, and a signed coverage table. This document becomes the
   HFE input to the training programme definition.

## Pitfalls

- Selecting a lower training level informally to reduce cost without a
  formal waiver — the level-selection table is normative; undocumented
  downgrades leave the programme exposed during audits and safety reviews.
- Choosing a training means that is outside the admissible set for the
  required level — e.g. assigning briefing-only delivery for an expert-level
  task. The means must match the level or the training approach record is
  invalid.
- Leaving the recurrent interval unset for a recurrent or refresher strategy
  — a strategy that repeats with no interval bound provides no scheduling
  anchor and cannot be audited for currency compliance.
- Setting a recurrent interval that is longer than the maximum for the level
  — expert training decays faster than awareness training; extending the
  interval beyond the maximum produces operators who are out-of-currency
  before their next training event.
- Treating a coverage gap as a low-priority item — any operator task with no
  training approach record is operationally uncontrolled under §4.3.5; the
  gap must be closed or the task must be removed from the operator task list.

## Behavior contract (gate 3)

The level-selection, means-admissibility, record-validation, and
coverage-check logic is exercised by the gate 3 contract test:
scripts/test_e1011_training_approach.py against
scripts/e1011_training_approach_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_training_approach.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
