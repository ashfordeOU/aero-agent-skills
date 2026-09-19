---
name: q7045-fatigue-testing
description: "Derive a stress-life curve from an S-N set and report what its points are entitled to claim. Use when the methods clause of ECSS-Q-ST-70-45 calls for fatigue data: censor the run-outs out of the log-log least-squares fit instead of letting them pull the curve towards a life nobody observed, reconcile every point against the declared run-out threshold, report a run-out that stopped before the fitted curve predicts failure as constraining nothing, and carry the cycling frequency and the specimen form with the curve. Trigger: ecss, q-st-70-45, sn-curve-basquin-loglog-fit, fatigue-runout-censoring, fatigue-runout-threshold-contradiction, fatigue-cycling-frequency-band, fatigue-notched-specimen-kt."
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
  tags: [ecss, q-st-70-45-mechanical-testing-scope, q7045-fatigue-testing, sn-curve-basquin-loglog-fit, fatigue-runout-censoring, fatigue-runout-threshold-contradiction, fatigue-cycling-frequency-band, fatigue-notched-specimen-kt]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing of Metals -- Fatigue Testing (space-systems/ecss/q7045-fatigue-testing)

Use when the methods clause of ECSS-Q-ST-70-45 calls for fatigue data: a set
of specimens has been cycled at a controlled frequency, some failed and some
were stopped at a declared run-out, and the question is what stress-life
relation those points support and which of them were allowed to help
establish it.

## Domain quick reference

- A run-out is a lower bound, not an observation. The specimen did not fail,
  so its recorded life is the point at which somebody stopped the machine;
  letting it into a least-squares fit pulls the curve towards a life that was
  never measured, always in the unconservative direction.
- A run-out still has to be consistent with the curve it is excluded from. If
  it was stopped before the fitted relation places failure, it survived
  nothing the curve did not already expect and it constrains nothing.
- The declared threshold is a contract in both directions. A point marked
  run-out below it was stopped early, and a failure recorded beyond it says
  the threshold in the report is not the threshold that was used.
- The curve belongs to a specimen form. A notched set without its stress
  concentration factor cannot be carried to a different notch, and a factor
  declared against an unnotched form means the two records disagree.
- Frequency travels with the data. Outside the band where heating and rate
  effects are negligible, the set is internally consistent and not comparable
  with anything else in the allowables.

## Workflow

1. Validate the set: positive stress amplitudes, at least one whole cycle per
   point, and an explicit boolean run-out marking on every point.
2. Separate failures from run-outs and fit log10 life against log10 stress
   over the failures alone, requiring at least three of them.
3. Refuse a fit that rises with stress amplitude or that has no stress spread
   to fit against; neither describes a fatigue curve.
4. Reconcile each run-out with the declared threshold, then with the fitted
   curve, and report the ones that constrain nothing.
5. Report failures recorded beyond the declared threshold as a contradiction
   in the record rather than silently accepting them.
6. Compare the cycling frequency with the band and the specimen form with its
   notch factor, and attach both to the curve.
7. Invert the curve onto the run-out life to report the stress the data
   places there, and onto any design stress that was asked about.

## Pitfalls

- Fitting the run-outs with the failures. It is one line of code and it moves
  the whole curve to the right.
- Reporting the run-outs as an endurance limit. A set stopped at a threshold
  shows where the machine stopped, not where the material stops failing.
- Quoting a life from the curve far outside the stress range that was tested.
  A log-log line extrapolates cheerfully and without warning.
- Mixing notched and unnotched points into one set. The fit succeeds, the
  scatter looks like material variability, and the notch effect disappears
  into the curve.
- Comparing a set cycled well above the band with one inside it. Self-heating
  changes what is being measured, and neither set is wrong on its own.

## Behavior contract (gate 3)

The S-N validation, the censored log-log fit with its quality and refusals,
the life and stress inversions, the run-out threshold and consistency
findings, the frequency band, the specimen form and notch-factor
reconciliation and the usable-curve verdict are exercised by the gate 3
contract test: scripts/test_q7045_fatigue_testing.py against
scripts/q7045_fatigue_testing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7045_fatigue_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
