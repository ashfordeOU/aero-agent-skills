---
name: e2040-validation-qualification-acceptance-review
description: "Evaluate whether a completed device clears the final validation, qualification and acceptance review of ECSS-E-ST-20-40 clause 5.8.6. Use when the three evidence streams have to be closed out together and somebody must say whether the gate opens, opens against actions, or is held. Scores closure per stream, rejects a result claimed on a model the stream does not admit, confirms the qualification level envelopes the acceptance level by the declared ratio, refuses a waiver with no approved deviation behind it, and names the finding that binds the verdict. Trigger: ecss, e-st-20-40-device-scope, device-final-review-gate, validation-evidence-closure, qualification-envelope-ratio, acceptance-evidence-model-kind, review-open-action-budget, deviation-backed-waiver."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-validation-qualification-acceptance-review, device-final-review-gate, validation-evidence-closure, qualification-envelope-ratio, acceptance-evidence-model-kind, review-open-action-budget, deviation-backed-waiver]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Final Validation, Qualification and Acceptance Review (space-systems/ecss/e2040-validation-qualification-acceptance-review)

Use when the task is the closing review of ECSS-E-ST-20-40 clause 5.8.6
-- the single gate at which the validation, the qualification and the
acceptance evidence for a completed device are read together and the
device is either released, released against a bounded action list, or
held.

## Domain quick reference

- The gate reads three streams, not one. Validation answers whether the
  right device was built, qualification answers whether the design
  survives the environment with margin, and acceptance answers whether
  this particular unit was built to that design. A stream with no
  required evidence at all is an incomplete review package, not a
  cheap pass.
- Evidence is only evidence on a model the stream admits. Qualification
  results belong to a qualification or protoflight model; acceptance
  results belong to the flight or protoflight unit that ships. A
  qualification report carried on an engineering model, or an
  acceptance report carried on the qualification article, proves
  nothing about the delivered device and is a hold, not an action.
- Qualification only covers acceptance if it envelopes it. The
  qualification level divided by the acceptance level is the envelope
  ratio, and it has to reach the declared requirement; a ratio that
  merely equals the requirement passes, because the two levels are
  measured quantities and their quotient carries representation error.
- Open items are budgeted by criticality, not by appetite. A device in
  the top two categories leaves the gate with nothing open; lower
  categories carry a small, counted action list, and exceeding that
  count is a hold.
- A waiver is a route, not an exemption. An item carried as waived
  needs an approved deviation reference recorded against it, and the
  presence of any waiver keeps the verdict at open-against-actions
  even when every other item is closed.
- Something has to be named. A held or conditioned gate that does not
  identify the binding finding cannot be worked, so the verdict always
  carries the rule that produced it.

## Workflow

1. Normalise every evidence item: stream, state, the model kind it was
   produced on, and, where the state is waived, the deviation
   reference. Reject an unrecognised stream or state rather than
   defaulting it.
2. Confirm all three streams are represented. An empty stream is a
   package defect and stops the review before any counting.
3. Score closure per stream: closed, open, waived and not-started
   counts, plus the closed fraction the review chair reports.
4. Check model admissibility item by item and raise a finding for each
   result claimed on a model its stream does not admit.
5. Where a qualification and an acceptance level are supplied, compute
   the envelope ratio and compare it against the declared requirement
   with a tolerance that absorbs representation error.
6. Compare the open count against the budget the device criticality
   allows, then issue the verdict -- open, open against actions, or
   held -- with the binding finding named.

## Pitfalls

- Reading the three streams as one pile. A package that is ninety
  percent closed overall can still have an untouched acceptance
  stream, so the closure has to be scored per stream before any
  aggregate is quoted.
- Accepting a qualification report written against an engineering
  model because the hardware "is the same". The stream admits the
  models it admits; a build standard that was never formally the
  qualification article leaves the design unqualified.
- Passing an envelope check by bare arithmetic. The ratio of two
  measured levels can land a few units in the last place under a
  requirement it is meant to meet exactly, so the comparison absorbs
  that while the requirement itself stays untouched.
- Treating a waiver as a closed item. A waived item is an accepted
  shortfall with a deviation behind it, and counting it as closed
  hides the shortfall from the delivery review that follows.
- Carrying open actions on a top-category device because the schedule
  is tight. The budget is set by the consequence of the device
  failing, and an action list on a category-1 device is exactly the
  case the budget exists to refuse.

## Behavior contract (gate 3)

Item normalisation, stream closure scoring, model admissibility, the
envelope ratio comparison, the open-action budget and the final verdict
are exercised by the gate 3 contract test:
scripts/test_e2040_validation_qualification_acceptance_review.py
against
scripts/e2040_validation_qualification_acceptance_review_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2040_validation_qualification_acceptance_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
