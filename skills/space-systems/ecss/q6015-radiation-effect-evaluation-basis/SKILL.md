---
name: q6015-radiation-effect-evaluation-basis
description: "Evaluate whether measured parameter drift shows a part damaged by radiation. Use when the ECSS-Q-ST-60-15C clause 4.3 evaluation basis has to be applied to a drift run: reduce every reading to one excursion that rises toward failure whichever way the parameter moves, interpolate the exposure level at which it leaves its limit, report a run that never left as censored at the highest level applied rather than inventing a crossing, flag drift that recovered between steps, and take the worst sample as the demonstrated capability. Trigger: ecss, q-st-60-15c-clause-4-3, radiation-parameter-drift-evaluation, parameter-limit-crossing-level, censored-radiation-capability, non-monotonic-drift-recovery, worst-case-sample-capability."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-radiation-effect-evaluation-basis, q-st-60-15c-clause-4-3, radiation-parameter-drift-evaluation, parameter-limit-crossing-level, censored-radiation-capability, non-monotonic-drift-recovery, worst-case-sample-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Effects — Evaluation Basis (space-systems/ecss/q6015-radiation-effect-evaluation-basis)

Use when the task is the evaluation basis of ECSS-Q-ST-60-15C clause 4.3 —
deciding, from the electrical parameters measured at each exposure step,
whether a part has actually been damaged, and at what exposure level the
damage became a failure.

## Domain quick reference

- Radiation damage is read off drift, not off a pass or a fail. A part does
  not stop working at a threshold; its parameters walk away from where they
  started, and the judgement is about when that walk carried one of them out
  of the limit the design relies on.
- Direction is a property of the parameter, not of the data. An offset current
  climbs, a current transfer ratio falls, and a reference voltage can go
  either way out of a band measured from its own starting value. Reducing all
  three to a single excursion quantity that rises toward failure makes one
  comparison serve all of them.
- The limit is a boundary, not a trip point. A reading sitting exactly on it
  has met it; only the floating-point representation of the comparison is in
  doubt, and that is settled by a tolerance inside the comparison rather than
  by moving the limit.
- The crossing level is interpolated, not the step the failure was noticed at.
  The step grid is a test schedule; the parameter left its limit somewhere
  between the last reading inside and the first reading outside, and reporting
  the outside step as the capability throws away the interval.
- A run whose readings all stayed inside is censored, not passed at infinity.
  The evidence supports a capability of at least the highest level applied,
  and that is what has to be reported, because inventing a crossing beyond the
  data is what the evaluation exists to stop.
- Drift that partly recovers between steps is real annealing, not noise to be
  smoothed. It means the run is no longer a single monotonic degradation, so
  the crossing read off it means less than it appears to and the recovery is
  reported alongside.
- Samples do not average. The capability the part is credited with is the
  worst sample's, because the flight build will contain that sample's
  siblings.

## Workflow

1. Validate the parameter: its name, its pre-irradiation value, its limit and
   the direction drift takes it out. Refuse a one-sided parameter already
   outside its limit before exposure, and a two-sided band that is not
   positive.
2. Validate each sample's readings: exposure levels strictly ascending and
   positive, values finite, at least one level applied.
3. Reduce every reading to its excursion against the limit's own threshold, so
   rising, falling and two-sided parameters are judged identically.
4. Walk the readings in level order and find the first one outside the limit;
   interpolate the crossing between it and the last reading inside, returning
   a reading that lands exactly on the limit as still inside.
5. Report a run with no reading outside as censored at the highest level
   applied, with no crossing level.
6. Compare each step's excursion with the one before it and report every step
   where the drift moved back toward its starting value.
7. Take the worst sample as the demonstrated capability, form the margin
   against the specified level, and let an exact equality pass under a named
   tolerance.
8. Report per-sample crossings and relative drifts, the worst-case sample, the
   capability with its censoring flag, the margin and a verdict carrying every
   finding.

## Pitfalls

- Reporting the step the failure was seen at as the capability. That is the
  next point on a test schedule, and it is optimistic by the whole step.
- Treating a reading exactly on the limit as a failure. The limit is met at
  equality; failing it there makes the result depend on how the value printed.
- Averaging samples into one capability. The build ships the worst one, and an
  average hides it behind the best.
- Reporting a censored run as if a crossing had been found. Nothing in the
  data says where the parameter would have left its limit, and a number
  invented there will be used as if it were measured.
- Smoothing a recovered step out of the run. Partial annealing between steps
  is a real effect and it changes what the crossing means.
- Applying one comparison direction to every parameter. A ratio that falls out
  of its limit passes a rising-limit test forever.

## Behavior contract (gate 3)

The parameter validation, excursion reduction across all three drift
directions, limit comparison with its exact-equality tolerance, reading
validation, interpolated crossing level, censored-run reporting, recovery
detection, worst-case sample selection and the margin verdict are exercised by
the gate 3 contract test:
scripts/test_q6015_radiation_effect_evaluation_basis.py against
scripts/q6015_radiation_effect_evaluation_basis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6015_radiation_effect_evaluation_basis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
