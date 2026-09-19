---
name: q7006-radiation-environment-definition
description: "Derive the radiation environment an irradiation campaign is specified against under ECSS-Q-ST-70-06C: validate a differential particle spectrum, integrate it over the energy window of interest by trapezoid with the window edges interpolated inside their bins, accumulate fluence across mission phases carrying their own duration, exposed duty and spectrum scaling, convert illuminated time into equivalent sun hours at the declared solar intensity, and compare the facility energy window with the one the mission occupies. Use when writing the environment table of a test specification or checking a quoted mission fluence. Trigger: ecss, q-st-70-06c, differential-particle-spectrum, integral-particle-flux, mission-phase-fluence-accumulation, equivalent-sun-hours-uv-dose, spectrum-energy-window-coverage."
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
  tags: [ecss, q-st-70-06c-particle-and-uv-radiation-testing, q-st-70-06c, q7006-radiation-environment-definition, differential-particle-spectrum, integral-particle-flux, mission-phase-fluence-accumulation, equivalent-sun-hours-uv-dose, spectrum-energy-window-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Environment Definition (space-systems/ecss/q7006-radiation-environment-definition)

Use when the task is the environment clause of ECSS-Q-ST-70-06C: turning a
predicted orbit into the four numbers an irradiation campaign is written
against — the particle spectrum, the integral flux, the accumulated fluence
and the ultraviolet dose.

## Domain quick reference

- A spectrum is not a fluence. The environment arrives as a differential
  spectrum, particles per unit energy, and every specified quantity is an
  integral of it over a stated energy window. Quoting a fluence without the
  window it was integrated over leaves the campaign unspecifiable.
- The window is chosen by the material, not by the model. A surface-degrading
  agent is driven by the soft end of the spectrum that a shield would have
  removed; a bulk-damage agent is driven by the penetrating tail. The same
  orbit therefore yields two very different fluences for two coupons on the
  same spacecraft.
- Integration has to honour partial bins. A window edge that falls inside a
  tabulated bin is interpolated there and the bin split, otherwise the flux of
  a whole bin is either counted or dropped and the answer moves by a factor
  that has nothing to do with the physics.
- Missions are not uniform. Transfer, commissioning, operations and a disposal
  phase each carry their own duration, their own exposed fraction and often a
  scaled spectrum; the mission fluence is the sum over phases, and a single
  averaged flux hides the phase that actually did the damage.
- Ultraviolet is accounted in equivalent sun hours, so that an orbit spending
  a third of each revolution in shadow is charged for the sunlit two thirds
  only, and a concentrated or multi-lamp exposure is expressed as a multiple
  of the reference solar ultraviolet irradiance rather than in watts.
- The facility bounds the specification. An energy window the source cannot
  produce is a finding raised while the environment is still being defined,
  not a discovery made once beam time has been bought.

## Workflow

1. Validate the differential spectrum: at least two points, strictly
   increasing energies, no negative differential flux and not identically
   zero. A repeated or descending energy is a table error.
2. Fix the energy window the material cares about, and integrate the spectrum
   across it by the trapezoidal rule, inserting interpolated nodes at both
   window edges so partial bins are carried correctly.
3. Accumulate the mission phase by phase: each phase contributes its integral
   flux, its spectrum scaling, its exposed duty fraction and its duration.
4. Convert each phase's illuminated fraction into equivalent sun hours at the
   declared solar intensity, and sum them into the mission ultraviolet dose.
5. Where a measured lamp irradiance is available instead, convert it to
   equivalent sun hours against the reference solar ultraviolet irradiance.
6. Compare the facility's energy window with the mission spectrum's window and
   raise a finding for each end that is not covered.
7. Return the environment definition with per-phase records and every finding,
   marking it complete only when there are none.

## Pitfalls

- Quoting a fluence without its energy window. The number cannot be reproduced
  and cannot be compared with a facility capability, so the campaign is
  specified against a figure nobody can reconstruct.
- Dropping a partial bin at a window edge. Integrating from the nearest
  tabulated energy instead of the requested one moves the answer by the whole
  content of that bin, which on a steep soft end is most of the total.
- Averaging the mission into one flux. A short high-flux phase and a long
  quiet one give the same average as a uniform mission, and the degradation
  rate effects that the phase structure exists to expose disappear.
- Charging shadow time as ultraviolet exposure. Elapsed mission time is not
  illuminated time; using it inflates the equivalent sun hours by the eclipse
  fraction and buys lamp hours that no orbit ever delivers.
- Reporting a lamp in watts per square metre. Facilities differ in spectral
  content, so only the equivalent-sun-hour figure against the reference
  ultraviolet irradiance is comparable between two campaigns.
- Deferring the facility window check. A soft end the source cannot reach is
  cheap to discover while the table is being written and expensive to discover
  after the specimens are mounted.

## Behavior contract (gate 3)

The spectrum validation, interpolation, windowed trapezoidal integration,
phase accumulation, equivalent-sun-hour conversion and facility coverage check
are exercised by the gate 3 contract test:
scripts/test_q7006_radiation_environment_definition.py against
scripts/q7006_radiation_environment_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7006_radiation_environment_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
