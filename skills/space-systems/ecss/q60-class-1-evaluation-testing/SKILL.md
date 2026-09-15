---
name: q60-class-1-evaluation-testing
description: "Evaluate whether the test programme run on a candidate class 1 EEE part meets the conditions and pass criteria of ECSS-Q-ST-60C clause 4.2.3.4: refuse a step whose applied severity misses the required value in the sense that step declares, keep an unexecuted mandatory step apart from a step that ran with no drift, turn every end-point reading into a drift fraction against its own drift limit and its absolute limit band, and absorb an exactly-met bound with a named tolerance instead of relaxing it. Use when evaluation measurements have to become a candidate-part verdict. Trigger: ecss, q-st-60c-clause-4-2-3-4, class-1-candidate-part-evaluation, evaluation-test-programme-severity, applied-test-condition-sense, end-point-parameter-drift-limit, evaluation-pass-criteria-verdict, mandatory-evaluation-step-coverage."
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
  tags: [ecss, q-st-60c-class-1-eee-scope, q60-class-1-evaluation-testing, q-st-60c-clause-4-2-3-4, class-1-candidate-part-evaluation, evaluation-test-programme-severity, applied-test-condition-sense, end-point-parameter-drift-limit, evaluation-pass-criteria-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts — Evaluation Testing (space-systems/ecss/q60-class-1-evaluation-testing)

Use when the task is the evaluation test programme of ECSS-Q-ST-60C clause
4.2.3.4 — the tests a candidate electrical, electronic and electromechanical
part is put through, the conditions those tests are run at, and the criteria
the results are read against before the part may be carried forward as a
class 1 candidate.

## Domain quick reference

- The programme has three separable parts and they fail independently: which
  tests were run, how hard each one was run, and what the readings afterwards
  say. A step can be present, run at full severity and still fail on drift, so
  each is recorded on its own rather than folded into a single mark.
- A required severity means nothing without the sense it is read in. A hot
  soak has to reach at least its stated temperature; a cold soak has to reach
  at most its stated temperature; a cycle count and a duration are at-least
  quantities. The sense therefore travels with the required value, and is
  never guessed from the name of the condition.
- A condition that was required but never applied is not a condition that was
  met. It is a hole in the programme, and it is named as one, because the
  step's result carries no evidence about that stress at all.
- Pass criteria are read on the end point, not on the raw reading. The
  quantity of interest is the drift of a parameter against its own initial
  value, because a part that starts and ends inside the same catalogue band
  can still have moved far enough to say the construction is unstable.
- A drift limit and an absolute limit band answer different questions. Drift
  asks whether the part moved; the band asks whether the part is still usable.
  A reading can sit inside the band after an unacceptable move, so both are
  applied and both findings are kept.
- Drift is a quotient and severities pass through unit conversions, so a value
  that should sit exactly on its bound can land a few units in the last place
  away from it. That is a representation question, absorbed by a named
  tolerance; the declared bound itself is never moved.

## Workflow

1. Validate the candidate identity: manufacturer, part number and the
   assurance category being evaluated against. A programme aimed at another
   category is an input error, not a programme to be reinterpreted.
2. Validate each step: normalized name, the conditions actually applied, the
   required severity with its sense, and the end-point measurements. Reject a
   step declared twice and a parameter measured twice inside one step.
3. Compare every required condition with what was applied, in its declared
   sense, and record a required-but-never-applied condition as its own
   finding.
4. Convert each measurement into a drift fraction against its initial reading,
   refusing a zero initial reading rather than dividing by it, and hold the
   fraction to the measurement's own drift limit or to the programme default.
5. Hold the final reading to its absolute limit band when one is declared, and
   refuse an inverted band instead of silently reordering it.
6. Compare the executed set against the mandatory step set and record each
   absent step as a coverage finding.
7. Report the per-step records, the absent steps and a programme verdict
   carrying every finding, not only the first.

## Pitfalls

- Assuming the sense of a condition from its name. A cold step read as an
  at-least quantity passes a soak that never got cold, which is the exact
  failure the step existed to catch.
- Reading a required-but-never-applied condition as satisfied because the step
  ran. The step ran; that stress did not, and the evidence for it does not
  exist.
- Judging a part on the final reading alone. A parameter that stayed inside
  its catalogue band while moving most of the way across it is the signature
  of an unstable construction, and only the drift comparison sees it.
- Applying one drift limit to every parameter. A leakage current and a
  threshold voltage do not move by the same fraction in a healthy part, so a
  measurement that declares its own limit keeps it over the programme default.
- Widening a drift limit or lowering a required severity to make an
  exactly-met case pass. An equality at the limit is handled by the tolerance
  inside the comparison; the declared value stays as specified.
- Stopping at the first finding. The programme owner needs the whole list to
  plan one repeat round rather than discovering the next shortfall after the
  next round.

## Behavior contract (gate 3)

The candidate identity validation, condition-sense comparison, drift-fraction
and limit-band verdicts, mandatory-step coverage and the overall programme
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_evaluation_testing.py against
scripts/q60_class_1_evaluation_testing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_1_evaluation_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
