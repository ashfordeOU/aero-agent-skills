---
name: e3102-test-programme-units-sequence-tolerances
description: "Define and grade the test programme of a two-phase heat transport item under ECSS-E-ST-31-02C clauses 5.6.1 to 5.6.4. Use when the task is fixing how many test articles a heat pipe or a capillary driven loop owes for its model philosophy, ordering the campaign into the flow its equipment type requires so proof pressure precedes any performance run and the destructive burst comes last, grading the tolerance a facility applies to each set parameter against its allowable band, and checking the declared instrumentation accuracy is fine enough to police that band. Trigger: ecss, e-st-31-02c, two-phase-test-article-count, heat-pipe-test-sequence, capillary-loop-test-sequence, applied-test-parameter-tolerance, test-measurement-accuracy-requirement, burst-last-sequence-precedence."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport-scope, e3102-test-programme-units-sequence-tolerances, two-phase-test-article-count, heat-pipe-test-sequence, capillary-loop-test-sequence, applied-test-parameter-tolerance, test-measurement-accuracy-requirement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Test Programme, Units, Sequence and Tolerances (space-systems/ecss/e3102-test-programme-units-sequence-tolerances)

Use when the task is writing or reviewing the test programme of
ECSS-E-ST-31-02C clauses 5.6.1 to 5.6.4 -- how many articles the
campaign consumes, the order the tests run in for the equipment type in
front of you, and the two numbers that decide whether any of the
readings mean anything: the tolerance on what was applied and the
accuracy of what was measured.

## Domain quick reference

- Unit count follows from the model philosophy, not from convenience. A
  dedicated qualification model is taken to destruction, so the
  programme needs articles beyond the one that flies; a protoflight
  approach puts the flight item through the campaign and therefore
  cannot afford a burst article unless a separate one is procured. The
  equipment type moves the count too, because a loop carries more
  distinct functional tests than a fixed-conductance pipe.
- The sequence differs by equipment type. Both flows start with proof
  pressure and a leak check and end with the destructive burst, but a
  capillary driven loop inserts start-up and set-point regulation
  between the leak check and the environmental block, and a heat pipe
  has no equivalent of either.
- The ordering rules are precedence constraints, not a single fixed
  list. Proof pressure precedes any performance run because an article
  that has not been pressure-proofed is not yet a test article; a leak
  check follows every pressure application because that is when a seal
  fails; environmental exposure precedes pressure cycling so the cycling
  sees the article in its post-environment state; burst is last because
  nothing runs after it.
- A tolerance is on the applied value: the band the facility is allowed
  to hold a set point inside. Some quantities carry it as an absolute
  width and some as a fraction of the set value, and mixing the two is
  how a wide pressure tolerance gets reported as a tight one.
- An accuracy is on the measured value, and it has two separate jobs to
  pass. It must be at least as fine as the tabulated requirement for
  that quantity, and it must be several times finer than the tolerance
  band it is policing -- an instrument no better than the band cannot
  show the parameter stayed inside it, no matter what the reading says.

## Workflow

1. Normalise the equipment type and model philosophy; reject anything
   outside the recognised sets rather than defaulting.
2. Grade the declared article count against the tabulated minimum for
   that pair, honouring a programme-specific override when one is
   declared, and report the shortfall rather than only a verdict.
3. Grade the declared sequence against the flow for that equipment type:
   missing steps, steps that belong to the other flow or to no flow,
   repeated steps, and every fixed precedence pair.
4. For each set parameter, convert the applied tolerance to an absolute
   half-width at the nominal value and grade it against the allowable
   half-width for that quantity.
5. For each measured quantity, convert the declared accuracy the same
   way, grade it against the required accuracy, and separately grade it
   against the applied band at the resolution ratio.
6. Roll the four checks into one verdict and prefix every finding with
   the check that raised it, so a programme review can see whether the
   problem is the article count, the order, the facility or the sensors.

## Pitfalls

- Reusing the heat-pipe flow for a capillary driven loop. The loop's
  start-up and regulation steps are the ones that verify the parts of it
  a pipe does not have, and dropping them leaves the loop's own
  behaviour untested while every other step still passes.
- Putting burst anywhere but last. A burst article is consumed, so any
  step scheduled after it either never runs or runs on a different unit
  and is quietly no longer part of the same qualification chain.
- Comparing a relative tolerance with an absolute allowable. Two percent
  of a megapascal is twenty kilopascals; graded against an absolute
  kilopascal band it looks compliant only if the conversion is skipped.
- Accepting an instrument because it meets the tabulated accuracy. The
  accuracy requirement and the band-resolution rule are two conditions,
  and a sensor can pass the first while being unable to demonstrate the
  second.
- Treating a repeated step as harmless. A sequence that names the same
  test twice is ambiguous about which occurrence the precedence rules
  apply to, which is a programme defect before it is a test defect.
- Relaxing an allowable band so an exactly-at-limit case reads as a
  pass. Equality at a limit is a representation question, handled by the
  tolerance inside the comparison, not by moving the band.

## Behavior contract (gate 3)

The equipment-type and model-philosophy validation, unit-count grading
with overrides, per-type sequence and precedence checking, absolute and
relative tolerance conversion, measurement-accuracy grading against both
the requirement and the applied band, and the rolled-up programme
verdict are exercised by the gate 3 contract test:
scripts/test_e3102_test_programme_units_sequence_tolerances.py against
scripts/e3102_test_programme_units_sequence_tolerances_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_test_programme_units_sequence_tolerances.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
