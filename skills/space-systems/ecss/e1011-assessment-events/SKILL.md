---
name: e1011-assessment-events
description: "Use when execute usability reviews, project design reviews, and crew
  station assessments of crew hardware under ECSS-E-ST-10-11C §4.10.2: determine
  the applicable review type for each hardware item based on hardware category,
  schedule each review event against the programme milestone plan, define evaluation
  criteria and acceptance thresholds per event, conduct the review with human factors
  engineers and project stakeholders, record each finding as a tracked action item
  with severity level, verify all findings are either resolved or formally waived,
  and confirm gate readiness before advancing to the next programme phase. Trigger:
  ecss, e-st-10-system-scope, e-st-10-11c, usability-review, design-review,
  crew-station-review, crew-hardware, human-factors, hfe-review, assessment-events."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, usability-review, design-review, crew-station-review, crew-hardware, human-factors, hfe-review, assessment-events]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Assessment Events (space-systems/ecss/e1011-assessment-events)

Use when the task is planning and executing the formal human factors assessment
events for crew hardware under ECSS-E-ST-10-11C §4.10.2 — usability reviews,
project design reviews, and crew station reviews — covering event scheduling
against programme milestones, finding management, and gate readiness verification.

## Domain quick reference

- §4.10.2 defines three assessment event types. Each hardware item is assigned to
  one or more event types based on its category; no item enters the assessment
  without a type assignment.
  - **Usability review**: evaluates how effectively and comfortably the crew can
    operate the hardware during nominal and off-nominal tasks. Required at CDR,
    QR, and ORR.
  - **Design review**: verifies that the hardware design satisfies the human
    factors requirements captured in the HFE requirements baseline. Required at
    PDR and CDR.
  - **Crew station review**: evaluates the integrated crew workstation against
    accommodation geometry, reach, visibility, and labelling requirements.
    Required at CDR, QR, and AR.
- Programme milestone sequence for scheduling: PDR → CDR → QR → AR → ORR.
  Each milestone mandates a specific subset of review types; scheduling a review
  after its mandatory milestone is a non-compliance.
- Hardware categories drive review type assignment. Examples: a display item
  requires usability and design reviews; a crew control panel requires all three;
  a seat requires crew station and design reviews.
- Findings lifecycle: every issue raised during a review is recorded as an action
  item with a severity level (critical / major / minor / observation) and an
  initial status of open. A finding is resolved by either closing it (with a
  resolution note) or formally waiving it (with a documented rationale). A
  programme gate cannot be passed while any finding remains open.

## Workflow

1. Inventory all crew hardware items. For each item, identify its hardware
   category and derive the applicable review types. Reject any item whose
   category is not on the recognised list before assigning it to a review event.
2. Build the review schedule: for each review type, identify the programme
   milestones at which it is mandatory and confirm that the review is planned at
   or before each such milestone. Flag any mandatory review type that is absent
   from the schedule at a required milestone.
3. Before each review event, define the evaluation criteria and acceptance
   thresholds specific to the event type and hardware items in scope. Link each
   criterion to a human factors requirement identifier in the HFE requirements
   baseline.
4. Execute the review event with the HFE engineer and relevant project
   stakeholders present. For each evaluation criterion, record the outcome and
   supporting evidence.
5. Record every issue as a finding: assign a unique finding identifier, write a
   description of the non-conformance or concern, assign a severity level, and
   set its initial status to open.
6. For each open finding, either close it by documenting the corrective action
   and resolution, or waive it by providing a formal rationale accepted by the
   HFE authority. An empty resolution note or rationale is not accepted.
7. Before the programme proceeds past any milestone gate, run the gate readiness
   check: confirm the review schedule coverage at that milestone is complete and
   confirm no findings remain open. A gate with unresolved findings or a missing
   mandatory review is non-compliant.

## Pitfalls

- Treating a review event as complete because the session was held without
  recording findings formally — every issue raised in the session must be entered
  as a tracked finding; verbal acknowledgement is not a finding record.
- Scheduling a usability review only at CDR and relying on earlier informal
  walk-throughs as a substitute for the QR and ORR events — the standard requires
  separate, formal events at each mandatory milestone; informal sessions do not
  substitute for them.
- Waiving a finding without a documented rationale — a waiver without rationale
  cannot be defended at audit; the logic module rejects empty rationale strings.
- Carrying an open finding past a programme gate on the assumption it will be
  resolved in the next phase — gate readiness requires all findings to be either
  closed or waived at the time of the gate, not deferred to a future milestone.
- Assigning a hardware item to no review type because its category is
  unrecognised — unknown categories must be resolved by the HFE lead before the
  item enters the event schedule; do not silently skip it.

## Behavior contract (gate 3)

The review type validation, milestone coverage checking, finding lifecycle
(add / close / waive), gate readiness verification, and hardware category mapping
logic are exercised by the gate 3 contract test:
scripts/test_e1011_assessment_events.py against
scripts/e1011_assessment_events_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_assessment_events.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
