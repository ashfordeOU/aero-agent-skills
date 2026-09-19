---
name: q7001-cleanliness-level-definitions
description: "Define what a particulate and a molecular cleanliness level mean and the units each is expressed in, following the ECSS-Q-ST-70-01C framework. Use when a programme has to write down its levels before any hardware is graded and the definitions must survive a change of inspected area or areal mass unit: builds the size-resolved count allowance from the level label and the declared distribution slope over a reference area, scales it onto the area actually inspected, turns the curve into an implied obscuration, and picks the coarsest molecular ladder step that still meets a required areal mass. Trigger: ecss, q-st-70-01-cleanliness-contamination-scope, particulate-level-label-definition, size-resolved-count-allowance, reference-area-count-normalisation, molecular-areal-mass-unit, cleanliness-level-unit-conversion, implied-level-obscuration."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-scope, q7001-cleanliness-level-definitions, particulate-level-label-definition, size-resolved-count-allowance, reference-area-count-normalisation, molecular-areal-mass-unit, cleanliness-level-unit-conversion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness and Contamination Control — Level Definitions (space-systems/ecss/q7001-cleanliness-level-definitions)

Use when the task is writing down what the cleanliness levels of an
ECSS-Q-ST-70-01C programme actually mean — the particulate level as a
size-resolved count allowance over a stated reference area, and the
molecular level as an areal mass in a stated unit — so that everything
graded against them later is graded against the same definition.

## Domain quick reference

- A particulate level is named by the largest particle size it admits,
  but the label alone is not the definition. The definition is the
  whole curve: the allowance rises steeply as the size falls, following
  a log-log distribution whose slope the programme declares, and
  nothing coarser than the label is admitted at all.
- The allowance is a count over a reference area, not a count. Quoting
  a level without its reference area makes every later comparison
  ambiguous, and an inspection covering a different area has to scale
  the allowance before it can be compared with what was counted.
- The obscuration a level implies comes from the incremental count in
  each size band, not from the cumulative count at one size. Counts are
  cumulative and non-increasing with size, so the population in a band
  is the difference between its two channel allowances, projected
  through the area of a representative particle.
- A molecular level is a number and a unit together. Nanograms per
  square centimetre, micrograms per square centimetre, milligrams per
  square metre and grams per square metre all appear in programme
  documentation, and a level compared across two of them without
  conversion is out by orders of magnitude.
- Selecting a molecular level from a ladder means taking the coarsest
  step that still sits inside the required limit. Taking the finest is
  not conservative — it is an unverifiable requirement nobody costed.
- A size channel coarser than the level label is not an error in the
  measurement; it is a channel the level says nothing about, and the
  definition records that rather than reporting a zero as a pass.

## Workflow

1. Validate the level label, the declared slope, the reference area and
   the size channels; channels must strictly increase and there must be
   at least two of them to form a band.
2. Evaluate the cumulative count allowance at every channel from the
   label, the slope and the reference area, marking any channel coarser
   than the label rather than silently returning nothing.
3. Scale each allowance onto the inspected area when one is declared,
   keeping the reference-area figure alongside it.
4. Form the implied obscuration band by band: the incremental count
   between adjacent channels at the geometric-mean size, plus the
   residual population at the coarsest usable channel.
5. Convert every molecular figure to one canonical areal mass unit
   before comparing, refusing an unrecognised unit instead of guessing.
6. Select the coarsest molecular ladder step inside the required limit,
   absorbing an exact equality at the bound with a named tolerance, and
   report a required limit no step can meet.

## Pitfalls

- Quoting a particulate level as a single count. The level is a curve,
  and the count at one convenient size is not the definition.
- Dropping the reference area. A count allowance without the area it is
  quoted over cannot be compared with anything, and rescaling it later
  from memory is where most level disputes start.
- Building obscuration from cumulative counts. Cumulative counts
  double-count every band below the size in question; the band
  population is a difference, not a total.
- Comparing molecular levels across units. A figure in micrograms per
  square centimetre next to one in nanograms per square centimetre
  looks stricter by a thousand until it is converted.
- Selecting the finest molecular step available. The requirement is the
  coarsest step that still meets the limit; anything finer adds cost
  and verification burden that nothing asked for.
- Reading a zero allowance above the level label as a clean result. The
  level admits nothing there because it says nothing there, so the
  channel is reported as outside the definition.

## Behavior contract (gate 3)

The level-label and channel validation, the slope-driven count
allowance, reference-area normalisation and rescaling, band-wise
obscuration, areal mass unit conversion with unknown-unit refusal,
coarsest-step molecular selection at the bound and the definition
record's findings are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_level_definitions.py against
scripts/q7001_cleanliness_level_definitions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanliness_level_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
