---
name: e1004-atmosphere
description: "Use when defining the neutral atmosphere environment for a mission under ECSS-E-ST-10-04C: select the applicable neutral-atmosphere density model (NRLMSISE-00 for general-purpose drag and lifetime work, JB-2006 for precision analyses) based on the case's precision need, verify the analysis altitude falls within the model's valid range, classify the solar activity level from the F10.7 solar flux index, apply solar/geomagnetic scaling to the reference density, select a wind model (HWM-type) when the case needs thermospheric wind data, and flag any non-Earth target body as needing a planet-specific atmosphere model instead of an Earth model. Trigger: neutral atmosphere, NRLMSISE-00, JB-2006, HWM, thermosphere, atmospheric density, drag, orbital lifetime, F10.7, solar flux index, geomagnetic index, wind model, e-st-10-04, ecss, space environment, planetary atmosphere."
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
  tags: [ecss, e-st-10-04c, atmosphere, neutral-atmosphere, nrlmsise, jb2006, thermosphere, drag, density, wind-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Neutral Atmosphere Environment (space-systems/ecss/e1004-atmosphere)

Use when the task is selecting and applying a neutral atmosphere model
under ECSS-E-ST-10-04C clause 7.2, to characterize atmospheric density
(and, when needed, thermospheric winds) for drag, orbital-lifetime, or
attitude-disturbance-torque analyses.

## Domain quick reference

- The neutral atmosphere is the non-ionized upper-atmosphere gas
  (mainly the thermosphere/exosphere region for orbital altitudes)
  whose density drives aerodynamic drag on a spacecraft, which in turn
  drives orbital decay rate, propellant budget for drag makeup, and
  low-altitude attitude disturbance torques.
- Density falls off rapidly with altitude but is not a fixed function
  of altitude alone: it is strongly modulated by solar activity (the
  thermosphere heats and expands when solar EUV/UV input rises,
  raising density at a given altitude by roughly an order of magnitude
  between solar minimum and solar maximum) and, on shorter timescales,
  by geomagnetic activity (storms transiently heat and raise density
  independent of the solar-flux level).
- The F10.7 index (10.7 cm solar radio flux, in solar flux units) is
  the standard proxy for the solar-activity driver; the Ap/Kp indices
  are the standard proxy for the geomagnetic driver. A density model
  run needs both to be meaningful, not F10.7 alone.
- NRLMSISE-00-class models are the general-purpose, whole-atmosphere
  empirical reference for Earth neutral density and are the default
  choice for drag-budget and lifetime work. JB-2006-class
  (Jacchia-Bowman) models are an alternative tuned to more recent
  solar/geomagnetic drivers and are preferred for precision analyses
  (e.g. precision orbit determination) where the extra fidelity
  matters.
- HWM-type horizontal wind models supply the thermospheric wind
  velocity field. Wind is a secondary correction on top of density:
  needed for precision drag/attitude-torque work, not for a basic
  drag-budget estimate that only needs density.
- These Earth-atmosphere models are valid over a bounded altitude
  range (roughly 90-1000 km, the thermosphere/exosphere region for
  common orbital altitudes); do not extrapolate a model outside its
  valid range, and do not apply an Earth atmosphere model to a
  non-Earth target body -- a planetary mission needs a planet-specific
  reference atmosphere instead.
- This leaf scopes Earth neutral-atmosphere model selection, altitude
  applicability, solar/geomagnetic density scaling, and wind-model
  selection only. Charged-particle (plasma/ionosphere) environments are
  the sibling e1004-plasma leaf; reference data tables for atmosphere
  models (incl. planetary atmosphere notes) are the sibling
  e1004-ref-atmosphere leaf.

## Workflow

1. For each drag, lifetime, or attitude-disturbance-torque analysis
   case, record its target body, altitude (km), the precision need
   ("standard" or "precision"), the assumed F10.7 solar flux index and
   Ap geomagnetic index, whether the case needs thermospheric wind
   data, and a reference density to be scaled.
2. Determine whether the target body is Earth. For a non-Earth target
   body, flag the case as needing a planet-specific atmosphere model
   and do not select an Earth density model for it.
3. For an Earth target body, verify the case's altitude falls within
   the neutral-atmosphere model's valid altitude range; flag an
   out-of-range altitude rather than extrapolating the model.
4. Select the applicable Earth neutral-atmosphere density model from
   the case's precision need (NRLMSISE-00-class for "standard",
   JB-2006-class for "precision").
5. Classify the case's solar activity level from its F10.7 value (low,
   moderate, or high) so the density estimate can be checked against
   the intended worst case for the analysis purpose.
6. Apply solar/geomagnetic scaling to the case's reference density
   using its F10.7 and Ap values to obtain the density applicable to
   the case's assumed conditions.
7. If the case needs thermospheric wind data, select a wind model
   (HWM-type) in addition to the density model; otherwise no wind
   model is required.
8. Mark a case compliant only when its target body is Earth and its
   altitude is in range; roll every case's compliance into the
   assessment record and do not close the atmosphere characterization
   while any case remains non-compliant.

## Pitfalls

- Applying the same solar-activity assumption to both a drag/fuel
  budget analysis and a post-mission decay/disposal-compliance
  analysis, when the two need opposite worst cases: high solar
  activity (high density, high drag) is conservative for drag force
  and propellant budgeting, while low solar activity (low density, low
  drag, slower decay) is conservative for verifying that decay happens
  within the required disposal time.
- Selecting an Earth neutral-atmosphere model (NRLMSISE-00/JB-2006) for
  a non-Earth target body instead of flagging the need for a
  planet-specific reference atmosphere.
- Extrapolating a neutral-atmosphere density model outside its valid
  altitude range instead of flagging the case as out of range.
- Omitting the wind model for precision drag or attitude-disturbance-
  torque work that needs thermospheric winds, understating disturbance
  effects that a density-only treatment misses.
- Treating F10.7 as the only density driver and ignoring geomagnetic
  activity, which can transiently raise density during a storm
  independent of the solar-flux level.

## Behavior contract (gate 3)

The model-selection, altitude-applicability, solar-activity
classification, density-scaling, and compliance logic is exercised by
the gate 3 contract test: scripts/test_e1004_atmosphere.py against
scripts/e1004_atmosphere_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_atmosphere.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
