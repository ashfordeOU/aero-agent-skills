---
name: q7003-acceptance-testing
description: "Build the acceptance test programme a processed anodizing batch owes, per batch and per part category. Use when a lot has come off the line and someone has to say what it is tested for and whether it is accepted: take the required test set from the part category, size the sample from the lot with a square-root plan and a category floor, work out how many witness coupons each rack owes for the tests that destroy what they touch, then judge the sample against the category allowance and separate a lot that can be recovered by screening from one where screening is not a route back in. Trigger: ecss, q-st-70-03-anodizing, anodize-batch-acceptance-sampling, anodize-part-category-test-set, anodize-witness-coupon-count, anodize-lot-disposition."
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
  tags: [ecss, q-st-70-03-anodizing, q7003-acceptance-testing, anodize-batch-acceptance-sampling, anodize-part-category-test-set, anodize-witness-coupon-count, anodize-lot-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Anodizing — Acceptance Testing (space-systems/ecss/q7003-acceptance-testing)

Use when the task is the acceptance clause of ECSS-Q-ST-70-03: settling
what a processed anodizing batch is tested for, how much of it is
sampled, and what happens to the lot when the sample carries a
defective.

## Domain quick reference

- Acceptance runs per processed batch, not per delivery and not per
  drawing. A batch is the set of parts that went through the same tanks
  at the same chemistry and current density, so it is the smallest unit
  whose result actually transfers between parts.
- The test set comes from the part category. A flight-critical part owes
  every characteristic including corrosion resistance and dimensional
  growth; a flight-standard part owes the load-bearing ones; ground
  support hardware owes the basics. Running the critical set on every
  batch is not conservative, it is a schedule cost that buys nothing.
- The sample grows with the lot but not in proportion to it. A
  square-root plan with a category floor keeps a small lot from being
  sampled trivially and a large one from being sampled to destruction,
  and the sample never exceeds the lot itself.
- The defective allowance is a rate, not a count. It is taken from the
  sample actually drawn, so the same rule gives zero on a small lot and
  a handful on a large one without a second table.
- A flight-critical batch allows no defective, and screening the rest of
  the lot is not a route back in. A defective there is evidence about
  the process the whole batch shared, so removing the parts that happened
  to be caught leaves the same process behind the ones that were not.
- Adhesion and corrosion testing consume what they touch, so they run on
  witness coupons carried through the tanks with the batch. A coupon
  only speaks for the parts it travelled with, so a batch split over
  several racks owes a coupon set per rack rather than one per batch.
- An incomplete test record is not a pass and not a failure. Until every
  required test is on the record there is no disposition to give, and
  naming the missing test is more useful than a verdict.

## Workflow

1. Take the part category and read its required test set, sample floor,
   defective allowance and whether screening is available to it. Reject
   an uncategorized batch rather than defaulting it to the lightest set.
2. Size the sample from the lot: the square-root plan, raised to the
   category floor, capped at the lot. Compute the root in integer
   arithmetic so a perfect-square lot cannot land either side of its own
   root on a different machine.
3. Derive the defective allowance from the sample that was actually
   drawn rather than from the lot.
4. Count the witness coupons: one set per rack for each test in the
   required set that destroys what it is run on. Report the destructive
   tests alongside the count so the coupon plan is auditable.
5. Compare the recorded tests against the required set. Report anything
   missing and stop there with no disposition; report anything recorded
   that the category does not call for as a finding, not a failure.
6. Judge the sample: within the allowance accepts; over the allowance
   calls for screening where the category permits it and rejects where
   it does not; a screen that has actually been completed accepts the
   lot, and on a flight-critical batch it does not.

## Pitfalls

- Sampling the delivery instead of the batch. Two deliveries can share a
  batch and one delivery can span three, so a sample drawn on paperwork
  boundaries says nothing about the tanks the parts went through.
- Taking the defective allowance from the lot size. The allowance
  applies to the sample drawn, and reading it off the lot inflates it by
  the sampling ratio, which is exactly the factor the plan exists to
  control.
- Screening a flight-critical lot to recover it. The defective is
  evidence about the shared process, and screening only removes the
  parts that happened to be caught while leaving the same process behind
  every part that was not.
- Running one witness coupon set for a batch that filled three racks.
  Bath agitation, current distribution and dwell differ by rack, so a
  coupon from one rack does not stand for parts hung on another.
- Issuing a disposition on an incomplete test record. A missing test is
  not a passed test, and an accept written before the record is closed
  is the hardest finding to unwind later.
- Rounding the square-root sample with floating-point arithmetic. A
  perfect-square lot sits exactly on its root, which is the value most
  likely to round differently between platforms, so the sample is
  computed in integers throughout.

## Behavior contract (gate 3)

The category rules, square-root sampling, defective allowance, witness
coupon count, test-record completeness check and the lot disposition are
exercised by the gate 3 contract test:
scripts/test_q7003_acceptance_testing.py against
scripts/q7003_acceptance_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7003_acceptance_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
