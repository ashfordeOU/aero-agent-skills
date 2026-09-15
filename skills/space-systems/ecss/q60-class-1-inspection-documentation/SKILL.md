---
name: q60-class-1-inspection-documentation
description: "Audit the inspection and control records a class 1 parts programme has produced under ECSS-Q-ST-60C clause 4.7: name every performed activity carrying no record at all, test each record for a traceable lot identity, a stated outcome, an authorised signatory, an evidence reference and a disposition behind every failed outcome, measure the retention shortfall against the programme retention period, and return one documentation-complete, documentation-incomplete or documentation-not-auditable disposition with the completeness fraction. Use when the inspection evidence for a class 1 parts programme is compiled or reviewed. Trigger: ecss, q-st-60c, class-1-inspection-record-defects, class-1-record-retention-shortfall, class-1-documentation-completeness, class-1-documentation-disposition."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-1-inspection-documentation, class-1-inspection-record-defects, class-1-record-retention-shortfall, class-1-documentation-completeness, class-1-documentation-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 1 — Inspection and Control Documentation (space-systems/ecss/q60-class-1-inspection-documentation)

Use when the task is clause 4.7 of ECSS-Q-ST-60C: the documentation of the
outcomes of the inspection and control activities carried out across the class
1 parts programme. This leaf grades the record set the programme has actually
produced against the activities it actually performed.

## Domain quick reference

- The record set is graded against the work performed, not against a template.
  An activity carried out and never written down is invisible to the audit,
  and the programme reads complete because nobody counted what was missing.
- A record exists or it is auditable; those are two different tests. A record
  naming an activity nobody recognises, carrying no lot identity, no stated
  outcome, no authorised signatory or no evidence reference occupies the slot
  without closing it.
- The signatory list is a closed set. A name on the record is not the same as
  an authorised name, and a record signed by someone outside the list proves
  the activity happened and not that it was accepted.
- A failed outcome without a disposition is an open loop, not a record. The
  interesting records are the ones that failed, and a failure written down and
  never dispositioned is the defect the audit is looking for.
- A pending outcome is not a closed one. It is real evidence of work in
  progress and it still leaves the activity open.
- Retention is part of the record, not a filing detail. Evidence that will not
  survive to the audit cannot be called complete however sound it reads today,
  and the shortfall overrides every other state.
- Completeness counts activities covered by a defect-free record, not records
  filed. Three defective records for one activity cover nothing, and one sound
  record among them covers it.

## Workflow

1. Order the performed activities into audit order and reject any name the
   programme does not recognise.
2. Group the submitted records under the activity each one covers, keeping the
   records that name nothing recognisable visible rather than dropping them.
3. Name every performed activity carrying no record at all.
4. Test each record for lot identity, a stated outcome, a named and authorised
   signatory, an evidence reference, a disposition behind a failed outcome and
   an outcome that is not still open. Report every defect a record carries.
5. Measure the retention shortfall between the required retention period and
   the period the records are actually kept for.
6. Measure completeness as the fraction of performed activities covered by at
   least one defect-free record, and return one disposition:
   documentation-complete, documentation-incomplete or
   documentation-not-auditable, with the shortfall overriding.

## Pitfalls

- Grading the record set against the standing activity list instead of the
  work performed. A programme that skipped an activity and filed no record
  scores the same as one that did the work and wrote it up.
- Counting records rather than covered activities. A thick folder against one
  activity and nothing against the next reads as progress and closes neither.
- Accepting any signature as an acceptance. The signatory list is what makes a
  record an acceptance; a name outside it records only that somebody was
  standing there.
- Filing a failed outcome and moving on. The failure is the record that
  matters, and without a disposition behind it the lot has no decision
  attached to the only evidence that questioned it.
- Reading a pending record as a closed one. Work in progress is honest
  evidence and it still leaves the activity open at the review.
- Treating retention as a records-office problem. The evidence is part of the
  deliverable, and a set kept for less than the required period fails the
  audit years after everyone signed it off.

## Behavior contract (gate 3)

The audit ordering, record-to-activity grouping, unrecorded-activity listing,
per-record defect tests, authorised-signatory check, retention shortfall,
completeness fraction and the documentation disposition are exercised by the
gate 3 contract test:
scripts/test_q60_class_1_inspection_documentation.py against
scripts/q60_class_1_inspection_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_inspection_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
