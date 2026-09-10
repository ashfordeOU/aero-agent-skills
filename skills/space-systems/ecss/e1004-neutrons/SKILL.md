---
name: e1004-neutrons
description: "Use when you must define the atmospheric albedo neutron environment for a LEO mission and include it in the radiation environment specification (RES) per ECSS-E-ST-10-04C: decide whether the environment applies to the orbit regime, classify the neutron energy spectrum into bands, assess the geomagnetic-latitude exposure that drives the flux, and verify the RES entry carries every required field before the RES is closed out. Trigger: ecss atmospheric albedo neutrons, albedo neutron environment, leo neutron flux, radiation environment specification neutrons, e-st-10-04c 9.2.5."
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
  tags: [ecss, e-st-10-04c, radiation, albedo-neutrons, leo, radiation-environment-spec]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Atmospheric Albedo Neutrons (space-systems/ecss/e1004-neutrons)

Use when the task is ECSS-E-ST-10-04C clause 9.2.5: deciding whether
the atmospheric albedo neutron environment belongs in a mission's
radiation environment specification (RES), and building a complete RES
entry for it when it does.

## Domain quick reference

- Atmospheric albedo neutrons are secondary neutrons produced when
  galactic cosmic rays (and, to a lesser degree, solar energetic
  particles) collide with the upper atmosphere; a fraction of the
  resulting neutron field streams back upward into near-Earth orbits.
- The environment is only significant close to the Earth: it is
  specified for LEO missions and is not carried into MEO, GEO, GTO,
  HEO, L2, or interplanetary radiation specifications.
- Flux depends on altitude within the LEO band and on geomagnetic
  latitude: orbits reaching higher geomagnetic latitudes see a weaker
  cutoff-rigidity shield against the primary cosmic rays that generate
  the neutrons, so exposure rises with inclination.
- The neutron spectrum spans thermal, epithermal, fast, and
  high-energy (evaporation/spallation) bands; the higher-energy bands
  matter most for single-event effects in electronics.
- A RES entry for this environment is incomplete without: an
  orbit-applicability call, the energy bands present, the geomagnetic
  exposure class, and a note tying the two together.

## Workflow

1. Determine orbit applicability with albedo_neutrons_applicable
   (regime plus altitude for LEO); anything outside LEO is excluded
   from the RES for this environment.
2. Classify each energy of interest into its spectral band with
   neutron_energy_band (thermal, epithermal, fast, high-energy).
3. Classify the mission's geomagnetic exposure from inclination with
   geomagnetic_exposure_class (equatorial-shielded, mid-latitude,
   polar-unshielded).
4. Assemble the RES entry with build_res_entry, combining steps 1-3
   into one record.
5. Verify the entry before closing the RES with res_entry_is_complete;
   resolve any missing field it reports.

## Pitfalls

- Carrying the albedo neutron environment into a MEO/GEO/HEO/L2 RES
  entry — it is a LEO-only secondary environment in this clause.
- Treating the neutron flux as latitude-independent; a polar or
  high-inclination LEO orbit sees materially more flux than an
  equatorial one at the same altitude.
- Reporting only a single energy value instead of the spectral bands
  relevant to the mission's SEE and dose assessments.
- Closing the RES with an entry that states "included" but omits the
  energy bands or geomagnetic exposure class needed to use it.

## Behavior contract (gate 3)

The applicability, energy-band, geomagnetic-exposure, and RES-entry
logic is exercised by the gate 3 contract test:
scripts/test_e1004_neutrons.py against scripts/e1004_neutrons_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1004_neutrons.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
