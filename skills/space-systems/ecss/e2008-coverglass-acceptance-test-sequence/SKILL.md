---
name: e2008-coverglass-acceptance-test-sequence
description: "Use when a coverglass acceptance flow chart, test order table or run traveller has to be reviewed. Verify that the coverglass acceptance activities of clause 8.5.2 of ECSS-E-ST-20-08C run in their fixed order on both populations the clause reaches: the pieces being delivered and the pieces qualification consumes. Reduce a declared order to an inversion count and a conformance fraction, keep a missing activity apart from a reordered one, refuse an invented step, report a precedence pair broken whatever else moved, name a population left with no declared order at all, and return one campaign verdict with ranked findings. Trigger: ecss, e-st-20-08c, coverglass-acceptance-test-order, coverglass-delivery-population-sequence, coverglass-qualification-population-sequence, coverglass-sequence-inversion-count, coverglass-test-precedence-pair, coverglass-acceptance-order-verdict."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c, e2008-coverglass-acceptance-test-sequence, coverglass-acceptance-test-order, coverglass-delivery-population-sequence, coverglass-qualification-population-sequence, coverglass-sequence-inversion-count, coverglass-test-precedence-pair, coverglass-acceptance-order-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses — Acceptance Test Sequence (space-systems/ecss/e2008-coverglass-acceptance-test-sequence)

Use when the task is clause 8.5.2 of ECSS-E-ST-20-08C: coverglass acceptance
testing runs in a fixed order, and that order is applied to the pieces being
delivered and to the pieces the qualification campaign consumes alike. This
leaf grades a declared order against the baseline, population by population.

## Domain quick reference

- The second population is what the clause is for. Qualification hardware is
  not being shipped, so its acceptance order looks like somebody else's
  problem. It is the reverse: a qualification result only carries meaning if
  the pieces behind it went through the same order the delivered pieces did,
  and a campaign that reordered them is comparing two different histories.
- Order is not decoration on an acceptance run. A coverglass flow mixes
  observations that leave the piece as it was with steps that can mark, load
  or coat it, so a step taken out of turn quietly changes what every later
  step is measuring, and the number still looks like a number.
- Two kinds of deviation are graded apart because they mean different things.
  A run that drifted -- two adjacent measurements swapped by a technician
  working down a bench -- is an aggregate, so it is scored as a fraction of
  the pairs the run holds. A precedence pair is not an aggregate: one break
  is a defect on its own however clean the rest of the order is.
- Reducing an order to a single pass or fail throws away the distinction. A
  run reversed end to end and a run with one swap both read as non-conforming,
  and the report cannot tell a process problem from a bench habit.
- Coverage is a separate axis from order. A sequence missing an activity has
  not been reordered, it has been shortened, and scoring the two together lets
  a short run score well simply by having fewer pairs to get wrong.
- An invented step is refused rather than counted. An extra operation in an
  acceptance run is a change to the article's history nobody agreed to, and
  crediting it as coverage rewards the change.
- Absence and deviation are different states. A population with no declared
  order has not been sequenced; a population with a flawed order has been
  sequenced badly, and the two reach different people.

## Workflow

1. Validate each declared sequence: a known population, steps drawn only from
   the acceptance activity set, none repeated. Refuse an invented step.
2. Split the baseline activity set into what the sequence reached and what it
   omitted, and reduce that to a coverage fraction.
3. Count the activity pairs sitting in the reverse of the baseline order, and
   reduce the count to a conformance fraction over the pairs the run holds.
4. Check each declared precedence pair whose two members are both present, and
   report every one whose required order the run broke.
5. Rank the population verdict -- no order first, then incomplete, then a
   broken precedence pair, then a plain reordering.
6. Roll the populations up: populations grouped by verdict, any population
   left without a declared order, the weakest population, and every finding.

## Pitfalls

- Grading the delivery order only. The qualification pieces are inside the
  clause, and leaving them out is the single defect this leaf exists to catch.
- Collapsing inversions and precedence breaks into one score. A bench-level
  drift and a step that invalidates everything after it then read the same,
  and the report cannot say which one the project has.
- Scoring coverage and order together. A short run wins by holding fewer pairs
  to get wrong, and the omission disappears into a respectable fraction.
- Counting an invented step as coverage. It is an unagreed change to the
  article's history, and crediting it makes the change invisible.
- Reading a precedence pair as broken when only one member is present. The
  pair constrains an order between two steps that both ran; a run that never
  reached one of them has a coverage problem, not an order problem.
- Collapsing an undeclared order into a deviating one. The first has no
  evidence; the second has evidence of the wrong shape.
- Judging a conformance or coverage fraction that lands exactly on its
  declared floor by bare arithmetic. Both are quotients of activity counts, so
  a run sitting exactly on its floor can evaluate a unit in the last place
  below it; the comparison absorbs that while the floor stays as declared.

## Behavior contract (gate 3)

The sequence record validation and its refusal of invented and repeated steps,
the coverage split, the inversion count and its conformance fraction, the
precedence pairs and the one-member-absent case, the floors a float lands
exactly on, the policy position on carrying a precedence break, the ranked
population verdict and the rolled-up campaign verdict over both populations
are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_acceptance_test_sequence.py against
scripts/e2008_coverglass_acceptance_test_sequence_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_acceptance_test_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
