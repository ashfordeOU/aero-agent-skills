---
name: q60-class-2-lot-homogeneity-sampling
description: "Verify that the specimens offered for class 2 radiation verification testing stand for the flight hardware under ECSS-Q-ST-60C clause 5.5.5, where the set is composed in line with the radiation standard: read the traceability axes the declared basis rests on, measure every specimen against the flight lot on exactly those axes, size the irradiated, control and spare roles in integer arithmetic from the test method and the number of bias conditions, and hold the scope the result will be written to against what that basis can carry. Use when a radiation result is about to be extended to parts nobody irradiated. Trigger: ecss, q-st-60c-clause-5-5-5, class-2-radiation-sample-composition, radiation-specimen-traceability-basis, irradiated-control-spare-role-counts, bias-condition-specimen-consumption, radiation-result-scope-limit."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-2-lot-homogeneity-sampling, class-2-radiation-sample-composition, radiation-specimen-traceability-basis, irradiated-control-spare-role-counts, bias-condition-specimen-consumption, radiation-result-scope-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Radiation Test Sample Composition (space-systems/ecss/q60-class-2-lot-homogeneity-sampling)

Use when the task is the clause 5.5.5 question of ECSS-Q-ST-60C: a set of
class 2 parts has been offered for radiation verification testing, and the
set has to be composed the way the radiation standard composes one before
anything is put in a beam. The question is not whether the parts will
survive. It is whether this particular set of specimens can carry an answer
for the flight parts, and how far that answer reaches.

## Domain quick reference

- A radiation result is always a statement about parts that were never
  irradiated. Two things carry it across: the specimens came out of material
  the flight parts also came out of, and there were enough of them, in the
  right roles, for the method being run.
- Traceability is not one thing. A set drawn from the same wafer diffusion
  lot as the flight parts is tested on every axis — part number, maker, die
  revision, diffusion lot, assembly date code, package style. A set sharing
  only the assembly date code is tested on fewer. A set sharing only the part
  type is tested on fewer still. The basis chosen decides which axes a
  mismatch is even visible on.
- The basis also fixes how far the result reaches. Same diffusion lot carries
  a lot-specific claim; same date code carries a date-code-family claim; same
  part type carries nothing better than generic part-type data. A claim
  written above what the basis holds is not conservative and not
  recoverable — it is a number applied to material it was never taken from.
- The set has three roles and they are not interchangeable. Irradiated
  specimens take the dose. Control specimens stay out of the beam so drift in
  the measurement itself can be separated from drift caused by the beam.
  Spares absorb a specimen lost to handling without collapsing the run.
- Method decides whether bias conditions multiply the specimen count. A dose
  method retires each specimen once it has been irradiated, so every extra
  bias condition costs a fresh group. An event method sweeps its conditions
  on the same specimen, so the count does not move. Sizing a latch-up run as
  if it were a dose run buys parts nobody will use; sizing a dose run as if
  it were an event run leaves conditions with no specimens behind them.
- Counts come out of integer arithmetic. Per-condition counts multiplied and
  added as integers land on the same number on every machine; the same sizing
  done as a percentage of a lot does not.

## Workflow

1. Validate the flight lot record: an identifier plus every traceability
   value. A blank value is an input error, not an axis to be skipped.
2. Validate each offered specimen the same way, with its role in the set.
   Reject a repeated specimen identifier before anything is counted.
3. Read the axis set the declared basis rests on, and measure each specimen
   against the flight lot on exactly those axes. Name the axes that differ.
4. Split the offered set into the specimens the basis holds and the ones it
   does not. Only the first group counts toward the roles.
5. Size the requirement from the method and the number of bias conditions,
   multiplying the per-condition count only where the method consumes a fresh
   specimen per condition, and add the control and spare counts.
6. Take the shortfall per role and the share of the irradiated requirement
   actually covered.
7. Hold the scope the result will be written to against the scope the basis
   supports, defaulting the declared scope to what the basis supports rather
   than to the strongest one.
8. Return one verdict in precedence order: a specimen outside the basis, a
   claim above the basis, a short irradiated count, a short control group, a
   short spare count, otherwise a composed set. Report the requirement, the
   roles offered, the shortfalls and every finding.

## Pitfalls

- Counting an off-basis specimen toward the required irradiated group because
  it is physically the same part number. It sits outside the axis set the
  basis was declared on, so it neither carries the claim nor fills the count.
- Choosing the basis after the specimens have been found. The basis is what
  the result will be defended on; picking the widest one that happens to
  admit the parts on the shelf writes a lot-specific claim out of part-type
  material.
- Dropping the control specimens because the irradiated group looks healthy.
  Without them no reading separates beam-induced drift from measurement drift.
- Sizing every method the same way. Multiplying an event method by its bias
  conditions is waste; failing to multiply a dose method leaves conditions
  with no specimens behind them.
- Treating spares as optional padding. One specimen lost in handling ends the
  run at the required count, and a re-draw restarts the traceability argument
  from the beginning.
- Writing the strongest available scope into the report by default. The
  supported scope follows from the basis, and defaulting to lot-specific
  quietly upgrades every heritage set that passes through.

## Behavior contract (gate 3)

The plan validation, basis axis sets, flight lot and specimen validation,
mismatch detection, offered-set partition, integer sizing against bias
conditions, role counts, coverage fraction, scope support test and verdict
precedence are exercised by the gate 3 contract test:
scripts/test_q60_class_2_lot_homogeneity_sampling.py against
scripts/q60_class_2_lot_homogeneity_sampling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_lot_homogeneity_sampling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
