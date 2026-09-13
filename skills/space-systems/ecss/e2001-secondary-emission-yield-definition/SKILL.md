---
name: e2001-secondary-emission-yield-definition
description: "Use when define the secondary-electron-yield that ECSS-E-ST-20-01C clause 9.1 fixes for every multipactor provision: count the whole emitted population, true-secondaries plus backscattered-primaries, per arriving primary; read it from a measured emitted-to-incident current ratio; and treat it as a function of impact-energy and incidence-angle rather than one number per material. Compute the yield on Vaughan's empirical curve, locate the two impact energies at which it passes unity, and report the electron-growth-band they bracket, the angle-corrected peak-yield and peak-yield-energy, and whether a surface whose peak sits at or below unity carries any susceptible band at all. Trigger: ecss, e-st-20-01c, secondary-electron-yield, yield-crossover-energy, vaughan-yield-curve, impact-energy-dependence, incidence-angle-correction, peak-yield-energy, electron-growth-band."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-secondary-emission-yield-definition, secondary-electron-yield, yield-crossover-energy, vaughan-yield-curve, incidence-angle-correction, electron-growth-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Secondary Emission Yield, Defined (space-systems/ecss/e2001-secondary-emission-yield-definition)

Use when the task is the clause 9.1 meaning of secondary electron yield in
ECSS-E-ST-20-01C -- the quantity, written delta, that every later
multipactor provision consumes. This leaf fixes what delta counts, what it
depends on, and what its two unity crossings imply; it does not run a
susceptibility analysis or size a gap.

## Domain quick reference

- Delta is the number of electrons leaving a surface per electron arriving
  at it. The emitted population is counted whole: true secondaries freed
  from the material plus primaries returned by elastic and inelastic
  backscatter. Splitting the two is a measurement convenience -- the
  provisions consume their sum. Delta is a pure ratio and carries no unit,
  which is why it can be read straight off a measured emitted current
  divided by the incident current.
- Delta is not one number per material. It is a function of the impact
  energy of the arriving electron and of the angle that electron makes with
  the surface normal. Quoting a bare peak value for a material states only
  the maximum of that function, not the value at the energy any particular
  gap actually delivers.
- The deterministic reference shape used here is Vaughan's empirical curve:
  zero at and below a threshold energy, rising on a reduced-energy variable
  to the peak yield at the peak-yield energy, then decaying through a
  shallower branch and a slow tail. The curve is parameterised by the peak
  yield, the peak-yield energy and the threshold energy.
- Off-normal incidence raises both the peak yield and the peak-yield
  energy, because a grazing primary deposits its energy nearer the surface
  and more of what it frees escapes. A roughness factor scales that
  response, from a rough surface that is nearly angle-blind to a polished
  one that responds fully. The energy shift is twice the yield shift.
- The two impact energies at which delta equals one -- the lower and upper
  crossovers -- bracket the band inside which an electron population grows.
  Below the lower crossing and above the upper one the population decays
  whatever the geometry does. A surface whose peak yield sits at or below
  unity has no crossings at all and therefore no susceptible band, which is
  the whole point of a low-yield surface treatment.

## Workflow

1. Establish delta itself: sum the true-secondary and backscattered
   contributions, or divide a measured emitted current by the incident
   current. Reject a negative contribution or a non-positive incident
   current outright.
2. Correct the peak yield and peak-yield energy for the incidence angle and
   the surface roughness factor; reject an angle outside the physical range
   or a roughness factor outside its band.
3. Evaluate delta at each impact energy of interest on the Vaughan curve,
   returning zero at and below the threshold energy.
4. Locate the lower crossing between the threshold energy and the
   angle-corrected peak, and the upper crossing above the peak, by
   bisection on the curve. Return no crossing when the corrected peak yield
   sits at or below unity.
5. Report the band the two crossings bracket and mark each impact energy of
   interest as inside it or outside it. Treat an energy exactly at a
   crossing as replacement, not growth.
6. Sort the surface by its angle-corrected peak yield into low, moderate,
   elevated or high, and carry that categorization forward with the band.

## Pitfalls

- Quoting a material's peak yield as "the" yield: the provisions ask for
  delta at the impact energy the gap delivers, and at that energy the value
  can sit far below the peak, or outside the band entirely.
- Counting only true secondaries: backscattered primaries leave the surface
  too, and dropping them understates delta most exactly where the impact
  energy is low and the backscatter fraction is largest.
- Evaluating yield at normal incidence alone: the grazing case raises both
  the peak yield and the peak-yield energy, so it widens the band rather
  than shifting it, and a normal-incidence-only check can declare a surface
  clear that a grazing trajectory would not.
- Reading a peak yield above unity as susceptibility on its own: the band
  and the energy actually delivered decide that, and a peak barely above
  unity brackets a band too narrow for most gaps to sit in.
- Treating a peak yield of exactly one as susceptible because the computed
  value lands one unit-in-the-last-place above: unity is replacement, not
  growth, so the unity case is absorbed by tolerance and reported as no
  band rather than as a band of vanishing width.

## Behavior contract (gate 3)

The yield-definition, current-ratio, angle-correction, Vaughan-curve,
crossover, band-membership and categorization logic is exercised by the
gate 3 contract test:
scripts/test_e2001_secondary_emission_yield_definition.py against
scripts/e2001_secondary_emission_yield_definition_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_secondary_emission_yield_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
