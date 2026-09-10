---
name: e1004-b5-geo-wc
description: "Use when implementing the NASA worst-case geosynchronous (GEO) electron environment spectrum per ECSS-E-ST-10-04C Annex B.5: select the applicable energy band of the two-population exponential spectral fit (a lower-energy population associated with spacecraft surface charging and a higher-energy, penetrating population associated with deep-dielectric/internal charging), compute the differential and integral electron flux at a given energy, derive the worst-case fluence for a stated exposure duration, and assess a case's worst-case fluence against its qualified fluence limit. Trigger: NASA worst-case GEO electron spectrum, geosynchronous electron environment, internal charging, deep dielectric charging, Annex B.5, e-st-10-04, ecss, space environment, electron fluence."
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
  tags: [ecss, e-st-10-04c, annex-b5, geo, electron-spectrum, internal-charging, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS NASA Worst-Case GEO Electron Spectrum (space-systems/ecss/e1004-b5-geo-wc)

Use when the task is implementing the NASA worst-case geosynchronous
(GEO) electron environment spectrum under ECSS-E-ST-10-04C Annex B.5,
to compute worst-case electron flux and fluence at GEO for internal
(deep-dielectric) and surface charging assessments.

## Domain quick reference

- The NASA worst-case GEO electron environment is a conservative
  design spectrum derived from historical geosynchronous satellite
  electron measurements. It is used to bound the electron population
  a GEO spacecraft can encounter, rather than to represent a typical
  or average condition.
- The spectrum is commonly represented as two exponential-fit electron
  populations across contiguous energy bands: a lower-energy
  population, which drives spacecraft surface charging, and a
  higher-energy, more penetrating population, which drives
  deep-dielectric (internal) charging of shielded internal components.
- Each band's differential flux falls off exponentially with energy,
  characterized by a coefficient and a characteristic (e-folding)
  energy specific to that band; the two bands meet at a shared
  boundary energy.
- The model is a worst-case, not a time-varying, spectrum: it is
  conventionally applied as a sustained flux over a stated worst-case
  exposure duration (e.g. a worst-case day) to derive a worst-case
  fluence, without duty-cycle reduction.
- This leaf implements the spectral form itself (band selection,
  differential/integral flux, worst-case fluence) and a fluence-vs-limit
  assessment. Rolling this environment into the trapped-electron
  internal-charging screening (clause 9.2.1.3, alongside the sibling
  FLUMIC-based Annex B.4 model) is the sibling e1004-internal-charging
  leaf; producing the overall radiation environment specification is
  the sibling e1004-rad-env-spec leaf.

## Workflow

1. For a given energy, select the model's energy band (surface or
   internal) that contains it; reject energies outside the model's
   overall valid energy range rather than extrapolating.
2. Compute the differential electron flux at that energy from the
   band's exponential fit (coefficient and characteristic energy).
3. Compute the integral flux above a threshold energy by summing the
   analytic band integral for the threshold's own band (from the
   threshold up to that band's upper edge) with the full analytic
   integral of every band above it.
4. Derive the worst-case fluence above a threshold energy for a stated
   exposure duration by multiplying the integral flux by the duration,
   applying the flux as sustained for the full duration (no duty-cycle
   reduction, consistent with the model's worst-case intent).
5. For each assessment case, record the case's penetration threshold
   energy (the minimum electron energy able to reach the
   shielded/vulnerable location), its exposure duration, and its
   qualified fluence limit (the fluence level the location's shielding
   or material has been qualified to withstand).
6. Compute the case's worst-case fluence at its threshold energy and
   duration, and mark it compliant only when that fluence does not
   exceed the qualified fluence limit.
7. Roll every case into an assessment record and do not close the
   internal-charging screening while any case remains non-compliant.

## Pitfalls

- Extrapolating the exponential fit beyond the model's valid energy
  range instead of rejecting the out-of-range energy, which silently
  overstates or understates flux outside the fitted bands.
- Applying only the internal (higher-energy) band's flux when
  evaluating a low penetration-threshold energy that falls in the
  surface band, undercounting the flux contribution from bands above
  the threshold's own band.
- Treating the worst-case spectrum as a time-averaged or typical
  environment and applying a duty-cycle reduction to the exposure
  duration, which defeats the model's conservative, worst-case intent.
- Comparing worst-case fluence against a qualified fluence limit
  without matching the exposure duration the limit was qualified for,
  producing a compliance call that does not reflect the actual
  mission exposure.

## Behavior contract (gate 3)

The band-selection, differential/integral flux, worst-case fluence,
and compliance logic is exercised by the gate 3 contract test:
scripts/test_e1004_b5_geo_wc.py against
scripts/e1004_b5_geo_wc_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_b5_geo_wc.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
