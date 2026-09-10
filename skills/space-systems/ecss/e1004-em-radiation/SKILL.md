---
name: e1004-em-radiation
description: "Use when you must define a mission's natural electromagnetic radiation environment per ECSS-E-ST-10-04C clause 6.2: assemble the solar spectrum bands (XUV through IR and solar radio), scale total solar irradiance (TSI) to the mission's heliocentric distance, and combine planetary albedo and infrared emission into the incident EM flux a spacecraft must design against. Trigger: electromagnetic radiation environment, solar spectrum, TSI, total solar irradiance, solar radio, planetary albedo, planetary IR, earth albedo, e-st-10-04c 6.2."
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
  tags: [ecss, e-st-10-04c, em-radiation, solar-spectrum, tsi, solar-radio, planetary-albedo, planetary-ir, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Natural EM Radiation Environment (space-systems/ecss/e1004-em-radiation)

Use when the task is ECSS-E-ST-10-04C clause 6.2: defining the natural
electromagnetic radiation environment a mission must design against —
the solar spectrum across its bands (XUV, EUV, UV, visible, IR, solar
radio), total solar irradiance (TSI) at the mission's distance from the
Sun, and the planetary contribution (reflected albedo flux plus
planetary infrared emission) at the body the mission orbits.

## Domain quick reference

- The solar EM spectrum is conventionally split into bands by
  wavelength (XUV, EUV, UV, visible, IR) plus solar radio emission.
  Each band has a reference irradiance drawn from the standard's
  reference index tables (sibling leaves e1004-indices and
  e1004-ref-indices hold those source values); this leaf treats the
  per-band reference irradiance as caller-supplied data and focuses on
  validating that the assembled spectrum is well-formed: bands ordered
  by wavelength with no gaps skipped out of order and no two bands
  overlapping the same wavelength range.
- TSI (total solar irradiance) is defined at a reference distance of 1
  AU (the ECSS reference value is ~1361 W/m^2, varying modestly with
  the solar cycle). For any other heliocentric distance, irradiance
  follows the inverse-square law: flux falls off as
  1/distance_au^2. A mission at Mercury's distance sees several times
  the 1-AU TSI; a mission near Jupiter sees a small fraction of it. A
  computed TSI that does not shrink monotonically as distance
  increases (all else fixed) indicates a scaling error, not a valid
  result.
- The planetary contribution to the EM environment has two parts:
  reflected sunlight (incident TSI at the body's distance, times the
  body's albedo coefficient, a fraction in [0, 1]) and the body's own
  infrared emission (thermal re-radiation, an independent input from
  the mission's planetary environment data). Both add to the
  spacecraft's incident EM flux and both are orbit-geometry-dependent
  in practice (eclipse, beta angle) — this leaf computes the
  flat-plate reference magnitudes the environment specification
  states, not the time-varying view-factor geometry (that belongs to
  the thermal/attitude analyses that consume this specification).
- This leaf covers the natural EM radiation environment definition
  only (clause 6.2). Solar and geomagnetic activity index values that
  feed band irradiance and TSI variability (F10.7, Ap/Kp, etc.) are
  covered by sibling leaf e1004-indices (clause 6.2.2 + Annex A); do
  not re-derive index tables here.

## Workflow

1. Collect the mission's solar spectrum band data (name, wavelength
   range, reference irradiance per band) from the project's reference
   index source (sibling e1004-indices / e1004-ref-indices). Validate
   the set with check_spectrum_band_order, which reports any band
   whose wavelength range is out of ascending order or overlaps its
   neighbor instead of silently accepting a malformed spectrum.
2. Fix the mission's heliocentric distance in AU (from the mission
   orbit definition) and compute TSI at that distance with
   compute_tsi_at_distance, starting from the 1-AU reference TSI.
3. Before accepting a single TSI value, spot-check the inverse-square
   scaling across the mission's distance range (e.g. perigee/apogee of
   an interplanetary transfer, or simply a sensitivity sweep) with
   check_tsi_distance_monotonicity — TSI must not increase as distance
   increases.
4. Fix the target body's albedo coefficient and reference infrared
   emission from the mission's planetary environment data, and combine
   them with the TSI at that body's distance using
   compute_planetary_total_flux to get the reflected and IR
   contributions to the incident EM flux.
5. Assemble steps 1-4 with em_radiation_environment_specification to
   produce the EM radiation environment entry for the mission
   specification; do not hand a spectrum forward unless its verified
   flag is True (no band ordering or overlap violations).

## Pitfalls

- Treating the 1-AU reference TSI as valid at every mission distance
  instead of rescaling it with the inverse-square law.
- Accepting a solar spectrum where two bands overlap the same
  wavelength range (for example UV and visible both claiming 380 nm) —
  a sign of a transcription error in the reference table, not a real
  environment.
- Hardcoding the reference index values (band irradiances, F10.7-class
  indices) into this workflow leaf instead of sourcing them from the
  dedicated reference-index leaves (e1004-indices, e1004-ref-indices).
- Forgetting the planetary contribution (albedo + IR) and specifying
  only the direct solar flux — both add to the spacecraft's incident
  EM environment and both must be in the specification.
- Using a negative or out-of-[0, 1] albedo coefficient carried over
  from an unvalidated planetary data source.

## Behavior contract (gate 3)

The band-validation, TSI-scaling, and planetary-flux logic is
exercised by the gate 3 contract test:
scripts/test_e1004_em_radiation.py against
scripts/e1004_em_radiation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_em_radiation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
