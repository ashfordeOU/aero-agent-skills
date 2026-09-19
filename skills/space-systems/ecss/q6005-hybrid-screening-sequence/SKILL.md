---
name: q6005-hybrid-screening-sequence
description: "Validate the ordered set of stress and inspection steps a hybrid microcircuit batch ran on every one of its units, under ECSS-Q-ST-60-05 clause 10.3. Use when a performed screening run has to be graded against the sequence it was meant to follow: name every inversion on both steps it involves, catch a step performed on the wrong side of the sealing operation, test that each step covered the whole batch and not part of it, report the mandatory steps nobody ran, and return the sequence-conformity index with one verdict. Trigger: ecss, q-st-60-05, hybrid-screening-sequence, hybrid-screening-step-order, pre-seal-and-post-seal-staging, hybrid-batch-screening-coverage, mandatory-hybrid-screening-steps, hybrid-screening-sequence-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-hybrid-screening-sequence, hybrid-screening-step-order, pre-seal-and-post-seal-staging, hybrid-batch-screening-coverage, mandatory-hybrid-screening-steps, hybrid-screening-sequence-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Hybrid Screening Sequence (space-systems/ecss/q6005-hybrid-screening-sequence)

Use when the task is clause 10.3 of ECSS-Q-ST-60-05: the ordered set of
stress and inspection steps every delivered unit of a production batch runs
through. The rules that govern how the sequence is planned and recorded are
graded separately under the screening general provisions, and the individual
steps have leaves of their own.

## Domain quick reference

- Screening is a sequence, not a checklist. Each step precipitates a defect
  the step after it can see, so a step in the wrong place still costs the
  same money and buys much less than its line on the plan suggests.
- The sealing operation splits the run in two. Everything that needs the
  package open belongs before it; everything that tests the closed package
  belongs after it. A step on the wrong side of the seal is not merely
  misordered — it could not have been performed as written.
- An inversion is read on both steps it involves. Neither ran where the
  sequence intended, and the evidence from both is weakened, so naming only
  the later one understates the damage.
- Screening covers every unit of the batch. A step run on part of the batch
  leaves the rest unscreened for the defect that step catches, and the yield
  on the units that did see it says nothing about the ones that did not.
- A few steps are what screening exists for. An absent one leaves the run
  incomplete rather than merely weaker, because no other step answers the
  question it answers.
- A step that declares no unit count is read as having covered the batch,
  because the alternative is to invent evidence; a count above the batch size
  is an input error rather than a generous step.
- The conformity index ranks what is outstanding. A stage violation, a
  missing mandatory step or a batch a step never covered decides the outcome
  on its own, at any index.

## Workflow

1. Take the batch identifier, the batch size, and the steps in the order they
   were actually performed rather than the order the plan lists.
2. Validate the run: every step is a published step, no step appears twice,
   and any declared unit count is a whole number within the batch.
3. Find the inversions by comparing every performed pair against the
   canonical positions, and name both members of each swap.
4. Locate the sealing operation and flag every pre-seal step that ran after
   it and every post-seal step that ran before it.
5. Compare each step's declared unit count with the batch size and name the
   steps that covered only part of it.
6. List the mandatory steps the run never performed.
7. Grade every published step — a stage violation outranks a coverage
   shortfall, which outranks an inversion — and take the weighted credit over
   total weight as the sequence-conformity index.
8. Name the verdict: incomplete while a mandatory step is missing, not
   accepted on a stage violation, a coverage shortfall or a low index,
   accepted with open actions when findings remain, accepted only when none
   do.

## Pitfalls

- Grading the plan instead of the run. The plan is always in order; the
  question is what the shop actually did and in what order.
- Reporting only the later half of a swap. Both steps ran out of place, and
  the earlier one lost the precipitation the later one was meant to expose.
- Treating a step on the wrong side of the seal as an ordering nuisance. It
  changes what the step could physically see, and no index should absorb it.
- Averaging a partial-batch step into the index and moving on. The unscreened
  units are the ones that will be found in the flight hardware.
- Letting a high yield stand in for coverage. Yield is measured on the units
  that were screened; it is silent about the units that were not.
- Dropping an inspection step because the stress before it passed. The stress
  exists to make a defect visible, and the inspection is what sees it.
- Re-running the sequence after a rework without re-running the steps that
  the rework invalidated. A reopened package is back before the seal.

## Behavior contract (gate 3)

The canonical step order, stage split at the sealing operation, inversion
detection on both members of a swap, batch-coverage test, mandatory-step
rule, step grading precedence, sequence-conformity index and run verdict are
exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_screening_sequence.py against
scripts/q6005_hybrid_screening_sequence_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6005_hybrid_screening_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
