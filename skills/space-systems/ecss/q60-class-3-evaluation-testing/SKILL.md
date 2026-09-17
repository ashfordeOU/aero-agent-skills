---
name: q60-class-3-evaluation-testing
description: "Evaluate the test methods, conditions and acceptance limits of a Class 3 evaluation campaign under ECSS-Q-ST-60C clause 6.2.3.4: check the mandatory methods were all run, open each mission condition out by an over-test factor and grade the severity actually applied against it, take the attribute accept-or-reject on sample size and failure count, compare every reading against its declared band, refuse a band taken from a typical column, and close with one campaign verdict. Use when a Class 3 evaluation has to show what it tested, at what severity and against which limits. Trigger: ecss, q-st-60c, q60-class-3-evaluation-testing, q60-c3-over-test-factor-coverage, q60-c3-attribute-acceptance-number, q60-c3-acceptance-limit-source, q60-c3-evaluation-campaign-verdict."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q-st-60c, q60-class-3-evaluation-testing, q60-c3-over-test-factor-coverage, q60-c3-attribute-acceptance-number, q60-c3-acceptance-limit-source, q60-c3-mandatory-test-method-set, q60-c3-evaluation-campaign-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Evaluation Testing (space-systems/ecss/q60-class-3-evaluation-testing)

Use when the task is clause 6.2.3.4 of ECSS-Q-ST-60C: the test methods,
conditions and acceptance limits a Class 3 evaluation is run under. The leaf
turns a campaign report into three separable answers — what was run, how hard,
and against what — so a weak campaign can be repaired at the right place.

## Domain quick reference

- A campaign is worth what it declares about each test: the method, the
  severity it was run at, and the acceptance basis the survivors were measured
  against. A report that gives two of the three has not been graded.
- The mandatory methods are a set, not a menu. A method never run is its own
  finding, and it stays separate from a method that ran and disappointed.
- A test run exactly at the mission condition demonstrates nothing about the
  margin beyond it, so each mission condition is opened out by an over-test
  factor before the applied severity is compared with it.
- The severe direction differs by condition. A cold soak is severe downward
  and a cycle count is severe upward, so the factor is applied against the
  magnitude of the mission value and the sense is carried with it rather than
  guessed from the parameter name.
- The attribute decision and the parametric one are different questions. How
  many parts went in and how many failed is one; whether each survivor's
  reading sat inside its band is the other. They fail for different reasons
  and they take different repairs.
- A raised acceptance number is only meaningful against a sample big enough to
  carry it, so an acceptance number that would accept every possible outcome
  is an input error rather than a lenient plan.
- Where a limit came from is part of the limit. A typical column is a central
  value with a population around it, so a campaign resting on one has not
  demonstrated an acceptance limit — even when every reading fell inside it.
- A part that failed and a campaign that was thin are different verdicts. The
  failure is a fact about the part; the thin campaign is a gap in the evidence.

## Workflow

1. Identify the candidate and the campaign defaults: the over-test factor, the
   sample size required per method and the acceptance number.
2. Normalize each declared method name onto the published form, and reject the
   same method declared twice.
3. For every mission requirement, read its sense and its over-test factor,
   build the demanded severity from the magnitude of the mission value, and
   grade the severity actually applied. A requirement the campaign never
   applied is recorded as a hole, not left out of the count.
4. Take the attribute decision: sample size against the required size, failure
   count against the acceptance number, both reported even when one carries
   the answer.
5. Compare every reading with its declared band, absorbing a reading landing
   exactly on an edge rather than failing it, and record where the band came
   from beside the result.
6. Name the mandatory methods the campaign never ran.
7. Close with one verdict: failed where a part failed or a reading fell
   outside its band, incomplete where a method, a severity or a guaranteed
   limit is missing, passed only when all three answers are clean.

## Pitfalls

- Reading a test as covered because it ran. Running at the mission condition
  is not running with margin, and the over-test factor is the whole difference.
- Guessing the severe direction from the parameter name. The sense travels
  with the requirement, because the same parameter can be severe in either
  direction depending on the mission.
- Folding the attribute decision into the parametric one. A campaign with no
  failures and a sample of three is not the same result as a campaign with one
  failure out of twenty, and one number cannot say both.
- Accepting a band off a typical column because every reading fell inside it.
  The readings are then compared with a central value, and the population the
  parts come from extends past it on both sides.
- Reporting a required condition the campaign never applied as simply absent.
  It is an unmet requirement, and it belongs in the count with the others.
- Treating a thin campaign as a failure, or a failure as a thin campaign. One
  is a fact about the part and the other is a gap in the evidence.
- Comparing an applied severity with a demanded one by bare arithmetic. The
  demand is built by a product and a sum, so a condition set exactly on its
  demand can land a few units in the last place short of it; the comparison
  absorbs that representation error while the demand stays untouched.

## Behavior contract (gate 3)

The method-name normalization, over-test factor validation, demanded severity
in both senses, condition grading, acceptance limit band and its source, the
attribute accept-or-reject, per-method rollup, mandatory-method set and the
campaign verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_3_evaluation_testing.py against
scripts/q60_class_3_evaluation_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_3_evaluation_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
