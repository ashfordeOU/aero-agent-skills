---
name: e3102-proof-pressure-test
description: "Define the proof pressure test of a two-phase heat transport item under ECSS-E-ST-31-02C clause 5.6.5. Use when the task is turning a maximum design pressure and a proof factor into the pressure to apply, correcting that pressure for a test temperature whose material allowable differs from the design point, grading the applied pressure as a window between the proof target and the yield of the article rather than as a floor, checking the hold duration, and closing acceptance on no leakage and a permanent set inside its allowance. Trigger: ecss, e-st-31-02c, proof-pressure-factor, proof-test-temperature-correction, proof-pressure-hold-duration, proof-permanent-set-allowance, proof-yield-pressure-window, two-phase-proof-acceptance."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport-scope, e3102-proof-pressure-test, proof-pressure-factor, proof-test-temperature-correction, proof-pressure-hold-duration, proof-permanent-set-allowance, proof-yield-pressure-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Proof Pressure Test (space-systems/ecss/e3102-proof-pressure-test)

Use when the task is the proof pressure test of ECSS-E-ST-31-02C clause
5.6.5 -- deciding what pressure the article actually has to see, at what
temperature, for how long, and what the test has to leave behind before
it counts as passed.

## Domain quick reference

- The proof pressure is the maximum design pressure times a proof factor
  above unity. A factor of one is the service condition with a
  certificate attached: it demonstrates nothing the article has not
  already survived, so it is refused rather than applied.
- Test temperature changes the pressure, not the requirement. What the
  proof demonstrates is a fraction of material capability, and capability
  moves with temperature. Running the test where the alloy is stronger
  and applying the design-temperature pressure imposes a smaller fraction
  of capability than intended, so the pressure is scaled by the ratio of
  the allowable at the test temperature to the allowable at the design
  temperature.
- The applied pressure is a window with two sides. It has to reach the
  corrected target, and it has to stay below the pressure that yields the
  article. A proof test that overshoots into yield has not produced a
  stronger article; it has consumed the one it was verifying, and the
  overshoot is a finding even though the target was met.
- An article whose yield pressure is at or below its own proof target
  cannot be proof tested as specified at all. That is a design or
  category error surfaced by the test definition, not a test result to
  be reported.
- Hold duration is part of the test, not an operator preference. A brief
  excursion to pressure and back does not expose time-dependent
  behaviour the hold exists to find.
- Acceptance is a conjunction, not a best-of. Pressure window, hold,
  no leakage, and permanent set inside its allowance all have to hold.
  A gauge that reads shorter after the hold than before is a measurement
  or reference-dimension problem and is reported as such rather than
  being taken as a favourable negative set.

## Workflow

1. Validate the maximum design pressure and the proof factor; refuse a
   factor at or below unity.
2. Form the proof pressure at the design temperature, then apply the
   test-temperature correction when both material allowables are
   declared. Refuse a half-declared correction: one allowable alone
   cannot form a ratio.
3. Grade the applied pressure against the corrected target and, when a
   yield pressure is declared, against that ceiling. Raise the
   unproofable-article error when the ceiling sits at or below the
   target.
4. Grade the hold duration against the minimum for the article.
5. Convert the before and after gauge readings into a permanent set
   fraction and grade its magnitude against the allowance, flagging a
   negative set separately.
6. Take the leakage observation as a boolean; refuse anything that is not
   one, because an ambiguous leak record is not an acceptance input.
7. Combine the four checks into one verdict, name each failed check, and
   absorb exact-equality cases with a named tolerance rather than by
   moving a limit.

## Pitfalls

- Applying the design-temperature proof pressure at an arbitrary test
  temperature. The number is right only where the allowable it was
  derived against holds, and an uncorrected cold test under-proofs the
  article while reading as a pass.
- Inverting the correction ratio. The allowable at the test temperature
  goes on top: a stronger article at test needs more pressure, not less,
  to reach the same fraction of capability.
- Treating the applied pressure as a floor to be comfortably exceeded.
  The generous overshoot that makes the target obviously met is the same
  overshoot that yields the article.
- Reporting a passed proof on an article whose yield pressure never
  cleared the proof target. The test definition itself is invalid there
  and no applied pressure makes it valid.
- Accepting a negative permanent set as extra margin. A gauge that came
  back shorter did not improve; the measurement or the reference
  dimension is wrong and the result is not usable.
- Recording leakage as a free-text note and grading it as absent. Only an
  explicit no-leak observation is acceptance evidence.

## Behavior contract (gate 3)

The proof-factor validation, proof pressure formation, test-temperature
correction, applied-pressure window against target and yield, hold
duration grading, permanent set computation and grading, leakage
observation handling and the rolled-up verdict are exercised by the
gate 3 contract test: scripts/test_e3102_proof_pressure_test.py against
scripts/e3102_proof_pressure_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3102_proof_pressure_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
