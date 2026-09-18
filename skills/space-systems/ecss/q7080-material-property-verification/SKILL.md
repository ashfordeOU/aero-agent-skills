---
name: q7080-material-property-verification
description: "Verify the mechanical properties of an additive build or batch from its witness coupons. Use when a coupon population has to carry the batch: keep only coupons from the same build plate and the same furnace lot and name every one excluded, check that the population samples the build direction and not just the in-plane orientations, grade each coupon against the minimum rather than the population mean, report count, mean, extremes and spread per property, form the ratio of the weakest orientation mean to the strongest, then take the worst and name the property that drove it. Trigger: ecss, q-st-70-80-additive-manufacturing, am-witness-coupon-properties, am-build-direction-coupon-orientation, am-coupon-build-lot-provenance, am-build-batch-tensile-acceptance, am-as-built-property-anisotropy."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-material-property-verification, am-witness-coupon-properties, am-build-direction-coupon-orientation, am-coupon-build-lot-provenance, am-build-batch-tensile-acceptance, am-as-built-property-anisotropy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Coupon Property Verification (space-systems/ecss/q7080-material-property-verification)

Use when the quality clause of ECSS-Q-ST-70-80 is the task: deciding
whether the witness coupons built and heat treated alongside an
additively manufactured part are enough evidence, and whether what they
measured lets the build or batch go forward.

## Domain quick reference

- The part is never tested. Coupons built beside it are, and they are
  evidence only while they share the things that made the part what it
  is: the same plate, the same parameter set and the same furnace lot.
- A coupon from another build or another heat-treatment lot is evidence
  about that build. It is excluded and named, never averaged into this
  population, because the average of two populations describes neither.
- The build direction is the weak direction of the process. Layer
  boundaries are transverse to it, lack-of-fusion defects lie in it, and
  a population sampled only in plane cannot see the property that
  usually governs the part.
- Each coupon is graded against the minimum. The mean of the population
  is a summary, and a mean above the minimum is exactly what a plate
  with one cold corner produces.
- The spread is reported with the mean. Two builds with the same mean
  and different standard deviations are different processes, and only
  the spread shows which one produced the batch.
- Anisotropy is a process quantity in its own right. The ratio of the
  weakest orientation mean to the strongest can collapse while every
  individual coupon is still above its minimum, and that is a finding
  about the machine, not about the coupon.
- A population that samples one orientation cannot form that ratio at
  all, which is itself something to report rather than to pass over.

## Workflow

1. Select the evidence first: keep the coupons whose build plate and
   furnace lot match the batch under assessment, list every coupon
   excluded together with the reason, and refuse a batch that has no
   coupon of its own rather than borrowing one.
2. Count the surviving coupons by orientation against the required set,
   treating an absent orientation as a rejection and a thin one as a
   review, and call out an absent build-direction orientation by name.
3. Grade every coupon against every declared minimum, naming the coupon,
   its orientation and the property that failed.
4. Summarise each property over the accepted population: count, mean,
   extremes and sample standard deviation, so the spread is visible
   beside the mean.
5. Take the mean of the governing property per orientation, form the
   ratio of the weakest to the strongest, and grade it against the
   declared anisotropy floor.
6. Take the worst of the coupon grading, the coverage and the anisotropy
   as the batch verdict, name the property that drove it, and prefix
   every finding with the characteristic it came from.
7. Where a coupon value should land exactly on its minimum, grade it
   with the tolerant comparison so a unit conversion cannot turn an
   on-limit coupon into a reject.

## Pitfalls

- Averaging coupons from more than one build or furnace lot to reach the
  sample size. The result describes a population that was never built,
  and it usually hides the one build that moved.
- Grading the population mean against the minimum. The minimum applies
  to material, and the coupon that failed is the one that came from the
  part of the plate the part was built on.
- Sampling only the in-plane orientations because they are easier to
  fit on the plate. The build direction is where the process is weakest
  and where the design usually has least margin.
- Reporting a mean with no spread. A tight build and a scattered one
  with the same mean are different processes and only one of them is
  repeatable.
- Reading an anisotropy collapse as acceptable because every coupon
  passed. The ratio is evidence about the machine and the parameter
  set, and it moves before the minima do.
- Forming a ratio from one orientation. With a single direction
  populated there is no ratio, and reporting unity for it invents a
  result.
- Treating a coupon that sits exactly on the minimum as a reject. That
  is a representation question inside the comparison, not a change to
  the requirement.

## Behavior contract (gate 3)

The coupon validation, build and lot provenance selection, orientation
coverage, per-coupon minima grading, property statistics and the
anisotropy ratio are exercised by the gate 3 contract test:
scripts/test_q7080_material_property_verification.py against
scripts/q7080_material_property_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_material_property_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
