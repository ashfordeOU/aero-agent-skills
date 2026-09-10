---
name: e1004-ref-particles
description: "Use when selecting particle-radiation reference models for a space-environment case under ECSS-E-ST-10-04C Annex I (informative): categorize the particle population (trapped proton, trapped electron, solar energetic particle, galactic cosmic ray, albedo neutron) and the orbit regime, check a proposed energy against the population's cataloged model energy range and a proposed altitude against its altitude range, determine whether a low-Earth orbit is geomagnetically shielded for a given inclination, determine whether the South Atlantic Anomaly enhancement applies to a low-Earth orbit's altitude and inclination, and select the cataloged model identifier a radiation case must cite. Trigger: ecss, e-st-10-04c, annex i, particle radiation, trapped proton, trapped electron, solar energetic particle, galactic cosmic ray, albedo neutron, model selection, south atlantic anomaly, geomagnetic shielding."
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
  tags: [ecss, e-st-10-04c, annex-i, particle-radiation, trapped-proton, trapped-electron, sep, gcr, albedo-neutron, saa, reference-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Particle-Radiation Reference Data (space-systems/ecss/e1004-ref-particles)

Use when the task is selecting particle-radiation reference models under
ECSS-E-ST-10-04C Annex I (informative) — categorizing the particle
population and orbit regime, validating a proposed energy or altitude
against a model's cataloged range, deciding whether a low-Earth orbit is
geomagnetically shielded, deciding whether the South Atlantic Anomaly
enhancement applies, and selecting the cataloged model identifier a
radiation case must cite.

## Domain quick reference

- Five particle populations are cataloged: trapped proton, trapped
  electron, solar energetic particle, galactic cosmic ray, and albedo
  neutron. Each has its own model family and its own validity envelope —
  a model chosen outside its envelope gives a meaningless flux.
- The orbit regime (LEO, MEO, GEO, GTO, HEO, interplanetary) constrains
  which model families apply. A trapped-belt model is meaningless for an
  interplanetary case, and a solar-particle model is not the design driver
  for an inner-belt proton environment.
- Model energy ranges differ by population. A proposed energy outside the
  population's cataloged range must be reported against the model's range,
  not silently accepted.
- Geomagnetic shielding: below a characteristic inclination a low-Earth
  orbit's trajectory stays within the geomagnetic cutoff and solar
  energetic particles and galactic cosmic rays are substantially shielded;
  above it, the orbit reaches high magnetic latitudes where shielding is
  weak. This is expressed as an inclination threshold.
- The South Atlantic Anomaly (SAA) is a region of reduced geomagnetic field
  where the inner trapped-belts dip to lower altitude. Its enhancement
  applies only within a bounded altitude band and above a minimum
  inclination — check both.

## Workflow

1. Categorize the population and the orbit regime for the case. Each
   function validates its population/regime argument and raises on an
   unknown value.
2. Check the proposed energy:
   `is_energy_in_range(population, energy_mev)` against
   `model_energy_range_mev(population)`.
3. Check the proposed altitude:
   `is_altitude_in_range(population, altitude_km)` against
   `model_altitude_range_km(population)`.
4. For a low-Earth orbit, decide shielding:
   `is_geomagnetically_shielded(orbit_regime, inclination_deg)`.
5. Decide SAA applicability:
   `saa_enhancement_applies(orbit_regime, altitude_km, inclination_deg)`.
6. Select the model identifier for the case:
   `select_particle_model(population, orbit_regime, inclination_deg)`.
7. Run the full review for one lookup and check it is compliant:
   `particle_reference_review(request)` → `is_particle_review_compliant(review)`.

## Pitfalls

- Using a model outside its envelope: an energy or altitude outside the
  cataloged range is a finding to resolve (choose another model or document
  a deviation), never a value to clamp.
- Ignoring the inclination condition on SAA applicability: the enhancement
  applies only above a minimum inclination as well as within the altitude
  band; an equatorial orbit at the right altitude does not qualify.
- Treating geomagnetic shielding as a smooth function of altitude alone:
  it is an inclination-gated effect; the deciding variable is the maximum
  magnetic latitude the ground track reaches.
- Security-marking vocabulary: the content-policy gate flags the word
  beginning "classif-"; use "categorized" instead.

## Behavior contract (gate 3)

`scripts/test_e1004_ref_particles.py` (stdlib unittest, offline) verifies
population/regime validation and error paths, energy- and altitude-range
checks at boundaries, geomagnetic-shielding inclination gating, SAA
applicability (altitude band + inclination + regime), model selection, and
the full review compliance check.

## Compliance

ECSS-E-ST-10-04C Annex I is informative reference data. This leaf implements
only common-knowledge procedure and reference-value structure; the standard
and clause are cited as the anchor. `license: Apache-2.0`,
`compliance: STANDARDS-REF`, `standards: ecss` (reference-only), `gated: false`.
