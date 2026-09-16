---
name: e2008-solar-cell-adherence-measurement
description: "Use when a coupon adherence campaign has to be accepted, sentenced or repeated. Compute the adherence of bonded cell assemblies to the panel substrate from process-coupon data under ECSS-E-ST-20-08C clause 5.3.3.11.1: compare each coupon build record against the panel bondline and set aside any coupon that does not share facesheet, adhesive designation, adhesive lot, cure profile, cell assembly and bonding tool; reduce each coupon to a separation stress and a separation mode; carry a facesheet or cell-assembly fracture as a lower bound on the bond rather than as a measurement of it; reduce the surviving population to a one-sided lower tolerance bound so the weak tail governs acceptance; and cap the share that let go at the bondline interface. Trigger: ecss, e-st-20-electrical-scope, solar-cell-adherence-measurement, process-coupon-adherence, bondline-separation-mode, cell-to-substrate-bond-strength, adherence-lower-tolerance-bound, coupon-representativeness-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-solar-cell-adherence-measurement, solar-cell-adherence-measurement, process-coupon-adherence, bondline-separation-mode, cell-to-substrate-bond-strength, adherence-lower-tolerance-bound, coupon-representativeness-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Solar Cell Adherence Measurement (space-systems/ecss/e2008-solar-cell-adherence-measurement)

Use when the task is the adherence measurement of ECSS-E-ST-20-08C
clause 5.3.3.11.1 -- showing that the cell assemblies are actually bonded
to the panel substrate, with the evidence taken from process coupons
built alongside the panel rather than from the panel itself.

## Domain quick reference

- The flight panel cannot be the specimen. Pulling a cell assembly off
  it destroys the article, so the adherence evidence comes from process
  coupons laid up in the same run. The measurement is therefore only as
  good as the claim that the coupon carries the same bondline.
- Representativeness is decided attribute by attribute: substrate
  facesheet, adhesive designation, adhesive lot, cure profile, cell
  assembly type and bonding tool. A coupon that differs on any of them
  is evidence about a different joint, so it leaves the population
  rather than diluting it. An undeclared attribute is rejected, never
  assumed equal.
- Each coupon yields a separation stress -- peak force over bonded area
  -- and a separation mode. The stress is the number; the mode says what
  the number means.
- Separation at the bondline interface is the mode a bond defect
  produces, so the acceptance policy caps its share of the population.
  Cohesive separation inside the adhesive means the joint outlived the
  adhesive bulk. Separation through the facesheet or a fractured cell
  assembly means a weaker member gave way first, so the recorded stress
  is a lower bound on the bond, not a measurement of it.
- Acceptance is taken on the weak tail, not the mean. A one-sided lower
  tolerance bound -- the mean less a factor times the sample standard
  deviation, with the factor falling as the sample grows -- is what the
  requirement is compared against, so a scattered population can fail
  even when every single coupon cleared the minimum.
- The tolerance factors, the minimum strength and the coupon count are a
  declared project policy rather than physical constants, so they are
  stated with the result.

## Workflow

1. Capture the panel build record and the build record of every coupon.
   Reject a record that leaves a governing attribute undeclared instead
   of defaulting it, because an undeclared bondline attribute is exactly
   what makes the campaign unusable later.
2. Compare each coupon against the panel and set aside the ones that do
   not match, naming the attribute that differs. Record how many
   coupons were set aside; the count is itself a process finding.
3. Reduce every surviving coupon to a separation stress from its peak
   force and bonded area, and categorize its separation mode.
4. Mark facesheet and cell-assembly fractures as lower bounds. They
   still have to clear the minimum -- the load path failed at that
   stress whatever gave way -- but they must never be quoted as the
   strength of the bond.
5. Compute the population statistics and the one-sided lower tolerance
   bound at the sample size actually achieved, taking the conservative
   tabulated factor when the size falls between entries.
6. Sentence the campaign against the policy: enough representative
   coupons, every coupon above the minimum, the interface-separation
   share within its cap, and the lower tolerance bound above the
   minimum. Report each shortfall separately so the retest is scoped to
   the one that failed.

## Pitfalls

- Accepting on the mean. The mean hides the tail that the panel will
  actually fail at, and a population with wide scatter can put every
  coupon above the minimum while the lower tolerance bound sits well
  below it.
- Letting a coupon from a different adhesive lot or cure run stay in the
  population because its number looked fine. It is evidence about
  another joint; a high value from it is worse than no value, because it
  lifts the mean and shrinks the apparent scatter.
- Quoting a facesheet or cell-fracture separation as the bond strength.
  The bond never let go in that test, so the figure understates it, and
  a design decision taken on that number is taken on the wrong quantity.
- Treating interface separations as just another data point. They are
  the signature of a contaminated, starved or under-cured bondline, so
  their share is capped independently of the strength numbers.
- Comparing a stress against the acceptance number by bare arithmetic.
  The stress is a quotient and the bound is a difference of products, so
  a coupon meant to sit exactly on the requirement can land a few units
  in the last place below it; the comparison absorbs that representation
  error while the requirement stays untouched.

## Behavior contract (gate 3)

Representativeness screening, separation stress, separation-mode
handling, population statistics, the one-sided lower tolerance bound and
the campaign verdict are exercised by the gate 3 contract test:
scripts/test_e2008_solar_cell_adherence_measurement.py against
scripts/e2008_solar_cell_adherence_measurement_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_solar_cell_adherence_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
