---
name: e2008-external-protection-diode-testing
description: "Audit a declared external protection diode test programme against clause 9.2.1.2.2 of ECSS-E-ST-20-08C. Use when diode test conditions or methods have to be traced to the part's own dedicated source control drawing: refuse a test taken from a house specification or a datasheet, catch a drawing raised for another part number, hold a citation at a superseded issue, settle a substituted method before any condition, judge each condition under its own sense so a relaxation and an over-test are told apart, and name the drawing test nobody ran. Trigger: ecss, e-st-20-08c-clause-9-2-1-2-2, external-protection-diode-test-conditions, external-protection-diode-source-control-drawing, external-protection-diode-drawing-issue-standing, external-protection-diode-method-substitution, external-protection-diode-test-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c-clause-9-2-1-2-2, e2008-external-protection-diode-testing, external-protection-diode-test-conditions, external-protection-diode-source-control-drawing, external-protection-diode-drawing-issue-standing, external-protection-diode-method-substitution, external-protection-diode-test-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS External Protection Diodes -- Testing (space-systems/ecss/e2008-external-protection-diode-testing)

Use when the task is clause 9.2.1.2.2 of ECSS-E-ST-20-08C: an external
protection diode is not tested to a generic diode routine. Its test
conditions and its methods are the ones its own dedicated source control
drawing defines, so this leaf grades a declared test programme against
the drawing it claims to be following.

## Domain quick reference

- The work here is binding work, not measurement work. A test can be run
  carefully, logged completely and signed, and still prove nothing about
  this part, because the definition it followed came from somewhere the
  clause never pointed at.
- Only the part's own drawing governs. A house test specification, a
  supplier datasheet and an undeclared source are all references, and
  none of them is the dedicated drawing; a test resting on one is
  ungoverned however good the bench was.
- A drawing raised for another part number is somebody else's drawing.
  It reads as a citation, it passes every presence check, and it defines
  a different diode -- which is why the part number on the drawing is
  compared with the part on test rather than assumed.
- A drawing is read for its issue as well as its number. A test run to an
  issue the governing one has replaced was run to a definition nobody
  works to now, and that is a different finding from citing no drawing at
  all: one has the right document at the wrong edition.
- A substituted method is settled before any condition is looked at.
  Swapping a curve-tracer sweep for a handheld probe invalidates every
  condition underneath it, and comparing the conditions anyway produces a
  tidy table about nothing.
- The same numeric gap means opposite things depending on the condition.
  A severity floor -- reverse bias, forward drive, dwell count -- is
  weakened by a smaller number. A permitted ceiling -- dwell time, ramp
  rate, ambient humidity -- is weakened by a larger one. A set point with
  a tolerance, such as a junction temperature, is off its baseline in
  either direction.
- Relaxation and escalation are both deviations and are not the same
  finding. A relaxation leaves the diode less tested than its drawing
  asks, which is what the clause exists to prevent. An escalation
  over-tests delivered parts, costs money and rejects good hardware, so
  it is reported -- but whether it blocks is a project position, not a
  default.
- An omitted condition and an invented one are changes to the defined
  test, not details. A programme that drops the dwell and adds one of its
  own is not running the drawing's test at a variation; it is running a
  different test under the drawing's name.
- A test the drawing defines and nobody ran is a hole exactly where
  nobody is looking, so coverage is read from the drawing rather than
  from the programme.

## Workflow

1. Validate the drawings: identifier, part number, issue, governing issue
   and, per test, a method and its conditions with a sense each. A set
   point must carry a positive tolerance.
2. Validate each declared test: the document its definition came from,
   the drawing cited, the method run and the condition values declared.
3. Resolve the governing document. A source other than the part's own
   drawing, or a drawing nobody supplied, stops the test there as
   ungoverned.
4. Check the drawing belongs to the part on test, then check the cited
   issue against the governing one, then check the declared method
   against the drawing's method -- in that order, because each one makes
   the next comparison meaningless.
5. Split the condition sets: drawing conditions the programme omitted,
   declared conditions the drawing does not define, and the overlap.
6. Compare each overlapping condition under its own sense and group it as
   reused, relaxed, escalated or off its baseline band, absorbing
   representation error at the bound.
7. Rank the test at its worst standing, apply the carry positions for an
   over-test and an off-baseline set point, then roll the programme up:
   tests worst first, the drawing tests nobody ran, the conforming share
   and every finding.

## Pitfalls

- Reading a complete test report as a governed test. Completeness is a
  property of the paperwork; governance is a property of the document the
  conditions came from, and only one of the two is visible without asking
  where they came from.
- Accepting a house test specification because it is stricter. Stricter
  than what is exactly the question the drawing answers, and a programme
  that never opens the drawing cannot know.
- Matching a drawing by number and not by part. A neighbouring part's
  drawing cites cleanly and defines a different diode.
- Reading a drawing for its number and not its issue. The right drawing
  at a superseded edition passes every presence check and still describes
  a definition nobody works to.
- Comparing conditions across two different methods. The table looks
  rigorous, means nothing, and hides the substitution that caused it.
- Comparing every condition in one direction. A dwell ceiling and a bias
  floor are weakened by opposite signs, so a single-direction comparison
  reports half the relaxations as over-tests and the rest the other way
  round.
- Treating an over-test as harmless. Over-testing delivered diodes
  rejects good parts and costs schedule; it is reported, and whether it
  blocks is read from the project position rather than assumed either
  way.
- Grading only the tests the programme listed. A test the drawing defines
  and nobody ran leaves a hole exactly where no one is looking.
- Judging a condition that lands exactly on its drawing value by bare
  arithmetic. Declared values are routinely arrived at by arithmetic -- a
  step count multiplied out, a band summed up -- and the result can
  evaluate a unit in the last place either side of the bound on one
  platform and not on another; the comparison absorbs that while the
  drawing value stays as drawn.

## Behavior contract (gate 3)

The document-source vocabulary, the drawing validation with its per-test
methods and sensed conditions, the part-number binding, the
superseded-issue state, the substituted method settled before any
condition, the floor, ceiling and nominal senses with their opposite
directions of relaxation and escalation, the omitted and invented
conditions, the carry positions for an over-test and an off-baseline set
point, the worst-first test ranking, the drawing tests nobody ran and the
rolled-up programme verdict are exercised by the gate 3 contract test:
scripts/test_e2008_external_protection_diode_testing.py against
scripts/e2008_external_protection_diode_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_external_protection_diode_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
