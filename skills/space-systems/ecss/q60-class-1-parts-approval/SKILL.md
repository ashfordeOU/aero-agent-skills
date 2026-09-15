---
name: q60-class-1-parts-approval
description: "Assess whether every EEE part proposed for class 1 flight use carries the customer review and sign-off of ECSS-Q-ST-60C clause 4.2.4: hold each submission to the mandatory evidence set, test the signatory both against the customer roster and for independence from the submitting organisation, treat an undated or out-of-validity sign-off as unreleased, release nothing on a conditional approval until every condition carries a closure record, and name each proposed part that never reached a review. Use when a proposed parts list has to become a released flight parts list. Trigger: ecss, q-st-60c-clause-4-2-4, class-1-part-customer-approval, parts-approval-evidence-package, approval-signatory-independence, approval-validity-window, conditional-approval-closure-record, unsubmitted-proposed-part."
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
  tags: [ecss, q-st-60c-class-1-eee-scope, q60-class-1-parts-approval, q-st-60c-clause-4-2-4, class-1-part-customer-approval, parts-approval-evidence-package, approval-signatory-independence, approval-validity-window, conditional-approval-closure-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts — Customer Approval (space-systems/ecss/q60-class-1-parts-approval)

Use when the task is the customer approval step of ECSS-Q-ST-60C clause
4.2.4 — the review and sign-off every electrical, electronic and
electromechanical part proposed for class 1 flight use has to carry before it
may be built into flight hardware.

## Domain quick reference

- Approval is per part, not per programme. A supplier that has been approved
  before carries no approval for a part number that was never submitted, so
  the unit the verdict attaches to is the part, and the proposed list is
  checked part by part against the submitted set.
- A submission the customer cannot review is not a submission that has nothing
  wrong with it. The evidence package — who the part is, what the evaluation
  found, how the part will be used, and what is actually being bought — is
  what the review is performed on, and an absent item is named as a gap in its
  own right.
- A sign-off carries two independent authority questions: is this signatory on
  the customer's approver roster, and is the signatory independent of the
  organisation that proposed the part. A name on the roster who sits inside
  the submitting organisation satisfies the first and fails the second.
- An undated sign-off cannot be aged and so cannot be shown to be current; it
  is treated as a finding rather than as an approval of unknown age. A
  sign-off dated after the review itself is an input error, not an
  unusually fresh approval.
- A conditional approval is a plan, not a release. Each condition attached to
  it releases nothing until a closure record exists against that reference, so
  a conditional disposition with open conditions leaves the part blocked.
- A rejected or still-pending disposition is not a neutral state to be carried
  forward. The proposed list and the released list are different lists, and
  only the second one may be built to.

## Workflow

1. Validate each submission: part number, manufacturer, the organisation that
   proposed it, the evidence package, the disposition, the signatory and the
   decision date. Reject a free-text disposition, a duplicated evidence item
   and a duplicated condition reference.
2. Compare the evidence package with the mandatory set and record each absent
   item as its own finding.
3. Test the signatory against the customer roster, then against the submitting
   organisation for independence, keeping both findings when both apply.
4. Age the sign-off against the review date, refusing a decision date later
   than the review, and compare the age with the validity window.
5. Read the disposition. Hold a conditional approval open until every attached
   condition carries a closure record, and refuse a conditional disposition
   that lists no conditions at all.
6. Compare the proposed part list with the submitted set and name every part
   that was proposed for flight but never reviewed.
7. Report the per-part records, the never-submitted parts, the released list
   and a round verdict carrying every finding, not only the first.

## Pitfalls

- Treating a conditional approval as an approval. The conditions are the
  reason the customer did not simply approve, and the part is released only
  once each one is closed against its reference.
- Accepting a sign-off from a name on the roster who works for the submitting
  organisation. Roster membership answers authority; it does not answer
  independence, and the two are tested separately.
- Reading an undated sign-off as current. An approval whose age cannot be
  computed cannot be shown to sit inside the validity window, so it is a
  finding rather than a default pass.
- Reporting only the parts that were submitted. The parts that never reached a
  review are the ones most likely to reach the board unapproved, and they are
  visible only by comparing against the proposed list.
- Counting a blocked part in the released total. The released list is what the
  build is authorised against, so a part carrying any finding stays out of it.
- Stopping at the first finding. The submitter needs the whole list to prepare
  one resubmission rather than discovering the next gap at the next review.

## Behavior contract (gate 3)

The submission validation, evidence-package coverage, signatory roster and
independence tests, sign-off ageing, conditional-approval closure, the
never-submitted comparison and the overall round verdict are exercised by the
gate 3 contract test: scripts/test_q60_class_1_parts_approval.py against
scripts/q60_class_1_parts_approval_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_1_parts_approval.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
