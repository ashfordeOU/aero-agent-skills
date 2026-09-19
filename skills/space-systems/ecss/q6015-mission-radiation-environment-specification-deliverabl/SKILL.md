---
name: q6015-mission-radiation-environment-specification-deliverabl
description: "Audit the mission radiation environment specification for the content Annex A requires. Use when ECSS-Q-ST-60-15C Annex A has to be applied to that deliverable: check the orbit definition, each trapped, solar particle and cosmic ray population, and the derived dose-depth, displacement fluence and linear energy transfer products are all present, that every modelled environment names its model, its version and the standard it was drawn from, that a statistical fluence declares its confidence level while an activity-conditioned model declares solar minimum or maximum instead, and that the tabulated shielding span reaches the thinnest equipment shielding. Trigger: ecss, q-st-60-15c-annex-a, radiation-environment-specification-content, environment-model-version-attribution, statistical-fluence-confidence-level, solar-activity-condition-declaration, dose-depth-shielding-span-coverage."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-mission-radiation-environment-specification-deliverabl, q-st-60-15c-annex-a, radiation-environment-specification-content, environment-model-version-attribution, statistical-fluence-confidence-level, solar-activity-condition-declaration, dose-depth-shielding-span-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Environment Specification Deliverable (space-systems/ecss/q6015-mission-radiation-environment-specification-deliverabl)

Use when the task is the environment specification of ECSS-Q-ST-60-15C
Annex A — deciding whether the document every later radiation analysis
reads from actually contains what those analyses will need, and
whether each environment in it is attributed well enough to be
reproduced.

## Domain quick reference

- This deliverable is upstream of everything else in the radiation
  programme. A dose analysis, a displacement analysis and a single
  event rate all read their inputs from here, so an item missing from
  this document is not a documentation defect, it is an analysis that
  cannot be started.
- Its content divides into three. The mission and orbit definition
  says where the spacecraft goes; the particle environments say what
  it meets there; and the derived products — ionising dose against
  shielding, displacement damage fluence, linear energy transfer
  spectra — are the forms the analyses actually consume. The derived
  products are the ones most often left out, because they look like
  results rather than specification.
- An environment without an attributed model is unusable later. The
  model identifier says which population model was run, and the model
  version says which revision, because a model is revised and an
  analysis has to be reproducible against the revision actually used.
  The cited standard says where the model was taken from.
- The kind of model decides what else it owes. A solar particle event
  fluence is statistical: it exists only at a confidence level, and a
  fluence quoted without one is a number of unknown severity. Trapped
  and cosmic ray models are evaluated for a solar activity condition
  instead, and a confidence level pinned to one of those is a category
  error that makes the document look more rigorous than it is.
- A confidence level low enough to be typical rather than worst case
  adds little to a design case; the deliverable is expected to quote
  a high one, and a low one is reported rather than silently accepted.
- A derived product is read at a thickness. A dose-depth curve whose
  thinnest tabulated shielding is thicker than the thinnest shielding
  in the equipment cannot be read at the parts that need it most, so
  the span is cross-checked against the design rather than taken on
  its own.

## Workflow

1. Validate each content entry: a known item, a confidence level
   strictly inside nought to a hundred when one is given, a known
   solar activity condition when one is given, and an ascending
   positive shielding span when one is given.
2. Validate the document: unique items, a non-empty content list, and
   a positive thinnest equipment shielding when it is declared.
3. Compare the declared items with the required set and list what is
   missing; count the ratio so partial progress is visible.
4. For each modelled environment, require a model identifier, a model
   version and a cited reference standard.
5. For a statistical environment, require a declared confidence level
   and report one below the expected minimum; for any other item,
   report a confidence level that should not be there at all.
6. For an activity-conditioned environment, require the solar activity
   condition it was evaluated for.
7. Cross-check every derived product's shielding span against the
   thinnest equipment shielding, treating a span starting exactly at
   that thickness as reaching it.
8. Report the declared items, the missing items, the completeness
   ratio and every finding, with one verdict.

## Pitfalls

- Treating the derived products as analysis outputs rather than
  specification content. They are what the analyses read, and leaving
  them out pushes the modelling choice into each analyst's hands.
- Naming a model without its version. Two revisions of the same model
  give different fluences, and an analysis that cannot say which one
  it used cannot be repeated.
- Quoting a solar particle event fluence with no confidence level. The
  number is meaningless on its own — it could be a median or a
  worst case, and those size a design differently.
- Attaching a confidence level to a trapped or cosmic ray model. It
  reads as extra rigour and is a category error; what that model owes
  is the solar activity condition.
- Accepting a dose-depth curve that starts thicker than the thinnest
  shielding in the equipment. The exposed parts are exactly the ones
  the curve then cannot answer for.
- Failing a span that starts exactly at the thinnest equipment
  shielding. It reaches it; the equality is settled inside the
  comparison by a named tolerance.

## Behavior contract (gate 3)

The entry and document validation, required-item comparison and
completeness ratio, model identifier, version and standard checks,
statistical confidence-level rules including the misplaced-confidence
case, solar activity condition requirement and the shielding-span
cross-check are exercised by the gate 3 contract test:
scripts/test_q6015_mission_radiation_environment_specification_deliverabl.py
against
scripts/q6015_mission_radiation_environment_specification_deliverabl_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6015_mission_radiation_environment_specification_deliverabl.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
