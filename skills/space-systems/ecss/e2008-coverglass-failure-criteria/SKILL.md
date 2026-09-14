---
name: e2008-coverglass-failure-criteria
description: "Assess which coverglasses a subgroup test and the inspection after it leave failed under ECSS-E-ST-20-08C clause 8.8.1: refuse a criteria set carrying no specification reference, take each measured property's decay between its before and after reading against its own allowance with a tie admissible, catch a coating that has stopped bleeding charge, fail a measured-clean piece on any observed condition the specification lists, name every mode a piece shows rather than the first, hold a piece whose after reading is missing as not evaluated instead of passed, and weigh the failed share of the subgroup against its allowance. Use when subgroup coverglass results have to become per-piece failure calls. Trigger: ecss, coverglass-failure-modes, coverglass-subgroup-test-failure, coverglass-transmittance-decay-allowance, coverglass-coating-conduction-loss, coverglass-disqualifying-condition, coverglass-subgroup-failure-allowance."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e2008-coverglass-failure-criteria, e-st-20-08c-clause-8-8-1, coverglass-failure-modes, coverglass-subgroup-test-failure, coverglass-transmittance-decay-allowance, coverglass-coating-conduction-loss, coverglass-disqualifying-condition, coverglass-subgroup-failure-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Coverglass Failure Criteria (space-systems/ecss/e2008-coverglass-failure-criteria)

Use when the task is clause 8.8.1 of ECSS-E-ST-20-08C: the conditions that
mark a coverglass failed during a subgroup test and the inspection that
follows it. A subgroup is measured, exposed, measured again and then looked
at. This leaf reads one declared criteria set and turns that evidence into a
per-piece call, with every mode named.

## Domain quick reference

- There are two independent arms and neither offsets the other. A measured
  property can move further than its allowance, and the inspection can see a
  condition the specification lists. A piece that is clean on the numbers is
  still failed on a listed condition, and a piece that looks perfect is still
  failed on a property that moved too far.
- The criteria come from the specification that governs this coverglass
  type. A criteria set with no reference behind it produces a word nobody can
  audit later, so an unreferenced set closes the assessment rather than
  grading anything.
- The decay is the movement in the direction that hurts, and that direction
  differs per property. Transmittance and surface conductivity fail by
  falling; absorptance fails by rising. Taking an absolute difference without
  the sense fails a piece that got better.
- A tie is admissible. The allowance is a ceiling on decay, so a piece
  landing exactly on it is still admissible and the comparison tolerance
  exists to absorb representation error rather than to widen the
  specification.
- A conductive coating reading no conductivity at all is its own mode, not a
  large percentage. The proportional allowance answers "how much did it
  degrade"; a coating that no longer bleeds charge has stopped doing its job
  entirely, and the two want different responses.
- A missing after reading is not a pass. The piece has not been evaluated,
  and reporting it as passed silently converts absent evidence into
  favourable evidence.
- Every mode counts, not the first one found. Two pieces failed for one
  reason and for four reasons are the same word and very different causes,
  and the investigation starts from the causes.
- How many failed pieces a subgroup may carry is a separate, declared
  question. It is a subgroup allowance, not arithmetic on the pieces, and it
  does not move any individual piece's call.

## Workflow

1. Validate the criteria set first: a non-blank specification reference,
   per-property allowances inside zero to one and naming known properties, a
   non-empty list of disqualifying conditions drawn from the recognised set,
   and a subgroup failed-share allowance inside zero to one.
2. For each piece, pair the before and after reading of every graded
   property. A property with either reading absent is recorded as unread, not
   as unchanged.
3. Take the decay in the sense that property degrades in, express it against
   the before reading, and compare it with its allowance admitting a tie.
   Record the margin either way.
4. Raise the lost-conduction mode separately when the coating reads zero
   surface conductivity after the test.
5. Read the inspection findings, refuse an unrecognised condition rather than
   ignoring it, and fail the piece on any condition the criteria set lists,
   whatever the measurements said.
6. Close each piece on one of three words: failed with every mode named,
   not evaluated when a reading is missing, or passed.
7. Take the failed share of the subgroup against its allowance, report the
   modes grouped by piece, and close the subgroup on meets-criteria, failed,
   or not-evaluable while any piece lacks a complete reading pair.

## Pitfalls

- Grading on the after reading alone. The criterion is the movement between
  two readings, and a piece that started low and did not move is a different
  finding from one that fell during the test.
- Letting comfortable numbers outvote the inspection. The observed conditions
  fail a piece on their own, which is exactly why they are listed separately
  from the allowances.
- Taking an unsigned difference. Absorptance rising and transmittance rising
  are opposite news, and an unsigned comparison fails the piece that improved.
- Recording a missing reading as a pass. It converts absent evidence into
  favourable evidence, and it is the one error nobody can detect downstream
  from the verdict alone.
- Stopping at the first mode. The repair depends on which modes appeared
  together, and a first-match verdict destroys that pairing.
- Averaging the subgroup. A mean decay inside the allowance over a piece that
  cracked has decided nothing about that piece.

## Behavior contract (gate 3)

The criteria validation, the per-property decay and its sense, the allowance
comparison with an admissible tie, the lost-conduction mode, the observed
condition arm, the not-evaluated verdict, the margins and limiting margin,
the failed share against its allowance and the subgroup verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_coverglass_failure_criteria.py against
scripts/e2008_coverglass_failure_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_failure_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
