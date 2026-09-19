---
name: q7006-specimen-preparation
description: "Prepare the coupon population for a particle and ultraviolet degradation campaign under ECSS-Q-ST-70-06C: decide for each measured property whether reading it consumes the coupon or can be taken in place under vacuum, count the exposed coupons a destructive reading needs at every measurement point, count the matching unexposed reference coupons that carry the same thermal history in the dark, fit a coupon into the uniform beam area in either orientation with its gap and edge keep-out, and divide the population into exposure runs. Use when sizing a coupon order or reviewing a preparation record. Trigger: ecss, q-st-70-06c, radiation-test-coupon-population, unexposed-reference-coupon, destructive-property-measurement-point, uniform-beam-area-coupon-fit, exposure-run-count."
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
  tags: [ecss, q-st-70-06c-particle-and-uv-radiation-testing, q-st-70-06c, q7006-specimen-preparation, radiation-test-coupon-population, unexposed-reference-coupon, destructive-property-measurement-point, uniform-beam-area-coupon-fit, exposure-run-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Specimen Preparation (space-systems/ecss/q7006-specimen-preparation)

Use when the task is the test-item clause of ECSS-Q-ST-70-06C: how many
coupons a radiation degradation campaign needs, which of them go into the
beam and which are held back unexposed, how big a coupon may be, and how many
exposure runs the population implies.

## Domain quick reference

- The coupon count is driven by the measurement, not by the material. Whether
  a property is read by breaking the coupon decides everything: a destructive
  reading consumes a fresh set of replicates at every measurement point, a
  non-destructive one re-reads the same set, and a campaign with four
  measurement points therefore needs four times the coupons for one property
  and one set for another.
- A reading taken in place, without breaking vacuum, changes the population
  twice over. It removes the coupon-per-point multiplication and it removes
  the unexposed reference set, because the same coupon is its own baseline
  measured before the beam is switched on.
- Unexposed references are part of the test item. A degradation figure is a
  difference, and without a coupon that saw the same pump-down, the same
  thermal history and the same handling in the dark, storage ageing and
  exposure damage arrive in the answer together and cannot be separated.
- Replicates are how a preparation accident is caught. One coupon per point
  gives a curve that cannot be distinguished from a single mounting error or
  a single contaminated surface, so a replicate minimum applies per property.
- A coupon has to sit in the uniform part of the beam, not merely inside the
  chamber. The uniform area is smaller than the target plane, it carries an
  edge keep-out, and coupons need a gap so that a holder finger does not
  shadow a neighbour; a coupon may be turned, so the fit is tried in both
  orientations before it is refused.
- Runs follow from capacity. Once the uniform area and the coupon size are
  fixed, the population divides into whole exposure runs, and the remainder
  costs a complete extra run rather than a fraction of one.

## Workflow

1. Validate each property: a name, whether the reading consumes the coupon,
   whether it is taken in place, and the replicate count. Destructive and
   in-place together is a contradiction, not a special case.
2. Count the exposed coupons property by property, multiplying the replicates
   by the measurement points for a destructive reading and leaving them
   unmultiplied for a non-destructive one.
3. Count the unexposed references on the same rule, dropping them entirely
   for a property read in place under vacuum.
4. Add the spare allowance as a fraction of the exposed population, rounding
   up, so a handling loss does not cost a measurement point.
5. Fit the coupon into the uniform area in both orientations, subtracting the
   edge keep-out on both sides and adding the inter-coupon gap to the pitch,
   and take the better of the two arrangements.
6. Divide the exposed population by the per-run capacity, rounding up, to get
   the number of exposure runs.
7. Return the plan with every finding — a thin replicate count, an empty
   property list, a coupon that cannot be made to fit — and mark it ready
   only when there are none.

## Pitfalls

- Ordering one coupon per property. A destructive reading at four points
  needs four sets, and discovering that at the second measurement point ends
  the campaign with half a degradation curve.
- Omitting the unexposed references. The difference being reported then
  contains storage ageing, handling and the exposure together, and a material
  that merely aged on the shelf is refused as radiation-sensitive.
- Treating an in-place reading as if it still needed a reference set. The
  coupon's own pre-exposure reading is the baseline, and the extra coupons
  occupy uniform beam area that the exposed population needed.
- Comparing the coupon to the uniform area axis by axis. A long narrow coupon
  that drops straight in when turned is rejected, and the coupon is cut
  smaller than it needed to be for no gain.
- Sizing to the target plane instead of the uniform area. The coupons at the
  edge then see a lower flux than the dosimetry says, and the scatter that
  produces is read as material variability.
- Forgetting that the remainder costs a whole run. Seventeen coupons into a
  sixteen-coupon fixture is three runs, and the schedule written on two is
  short by a full pump-down and exposure.

## Behavior contract (gate 3)

The property validation, exposed and reference coupon counting, spare
allowance, uniform-area fit in both orientations and the run-count division
are exercised by the gate 3 contract test:
scripts/test_q7006_specimen_preparation.py against
scripts/q7006_specimen_preparation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7006_specimen_preparation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
