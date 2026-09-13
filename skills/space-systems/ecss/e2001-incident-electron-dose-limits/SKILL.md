---
name: e2001-incident-electron-dose-limits
description: "Use when verify that the incident electron-beam dose delivered to a secondary-emission-yield coupon under ECSS-E-ST-20-01C clause 9.4.2.3 stays below the level that conditions or charges the measured surface: validate the beam-current, spot-area and dwell-time settings, compute the incident charge-density per measurement point and per irradiated spot, derate the allowable dose for beam-energy and for the coupon category (grounded-metal, coated-conductor, rear-grounded-dielectric, floating-dielectric), compare the accumulated dose against that allowance, and derive the maximum dwell-time and the number of fresh spots a measurement campaign needs. Trigger: ecss, e-st-20-electrical-scope, incident-electron-dose, secondary-emission-yield, electron-beam-dose-budget, surface-conditioning-avoidance, charge-density-per-spot, fresh-spot-planning, multipactor-coupon-measurement."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-incident-electron-dose-limits, incident-electron-dose, secondary-emission-yield, electron-beam-dose-budget, surface-conditioning-avoidance, fresh-spot-planning]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Incident Electron Dose Limits (space-systems/ecss/e2001-incident-electron-dose-limits)

Use when the task is the incident-dose control of ECSS-E-ST-20-01C
clause 9.4.2.3 -- keeping the electron dose delivered to a
secondary-emission-yield coupon low enough that the measurement does
not itself condition the surface or leave charge on it, and therefore
low enough that the reported yield still describes the as-received
material rather than the beam-modified one.

## Domain quick reference

- A secondary-emission-yield measurement is destructive to the very
  property it measures. Electron bombardment cleans and graphitizes an
  adsorbate layer (electron-beam conditioning), which drives the yield
  down monotonically with accumulated dose; on a poorly conducting
  surface the same bombardment leaves trapped charge, which shifts the
  effective landing energy and corrupts the yield at low energies.
  Clause 9.4.2.3 therefore bounds the dose, not the current alone.
- The controlled quantity is incident charge-density on the
  irradiated spot: beam-current times dwell-time divided by
  spot-area, accumulated over every measurement point taken on that
  spot. Two settings with the same beam-current but different
  spot-area are not equivalent, and a long sweep over many landing
  energies accumulates dose point by point on the same spot.
- The allowance depends on the coupon category, because the escape
  route for the deposited charge differs: a grounded-metal coupon
  tolerates the most, a coated-conductor less (the coating is the
  measured layer and conditions first), a rear-grounded-dielectric
  much less (charge leaks only through the bulk), and a
  floating-dielectric least of all.
- The allowance is further derated for landing energy. Below roughly
  50 eV the range is so shallow that the whole dose lands in the
  emitting layer; between 50 eV and 200 eV it is still shallow; above
  about 2 keV the primaries implant below the escape depth and build
  an embedded charge layer instead of conditioning the surface. Only
  the mid-band carries the full allowance.
- When the planned campaign exceeds the allowance on one spot, the
  remedies are ordered: shorten the dwell-time, widen the spot, lower
  the beam-current, or move to a fresh unirradiated spot. Moving spots
  is the only remedy that resets the accumulated dose, so a campaign
  is planned as a number of points per spot and a number of fresh
  spots, and the coupon must be large enough to supply them.

## Workflow

1. Validate the beam settings: beam-current, spot-area, dwell-time
   and landing energy must all be finite and strictly positive, and
   the landing energy must sit inside the facility's usable band.
   Reject the settings before any dose number is produced.
2. Compute the incident charge-density for one measurement point:
   beam-current times dwell-time divided by spot-area, carried in
   microcoulomb per square centimetre. Multiply by the number of
   points taken without moving the beam to get the accumulated dose
   on that spot.
3. Look up the base allowance for the coupon category and multiply it
   by the landing-energy derating factor to get the allowable dose for
   this measurement. Reject an unrecognized coupon category rather
   than defaulting it to the most permissive one.
4. Compare the accumulated dose against the allowance. Report
   compliant when the dose is at or below the allowance, marginal when
   it sits inside the caution band just under it, and exceeded above
   it. Absorb floating-point representation error at the boundary with
   a relative tolerance -- a plan that lands exactly at the allowance is
   inside it, and the allowance itself is never widened.
5. When the plan is not compliant, derive the corrective numbers: the
   maximum dwell-time that fits the allowance at the present current
   and spot-area, and the number of points per spot that fits it.
6. Convert the points-per-spot allowance and the total campaign point
   count into a number of fresh spots, and check that count against
   the spots the coupon can physically supply at the given spot-area
   and coupon area.
7. Aggregate the findings; the dose plan is not acceptable until the
   accumulated dose is inside the allowance and the coupon supplies
   the fresh spots the campaign needs.

## Pitfalls

- Budgeting the beam-current alone and leaving dwell-time out -- the
  conditioning threshold is a charge-density, so a low current held
  for a long sweep breaks it exactly like a high current held briefly.
- Accumulating dose per measurement point but reporting it per point
  -- a forty-point energy sweep on one spot delivers forty times the
  single-point dose, and only the accumulated figure is comparable to
  the allowance.
- Applying the grounded-metal allowance to a floating-dielectric
  coupon -- the dielectric has no leakage path, so the same dose that
  merely cleans a metal shifts the dielectric's surface potential and
  invalidates the low-energy end of the yield curve.
- Treating the landing-energy derating as optional -- a 30 eV sweep
  and a 1 keV sweep deposit the same charge into very different
  depths, and using the full allowance at the shallow end
  conditions the surface while the plan still reads as compliant.
- Reading a first-pass exceedance as a reason to widen the allowance
  -- the allowance is the engineering limit; the plan moves (shorter
  dwell, wider spot, lower current, fresh spot), never the limit.
- Planning fresh spots without checking coupon area -- a campaign that
  needs more unirradiated spots than the coupon can supply is not a
  dose-compliant plan, it is an undersized coupon.

## Behavior contract (gate 3)

The beam-settings validation, charge-density, category and
landing-energy derating, dose-margin categorization, maximum-dwell and
fresh-spot planning logic is exercised by the gate 3 contract test:
scripts/test_e2001_incident_electron_dose_limits.py against
scripts/e2001_incident_electron_dose_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_incident_electron_dose_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
