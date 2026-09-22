---
name: e50-activities
description: "Assess the activity set a communication system engineering step actually declares against ECSS-E-ST-50C clause 5.2.1.2, which fixes the activities of the step rather than leaving them to whatever the schedule allowed. Grade a plan on three properties at once: every required activity is declared by somebody, every declared activity both consumes an input and produces an output, and every input consumed is either available to the step or produced by a peer activity. Report coverage as a fraction with the orphans and the unsatisfiable inputs named. Use when planning or reviewing a communication system engineering process. Trigger: ecss, e-st-50-communications, communication-system-engineering-activities, communication-process-activity-coverage, activity-input-traceability, orphan-process-activity, communication-design-process-audit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.2.1.2
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-activities, communication-system-engineering-activities, communication-process-activity-coverage, activity-input-traceability, orphan-process-activity, communication-design-process-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Engineering Process Activities (space-systems/ecss/e50-activities)

Use when the question is what a communication system engineering step is
required to do, per ECSS-E-ST-50C clause 5.2.1.2 — and whether the plan in
front of you actually declares it.

## Domain quick reference

- The clause fixes the activities of the step. They are not a menu a
  project draws from according to how much time it has; a step that
  skips one has not done the step, whatever its schedule says.
- A declared activity is a name plus what it consumes and what it
  produces. A name on its own is a heading in a plan, and headings are
  what a review slides past.
- Three properties have to hold together, and a plan can satisfy any one
  while failing the others. Coverage: every required activity is
  declared. Connection: each declared activity consumes something and
  produces something. Satisfiability: each input consumed is either an
  input to the step or an output of a peer activity.
- Coverage without connection is the common failure. Every required
  name appears, none of them is wired to anything, and the step's
  outputs turn out to have been written by whoever had the file open.
- Satisfiability is what catches ordering. An activity whose input no
  peer produces and the step does not hold cannot start, which is a
  scheduling fact the plan is asserting without noticing.

## Workflow

1. Write down the required activity set for the step before looking at
   the plan. In communication system requirements engineering that set
   falls to the customer and holds three: working through what the
   mission's top-level specifications demand, settling which
   requirements are the space communication system's own and putting
   them in writing, and composing the communication system requirements
   no other mission document already yields. Reading the plan first
   anchors the review on what is there rather than on what is owed.
2. Normalise each declared activity into name, inputs and outputs, and
   reject anything that does not carry all three — the missing field is
   usually where the gap is.
3. Reject a duplicate activity name outright. Two entries under one name
   mean two teams believe they own it, which is indistinguishable from
   nobody owning it.
4. Take coverage as a fraction of the required set written down in step
   1, so the fraction states how many of the three owed by the customer
   the plan actually declares, and keep the extra activities separate.
   Extras are not credit; a plan with four invented activities and one
   required one is one third covered, not more.
5. Flag every activity that consumes nothing or produces nothing, with
   the reason stated — one cannot be started from the step's inputs, the
   other cannot reach the step's outputs.
6. Resolve each consumed input against the step's available inputs and
   the peers' outputs, and name every one that resolves to neither.
7. Report all three together. A plan is conformant only when nothing is
   missing, nothing is disconnected, and nothing is unsatisfiable.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.2.1.2a | 4 |

## Pitfalls

- Grading coverage alone and calling the step planned. It is the cheapest
  of the three checks and the one a plan is most easily written to pass.
- Counting additional activities toward coverage. They may be good work;
  they are not the work the clause names, and mixing them in hides the
  gap the fraction exists to expose.
- Accepting an activity with no declared output. It will be defended as
  "analysis", and analysis that produces nothing cannot be reviewed,
  reused, or shown to have happened.
- Resolving inputs by name against a document list rather than against
  peer outputs. The document exists somewhere in the project, which is
  not the same as this step being able to obtain it.
- Treating a duplicate name as a formatting issue and merging the two
  entries. The duplication is the finding: two owners, one activity.

## Behavior contract (gate 3)

Activity normalisation, duplicate rejection, the coverage fraction with
extras held separate, the disconnected-activity findings and the
unsatisfied-input resolution against peer outputs are exercised by the
gate 3 contract test:
scripts/test_e50_activities.py against
scripts/e50_activities_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_activities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
