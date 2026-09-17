---
name: q60-procurement-specification-drd
description: "Evaluate a part purchasing specification against the content its DRD requires, down to the screening and lot acceptance detail. Use when an Annex C specification is about to become the baseline an order is placed against: validate the controlled header, weight the required content sections by how much of the purchasing decision rests on each, grade every screening step on what is done and what rejects the part, catch a repeated sequence position and a mandated screening family nobody covered, prove the lot acceptance plan can actually reject a lot, and report the exact acceptance probability the stated sampling gives. Trigger: ecss, q-st-60c, q60-ps-drd-required-content, q60-ps-drd-screening-sequence, q60-ps-drd-screening-family-coverage, q60-ps-drd-lot-acceptance-plan, q60-ps-drd-acceptance-probability."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-procurement-specification-drd, q60-ps-drd-required-content, q60-ps-drd-screening-sequence, q60-ps-drd-screening-family-coverage, q60-ps-drd-lot-acceptance-plan, q60-ps-drd-acceptance-probability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Part Purchasing Specification Data Item (space-systems/ecss/q60-procurement-specification-drd)

Use when the task is Annex C of ECSS-Q-ST-60C: what a part purchasing
specification has to contain before an order can be placed against it, and in
particular the two blocks that decide what the supplier actually screens out —
the screening sequence and the lot acceptance plan. This leaf grades a draft
specification on content, on executability and on whether its sampling can
reject anything at all.

## Domain quick reference

- Content coverage is weighted, not counted. A specification missing its lot
  acceptance section and one missing its packaging section both show eight
  headings out of nine; only one of them leaves the buyer with no basis for
  refusing a lot. Weighting by how much of the purchasing decision rests on a
  section is what separates the two.
- A screening step is executable only if it says what is done, under what
  condition and what result rejects the part. A step naming a test with no
  reject criterion reads as a screen and functions as a description: the
  supplier can run it, record a number and ship the part regardless.
- Sequence position is part of the flow, not decoration. Two steps claiming
  the same position leave the order in which they run undefined, and screening
  order is exactly what a burn-in followed by a final electrical is for.
- Family coverage is independent of sequence depth. Ten electrical
  measurements do not stand in for an absent burn-in, and a long flow is the
  easiest way for a missing family to go unnoticed.
- A sampling plan has to be able to fail. A sample larger than the lot cannot
  be drawn at all, and an accept number at or above the sample size passes
  every lot that can be drawn — both read as a plan and neither screens.
- The acceptance probability is computable, so compute it. Sampling without
  replacement is hypergeometric; building the sum from exact integer binomials
  and dividing once gives a figure a reviewer can act on and one that does not
  drift between platforms.

## Workflow

1. Validate the header: identifier, issue, part type, issue date and approving
   authority. An uncontrolled document cannot be an order baseline whatever it
   contains.
2. Score the required content sections by weight, naming every absent section
   rather than returning a bare fraction.
3. Grade each screening step against the field set, and report an incomplete
   step before reading its sequence position — a step nobody can execute has
   no position worth checking.
4. Check the positions are unique across the flow, so the order the steps run
   in is defined.
5. Check every mandated screening family appears at least once, counting only
   steps that were complete enough to name one.
6. Check the lot acceptance plan holds its fields, then that its sample fits
   inside the lot and its accept number sits below the sample size.
7. Compute the acceptance probability of the stated plan against the assumed
   defective population, compare content coverage with the required level,
   absorbing floating-point representation error at the boundary with a named
   tolerance, and return one verdict with findings ranked worst first.

## Pitfalls

- Counting headings instead of weighting them. A specification can show a high
  coverage figure while the section the buyer needs to refuse a lot is the one
  that is missing.
- Accepting a screening step that names a test and no reject criterion. It
  will be run, a result will be recorded, and nothing will ever fail it.
- Ignoring duplicate sequence positions because every step is individually
  complete. The flow is then ambiguous exactly where screening order matters.
- Reading depth in one family as coverage of the flow. Repetition inside
  electrical measurement hides an absent burn-in behind a longer sequence.
- Passing a sampling plan whose accept number equals its sample size. Every
  drawable lot passes, so the plan is arithmetic, not acceptance.
- Estimating the acceptance probability with a float-heavy approximation. The
  exact binomial sum is cheap here and does not move between platforms, which
  matters when the figure is quoted back in a review.

## Behavior contract (gate 3)

The header validation, weighted content coverage, screening step grading,
sequence-position uniqueness, mandated family coverage, lot acceptance
consistency checks and the exact hypergeometric acceptance probability are
exercised by the gate 3 contract test:
`scripts/test_q60_procurement_specification_drd.py` against
`scripts/q60_procurement_specification_drd_logic.py` (stdlib unittest,
offline). Run: `python3 scripts/test_q60_procurement_specification_drd.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
