---
name: q6013-class-1-temperature-range
description: "Verify that the rated temperature limits of a commercial part cover the equipment operating envelope under clause 4.2.2.6 of ECSS-Q-ST-60-13C at Class 1: correct the hot end by the self-heating rise the part dissipation drives across its mounting thermal resistance, widen both ends by the margin the thermal knowledge state earns, compare against the rated or grade-implied limits, and report hot-end and cold-end headroom with a per-part verdict and the critical part. Use when a declared component list, thermal analysis or part grade has to be reconciled with an equipment thermal envelope. Trigger: ecss, q-st-60-13c, q6013-class-1-temperature-range, commercial-part-rated-temperature-range, equipment-thermal-operating-envelope, part-self-heating-rise, thermal-uncertainty-margin, temperature-range-coverage-verdict."
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
  tags: [ecss, q-st-60-eee-scope, q-st-60-13c, q6013-class-1-temperature-range, commercial-part-rated-temperature-range, equipment-thermal-operating-envelope, part-self-heating-rise, thermal-uncertainty-margin, temperature-range-coverage-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Class 1 Temperature Range (space-systems/ecss/q6013-class-1-temperature-range)

Use when the task is clause 4.2.2.6 of ECSS-Q-ST-60-13C: the rated temperature
limits of a commercial part have to match the operating envelope of the
equipment it is fitted in, for the highest assurance class. This leaf derives
the range the part actually has to cover and grades each part against it.

## Domain quick reference

- The equipment envelope is not the part requirement. Two corrections sit
  between them, and they act on different ends.
- The first is self-heating. The part dissipates power across the thermal
  resistance between its mounting reference and the point its rating is
  quoted at, so the hot end of the requirement sits above the hot end of the
  envelope by that rise. The cold end carries no rise: dissipation only helps
  there, and the conservative cold case is the part unpowered.
- The second is the uncertainty of the prediction itself, added at both ends.
  How large it is depends on how the temperature was established. A measured
  thermal balance earns the smallest margin, a correlated model more, an
  uncorrelated model more again, and a bare engineering estimate the most.
  Buying knowledge is the cheapest way to recover headroom.
- The rated range comes from the datasheet limits when they were transcribed,
  and only falls back to the grade otherwise. A grade is a family habit, not a
  measurement, and grade-implied limits are the weakest input in the chain.
- Headroom is reported per end because the two ends fail for different reasons
  and are fixed by different actions. A hot-end shortfall is a mounting,
  dissipation or part-choice problem; a cold-end shortfall is a part-choice
  problem alone.
- A shortfall does not exclude the part on its own, but the only route that
  keeps it is a substantiated extension of the rated range. A shortfall with
  no extension evidence is one finding; a shortfall with an extension claim is
  a different finding that stays open until the evidence is reviewed.

## Workflow

1. State the equipment envelope: cold extreme, hot extreme, and how the
   temperatures were established. Reject an inverted or non-finite envelope
   before any part is looked at.
2. List every part with an identifier, its rated limits or its grade, its
   dissipation, the thermal resistance to the rated reference point, any
   extension evidence, and whatever verdict was declared for it.
3. Compute the self-heating rise from dissipation and thermal resistance, and
   read the uncertainty margin off the thermal knowledge state.
4. Build the required range: envelope cold extreme minus the margin, envelope
   hot extreme plus the rise plus the margin.
5. Take hot-end and cold-end headroom against the rated limits, absorbing
   representation error with a named tolerance so a part landing exactly on a
   bound passes.
6. Name the verdict from the pair of headrooms, raise the extension findings,
   and audit the declared verdict against the derived one.
7. Roll the population up: counts per verdict, the hot-critical and
   cold-critical parts, and one consistency flag that is only true when every
   part covers the requirement with no open finding.

## Pitfalls

- Comparing the datasheet limits straight against the equipment envelope. The
  part never sees the envelope; it sees the envelope plus its own rise plus
  the uncertainty of the prediction.
- Applying the self-heating rise at the cold end as well. It makes the cold
  case look easier than it is, which is the wrong direction.
- Taking the grade as the rating when the datasheet limits are on file. The
  grade is a fallback, and it is usually the more generous of the two.
- Averaging the two ends into a single margin figure. A large hot headroom
  never pays for a cold-end shortfall; the ends are graded separately.
- Reading a comfortable margin from an uncorrelated model and never revisiting
  it after the thermal balance test. The margin is an input, not a constant.
- Closing a shortfall by writing an extension claim into the list. The claim
  opens a finding; only the evidence behind it closes one.
- Rolling a population up on the count of covered parts and losing the part
  that sets the worst headroom.

## Behavior contract (gate 3)

The margin policy, self-heating correction, required-range derivation,
headroom and verdict logic, extension findings, declaration audit and
population roll-up are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_temperature_range.py against
scripts/q6013_class_1_temperature_range_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_1_temperature_range.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
