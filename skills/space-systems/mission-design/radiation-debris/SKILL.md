---
name: radiation-debris
description: "Use when you must assess the space radiation and orbital debris environment for a spacecraft mission design: estimate the trapped radiation belt (van Allen) dose rate as a function of altitude and inclination with a simplified AE-8/AP-8 style flux band model, add the solar particle event fluence, compute the single-event upset rate with the RPP model from the upset cross-section and LET spectrum, size aluminum shielding against total ionizing dose with exponential attenuation, and estimate the debris collision probability from the flux, cross-section, and mission life. Produces the dose, SEU rate, and debris risk verdicts for the orbit. Trigger: radiation environment, trapped belts, total ionizing dose, single-event effects, seu rate, solar particle events, orbital debris, collision probability."
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
  subdomain: mission-design
  tags: [radiation-environment, trapped-belts, total-ionizing-dose, single-event-effects, seu-rate, solar-particle-events, orbital-debris, shielding-attenuation, collision-probability, mission-design]
  version: 0.1.0
  author: AeroSkills
---

# Radiation and Debris Environment Assessment (space-systems/mission-design/radiation-debris)

Use when the task is a space environment assessment for mission design:
estimating the trapped radiation belt dose the spacecraft accumulates,
adding the solar particle event contribution, checking the single-event
upset rate for sensitive electronics, sizing shielding against total
ionizing dose, and estimating the orbital debris collision probability
over the mission life.

Units convention (stated once): altitude in km, inclination in degrees,
dose rate in rad(Si) per day, mission life in years, shielding in mm of
aluminum, device cross-section in cm^2, spacecraft debris cross-section
in m^2, LET in MeV cm^2/mg, fluence in protons/cm^2, flux in
particles/m^2/year for debris and particles/cm^2/day for the LET
spectrum.

The models are simplified engineering proxies with the shape of the
AE-8/AP-8 trapped belt, JPL-style solar particle, and ORDEM/MASTER
debris environment families. They are trend tools for mission design,
not flight qualification data; a real program uses the actual
environment models with the actual component test data.

## Domain quick reference

- Trapped belt dose rate: two Gaussian flux bands, a proton belt
  peaking near 3500 km and an electron belt peaking near 20000 km,
  scaled by an inclination factor from 0.3 (equatorial) to 1.0
  (polar). At the proton belt peak in a polar orbit the unshielded
  rate is about 60.8 rad/day; at 600 km in a sun-synchronous-like
  orbit it is about 0.26 rad/day.
- Inclination factor: 1 - 0.7 * cos^2(inclination), symmetric about
  90 degrees, so an 80 degree and a 100 degree orbit see the same
  belt fraction. Equatorial orbits skim the belt edges; polar orbits
  cross the full belt structure every orbit.
- Solar particle event fluence: integral fluence above energy E is a
  power law, Phi = 1e8 * (E / 10 MeV)^(-3) * mission_years
  protons/cm^2, the order of a 1-in-5-year worst-week event above
  10 MeV. Over 5 years at 10 MeV that is 5e8 protons/cm^2; at 100 MeV
  the fluence drops by a factor of 1000.
- Single-event upset rate (RPP model): the Weibull cross-section
  sigma = sigma_sat * (1 - exp(-((LET - L0) / W)^S)) above the LET
  threshold, summed over the LET spectrum. The rate scales linearly
  with the saturation cross-section: doubling sigma_sat doubles the
  rate. A spectrum entirely below the threshold gives zero upsets.
- Total ionizing dose versus shielding: two-component exponential
  attenuation. The electron component (default 70 percent of the
  unshielded dose) is absorbed with a 3 mm aluminum 1/e length; the
  proton component (30 percent) penetrates with a 60 mm 1/e length.
  The shielded dose always sits below the unshielded dose and falls
  monotonically with thickness.
- Shielding sizing: shielding_for_dose_limit returns the minimum
  aluminum thickness meeting a dose limit, or None when even the
  maximum thickness cannot (the proton component floor sits above the
  limit). At the proton belt peak (60.8 rad/day, 1 year) a 10 krad
  limit needs about 4.5 mm of aluminum.
- Debris flux: a Gaussian density band peaking near 850 km where the
  catalogued debris population is densest, scaled by a size power law
  (s / 1 cm)^(-2.6). At the peak the flux of particles above 1 cm is
  5e-5 per m^2 per year; at 550 km it drops by about 63 percent.
- Collision probability: Poisson statistics, P = 1 - exp(-flux * area
  * mission_years). For small expected collisions the probability is
  approximately the product; it grows with mission life and
  cross-section, and is exactly 0 for zero area or zero flux.
- Verdicts: dose_verdict is ADEQUATE (at least 20 percent margin to
  the limit), MARGINAL (below the limit with less margin), or
  EXCEEDED (at or above the limit). debris_verdict is LOW below 1
  percent, MODERATE to 10 percent, HIGH above.
- ECSS-E-ST-10C (systems engineering general requirements) frames the
  space environment assessment within the ECSS lifecycle; ECSS
  standards are free to download from https://ecss.nl/standards/
  (name + paraphrase + link only).

## Workflow

1. Define the orbit and mission: altitude in km, inclination in
   degrees, and mission life in years.
2. Get the unshielded trapped belt dose rate with
   trapped_belt_dose_rate, and the solar particle event fluence with
   spe_fluence at the energies of interest (10 and 100 MeV are the
   usual reference points).
3. Build the LET spectrum with power_law_let_spectrum (or supply a
   measured spectrum as (LET, differential flux) pairs), then compute
   the single-event upset rate with seu_rate from the device
   saturation cross-section, LET threshold, Weibull width and shape.
4. Compute the total ionizing dose behind the chosen shielding with
   tid_after_shielding, or invert it with shielding_for_dose_limit to
   size the shielding against the component dose limit; check the
   dose margin with dose_verdict.
5. Get the debris flux with debris_flux_per_m2_yr at the mission
   altitude, then the collision probability with collision_probability
   from the spacecraft cross-section and mission life; grade it with
   debris_verdict.
6. Build the RadiationDebrisAssessment with all the mission parameters
   and use report for a single dict summary of dose, SEU rate, and
   debris risk with the verdicts.
7. Sanity-check the result: a low earth orbit sun-synchronous mission
   at 600 km with a few mm of aluminum accumulates a fraction of a
   krad over 5 years with a collision probability below 1 percent; an
   orbit through the proton belt peak without shielding accumulates
   tens of krad per year.

## Worked example

A 600 km sun-synchronous-like orbit (98 degrees inclination), 5-year
mission, 3 mm aluminum shielding, a 10 m^2 debris cross-section, and a
sensitive part with sigma_sat 1e-6 cm^2, LET threshold 10 MeV cm^2/mg,
Weibull width 15 and shape 1 against a power law LET spectrum
(k = 1e5, exponent 2.5, 0.1 to 100 MeV cm^2/mg):

- trapped_belt_dose_rate(600, 98) = 0.263 rad/day.
- spe_fluence(10, 5) = 5e8 protons/cm^2 above 10 MeV.
- tid_after_shielding(0.263, 5, 3) = 0.261 krad, verdict ADEQUATE
  against a 50 krad limit (unshielded it would be 0.481 krad, and
  behind 10 mm it drops to 0.134 krad).
- seu_rate = 4.8e-4 upsets per device per day, about 0.18 per device
  per year.
- debris_flux_per_m2_yr(600) = 2.50e-5 per m^2 per year;
  collision_probability(2.50e-5, 10, 5) = 1.25e-3, verdict LOW.

The design conclusion: the orbit is benign for dose at this shielding,
the part is borderline for single-event effects (one upset every
several years per device, so the system needs error correction or a
harder part), and the debris risk is low.

## Pitfalls

- Treating the proxies as qualification data: the simplified models
  reproduce environment shapes, not the AE-8/AP-8 or ORDEM/MASTER
  detail. A real program must run the actual environment models and
  the actual component test data before committing to a design.
- Forgetting the solar particle event contribution: a long mission or
  an event-rich period adds a proton fluence spike that dominates the
  dose behind thin shielding; the belt dose alone understates the
  requirement.
- Sizing shielding with a single attenuation length: the electron
  component stops in a few mm of aluminum while the proton component
  penetrates far deeper; a single exponential predicts a dose of zero
  behind modest shielding and misses the proton floor.
- Ignoring the LET threshold in SEU analysis: a device with a high
  threshold sees almost no upsets in a soft spectrum; folding the
  threshold into the Weibull fit is the difference between zero and
  a real rate.
- Using the debris flux at the wrong altitude: the flux at 550 km is
  about a third of the flux at 850 km; evaluating the collision
  probability at the wrong altitude misrates the risk by a factor of
  several.
- Adding collision probabilities instead of compounding: P = 1 -
  exp(-lambda) from the mission-life lambda; summing yearly
  probabilities is only valid while every yearly probability is tiny.
- Neglecting the cross-section of the deployed configuration: solar
  arrays and antennas multiply the debris cross-section; sizing the
  risk on the bus cross-section alone understates the probability.

## Behavior contract (gate 3)

The trapped belt dose, solar particle fluence, RPP single-event rate,
shielding attenuation, and debris collision math is exercised by the
gate 3 contract test: scripts/test_radiation_debris.py against
scripts/radiation_debris_logic.py (stdlib unittest, offline).
Run from the repo root:
python3 skills/space-systems/mission-design/radiation-debris/scripts/test_radiation_debris.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames the space environment
  assessment within the ECSS lifecycle, and the environment models
  above are common space engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
