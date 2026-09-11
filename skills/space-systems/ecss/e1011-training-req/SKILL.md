---
name: e1011-training-req
description: "Use when define training requirements and materials for operator tasks derived from operational products under ECSS-E-ST-10-11C §4.9.5: determine the training need tier for each task from task complexity, procedural novelty, and safety criticality (routine / standard / enhanced / specialized); verify that the minimum required training materials exist for the assigned tier; confirm that every personnel role performing the task holds a training assignment before first operational use; and assess whether available training time and scheduling window meet the tier minimum. Trigger: ecss, e-st-10-system-scope, e-st-10-11c, training-requirements, training-need-assessment, training-materials, personnel-roles, human-factors-engineering, hfe."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, training-requirements, training-need-assessment, training-materials, personnel-roles, human-factors-engineering, hfe]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Training Requirements (space-systems/ecss/e1011-training-req)

Use when the task is to define training requirements and materials for operator
tasks derived from operational products under ECSS-E-ST-10-11C §4.9.5 —
determining the training need tier per task, verifying required training
materials are in place, confirming personnel role coverage, and checking that
the training programme fits within the operational timeline.

## Domain quick reference

- §4.9.5 requires that training requirements be derived from the operational
  products produced during the development lifecycle: the operations concept,
  task analyses, operations procedures, and interface control documents. Each
  identified operator task is evaluated on three attributes — task complexity
  (low / medium / high), procedural novelty (whether the task involves a
  procedure not previously mastered by the target crew), and safety criticality
  (whether an error in the task can result in loss of mission, crew injury, or
  hardware damage). These three attributes together determine the training need
  tier assigned to the task.
- Four training need tiers are defined. A **routine** tier applies to
  low-complexity, familiar, non-safety-critical tasks; a procedure checklist is
  the minimum required material. A **standard** tier applies to medium-
  complexity or novel tasks; a training manual and a knowledge assessment are
  additionally required. An **enhanced** tier applies to high-complexity or
  safety-critical tasks; a simulation exercise is additionally required. A
  **specialized** tier applies when a task is simultaneously high-complexity,
  novel, and safety-critical; a certification record is additionally required on
  top of all enhanced materials. A task is assigned the highest tier reached by
  any of its three attributes.
- Required materials are the minimum set for the tier; additional materials
  are permitted but do not substitute for missing required ones. A training
  material is present only when it is a completed, reviewed artefact, not a
  draft or placeholder.
- Personnel role coverage: every role listed as performing the task must
  receive a training assignment before the task is declared operationally ready.
  An unassigned role is an open finding that blocks readiness declaration.
- Schedule adequacy: the available training hours must meet or exceed the tier
  minimum (routine 1 h, standard 8 h, enhanced 24 h, specialized 40 h) and,
  for non-routine tiers, at least one calendar day must remain before the
  operational deadline so that formal training can be scheduled. Routine tier
  only requires the hours check.

## Workflow

1. Collect all operator tasks from the operational products. Each task entry
   must carry a task-complexity rating, a procedural-novelty flag, and a
   safety-criticality flag. Flag any task missing one or more attributes before
   proceeding — an unrated task cannot be tiered.
2. For each task, apply the tier-determination rule: assign **specialized** if
   the task is high-complexity AND novel AND safety-critical; assign
   **enhanced** if it is safety-critical OR high-complexity; assign
   **standard** if it is novel OR medium-complexity; otherwise assign
   **routine**.
3. For each task, derive the required materials set from its tier and compare
   it against the provided materials. Record every missing material type as a
   finding against the task.
4. For each task, collect the full list of personnel roles that perform the
   task and compare it against the list of roles that have received a training
   assignment. Record every uncovered role as a finding.
5. For each task, confirm that available training hours meet the tier minimum
   and that, for non-routine tiers, the operational deadline is at least one
   day away. Record a schedule insufficiency finding if either condition fails.
6. A task is compliant when its missing-materials list is empty, its
   uncovered-roles list is empty, and its schedule is adequate. Any finding
   must be resolved before the training requirement record for that task can be
   closed.
7. Aggregate compliant and non-compliant tasks into the training requirements
   document. Include the tier rationale, the required and provided materials,
   the role coverage table, and the schedule confirmation for each task. This
   document becomes the HFE deliverable for the training programme.

## Pitfalls

- Assigning the tier from a single attribute and ignoring the others —
  all three attributes (complexity, novelty, criticality) must be evaluated;
  a task that scores low on two attributes but high on one still reaches the
  higher tier.
- Counting draft or placeholder artefacts as completed training materials —
  a material is only present when it has passed review; a draft checklist does
  not satisfy the procedure-checklist requirement.
- Treating a personnel role as covered because training was planned but not
  yet assigned — coverage is confirmed only when a training assignment record
  exists for the role, not when training is informally intended.
- Conflating the training approach (which delivery method, which strategy)
  with the training requirement (which tier, which materials, which roles) —
  both records are needed but are maintained separately; the training
  requirement drives the training approach, not the other way around.
- Treating schedule adequacy as met simply because the hours are available
  without checking the calendar deadline — for enhanced and specialized tiers
  the formal scheduling window (days until operational) must also be confirmed.

## Behavior contract (gate 3)

The tier-determination, material-completeness, role-coverage, and
schedule-adequacy logic is exercised by the gate 3 contract test:
scripts/test_e1011_training_req.py against
scripts/e1011_training_req_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_training_req.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
