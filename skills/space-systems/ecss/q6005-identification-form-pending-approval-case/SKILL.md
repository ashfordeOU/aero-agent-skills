---
name: q6005-identification-form-pending-approval-case
description: "Determine how a hybrid identification form is handled while the named production line is still working toward its capability approval: validate the milestone record, count the steps closed and the ones closed only by waiver, score the completion share against the provisional threshold, date the re-confirmation the form owes and the day it lapses, compare the approval target with the hardware need date, and return an accept-provisionally, hold or reject disposition with its findings. Use when a form arrives against a line whose approval is in progress and a procurement or product-assurance engineer must decide whether it can be carried. Trigger: ecss, q-st-60-05, hybrid-identification-form, pending-line-capability-approval, provisional-form-acceptance, hybrid-form-revalidation, approval-milestone-waiver, hybrid-procurement-schedule-margin."
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
  tags: [ecss, q-st-60-hybrid-procurement-scope, q6005-identification-form-pending-approval-case, hybrid-identification-form, pending-line-capability-approval, provisional-form-acceptance, hybrid-form-revalidation, approval-milestone-waiver]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Identification Form, Approval Pending (space-systems/ecss/q6005-identification-form-pending-approval-case)

Use when the task is the pending-approval case of the hybrid identification
form in ECSS-Q-ST-60-05 clause 6.2.3 — a form has been raised against a
supplier production line that has started its capability approval but has
not finished it, and someone has to decide whether that form can be carried,
on what terms, and until when.

## Domain quick reference

- The pending case is a state, not a grade. It exists only while the approval
  decision is still open and no approval milestone has been recorded as
  failed. Once the decision is settled in either direction the form leaves
  this clause: an approved line goes down the ordinary route, a failed
  milestone makes the form a rejection, not a hold.
- How far the line has travelled is the discriminator. Counting the closed
  milestones against the registry gives a completion share, and below roughly
  half the registry the line is too early in its approval for anything raised
  against it to be carried provisionally.
- A milestone closed by waiver is not the same evidence as a milestone closed
  by demonstration. Both count toward the share, because the approval body
  accepted them, but a waiver is reported separately so the reviewer sees what
  the share is actually made of.
- A form against a moving target has a shelf life. It is re-confirmed on a
  fixed cadence while the line stays unapproved and lapses outright at the
  longer interval, so a form that is merely overdue for re-confirmation and a
  form that has lapsed are different dispositions.
- Because the approval does not exist yet, the form owes content the approved
  case does not: the line's approval schedule, the interim process-capability
  data standing in for the approval, and the delta-inspection plan covering
  the gap. A form without them is not a thin form, it is an unsupported one.
- The last comparison is schedule, not quality: an approval target that lands
  after the date the hybrids are needed makes provisional acceptance a
  decision with no exit, and that is a finding in its own right.

## Workflow

1. Validate the declared milestone record against the registry — every
   registry step present, every status one of the four recognised ones. A
   step outside the registry is a data error, not a new milestone.
2. Decide whether the line is in the pending state at all: decision milestone
   still open, nothing failed. Route the settled cases out before grading.
3. Count the closed milestones, separate the waived ones, and form the
   completion share.
4. Date the form: its next re-confirmation and its lapse date from the issue
   date, then compare both with the assessment date so overdue and lapsed
   never collapse into one flag.
5. Confirm the pending-line evidence is carried, naming every absent item
   rather than reporting a count.
6. Take the schedule margin in whole days between the approval target and the
   hardware need date.
7. Return the disposition — accept provisionally, hold, reject, or out of
   scope — with the findings that produced it.

## Pitfalls

- Treating a waived milestone as demonstrated capability. The waiver counts
  toward the share because the approval body accepted it, but a share made
  mostly of waivers is a different risk from one made of closed audits, and
  collapsing the two hides exactly that.
- Reading an overdue re-confirmation as a lapse. The first is a paperwork
  action on a form that is still alive; the second means nothing can be used
  until the form is re-issued. Reporting both as "expired" over-restricts the
  first and under-restricts the second.
- Carrying the form because the technical case is good while the approval
  target lands after the need date. Provisional acceptance is a bridge to an
  approval; if the approval cannot arrive in time the bridge leads nowhere.
- Grading a line whose approval decision is already closed against this
  clause. It looks like a pass and is actually the wrong route, so the
  approved-line checks never run.
- Relaxing the completion threshold to let an early line through. The share
  comparison absorbs floating-point representation error with a named
  tolerance; the threshold itself stays where it is.

## Behavior contract (gate 3)

The milestone-record validation, pending-state test, completion share and
waiver separation, form dating, evidence check, schedule margin and
disposition are exercised by the gate 3 contract test:
scripts/test_q6005_identification_form_pending_approval_case.py against
scripts/q6005_identification_form_pending_approval_case_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_identification_form_pending_approval_case.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
