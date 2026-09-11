---
name: e1012-sensor-bg-margin
description: "Use when assess radiation-induced sensor background margins for space detector systems under ECSS-E-ST-10C §5.5.4: identify each contributing particle population (trapped protons, trapped electrons, galactic cosmic rays, solar energetic particles), compute the raw background count rate at the sensor sensitive area from each population flux and conversion efficiency, sum all contributions over the exposure duration, apply the required radiation design margin to account for environment model uncertainty, compare the margin-loaded background count against the sensor allocated background budget, and flag any exceedance or missing budget record. Trigger: ecss, e-st-10-system-scope, radiation-background, sensor-background, radiation-margin, particle-flux, background-budget, radiation-design-factor."
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
  tags: [ecss, e-st-10-system-scope, radiation-background, sensor-background, radiation-margin, particle-flux, background-budget, radiation-design-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Radiation-Induced Sensor Background Margins (space-systems/ecss/e1012-sensor-bg-margin)

Use when the task is to assess radiation-induced background margins for
space detector systems under ECSS-E-ST-10C §5.5.4 — enumerating the
particle populations that contribute spurious counts, computing a raw
background sum, applying the radiation design margin, and checking
compliance against the sensor background budget.

## Domain quick reference

- Space radiation environments expose detectors to several distinct
  particle populations: trapped protons and electrons in the Van Allen
  belts, galactic cosmic rays (GCR) present at all orbits, and solar
  energetic particles (SEP) that arrive during energetic solar events.
  Each population deposits energy in a detector's sensitive volume and
  produces spurious counts distinct from the intended signal.
- The background count rate from a population is the product of its
  particle flux (particles/cm²/s), the sensor's geometrical sensitive
  area (cm²), and a background conversion factor (counts per incident
  particle) that captures the detector's response to that species.
  Summed over all populations and multiplied by the exposure duration,
  this gives the raw background count for the observation.
- A radiation design margin (RDM) is applied to the raw background
  before comparing it against the sensor budget. The margin factor
  (≥ 1.0) accounts for uncertainties in the environment model, the
  transport calculation, and the detector response characterisation.
  Applying a factor below 1.0 is not a valid margin — it reduces, not
  expands, the design allowance. Per §5.5.4, the margin is applied
  multiplicatively to the total raw background.
- Each sensor carries an allocated background budget expressed in counts
  (or counts per integration interval). A missing budget is itself a
  finding — "no budget recorded" must not be read as compliant. An
  exceedance (margin-loaded background exceeds budget) requires either
  design action (shielding, shorter integration, orbit change) or
  explicit waiver with documented justification.

## Workflow

1. List every particle population relevant to the mission orbit (trapped
   proton, trapped electron, GCR, SEP, or other recognised species).
   Reject an unknown particle type before it enters the calculation.
2. For each population, record the incident flux at the detector location
   (accounting for any shielding already modelled), the sensor sensitive
   area, and the detector-specific background conversion factor. Validate
   that flux and area are non-negative and conversion is non-negative.
3. Compute the raw background counts for each population:
   counts = flux × sensitive_area × bg_conversion × integration_time.
4. Sum the per-population raw background counts to obtain the total raw
   background for the integration period.
5. Apply the radiation design margin: margin-loaded background =
   total raw background × margin_factor (margin_factor ≥ 1.0).
6. Compare the margin-loaded background against the sensor's allocated
   budget. Record the exceedance (margin-loaded minus budget, floored at
   zero) and set compliance to false when exceedance is positive.
7. Aggregate findings: an empty population list with zero background is
   compliant only when a budget is on record; a missing budget is a
   separate finding outside this module's scope but must be flagged at
   system level.

## Pitfalls

- Applying the margin factor to individual population contributions
  before summing rather than to the total — the margin is on the
  aggregate, not per species, and doing it per species inflates the
  total when the same margin is applied again at the system level.
- Treating a zero-flux population as removing the species from scope
  for future mission phases — zero flux may be correct for the current
  orbit but incorrect for a transfer orbit with higher trapped-particle
  exposure.
- Using a margin factor below 1.0 on the grounds that the environment
  model is conservative — §5.5.4 does not allow a sub-unity margin.
  If the model is known to overestimate, the appropriate action is to
  use a corrected environment input, not a downward margin.
- Reading "no populations listed" as compliant — a detector may simply
  be missing its environment inputs, which is a modelling gap, not a
  clean pass.
- Conflating the background margin check with the total-dose or SEE
  margin checks — §5.5.4 is specifically about spurious background
  counts in detector readout, not cumulative damage or single-event
  upsets, which are governed by separate clauses and separate margins.

## Behavior contract (gate 3)

The population validation, background computation, margin application,
and budget comparison logic is exercised by the gate 3 contract test:
scripts/test_e1012_sensor_bg_margin.py against
scripts/e1012_sensor_bg_margin_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_sensor_bg_margin.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
