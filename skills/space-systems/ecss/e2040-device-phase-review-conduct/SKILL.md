---
name: e2040-device-phase-review-conduct
description: "Evaluate the customer-led phase review of ECSS-E-ST-20-40C clause 5.1.4 against the evidence the development phase actually produced: confirm the review named is the one that closes that phase, check the board is chaired by the customer side, separate the mandatory data items delivered and mature from those still outstanding, fold every review observation onto a severity and a disposition, and let the open major observations and the missing mandatory items decide whether the phase closes, closes with actions, or is repeated. Use when a phase review is prepared, chaired or dispositioned at the end of a device development phase. Trigger: ecss, e-st-20-40-device-scope, device-phase-review-conduct, phase-review-board-chair, review-observation-disposition, mandatory-data-item-readiness, phase-closure-verdict, review-action-closure."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-phase-review-conduct, device-phase-review-conduct, phase-review-board-chair, review-observation-disposition, mandatory-data-item-readiness, phase-closure-verdict, review-action-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Phase Review Conduct (space-systems/ecss/e2040-device-phase-review-conduct)

Use when the task is the review duty of ECSS-E-ST-20-40C clause 5.1.4 --
holding the customer-led review that closes a device development phase,
and deciding from the outputs actually on the table whether the phase is
finished, finished with actions, or has to be run again.

## Domain quick reference

- A phase review is named for the phase it closes, not for the date it
  happens on. A review identifier that belongs to a different phase is
  the cheapest defect to find and the most expensive to leave, because
  the entry criteria and the mandatory output list both follow the
  phase rather than the meeting.
- The review is customer-led. The board chair sits on the customer
  side; a supplier-chaired board is a design walkthrough, and calling
  it a phase review lets the supplier disposition observations raised
  against its own work.
- Outputs arrive with two independent properties: whether the item was
  delivered at all, and whether it is mature enough to be reviewed. A
  draft delivered on time is still not reviewable, so delivery and
  maturity are counted separately and a mandatory item that is either
  absent or immature blocks the phase.
- Observations carry a severity and a disposition, and the two do
  different jobs. Severity says how much the finding matters; the
  disposition says what the board did with it. An observation rejected
  without a rationale is an undocumented disposition, whatever its
  severity.
- Open observations of major severity are the hard gate. Minor
  observations and comments left open become actions and let the phase
  close with actions, which is a different verdict from closed and has
  to be reported as such.
- Readiness is a fraction of the mandatory output set, and a fraction
  that lands exactly on its threshold has met it. Comparing a computed
  division strictly against a declared threshold fails reviews that are
  precisely on target.

## Workflow

1. Fold the review identifier and the phase onto recognised names and
   report a review that does not close the phase it is being held for.
2. Resolve the board: a chair with a named side, and the participants.
   Refuse a board with no chair, and report a chair that is not on the
   customer side as a finding rather than an input error.
3. Resolve the mandatory and optional output list. Refuse a repeated
   item identifier, and record delivery and maturity separately for
   each item.
4. Report every mandatory item that is undelivered or immature, and
   compute the readiness fraction over the mandatory set only.
5. Fold every observation onto a severity and a disposition. Report an
   observation rejected with no rationale, and keep the open ones
   grouped by severity.
6. Compare the readiness fraction against the declared threshold,
   absorbing representation error, and never widen the threshold.
7. Decide the verdict: repeated if a major observation is open or a
   mandatory output is missing or immature, closed with actions if
   anything lesser is outstanding, closed otherwise.

## Pitfalls

- Treating delivery as readiness. An item can be handed over on the due
  date and still be a skeleton; the review needs the content, so the
  maturity flag is the one the verdict depends on.
- Letting the supplier chair the board. The review exists so that the
  customer accepts the phase outputs, and a supplier-chaired board
  quietly converts acceptance into self-certification.
- Rolling a major observation into the action list to protect the
  schedule. Actions are the mechanism for the lesser findings; a major
  one moved there closes a phase on an unresolved defect and the record
  shows a clean review.
- Counting optional outputs in the readiness fraction. The figure then
  improves by adding nice-to-have items and gets worse by dropping
  them, which is exactly backwards.
- Comparing readiness against its threshold with a strict inequality. A
  three-in-four division landing on a 0.75 threshold can sit a unit in
  the last place below it and repeat a phase that was ready.

## Behavior contract (gate 3)

The review-to-phase match, board chair check, output delivery and
maturity accounting, observation severity and disposition folding,
readiness comparison and closure verdict are exercised by the gate 3
contract test: scripts/test_e2040_device_phase_review_conduct.py
against scripts/e2040_device_phase_review_conduct_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_phase_review_conduct.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
