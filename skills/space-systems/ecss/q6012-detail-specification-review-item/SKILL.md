---
name: q6012-detail-specification-review-item
description: "Review the detail specification review item of ECSS-Q-ST-60-12C clause 7.3.11 for a microwave die: check the product level document carries every content block the programme expects, validate each specified parameter for a unit, a guaranteed limit and the measurement conditions that limit is guaranteed under, test the limits for ordering, confront each guaranteed limit with the absolute maximum rating governing it, confirm the issue, date, approval and change record hold the document under configuration control, then accept, action or reject it. Use when a microwave die design review reaches the product level specification document. Trigger: ecss, q-st-60-12-microwave-die-scope, detail-specification-review, product-level-specification-content, guaranteed-limit-ordering, absolute-maximum-rating-consistency, specification-measurement-conditions, specification-issue-control."
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
  tags: [ecss, q-st-60-12-microwave-die-scope, q6012-detail-specification-review-item, detail-specification-review, product-level-specification-content, guaranteed-limit-ordering, absolute-maximum-rating-consistency, specification-measurement-conditions, specification-issue-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Detail Specification Review Item (space-systems/ecss/q6012-detail-specification-review-item)

Use when the task is the detail specification review item of
ECSS-Q-ST-60-12C clause 7.3.11 -- examining the product level
specification document presented for the microwave die design, as a
document rather than as a design.

## Domain quick reference

- The detail specification is the document a procurement order points
  at and an incoming inspection grades against. Whatever it fails to
  state is a property nobody can later require, so the review is about
  completeness and self-consistency, not about whether the numbers are
  good ones.
- Three passes answer the item. The content pass asks whether the
  expected blocks are there at all; the parameter pass asks whether
  each specified parameter is usable as a specification; the
  configuration pass asks whether the document is under issue control.
- A guaranteed limit without the conditions it is guaranteed under is
  not a specification, it is a number. Temperature and frequency are
  the minimum conditions for a microwave die, because both move the
  performance far enough to change whether a part conforms.
- Limits stack in an order: the lower bound at or below the typical
  value, the typical value at or below the upper bound. A document that
  breaks that order is internally contradictory, and the contradiction
  usually arrives through a late edit to one of the three numbers.
- Absolute maximum ratings are not performance limits. They bound where
  the die survives, so every guaranteed limit has to sit inside the
  rating that governs it. A guaranteed value outside its rating asks a
  supplier to deliver parts operating beyond their own survival bound.
- A parameter stating only bounds and no expected value is legal but
  weak: the procuring side has nothing to plan a design margin against
  and no way to see a lot drifting inside its limits.
- Issue control is part of the technical review. Without an issue
  identifier, a date, a named approval and a record of what changed,
  two readers can hold two documents and both believe they hold the
  specification.

## Workflow

1. Take the list of blocks the document carries, canonicalize it and
   compare it against the expected set. Report a missing block as a
   finding and an unexpected block as an action rather than merging the
   two.
2. Validate every specified parameter: a name, a unit, at least one
   guaranteed limit, and the measurement conditions the limit holds at.
   Reject a parameter that states only a typical value.
3. Test the limit ordering on each parameter, and report the specific
   pair that is out of order so the edit lands on the right number.
4. Confront every governed limit with its absolute maximum rating.
   Treat a limit outside its rating and a rating the ratings block never
   states as findings of the same weight.
5. Check the issue record: identifier, date in a calendar form, named
   approval, and for any issue after the first, a record of what
   changed.
6. Report the bound-only parameters as an action, then accept, action
   or reject the document with the findings that drove the verdict.

## Pitfalls

- Reviewing the numbers and not the blocks. A document can be
  internally perfect across every parameter it states while omitting
  storage and handling or the screening route entirely, and no amount
  of reading the parameter table reveals a block that is not there.
- Accepting a limit with the conditions stated elsewhere in prose. The
  condition belongs to the limit; carried loose in a paragraph it
  drifts away from the number at the next issue, and the reader is left
  guessing which temperature a gain figure was guaranteed at.
- Reading absolute maximum ratings as the specification. They bound
  survival, not performance, and a guaranteed limit that reaches one is
  a part specified to operate at the edge of its own destruction.
- Letting a typical value stand in for a limit. A typical value is what
  the population does; a guaranteed limit is what every part does, and
  only the second is something a supplier can be held to.
- Comparing a limit against its bound by bare arithmetic. Limits arrive
  from spreadsheets and unit conversions, so a value that should sit
  exactly on its bound can land a few units in the last place outside
  it; the comparison absorbs that representation error while the bound
  stays untouched.

## Behavior contract (gate 3)

The content block completeness, parameter validation, condition duty,
limit ordering, absolute maximum confrontation, issue control and
document verdict are exercised by the gate 3 contract test:
scripts/test_q6012_detail_specification_review_item.py against
scripts/q6012_detail_specification_review_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_detail_specification_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
