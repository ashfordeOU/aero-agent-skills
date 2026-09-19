---
name: q7040-destructive-sampling
description: "Size the destructive sample a brazed lot owes and disposition the lot on what the sections show. Use when non-destructive inspection has seen the outside of the fillets and somebody has to decide how many joints get cut open, which test reads them and what the readings mean: take the applicable tests from the joint geometry, size the plan from lot size and criticality between a floor and a ceiling, switch to coupons brazed alongside the lot when the plan would eat the delivery, then grade each section on coverage, total void fraction and the longest continuous void before accepting, holding or rejecting. Trigger: ecss, q-st-70-40-brazing, braze-destructive-sample-plan, braze-metallographic-section-coverage, braze-peel-test, braze-continuous-void-limit, braze-representative-coupon."
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
  tags: [ecss, q-st-70-40-brazing, q7040-destructive-sampling, braze-destructive-sample-plan, braze-metallographic-section-coverage, braze-continuous-void-limit, braze-representative-coupon]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Destructive Sampling (space-systems/ecss/q7040-destructive-sampling)

Use when the task is the destructive-verification clause of
ECSS-Q-ST-70-40: setting how many brazements of a lot are cut open or
peeled, which test the geometry allows, and what the readings mean for
the lot.

## Domain quick reference

- Non-destructive inspection sees the outside of a fillet. The two
  properties that decide whether the joint carries load — how much of
  the faying area the filler actually wetted, and whether the voids are
  scattered or joined into one unbonded run — are inside it.
- The test comes from the geometry, not from preference. A lap joint
  peels and the peeled faces show the wetted area directly; a butt or
  sleeve joint tears the parent before it peels, so it is sectioned and
  read under a microscope.
- The number comes from the lot size and the criticality, held between
  a floor and a ceiling. Below the floor a single bad joint is not
  visible at all; above the ceiling the verification costs more flight
  parts than the delivery is worth.
- When the plan would consume a large fraction of a small lot, the
  answer is not to destroy the lot. Representative coupons brazed in
  the same run, on the same fixture and out of the same filler batch
  carry the evidence instead.
- A coupon is only representative while all three of those hold. A
  coupon brazed in a later run is a different thermal history and
  evidences that run, not this lot.
- Coverage, total void fraction and longest continuous void are three
  separate limits. The third exists because the same void area scattered
  across a joint is sound and joined into one run is a crack starter,
  and total void fraction cannot tell those two apart.
- A section whose continuous void exceeds its total void area, or whose
  coverage and voids together exceed the faying area, is a measurement
  error. It is refused rather than graded.
- One failure is not automatically a rejected lot outside the critical
  category. Double sampling exists so a single outlier can be tested
  rather than assumed; a failure after a resample is the lot answering.

## Workflow

1. Take the joint geometry and list the destructive tests that can
   actually read it.
2. Size the plan from the lot size and criticality, apply the floor and
   the ceiling, and never ask for more joints than the lot holds.
3. Compare the plan against the lot: past the switch fraction, call for
   representative coupons brazed with the lot and say why in the plan
   rather than leaving the reader to infer it.
4. Read each section for coverage, total void fraction and longest
   continuous void, refusing a reading set that is internally
   impossible.
5. Grade each against the limits for the criticality, absorbing
   representation error at each boundary with a named tolerance so a
   reading that lands exactly on a limit is not failed by arithmetic.
6. Disposition the lot: accept when every planned sample was read and
   passed; reject on any failure in a critical lot, on more than one
   failure, or on a failure after a resample; otherwise hold for double
   sampling. Report an under-sampled lot as a finding rather than
   accepting what was read.

## Pitfalls

- Reading total void fraction alone. Two sections with the same void
  area are not the same joint, and the one with the joined-up run is
  the one that fails in service.
- Sampling a small lot to plan and destroying most of the delivery.
  The plan is a means of evidencing the lot, not of consuming it.
- Brazing the coupons in a convenient later run. The coupon evidences
  the run it was brazed in; a coupon from another run evidences nothing
  about this lot.
- Peeling a butt joint because peel is the quicker test. The parent
  tears first and the result measures the parent, not the braze.
- Accepting a lot on the samples that happened to be read. Fewer
  samples than the plan is a coverage finding, and an accepted lot with
  a coverage finding behind it is an unverified lot.
- Rejecting a major lot on one outlier without the double sample. The
  resample is what distinguishes a process that drifted from one joint
  that was mishandled.

## Behavior contract (gate 3)

The geometry-to-test mapping, the floored and capped sample size, the
coupon switch with its boundary case, the three section limits with
their internally-impossible-reading refusals and the accept, hold and
reject dispositions are exercised by the gate 3 contract test:
scripts/test_q7040_destructive_sampling.py against
scripts/q7040_destructive_sampling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7040_destructive_sampling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
