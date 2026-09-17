---
name: q60-class-3-evaluation-general-requirements
description: "Determine whether a Class 3 part has to be taken through an evaluation, and how much of one, when nothing qualifies it against a specification the project accepts, under ECSS-Q-ST-60C clause 6.2.3.1: declare each unknown as a trigger condition, refuse a waiver raised against a hard trigger and one carrying no written justification, weigh the unknowns still open into a necessity index, open that index out by how severe the application is, then return the full or reduced decision with the programme elements still owed. Use when a Class 3 procurement has no prior qualification behind it. Trigger: ecss, q-st-60c, q60-class-3-evaluation-general-requirements, q60-c3-evaluation-trigger-ledger, q60-c3-evaluation-necessity-index, q60-c3-hard-trigger-override, q60-c3-outstanding-evaluation-elements."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q-st-60c, q60-class-3-evaluation-general-requirements, q60-c3-evaluation-trigger-ledger, q60-c3-evaluation-necessity-index, q60-c3-hard-trigger-override, q60-c3-evaluation-waiver-refusal, q60-c3-outstanding-evaluation-elements]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Evaluation, General Requirements (space-systems/ecss/q60-class-3-evaluation-general-requirements)

Use when the task is clause 6.2.3.1 of ECSS-Q-ST-60C: deciding that a Class 3
candidate part has to be evaluated before it is used, because nothing already
in hand qualifies it against a specification the project accepts — and
deciding how much of a programme that evaluation is.

## Domain quick reference

- The clause is not a judgement on the part. It is an inventory of what this
  particular procurement does not know, so the unknowns are declared first and
  the arithmetic comes afterwards.
- Each unknown is a trigger condition carrying a weight. The weights differ
  because the unknowns are not equally expensive to be wrong about: a part
  bought outside its rated envelope is a different order of exposure from a
  missing date code.
- A few triggers are hard. A hard trigger forces the full programme on its
  own, whatever the index reads and whatever anybody signs, because the thing
  being waived is the reason the clause was reached at all.
- A waiver is admissible against a soft trigger and only with a written
  justification. An unjustified waiver leaves the unknown open; recording it
  as granted is how an unevaluated part reaches a build.
- The necessity index is the weighted share of the unknowns still open, opened
  out by how severe the application is. The same part in a non-critical
  position and in a mission-critical one is genuinely two different decisions.
- The output is the programme elements still owed, not a template. Two of them
  are always owed once an evaluation is run at all, because they are about the
  line the part is built on rather than the part type.
- A decision landing exactly on a threshold is taken as meeting it. The index
  is a quotient of sums, so the boundary is absorbed by a named tolerance
  rather than by nudging the threshold.

## Workflow

1. Identify the candidate: manufacturer, part number and how severe the
   application is. An unrecognised severity is an input error, not a default.
2. Declare every unknown as a trigger condition from the published set.
   Reject an invented one and reject the same one declared twice.
3. Read the waivers. Refuse one raised against a hard trigger, refuse one with
   no written justification, and record both refusals as findings rather than
   dropping them.
4. Weigh the unknowns still open into the necessity index and scale it by the
   application severity, capping it at one.
5. Apply the hard-trigger override before reading the index, so a signature
   cannot buy its way past an unidentified line.
6. Decide: the full programme at or above the upper threshold, a reduced one
   at or above the lower threshold, no evaluation below it.
7. Return the elements still owed, so the evaluation plan starts from what
   this procurement is missing rather than from a standard campaign.

## Pitfalls

- Reading the index first. The hard triggers are the reason the clause exists,
  so they are applied before any arithmetic and cannot be averaged away by a
  short list of otherwise clean answers.
- Accepting a waiver because someone senior signed it. The test is whether a
  written justification exists and whether the trigger is soft, not who signed.
- Treating a mild application as a reason to skip the inventory. Severity
  scales the index; it never removes an unknown from the list.
- Reporting only the first refused waiver. Each refusal names a different
  unknown that is still open and a plan needs all of them.
- Issuing a reduced programme as an empty one. The line elements stay owed
  whatever the index reads, because no outside record describes this line.
- Declaring an unknown that is not in the published set. A free-text trigger
  cannot be weighed, so it silently drops out of the index.
- Comparing the index with a threshold by bare arithmetic. It is a quotient of
  a sum by a sum and then a product, so a case built to land exactly on a
  threshold can fall a few units in the last place short of it.

## Behavior contract (gate 3)

The trigger catalogue, hard-trigger flags, severity multipliers, waiver
admission and refusal, necessity index, threshold decision, hard-trigger
override and outstanding programme elements are exercised by the gate 3
contract test:
scripts/test_q60_class_3_evaluation_general_requirements.py against
scripts/q60_class_3_evaluation_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_3_evaluation_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
