---
name: e2008-blocking-diode-qualification-plan
description: "Build and grade the qualification programme a planar blocking diode owes under ECSS-E-ST-20-08C clause 12.5.2, where the plan is assembled from the tests the applicable table lists: name an owed test the plan books nowhere, catch a test booked that the table never listed, size each test against the specimen count the table asks for, hold a test planned ahead of the test it rests on, refuse a similarity claim carrying no heritage part and no delta justification, total the specimen demand per group and overall, and return one plan verdict with ranked findings. Use when a blocking diode qualification plan, test matrix or specimen budget is assembled or reviewed. Trigger: ecss, e-st-20-08c, blocking-diode-qualification-plan, blocking-diode-test-table-coverage, blocking-diode-specimen-count-shortfall, blocking-diode-test-sequence-prerequisite, blocking-diode-similarity-claim-justification."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-qualification-plan, blocking-diode-qualification-plan, blocking-diode-test-table-coverage, blocking-diode-specimen-count-shortfall, blocking-diode-test-sequence-prerequisite, blocking-diode-similarity-claim-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Qualification Plan (space-systems/ecss/e2008-blocking-diode-qualification-plan)

Use when the task is clause 12.5.2 of ECSS-E-ST-20-08C: the qualification
programme for a planar blocking diode is not written from scratch, it is
assembled from the tests the applicable table lists. Each owed test is
given a specimen count, a place in a sequence and a statement of whether it
will be run or carried by similarity. This leaf reads the table and the
plan as two separate things and returns whether the assembly is complete.

## Domain quick reference

- The table is the authority on what is owed. The plan is an allocation
  against it, so every finding is a difference between two lists, not an
  opinion about a test.
- An omission and an invention are opposite defects with the same
  symptom, a plan of the wrong length. One leaves the programme short,
  the other spends specimens and schedule outside it.
- A specimen count is a plan-time number, and an undersized test reads as
  fully planned until the lot is drawn. Sizing it at review is the only
  cheap moment.
- A sequence is not a sort order. A test that rests on another has to sit
  after it in the run order, and a plan listed alphabetically hides the
  inversion completely.
- A similarity claim is an argument, not a shortcut. Without the heritage
  part and the delta justification it rests on, it is an omission wearing
  a different label, and it should not count towards coverage.
- Some programmes admit similarity for an owed test and some do not. That
  is a policy the plan is graded against, not a property of the test.
- A specimen demand nobody totalled is a plan that fails at the lot draw.
  The number is small arithmetic and it belongs in the plan.
- Optional table rows are not owed. Counting them into coverage makes a
  complete plan read as incomplete.

## Workflow

1. Read the table into an index keyed on the test, refusing a repeated
   row, an unrecognised group, a zero specimen count, and a prerequisite
   the table itself never lists.
2. Read the plan into sequence order, refusing a test booked twice, a
   position booked twice, and an unrecognised source.
3. Take the owed set: the table rows marked as owed, optional rows aside.
4. Grade each booked test: is it in the table at all, is its similarity
   claim admitted and justified, are its prerequisites booked and booked
   earlier, and is its specimen count at least what the table asks for.
5. Walk the owed set against what the plan books and name every owed test
   the plan omits.
6. Total the specimen demand from the run-sourced entries, per group and
   overall, leaving similarity entries out of the count.
7. Score coverage over the owed set and rank the arms into one plan
   verdict: omission first, then a test outside the table, then a
   similarity claim that is not admitted, then one that is unjustified,
   then an absent prerequisite, then a late one, then a short count.
8. Return the roll-up: tests grouped by verdict, the omitted set, the
   open tests, the coverage share, the specimen demand and the arm to
   close first.

## Pitfalls

- Grading the plan against itself. A plan that is internally consistent
  and misses half the table passes every check that never reads the
  table.
- Sorting the plan by test identifier before checking order. The sequence
  position is the only thing that says what runs first.
- Counting a bare similarity claim as coverage. It is the most common way
  a plan reads complete while owing a test.
- Counting optional rows into the owed set. Coverage then never reaches
  one and the plan cannot be signed.
- Measuring a similarity entry against a specimen count. It draws no
  specimens, so the count is not the question being asked of it.
- Totalling the specimen demand across similarity entries. The number
  then over-states the lot and the draw comes up short in the other
  direction.
- Merging an absent prerequisite with a late one. The first needs a test
  added, the second needs the sequence moved.

## Behavior contract (gate 3)

The plan policy validation, the table normalisation with its prerequisite
closure, the owed set, the plan normalisation into sequence order, the
similarity argument, the prerequisite order check, the per-test verdict
with its specimen shortfall, the omission sweep, the specimen demand
total, the worst-arm selection and the plan roll-up are exercised by the
gate 3 contract test:
scripts/test_e2008_blocking_diode_qualification_plan.py against
scripts/e2008_blocking_diode_qualification_plan_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_qualification_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
