---
name: e2008-protection-diode-failure-criteria
description: "Assess which protection diodes a subgroup test programme and the inspection closing it leave failed under ECSS-E-ST-20-08C clause 9.7.1: refuse a criteria set carrying no specification reference, take each parameter's drift in the sense that parameter degrades in with a tie admissible, test the after reading against its own absolute limit as a separate arm, raise a junction that no longer blocks in reverse as its own mode, fail a numerically clean part on any listed observed condition, hold a part missing an after reading as not evaluated rather than passed, and weigh the failed share against its allowance. Use when subgroup diode results have to become per-part failure calls. Trigger: ecss, e-st-20-08c-clause-9-7-1, protection-diode-subgroup-test-failure, protection-diode-failure-modes, protection-diode-parameter-drift-allowance, protection-diode-absolute-limit-breach, protection-diode-blocking-function-loss, protection-diode-subgroup-failure-allowance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-protection-diode-failure-criteria, e-st-20-08c-clause-9-7-1, protection-diode-subgroup-test-failure, protection-diode-failure-modes, protection-diode-parameter-drift-allowance, protection-diode-absolute-limit-breach, protection-diode-blocking-function-loss, protection-diode-subgroup-failure-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Protection Diode Failure Criteria (space-systems/ecss/e2008-protection-diode-failure-criteria)

Use when the task is clause 9.7.1 of ECSS-E-ST-20-08C: the conditions that
mark a protection diode failed inside its subgroup test programme. A subgroup
is characterised, driven through a test, characterised again and then looked
at. This leaf reads one declared criteria set and turns that evidence into a
per-part call, with every mode named.

## Domain quick reference

- There are three independent arms and none of them offsets another. A
  parameter can drift further than its allowance, an after reading can sit
  outside an absolute limit whatever its drift, and the closing inspection can
  see a listed condition. A part clean on two arms is still failed on the
  third.
- Drift and the absolute limit answer different questions. A part that crept
  a few percent from a value already close to the ceiling is out; a part that
  moved a long way from a comfortable start can still be well inside. Grading
  on either arm alone misses one of those two parts every time.
- The criteria come from the specification governing this diode type. A
  criteria set with no reference behind it produces a word nobody can audit
  later, so an unreferenced set closes the assessment rather than grading
  anything.
- The drift is the movement in the direction that hurts, and that direction
  differs per parameter. Forward voltage drop, reverse leakage and thermal
  resistance fail by rising; reverse breakdown voltage fails by falling.
  Taking an unsigned difference fails the part that got better.
- A tie is admissible on both numeric arms. The allowance is a ceiling on
  drift and the absolute limit is a bound on the reading, so a part landing
  exactly on either is still admissible, and the comparison tolerance exists
  to absorb representation error rather than to widen the specification.
- A junction reading no reverse breakdown at all is its own mode, not a large
  percentage. The proportional allowance asks how much it degraded; a part
  that no longer blocks has stopped doing the protection job it was fitted
  for, and the two want different responses.
- A missing after reading is not a pass. The part has not been evaluated, and
  reporting it as passed silently converts absent evidence into favourable
  evidence.
- Every mode counts, not the first one found. Two parts failed for one reason
  and for four reasons are the same word and very different causes, and the
  investigation starts from the causes.
- How many failed parts a subgroup may carry is a separate, declared
  question. It is a subgroup allowance, not arithmetic on the parts, and it
  does not move any individual part's call.

## Workflow

1. Validate the criteria set first: a non-blank specification reference,
   per-parameter drift allowances inside zero to one naming known parameters,
   absolute limits that are finite and non-negative, a non-empty list of
   disqualifying conditions drawn from the recognised set, and a subgroup
   failed-share allowance inside zero to one.
2. For each part, pair the before and after reading of every graded
   parameter. A parameter with either reading absent is recorded as unread,
   not as unchanged.
3. Take the drift in the sense that parameter degrades in, express it against
   the before reading, and compare it with its allowance admitting a tie.
   Record the margin either way.
4. Test the after reading against its absolute limit as a separate arm, as a
   ceiling for a parameter that fails by rising and as a floor for one that
   fails by falling.
5. Raise the lost-blocking mode separately when the part reads no reverse
   breakdown voltage after the test.
6. Read the inspection findings, refuse an unrecognised condition rather than
   ignoring it, and fail the part on any condition the criteria set lists,
   whatever the measurements said.
7. Close each part on one of three words: failed with every mode named, not
   evaluated when a reading is missing, or passed.
8. Take the failed share of the subgroup against its allowance, report the
   modes grouped by part, and close the subgroup on meets-criteria, failed,
   or not-evaluable while any part lacks a complete reading pair.

## Pitfalls

- Grading on drift alone. A part that started at the ceiling and crept is out
  on the absolute limit and comfortable on the percentage, and a drift-only
  check ships it.
- Grading on the after reading alone. The criterion is also the movement
  between two readings, and a part that started low and did not move is a
  different finding from one that ran away during the test.
- Letting comfortable numbers outvote the inspection. The observed conditions
  fail a part on their own, which is exactly why they are listed separately
  from the allowances.
- Taking an unsigned difference. Reverse breakdown rising and reverse leakage
  rising are opposite news, and an unsigned comparison fails the part that
  improved.
- Recording a missing reading as a pass. It converts absent evidence into
  favourable evidence, and it is the one error nobody can detect downstream
  from the verdict alone.
- Stopping at the first mode. The repair depends on which modes appeared
  together, and a first-match verdict destroys that pairing.
- Averaging the subgroup. A mean drift inside the allowance over a part whose
  junction shorted has decided nothing about that part.

## Behavior contract (gate 3)

The criteria validation, the per-parameter drift and its sense, the allowance
comparison with an admissible tie, the absolute-limit arm in both senses, the
lost-blocking mode, the observed condition arm, the not-evaluated verdict,
the margins and limiting margin, the failed share against its allowance and
the subgroup verdict are exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_failure_criteria.py against
scripts/e2008_protection_diode_failure_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_protection_diode_failure_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
