---
name: e2007-maximum-emission-operating-mode
description: "Determine which operating mode of a tested unit emits most in each measurement band, and assess whether the mode declared for an ECSS-E-ST-20-07C clause 5.2.7.1 emission run is that worst case: rank the surveyed mode levels band by band, correct a pulsed emitter to an effective average level before ranking, name the dominant mode, compute the decibel shortfall of the declared mode, and list every band that needs a run of its own. Use when a unit offers several operating modes, load states or duty cycles. Trigger: ecss, e-st-20-electrical-scope, maximum-emission-operating-mode, worst-case-mode-selection, emission-survey-ranking, duty-cycle-emission-correction, per-band-mode-shortfall, emission-run-mode-gate."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-maximum-emission-operating-mode, worst-case-mode-selection, emission-survey-ranking, duty-cycle-emission-correction, per-band-mode-shortfall, emission-run-mode-gate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Setup — Maximum-Emission Operating Mode (space-systems/ecss/e2007-maximum-emission-operating-mode)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.7.1 obligation that an
emission measurement be taken with the tested unit running in the mode that
emits the most -- ranking a mode survey band by band, naming the mode that
should carry the formal run, and holding that run while a declared mode
understates the emission.

## Domain quick reference

- An emission plot characterizes the mode, not the unit. A sweep taken in
  stand-by is a correct measurement of a configuration that never flies, and
  it is the easiest way to produce a clean, useless qualification record.
- The worst mode is a property of the band, not of the unit. A switching
  converter at full load usually dominates the low band while a transmitter
  dominates the band around its carrier, so the ranking is done per band and
  one mode rarely wins everywhere.
- The candidate modes are surveyed first, with a short comparable sweep of
  each, and the formal run follows the survey. Ranking modes on the formal
  sweeps alone means the formal sweeps have already been taken in whichever
  mode was convenient.
- A pulsed emitter and a continuous one are not comparable as read. The
  survey peak of a mode running at a duty cycle below unity is corrected to
  an effective average level before the ranking; the correction is negative,
  proportional to twenty times the logarithm of the duty cycle, and it can
  move a transmitter out of first place.
- The declared mode is graded by shortfall, not by identity. What matters is
  how many decibels below the worst surveyed level the declared mode sits in
  each band: inside the allowed margin it is survey scatter, beyond it the
  band needs its own run.
- A survey of one mode has ranked nothing. The minimum mode count is a
  requirement on the survey, not a formality, and it is reported as a finding
  rather than silently accepted.

## Workflow

1. Normalize the survey: validate every mode name and level, reject a
   duplicate name, and reject a survey where the modes do not share one
   common band set -- an unequal band set makes the ranking meaningless.
2. Apply the duty-cycle correction to each mode that declares one, producing
   the effective average level used for every comparison that follows.
3. Rank the effective levels band by band and record the leading mode and its
   level for each band, breaking a tie deterministically by mode name.
4. Name the dominant mode: the one leading the most bands, with ties resolved
   by the highest single level and then by name.
5. Compute the per-band decibel shortfall of the declared mode against the
   band leader, and take the maximum across bands.
6. List every band whose shortfall exceeds the allowed margin; each is a band
   that must be re-run in its own worst-case mode.
7. Aggregate the findings and emit the gate token. Only an empty finding list
   releases the emission run.

## Pitfalls

- Choosing the mode with the highest power draw and calling it worst case.
  Emission follows switching and modulation, not average consumption, and a
  low-power mode with a fast edge rate often wins the low band.
- Picking one mode for the whole sweep because it won the first band. The
  ranking is per band, and a single-mode campaign silently drops every band
  another mode dominates.
- Comparing a pulsed transmitter peak with a continuous converter level.
  Without the duty-cycle correction the pulsed mode wins on detector choice
  rather than on emission.
- Treating a small shortfall as a failure. Survey sweeps scatter, so a
  shortfall inside the declared margin is accepted; only a shortfall beyond
  it buys another run.
- Surveying a single mode and declaring it the maximum. One mode is a
  measurement, not a selection.
- Letting a decibel difference that lands a few units in the last place
  outside the margin read as a non-conformance. The logic absorbs
  representation error with a named tolerance far below any decibel value;
  the margin itself is never widened.

## Behavior contract (gate 3)

The survey normalization, duty-cycle correction, per-band ranking, dominant-
mode selection, shortfall computation, additional-run listing and readiness-
gate logic is exercised by the gate 3 contract test:
`scripts/test_e2007_maximum_emission_operating_mode.py` against
`scripts/e2007_maximum_emission_operating_mode_logic.py` (stdlib unittest,
offline).
Run: python3 scripts/test_e2007_maximum_emission_operating_mode.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
