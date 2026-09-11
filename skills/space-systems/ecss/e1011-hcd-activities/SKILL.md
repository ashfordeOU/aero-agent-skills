---
name: e1011-hcd-activities
description: "Use when run HCD activities for a crewed or human-tended space
  system per ECSS-E-ST-10-11C §4.4.3: decompose human tasks into steps with
  performer roles and criticality levels via task analysis; capture user and
  organisational requirements with priority and category; produce design
  solution elements traceable to each requirement; evaluate each design
  element against structured criteria to reach a pass, conditional, or fail
  outcome. Apply to crew interfaces, ground control workstations, maintenance
  operations, and any human-in-the-loop function requiring structured design
  justification. Trigger: ecss, e-st-10-11c, hcd, human-centred-design,
  task-analysis, user-requirements, design-evaluation, crew-interface."
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
  tags: [ecss, e-st-10-11c, hcd, human-centred-design, task-analysis, user-requirements, design-evaluation, crew-interface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — HCD Activities (space-systems/ecss/e1011-hcd-activities)

Use when the task is running the four Human-Centred Design (HCD) activities
defined in ECSS-E-ST-10-11C §4.4.3 — task analysis, capture of user and
organisational requirements, design solution production, and design evaluation
— for any crewed or human-tended space system element.

## Domain quick reference

- §4.4.3 mandates four HCD activity types in sequence. Each type must be
  traceable to the others: task analysis drives requirements; requirements
  constrain design elements; design elements are evaluated against criteria
  derived from those same requirements.
- **Task analysis** breaks every human operation into discrete steps, names
  the performer role (crew, ground operator, maintenance technician), records
  frequency (continuous, periodic, on-demand, emergency), and assigns a
  criticality level (low / medium / high / critical). A step with no named
  performer is incomplete.
- **User and organisational requirements** are captured with a source tag
  ("user" for individual operator needs, "organisational" for institutional
  constraints), a category (functional, performance, safety, comfort,
  organisational), a statement, and a priority (1 = highest). Each
  requirement must be traceable to at least one task in the task analysis.
- **Design solution production** produces design elements, each with a
  rationale and an explicit list of requirement identifiers it addresses. A
  design element with an empty addresses list is valid only if it is
  supporting infrastructure — flag it for review.
- **Design evaluation** records, for each design element, a set of
  evaluation criteria with an outcome (pass / conditional / fail) and
  supporting evidence. A single fail outcome on any criterion causes the
  element to fail overall; one or more conditional outcomes with no fail
  yields a conditional overall outcome.

## Workflow

1. Inventory every human operation the system requires. For each, create a
   task-analysis entry with a unique task identifier, a plain-language
   description, the performer role, the criticality level (one of: low,
   medium, high, critical), and an ordered list of steps. Reject any entry
   missing a performer or with an unrecognised criticality level.
2. From the task list, derive user and organisational requirements. For each
   requirement, record its identifier, source ("user" or "organisational"),
   category (functional / performance / safety / comfort / organisational),
   a complete requirement statement, and a priority integer from 1 to 5.
   Every task must contribute at least one requirement; a task that generates
   no requirement is a gap worth flagging.
3. Produce design solution elements. Each element carries an identifier, a
   description, the list of requirement identifiers it addresses, and the
   rationale for the design choice. Run the coverage check: every requirement
   must appear in at least one element's addresses list. Flag uncovered
   requirements before proceeding to evaluation.
4. For each design element, record evaluation criteria. Each criterion has an
   identifier, a description, an outcome (pass / conditional / fail), and
   evidence supporting that outcome. Derive criteria directly from the
   requirements addressed by that element. Compute the element's overall
   outcome: fail if any criterion fails; conditional if any criterion is
   conditional and none fail; pass only if all criteria pass.
5. Check that all four HCD activity types appear in the activity log and are
   marked complete. The assessment is not complete until task_analysis,
   user_requirements, design_production, and design_evaluation are all
   present and marked done.
6. Produce a summary: task count, requirement count, design element count,
   coverage ratio, evaluation fail count, and an overall pass/fail verdict.
   The verdict is pass only when all tasks and requirements are valid, all
   requirements are covered, and no design element carries a fail outcome.

## Pitfalls

- Treating "no evaluation criteria recorded" as a pass — an element with no
  criteria has not been evaluated; evaluate_design_element raises an error
  on an empty criteria list.
- Advancing to design evaluation before running the coverage check — an
  uncovered requirement left until evaluation is harder to remediate than one
  caught at design-production review.
- Assigning the same identifier to two tasks or two requirements — the
  coverage check compares identifiers; duplicates silently inflate the
  covered count and hide a real gap.
- Setting priority to 0 or to a value above 5 — the validation rejects
  anything outside 1–5, preventing silent out-of-scale priorities.
- Leaving "organisational" in both the source tag and the category field
  without distinction — source tracks who originated the requirement
  (organisational means the institution, not the individual operator);
  category tracks what aspect of the human-system interaction it governs.

## Behavior contract (gate 3)

The task-analysis validation, requirement validation, design-coverage check,
design-element validation, design-evaluation scoring, HCD completeness check,
and summary logic are exercised by the gate 3 contract test:
scripts/test_e1011_hcd_activities.py against
scripts/e1011_hcd_activities_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_hcd_activities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
