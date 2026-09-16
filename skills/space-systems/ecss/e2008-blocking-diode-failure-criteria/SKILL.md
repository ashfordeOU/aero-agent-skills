---
name: e2008-blocking-diode-failure-criteria
description: "Use when blocking diode subgroup results have to become per-part failure calls. Determine which planar blocking diodes a subgroup test and the inspection closing it leave failed under ECSS-E-ST-20-08C clause 12.7.1: refuse a criteria set carrying no specification reference, take each parameter's drift in the sense that parameter degrades in with a tie admissible, test the after reading against its own absolute limit as a separate arm, raise a junction that no longer blocks and one that no longer conducts forward as two distinct modes, hold a reverse reading taken below the reference bias as unread, and weigh the failed share against its allowance. Trigger: ecss, e-st-20-08c-clause-12-7-1, blocking-diode-subgroup-test-failure, blocking-diode-failure-modes, blocking-diode-parameter-drift-allowance, blocking-diode-absolute-limit-breach, blocking-diode-reverse-blocking-loss, blocking-diode-reverse-bias-reference."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-failure-criteria, e-st-20-08c-clause-12-7-1, blocking-diode-subgroup-test-failure, blocking-diode-failure-modes, blocking-diode-parameter-drift-allowance, blocking-diode-absolute-limit-breach, blocking-diode-reverse-blocking-loss, blocking-diode-reverse-bias-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Failure Criteria (space-systems/ecss/e2008-blocking-diode-failure-criteria)

Use when the task is clause 12.7.1 of ECSS-E-ST-20-08C: the conditions that
mark a planar blocking diode failed inside its subgroup test programme. A
subgroup is characterised, driven through a test, characterised again and then
looked at. This leaf reads one declared criteria set and turns that evidence
into a per-part call, with every mode named.

## Domain quick reference

- There are arms that do not offset one another. A parameter can drift further
  than its allowance, an after reading can sit outside an absolute limit
  whatever its drift, the part can have stopped doing one of its two jobs, and
  the closing inspection can see a listed condition. A part clean on three
  arms is still failed on the fourth.
- Drift and the absolute limit answer different questions. A part that crept a
  few percent from a value already near the limit is out; a part that moved a
  long way from a comfortable start can still be well inside. Grading on
  either arm alone misses one of those two parts every time.
- A blocking diode has two jobs and can lose either one. Reading no reverse
  blocking voltage means the bus is no longer held out of the string behind
  it; needing several volts before it conducts forward means the whole string
  has left the array. They are separate modes with separate causes, and
  neither is a percentage on a degradation curve.
- Reverse leakage is a strong function of the bias it is measured at. A
  reverse reading taken below the bias the specification names is not
  comparable with the limit, so it is held as unread rather than read as a
  reassuringly low number.
- The criteria come from the specification governing this diode type. A
  criteria set with no reference behind it produces a word nobody can audit
  later, so an unreferenced set closes the assessment rather than grading
  anything.
- The drift is the movement in the direction that hurts, and that direction
  differs per parameter. Forward voltage drop, reverse leakage and thermal
  resistance fail by rising; reverse blocking voltage fails by falling. Taking
  an unsigned difference fails the part that got better.
- A tie is admissible on both numeric arms. The allowance is a ceiling on
  drift and the absolute limit is a bound on the reading, so a part landing
  exactly on either is still admissible, and the comparison tolerance absorbs
  representation error rather than widening the specification.
- A missing after reading is not a pass. The part has not been evaluated, and
  reporting it as passed silently converts absent evidence into favourable
  evidence.
- Every mode counts, not the first one found. Two parts failed for one reason
  and for four reasons are the same word and very different causes, and the
  investigation starts from the causes.
- How many failed parts a subgroup may carry is a separate, declared question.
  It is a subgroup allowance, not arithmetic on the parts, and it does not
  move any individual part's call.

## Workflow

1. Validate the criteria set first: a non-blank specification reference,
   per-parameter drift allowances inside zero to one naming known parameters,
   absolute limits that are finite and non-negative, a positive reference
   reverse bias and open-circuit forward threshold, a non-empty list of
   disqualifying conditions drawn from the recognised set, and a subgroup
   failed-share allowance inside zero to one.
2. Check the bias the reverse readings were taken at. Below the reference
   bias, the reverse parameters are unread for that part and no reverse
   verdict follows.
3. For each part, pair the before and after reading of every graded parameter.
   A parameter with either reading absent is recorded as unread, not as
   unchanged.
4. Take the drift in the sense that parameter degrades in, express it against
   the before reading, and compare it with its allowance admitting a tie.
   Record the margin either way.
5. Test the after reading against its absolute limit as a separate arm, as a
   ceiling for a parameter that fails by rising and as a floor for one that
   fails by falling.
6. Raise the lost-blocking mode when the part reads no reverse blocking
   voltage, and the lost-forward-conduction mode when it needs at least the
   open-circuit threshold before it conducts.
7. Read the inspection findings, refuse an unrecognised condition rather than
   ignoring it, and fail the part on any condition the criteria set lists,
   whatever the measurements said.
8. Close each part on one of three words: failed with every mode named, not
   evaluated when a reading is missing or uncomparable, or passed.
9. Take the failed share of the subgroup against its allowance, report the
   modes grouped by part, and close the subgroup on meets-criteria, failed, or
   not-evaluable while any part lacks a complete reading pair.

## Pitfalls

- Grading on drift alone. A part that started at the limit and crept is out on
  the absolute arm and comfortable on the percentage, and a drift-only check
  ships it.
- Grading on the after reading alone. The criterion is also the movement
  between two readings, and a part that started low and did not move is a
  different finding from one that ran away during the test.
- Treating an open diode as a large forward drift. A part that never turns on
  has taken its string off the array, which is a different repair from a part
  whose drop crept, and a percentage hides that.
- Reading a low leakage taken at a low bias as good news. The measurement did
  not interrogate the junction, and the number it produced belongs to no
  limit.
- Letting comfortable numbers outvote the inspection. The observed conditions
  fail a part on their own, which is exactly why they are listed separately
  from the allowances.
- Taking an unsigned difference. Blocking voltage rising and leakage rising
  are opposite news, and an unsigned comparison fails the part that improved.
- Recording a missing reading as a pass. It converts absent evidence into
  favourable evidence, and it is the one error nobody can detect downstream
  from the verdict alone.
- Stopping at the first mode. The repair depends on which modes appeared
  together, and a first-match verdict destroys that pairing.
- Averaging the subgroup. A mean drift inside the allowance over a part whose
  junction shorted has decided nothing about that part.

## Behavior contract (gate 3)

The criteria validation, the reference-bias comparability arm, the
per-parameter drift and its sense, the allowance comparison with an admissible
tie, the absolute-limit arm in both senses, the lost-blocking and
lost-forward-conduction modes, the observed condition arm, the not-evaluated
verdict, the margins and limiting margin, the failed share against its
allowance and the subgroup verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_failure_criteria.py against
scripts/e2008_blocking_diode_failure_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_failure_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
