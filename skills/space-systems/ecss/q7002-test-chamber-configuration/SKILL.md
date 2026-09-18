---
name: q7002-test-chamber-configuration
description: "Evaluate a thermal-vacuum outgassing chamber as it is built. Use when an apparatus set-up is signed off under ECSS-Q-ST-70-02C before specimens are loaded: pair every heated compartment with its own collector plate, turn the aperture diameter and the compartment-to-collector gap into the single flux fraction the method band is written against, report the temperature spread of each heated zone separately, hold each collector plate inside its controlled band, and require a base pressure comfortably below the pressure the run is held at. Trigger: ecss, q-st-70-02c, outgassing-chamber-configuration, outgassing-collector-aperture-capture-fraction, outgassing-heater-bar-zone-uniformity, outgassing-collector-compartment-pairing, outgassing-chamber-base-pressure-margin, outgassing-collector-plate-band."
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
  tags: [ecss, q-st-70-02-outgassing-scope, q7002-test-chamber-configuration, outgassing-collector-aperture-capture-fraction, outgassing-heater-bar-zone-uniformity, outgassing-collector-compartment-pairing, outgassing-chamber-base-pressure-margin, outgassing-collector-plate-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening -- Chamber Configuration (space-systems/ecss/q7002-test-chamber-configuration)

Use when the task is the apparatus step of a thermal-vacuum outgassing
screening under ECSS-Q-ST-70-02C: the chamber, the heated specimen bar and
the cooled collector plates have been set up, and the question is whether the
configuration is the one the method assumes before any specimen is loaded.

## Domain quick reference

- Each heated compartment effuses onto one collector plate and no other. A
  plate serving two compartments carries a deposit belonging to two materials
  at once, and a compartment with no plate produces a mass-loss number with no
  condensable number beside it.
- Aperture diameter and compartment-to-collector gap are not two independent
  tolerances. They combine into the fraction of the effused flux the plate can
  intercept, and that single fraction is the quantity the method band is
  written against; a wider aperture can compensate a longer gap exactly.
- The compartments share a heated bar, so the property that decides whether
  the bar is usable is the spread of compartment temperatures inside one zone,
  not the mean of the chamber. A two-zone bar is graded twice.
- The collector plates are held on their own control loop. A plate above its
  band condenses less of what reaches it, and reports a lower condensable
  figure for a material that did not change.
- Base pressure is a capability, not a reading. If the pump set only just
  reaches the run pressure, the run is held by the pump rather than by a
  controlled condition, and a small leak moves the test point.

## Workflow

1. Validate every compartment record -- identifier, collector, zone, aperture,
   gap, temperature -- and refuse a duplicate compartment identifier instead of
   quietly overwriting one.
2. Form the intercepted flux fraction for each compartment from its aperture
   radius and gap, and compare it with the method band rather than checking the
   two dimensions separately.
3. Group the compartments by collector and raise one finding per plate that
   serves more than one of them, naming the compartments involved.
4. Group the compartments by heated zone, take max minus min of the
   compartment temperatures, and raise a finding per zone that exceeds the
   allowed spread.
5. Grade each collector plate against its controlled band, and name any plate
   the compartments reference that the chamber does not have, or that no
   compartment uses.
6. Divide the run pressure by the base pressure, compare the ratio with the
   required margin, and report the configuration as usable only when nothing
   above was raised.

## Pitfalls

- Signing off aperture and gap against separate tolerances. Only the combined
  intercepted fraction is comparable between chambers, and two set-ups inside
  both dimensional tolerances can sit on opposite sides of the band.
- Reporting one chamber temperature. The bar is graded on the spread inside a
  zone, and a well-centred mean hides a cold compartment at the end of it.
- Pairing two compartments onto a spare plate to run an extra material. The
  deposit cannot be split afterwards, so the extra material costs both
  condensable readings rather than only its own.
- Treating an unused collector as harmless. A plate nobody references is
  usually a pairing that was meant to exist, and saying so at set-up is far
  cheaper than finding it at read-out.
- Taking a base pressure equal to the run pressure as sufficient. The margin is
  what keeps the run condition a control setting rather than a pump limit.

## Behavior contract (gate 3)

The compartment validation, intercepted-flux fraction, collector pairing,
heated-zone spread, collector plate band and base-pressure margin are
exercised by the gate 3 contract test:
scripts/test_q7002_test_chamber_configuration.py against
scripts/q7002_test_chamber_configuration_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7002_test_chamber_configuration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
