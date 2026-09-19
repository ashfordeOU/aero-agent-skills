---
name: q7005-witness-plate-method
description: "Derive the organic deposition on a protected surface from witness plates and quartz crystal microbalances under ECSS-Q-ST-70-05C. Use when coupons and a crystal have been exposed alongside the hardware and their readings have to become an areal mass, a deposition rate and a projection to the end of exposure. Subtracts the handling gain seen on the control coupon, converts a crystal frequency shift through its own sensitivity, scales the coupon result onto the hardware by the view-factor ratio, and reports a coupon and crystal that disagree rather than averaging them away. Trigger: ecss, q-st-70-05, witness-plate-deposition-sampling, quartz-crystal-microbalance-frequency-shift, control-coupon-handling-gain, witness-plate-view-factor-scaling, deposition-rate-projection, contamination-areal-mass."
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
  tags: [ecss, q-st-70-contamination-infrared-scope, q7005-witness-plate-method, witness-plate-deposition-sampling, quartz-crystal-microbalance-frequency-shift, control-coupon-handling-gain, witness-plate-view-factor-scaling, deposition-rate-projection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Organic Contamination by IR — Witness Plate Sampling (space-systems/ecss/q7005-witness-plate-method)

Use when the task is sampling deposition with witness hardware rather
than measuring the flight surface itself — coupons read by infrared and
crystal microbalances read by frequency, exposed alongside the article
so the deposit they catch stands in for the deposit it catches.

## Domain quick reference

- A witness coupon is a surrogate, and the substitution is only as good
  as the geometry behind it. What the coupon sees of the sources is its
  view factor; the hardware has its own. Reporting the coupon figure as
  the hardware figure silently assumes those two are equal, which they
  are only when the coupon sits in the same place as the surface it
  represents.
- The coupon result is a difference of two readings on the same coupon,
  before and after exposure. A control coupon travels, is handled and is
  read the same way but is never exposed; whatever it gained is handling
  and storage, and it belongs subtracted from the exposed coupon rather
  than reported as deposition.
- A crystal microbalance reads mass as a frequency shift, and deposition
  drives the frequency down. The conversion is the crystal's own
  sensitivity in hertz per microgram per square centimetre, a property
  of that crystal and its cut, not a universal number. A positive shift
  is mass leaving, or a thermal drift, and either way it is not
  deposition.
- Crystal and coupon measure different things over different areas and
  can legitimately differ a little. A large disagreement is a result in
  itself — a shadowed coupon, a drifting crystal, a re-evaporating
  deposit — and averaging the two hides exactly the case worth seeing.
- A rate is only projectable while the source behaves the same way.
  Projecting an early outgassing-dominated rate across a whole mission
  overstates the end state, so the projection carries the interval it
  was measured over.

## Workflow

1. Validate the coupon records: area, exposure duration, the pre- and
   post-exposure areal readings, and the view factor at the coupon
   location and at the surface being represented.
2. Form the gross gain on each exposed coupon, subtract the gain seen on
   the control coupon, and refuse a net below the weighing noise as a
   measured deposition.
3. Convert the crystal frequency shift to an areal mass through the
   crystal sensitivity, refusing a shift in the direction that means
   mass left the crystal.
4. Cross-check the coupon and crystal areal masses against the
   agreement tolerance and record a disagreement as a finding instead of
   combining them.
5. Scale the coupon areal mass onto the represented surface by the ratio
   of view factors, and say so explicitly when the ratio is not unity.
6. Divide by the exposure duration for a deposition rate, and project to
   the end of exposure, carrying the measured interval with the
   projection.
7. Compare the projected areal mass with the allocated budget and report
   the margin, the rate, and every finding raised.

## Pitfalls

- Reporting the coupon number as the hardware number. The two differ by
  the view-factor ratio, and a coupon deliberately placed in a
  high-deposition location is conservative only if the ratio is applied.
- Skipping the control coupon. Handling, bagging and storage gains are
  not small next to a clean-hardware allocation, and without a control
  they are indistinguishable from flight deposition.
- Reading a frequency rise as deposition of the same magnitude. The sign
  carries the physics: mass gain lowers the frequency, so a rise is
  loss, drift or a temperature excursion and needs resolving first.
- Averaging a disagreeing coupon and crystal. The disagreement is the
  measurement telling you one of the two is not sampling what you think;
  the mean of a good reading and a bad one is a bad reading.
- Projecting a rate past the interval it was measured over without
  saying so. Outgassing sources decay, so a rate from the first days is
  not the rate of the last, and the projection has to name its basis.

## Behavior contract (gate 3)

The coupon validation, control subtraction, crystal frequency-shift
conversion, coupon-crystal cross-check, view-factor scaling, rate
formation, projection and budget comparison are exercised by the gate 3
contract test: scripts/test_q7005_witness_plate_method.py against
scripts/q7005_witness_plate_method_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7005_witness_plate_method.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
