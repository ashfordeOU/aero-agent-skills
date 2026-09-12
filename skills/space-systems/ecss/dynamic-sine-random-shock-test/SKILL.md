---
name: dynamic-sine-random-shock-test
description: "Use when perform sine-sweep, random-vibration, and shock dynamic
  structural tests under ECSS-E-ST-32C section 4.6.3.9: categorize each test
  type as sine-sweep, random-vibration, or shock; determine input levels for
  qualification and acceptance; compute overall Grms from a random-vibration
  power spectral density profile; apply notching rules where structural response
  limits cap the input at resonances; check a shock response spectrum value
  against the SRS envelope; and confirm every notching decision is backed by
  written justification before the test report is closed.
  Trigger: ecss, e-st-32-structures-scope, sine-sweep, random-vibration, shock,
  notching, grms, shock-response-spectrum, dynamic-test, srs."
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
  tags: [ecss, e-st-32-structures-scope, sine-sweep, random-vibration, shock, notching, grms, shock-response-spectrum, dynamic-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Dynamic Sine/Random/Shock Test (space-systems/ecss/dynamic-sine-random-shock-test)

Use when the task is planning or executing a dynamic structural test campaign
under ECSS-E-ST-32C section 4.6.3.9 — covering sine-sweep, random-vibration,
and shock tests including notching rules. The skill provides deterministic
rules for test-level selection, sweep-rate calculation, Grms computation,
SRS envelope checking, and notching compliance.

## Domain quick reference

- Three test types are recognized: sine-sweep (sinusoidal base excitation
  swept logarithmically through a frequency range), random-vibration
  (broadband base excitation defined by a power spectral density profile),
  and shock (transient excitation verified via a shock response spectrum
  envelope). Each type is matched to one of these three categories before
  its parameters are checked.
- Two primary test levels apply: qualification (higher levels, more pulses,
  longer duration — demonstrates design margin) and acceptance (lower levels,
  applied to each flight unit to screen workmanship). A proto-flight level
  combines the two: qualification-level inputs applied once per axis for
  the flight hardware.
- Notching is a controlled reduction of the input level at specific
  frequencies where structural resonances would otherwise drive component
  responses beyond their design limits. Notching is not permitted
  arbitrarily; each applied notch must be anchored to a structural response
  limit derived from a coupled-loads or component-level analysis, and the
  justification must be documented before the test is run.
- Grms (root-mean-square acceleration) is the scalar summary of a random-
  vibration PSD profile. It is computed by integrating the PSD over
  frequency and taking the square root; for a piecewise-flat PSD the
  integral reduces to the sum of psd × bandwidth over all bands.
- The shock response spectrum (SRS) is the maximum response of a set of
  single-degree-of-freedom oscillators to a shock input, plotted versus
  their natural frequency. Compliance requires the measured or predicted
  SRS to fall at or below the specified SRS envelope at every frequency.

## Workflow

1. Categorize each test item as sine-sweep, random-vibration, or shock.
   Reject any test type that does not match one of the three recognized
   categories before proceeding.
2. Determine the test level (qualification, acceptance, or proto-flight)
   for each item. Check that the qualification input level exceeds the
   acceptance level by the required margin (typically 6 dB for
   acceleration; verify the applicable margin from the project test
   specification).
3. For sine-sweep tests, compute the sweep rate (oct/min) from the
   frequency band and the elapsed time for one pass; compare against the
   maximum permitted rate in the test specification.
4. For random-vibration tests, compute Grms from the PSD segments and
   retrieve the standard test duration per axis: 120 s for qualification,
   60 s for acceptance and proto-flight.
5. For shock tests, retrieve the required number of pulses per axis: three
   for qualification and proto-flight, two for acceptance. Check each SRS
   data point against the specified SRS envelope.
6. For any resonance where the structural response is predicted to exceed
   a prescribed limit, apply notching: scale the input down proportionally
   so the predicted response equals the limit. Record the applied notch
   factor and link it to its justification.
7. Verify that every notch applied has a written justification on record.
   A test report with an unjustified notch is non-compliant regardless of
   measured response levels.
8. Aggregate findings: qualification margin violations, SRS exceedances,
   and missing notching justifications all constitute open findings that
   must be resolved before the test is closed.

## Pitfalls

- Applying the unnotched qualification input to a resonant component whose
  response has not been bounded by coupled-loads analysis — this can
  over-test and damage flight hardware or under-test if the actual response
  is unknown.
- Treating Grms as the only random-vibration compliance metric and ignoring
  the PSD spectral shape — a test can match the specified Grms while
  differing significantly from the required PSD, which may shift fatigue
  damage accumulation to uncharacterized frequency ranges.
- Confusing the number of shock pulses: qualification and proto-flight
  require three pulses per axis, not two; a two-pulse acceptance run run
  as a qualification sequence leaves the qualification margin unclosed.
- Notching without a justification document and reading a passing SRS
  comparison as full compliance — the documentation requirement is
  independent of the measured response; an unjustified notch is an open
  finding even if the SRS envelope is met.
- Using a linear (non-log) frequency axis to compute sweep rate — the
  correct sweep rate unit is oct/min on a logarithmic frequency scale.

## Behavior contract (gate 3)

The test-level categorization, test-type categorization, sweep-rate,
notching, Grms, SRS compliance, qualification-margin, duration, pulse-count,
notching-justification, and test-summary logic are exercised by the gate 3
contract test: scripts/test_dynamic_sine_random_shock_test.py against
scripts/dynamic_sine_random_shock_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_dynamic_sine_random_shock_test.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
