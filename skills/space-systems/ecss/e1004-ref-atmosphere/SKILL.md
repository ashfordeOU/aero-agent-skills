---
name: e1004-ref-atmosphere
description: "Use when determining which reference atmosphere model and
  inputs apply to a mission atmosphere lookup under ECSS-E-ST-10-04C Annex G:
  map the target body and altitude to the cataloged reference models
  (NRLMSISE-00, JB-2006, and GRAM-class planetary models), select the model
  that matches the analysis purpose (drag prediction, density reference, or
  full-profile engineering) while validating the altitude against that
  model's supported range, and verify every input the selected model needs
  (solar/geomagnetic activity or trajectory fields) is present before the
  model is run; also classifies an Earth altitude into its atmospheric
  regime for scoping. Trigger: ecss, e-st-10-04c, annex g, atmosphere model,
  nrlmsise-00, jb-2006, gram, planetary atmosphere, reference atmosphere,
  drag prediction."
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
  tags: [ecss, e-st-10-04c, atmosphere, nrlmsise-00, jb-2006, gram, reference-atmosphere]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Reference Atmosphere Data (space-systems/ecss/e1004-ref-atmosphere)

Use when the task is an ECSS-E-ST-10-04C Annex G (informative) reference
atmosphere lookup -- deciding which published atmosphere model covers a
given celestial body, altitude, and analysis purpose, and confirming the
model's activity/trajectory inputs are on hand before it is run.

## Domain quick reference

- Annex G points the engineer at external reference atmosphere models
  rather than defining one: NRLMSISE-00 and JB-2006 are Earth
  thermosphere/exosphere density models used for orbital drag and
  lifetime analysis, each covering an altitude band and each needing
  current solar-activity and geomagnetic-activity inputs to run.
  JB-2006 is the higher-fidelity drag-focused option above its
  altitude floor; NRLMSISE-00 covers a broader density-reference role
  and a lower floor. GRAM-class models (Earth-GRAM, Mars-GRAM,
  Venus-GRAM) give a full surface-to-orbit engineering profile for one
  body, including trajectory-driven inputs (date, latitude,
  longitude, altitude).
- A model only applies within its cataloged altitude range for its
  body; a request outside every cataloged model's range for that body
  has no coverage and must be flagged rather than silently answered
  with the nearest model.
- Model selection follows the analysis purpose: drag prediction on
  Earth prefers JB-2006 where its floor allows, falling back to
  NRLMSISE-00 and then Earth-GRAM; a general density reference prefers
  NRLMSISE-00, falling back to Earth-GRAM; a full-profile need (or any
  non-Earth body, since JB-2006/NRLMSISE-00 are Earth-only) uses the
  GRAM-class model for that body.
- A selected model is not actually runnable until every input it
  requires (solar flux, geomagnetic index, epoch, or trajectory
  position) is on record; a missing input is a finding against the
  lookup, separate from the model-selection step itself.
- Earth altitude additionally classifies into an atmospheric regime
  (troposphere, stratosphere, mesosphere, thermosphere, exosphere),
  useful for scoping which phenomena (e.g. drag-relevant density vs.
  launch-ascent aerodynamics) are in play at a given altitude.

## Workflow

1. Identify the target body and confirm it is one the catalog covers;
   reject an unrecognized body before selecting a model for it.
2. State the analysis purpose (drag prediction, density reference, or
   full-profile engineering) and the altitude of interest; reject a
   negative altitude or an unrecognized purpose.
3. Select the model using the purpose-driven preference order for the
   body, checking each candidate's altitude range in turn; if no
   cataloged model for that body covers the altitude, flag a coverage
   gap rather than forcing the nearest model.
4. Once a model is selected, compare the inputs on hand against that
   model's required-input set; flag each missing input by name.
5. For Earth-altitude scoping, classify the altitude into its
   atmospheric regime alongside the model selection.
6. Aggregate the coverage and input findings for the lookup; the
   lookup is not ready to hand to the model until both are empty.

## Pitfalls

- Picking the nearest cataloged model when the requested altitude is
  actually outside every model's range for that body -- that is a
  coverage gap to report, not an approximation to make silently.
- Treating JB-2006 as available below its altitude floor just because
  NRLMSISE-00 would be -- each model's range is independent and the
  fallback order exists precisely because JB-2006 cannot cover that
  band.
- Using an Earth-only model (NRLMSISE-00, JB-2006) for a non-Earth
  body -- only the body's GRAM-class model applies there regardless of
  purpose.
- Reading "a model was selected" as "the lookup is ready" -- a
  selected model with missing required inputs (solar flux,
  geomagnetic index, trajectory epoch/position) cannot actually be
  run and must still be flagged.

## Behavior contract (gate 3)

The model-range lookup, altitude-in-range check, body-to-model
mapping, purpose-driven selection, required-input gap check, and
altitude-regime classification are exercised by the gate 3 contract
test: scripts/test_e1004_ref_atmosphere.py against
scripts/e1004_ref_atmosphere_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_ref_atmosphere.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
