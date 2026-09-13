---
name: e2001-emission-yield-sample-characteristics
description: "Use when assess whether a secondary-emission-yield coupon is manufactured representatively of the real hardware under ECSS-E-ST-20-01C clause 9.4.3: compare the coupon's base-material, surface-treatment, production-route, surface-finish, cleaning-process and bake-out state against the flight-hardware definition, separate the mismatches that void representativeness outright from those that only need written justification, check the coupon area against the probe-beam footprint, check storage age against the shelf-life allowance, and return a per-attribute finding list with an overall representativeness verdict. Trigger: ecss, e-st-20-electrical-scope, emission-yield-coupon-representativeness, surface-treatment-fidelity, production-route-match, flight-hardware-representative-coupon, coupon-area-adequacy, secondary-emission-yield-sample."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-emission-yield-sample-characteristics, emission-yield-coupon-representativeness, surface-treatment-fidelity, production-route-match, flight-hardware-representative-coupon, coupon-area-adequacy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Emission Yield Sample Characteristics (space-systems/ecss/e2001-emission-yield-sample-characteristics)

Use when the task is the coupon-representativeness check of
ECSS-E-ST-20-01C clause 9.4.3 -- confirming that a coupon submitted for
a secondary-emission-yield measurement was made from the same material
by the same production route and carries the same surface treatment as
the real hardware, so that the measured yield curve is admissible as
input to the multipactor margin of that hardware.

## Domain quick reference

- Secondary-emission yield is a property of the outermost few
  nanometres, not of the bulk. Two coupons cut from the same alloy bar
  give different yield curves if one is chemically converted and the
  other bare, if one is machined and the other additively built, or if
  one is vapour-degreased and the other solvent-wiped. The measured
  curve therefore only belongs to hardware whose surface arrived by
  the same route.
- The comparison runs attribute by attribute against the flight
  definition, and the attributes are not equal in weight. Base
  material, surface treatment and production route are the ones that
  govern the emitting layer; a mismatch there voids representativeness
  and the measurement cannot be used. Cleaning process, bake-out state
  and surface finish shift the yield within a narrower band; a
  mismatch there is a finding that a written justification can close,
  and the result is a conditionally-representative coupon.
- Surface finish is compared as a number, not as a label. A coupon
  rougher than the hardware traps re-emitted electrons and reads low;
  a coupon smoother than the hardware reads high. The deviation is
  judged against a stated fractional tolerance on the flight roughness
  value, and a coupon exactly at the tolerance edge is inside it.
- The coupon must also be physically usable: its measurement area has
  to carry the probe-beam footprint with a keep-out margin, or the
  beam clips the edge and samples the mounting instead of the surface.
- Surfaces age. An untreated or freshly converted surface picks up
  adsorbates and oxide in storage, so a coupon measured long after its
  manufacture no longer represents freshly produced hardware unless it
  was stored to a controlled regime; the age check is against a stated
  shelf-life allowance, and an exceedance is a finding in its own
  right.
- An attribute absent from either definition is never assumed to
  match. A missing attribute is an incomplete submission and is
  rejected before any verdict is formed.

## Workflow

1. Validate both definitions -- the coupon's and the flight
   hardware's. Every governed attribute must be present and carry a
   usable value; reject an incomplete or malformed definition before
   any comparison is attempted.
2. Compare the three governing attributes (base material, surface
   treatment, production route) as normalized strings. Any mismatch
   is a voiding finding.
3. Compare the supporting attributes: cleaning process and bake-out
   state as normalized values, surface finish as a number judged
   against a fractional tolerance on the flight value. Each mismatch
   is a justification-required finding, not a voiding one.
4. Absorb representation error at the surface-finish tolerance edge
   with a relative tolerance -- a deviation that is exactly at the
   allowance is inside it, and the allowance is never widened to make
   a coupon pass.
5. Check the coupon's measurement area against the probe-beam
   footprint scaled by the keep-out margin factor; an undersized
   coupon is a voiding finding, because no justification recovers a
   beam that clips the edge.
6. Check storage age against the shelf-life allowance; an exceedance
   is a justification-required finding unless the coupon was held in a
   controlled-storage regime that the submission records.
7. Form the verdict: representative when no findings remain,
   conditionally-representative when only justification-required
   findings remain and each carries a recorded justification, and
   not-representative when any voiding finding is present or any
   justification is missing.

## Pitfalls

- Matching the base material and stopping there -- the emitting layer
  is the treatment, so an identical alloy with a different conversion
  coating is a different surface and a different yield curve.
- Treating the production route as bookkeeping -- an additively built
  surface and a machined surface of the same alloy differ in
  roughness, in trapped porosity and in oxide, all of which move the
  first crossover the multipactor margin is built on.
- Comparing surface finish by label ("polished", "as-machined")
  instead of by number -- the yield varies continuously with
  roughness, and a label hides a factor-of-three deviation.
- Accepting a coupon whose measurement area merely equals the beam
  footprint -- with no keep-out margin the beam samples the coupon
  edge and its mount, and the mount is not the material under test.
- Reading an absent attribute as a match -- a definition that never
  stated its cleaning process has not demonstrated a common process,
  it has failed to describe itself, and the submission is incomplete.
- Closing a voiding finding with a written justification -- a
  justification can explain a narrower-band difference such as a
  cleaning process; it cannot make a coupon of the wrong material
  represent the hardware.

## Behavior contract (gate 3)

The definition validation, governing- and supporting-attribute
comparison, surface-finish tolerance, coupon-area adequacy, storage-age
and verdict logic is exercised by the gate 3 contract test:
scripts/test_e2001_emission_yield_sample_characteristics.py against
scripts/e2001_emission_yield_sample_characteristics_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_emission_yield_sample_characteristics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
