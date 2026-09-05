---
name: stress-life-curve
description: "Use when S-N test data must be reduced to a Basquin curve, an endurance limit must be determined from runout tests, or a fatigue life must be predicted from a stress amplitude for a structure. Determine the stress-life (S-N) fatigue curve from test data and use it for fatigue life prediction: fit the Basquin equation S = A * N^b to the S-N test points by log-log regression, read the endurance limit from the runout stress level, and predict the cycles to failure at a given stress amplitude or the allowable amplitude for a required life. Trigger: stress-life-curve, sn-curve, basquin-equation, endurance-limit, fatigue-life-prediction, sn-data."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fatigue
  tags: [stress-life-curve, sn-curve, basquin-equation, endurance-limit, fatigue-life-prediction]
  version: 0.1.0
  author: Aero Agent Skills
---

# Stress-Life (S-N) Fatigue Curve (structures/fatigue/stress-life-curve)

Use when fatigue test data must be turned into a usable curve: fit
the Basquin equation to S-N test points, determine the endurance
limit from the runout stress level, and predict the fatigue life at
a constant stress amplitude. The leaf covers curve construction from
test data, the log-log fit, the endurance limit, and life
prediction; mean-stress corrections, cumulative damage, and notch
effects are separate leaves.

## Domain quick reference

- Basquin equation: S = A * N^b, with stress amplitude S, cycles to
  failure N, fatigue strength coefficient A (the stress amplitude at
  N = 1 cycle), and fatigue strength exponent b (negative for
  metals, typically -0.05 to -0.15).
- Worked curve, A = 1000 MPa, b = -0.1 (verified by running
  scripts/stress_life_curve_logic.py):
  S(1e4) = 398.1 MPa, S(1e5) = 316.2 MPa, S(1e6) = 251.2 MPa,
  S(1e7) = 199.5 MPa. Each decade of life costs roughly 20 to 25
  percent of the amplitude.
- Life prediction: N = (S / A)^(1 / b). At S = 300 MPa on the worked
  curve, N = (0.3)^-10 = 1.69e5 cycles.
- Log-log fit: log S = log A + b * log N; least squares over the
  (log N, log S) pairs recovers A and b. The three exact points
  (1e3, 501.2), (1e4, 398.1), (1e5, 316.2) refit to
  A = 1000 MPa, b = -0.1.
- Endurance limit: Se = A * N_runout^b at the runout threshold;
  for runout at 1e7 cycles the worked curve gives
  Se = 1000 * 1e7^-0.1 = 199.5 MPa. Equivalently, the endurance
  limit is the highest tested stress level whose test survived the
  runout life, read directly off the data.
- Typical metallic values: A near 0.9 * Sut and b between -0.05 and
  -0.15; the endurance limit of steels sits near 0.5 * Sut.
- Equivalent life-form parameterization N = C * S^-m appears in some
  references, with m = -1 / b and C = A^(-1 / b); convert before
  mixing parameters.

## Workflow

1. Gather the S-N test data as (cycles to failure N, stress
   amplitude S) pairs in one stress unit; keep runout tests (test
   stopped without failure at the runout life) separate from
   failures.
2. Fit the Basquin curve: run the log-log least squares regression
   over the failed specimens to get (A, b).
3. Determine the endurance limit: evaluate the fitted curve at the
   runout threshold, or take the highest runout stress level from
   the data when the curve is not needed.
4. Predict the life at the applied stress amplitude with
   N = (S / A)^(1 / b), or the allowable amplitude for a required
   life with S = A * N^b.
5. Report A, b, the endurance limit, the runout threshold, and the
   predicted life with the stress unit stated.

## Pitfalls

- Confusing the S-N curve with the Goodman mean-stress correction:
  the Basquin curve assumes fully reversed loading (zero mean
  stress); a fluctuating cycle on a mean stress must be corrected
  with the goodman-diagram leaf before the amplitude is read against
  the curve.
- Confusing curve construction with cumulative damage: the S-N curve
  gives the life of a constant-amplitude cycle; a varying-amplitude
  spectrum needs the miner-damage leaf to sum the damage fractions
  per cycle block.
- Confusing the smooth-specimen curve with notched behavior: a
  stress concentration shortens the life at the same nominal
  amplitude; reduce the amplitude with the fatigue notch factor from
  the notch-sensitivity leaf first.
- Mixing parameterizations: S = A * N^b and N = C * S^-m carry the
  exponent with opposite signs; using b as m (or the reverse)
  silently corrupts every prediction.
- Mixing stress units between A and the applied amplitude, or
  between the test data and the design case.
- Extrapolating far beyond the tested life range: fatigue lives are
  log-normally scattered, so predictions outside the data band are
  weak regardless of the fit quality.
- Claiming an endurance limit where none exists: aluminum and other
  non-ferrous alloys have no true fatigue limit, only a finite-life
  curve; report the runout-level stress, not an infinite-life
  guarantee.
- Fitting in linear space: the regression must run on (log N,
  log S) so every decade of life weighs equally.

## Behavior contract (gate 3)

The S-N analysis logic is exercised by the gate 3 contract test:
scripts/test_stress_life_curve.py against
scripts/stress_life_curve_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_stress_life_curve.py

The 21 test methods cover the worked anchors above, the trend
property that life grows as the stress amplitude drops, and the
ValueError cases for non-positive inputs, a zero exponent, too few
fit points, identical lives, and missing runouts.

## Compliance

- FAR-25, CS-25, and MMPDS are cited as reference-only certification
  context (compliance: STANDARDS-REF, gated: false); no text is
  quoted from any of them. The S-N methodology itself is standard
  mechanical engineering practice.
