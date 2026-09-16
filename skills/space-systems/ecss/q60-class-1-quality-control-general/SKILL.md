---
name: q60-class-1-quality-control-general
description: "Use when a class 1 lot is booked into incoming quality control. Determine the receiving control plan a class 1 EEE lot owes on arrival under ECSS-Q-ST-60C clause 4.5.1: stop an untraceable, empty or paperwork-rejected lot at the door, derive the control activities the package style, source history, radiation duty and age call for, order them so every non-destructive activity closes before a destructive one consumes parts, size each sample from the delivered quantity, and return the outstanding controls with one controls-complete, controls-outstanding or lot-not-admissible entry disposition. Trigger: ecss, q-st-60c, class-1-receiving-control-plan, class-1-destructive-analysis-sample-size, class-1-control-activity-ordering, class-1-lot-admissibility-disposition."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-1-quality-control-general, class-1-receiving-control-plan, class-1-destructive-analysis-sample-size, class-1-control-activity-ordering, class-1-lot-admissibility-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 1 — Receiving Quality Control Entry Point (space-systems/ecss/q60-class-1-quality-control-general)

Use when the task is clause 4.5.1 of ECSS-Q-ST-60C: the entry point to the
control measures applied to class 1 parts once they have been received. This
leaf opens the control plan for one lot, decides what that lot owes and in
what order, and says what is still outstanding.

## Domain quick reference

- The entry point is a gate, not a queue. A lot with no traceable identity,
  no stated quantity or a rejected data package does not get a control plan
  at all; opening one on an inadmissible lot spends parts on a lot that can
  never be released.
- The plan is derived, not copied. A hermetic package pulls in particle
  noise detection, an unqualified source and an aged lot each pull in
  solderability verification, and radiation duty pulls in its own lot
  verification. Two class 1 lots from the same programme can owe different
  plans.
- Order is a cost decision with no way back. Destructive activities consume
  the parts they touch, so every non-destructive activity is closed first;
  running the destructive physical analysis before the visual examination can
  destroy the only evidence that would have stopped the lot for free.
- Sample size follows lot size in bands, not proportionally. A band boundary
  belongs to the lower band, and one part past it moves the lot up, which is
  exactly the case a hand-built plan gets wrong.
- A sample can never exceed the lot. A five-device plan against a lot of one
  is not a plan, and returning the band value unchanged would authorise
  drawing parts that do not exist.
- Coverage is a fraction of the owed plan, not of the activities performed.
  Closing an activity the lot never owed raises the count of work done and
  moves the lot no closer to release.

## Workflow

1. Test admissibility first: lot identity, delivered quantity and whether the
   data package was accepted. Report every reason, ordered from identity
   outwards, rather than stopping at the first.
2. Derive the owed control activities from the always-owed class 1 baseline
   plus the additions the package style, source history, radiation duty and
   months since manufacture call for. A lot sitting exactly on the age
   trigger has not passed it.
3. Order the owed activities so every non-destructive activity precedes the
   destructive ones, and within each group follow the canonical performance
   order.
4. Size the sample each activity draws from the delivered quantity: the full
   lot for the non-destructive activities, the banded plan for the sampled
   ones, never more than the lot holds.
5. Compare the activities already closed against the owed set, and return the
   outstanding ones in performance order plus the coverage fraction.
6. Return one entry disposition: controls-complete, controls-outstanding, or
   lot-not-admissible, with inadmissibility overriding the plan state.

## Pitfalls

- Opening a control plan before testing admissibility. The plan looks healthy
  right up to the point someone asks which lot the parts came from.
- Applying one standing plan to every class 1 lot. The activities a lot owes
  come from its own package style, source and age, and a standing plan is
  right for the lot it was written against and no other.
- Sequencing by convenience. The destructive activities are the ones with a
  booked slot, so they get run first, and the cheap evidence that would have
  rejected the lot is gone with the parts.
- Reading a band boundary as the start of the next band. A lot of exactly two
  hundred sits in the lower band; treating it as the higher one draws parts
  the plan never asked for.
- Counting closed activities rather than owed ones. Work performed outside the
  plan inflates progress and closes nothing the lot actually needs.
- Reporting a sample larger than the lot. The arithmetic is only correct while
  the lot is bigger than the plan, and small lots are where it stops being so.

## Behavior contract (gate 3)

The admissibility test, control derivation, non-destructive-first ordering,
banded sample sizing, outstanding-control comparison, coverage fraction and the
entry disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_1_quality_control_general.py against
scripts/q60_class_1_quality_control_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_quality_control_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
