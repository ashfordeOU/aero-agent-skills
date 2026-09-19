---
name: q6005-hybrid-lot-acceptance-general
description: "Size and grade the destructive sampling arrangement applied to a finished batch of hybrids under ECSS-Q-ST-60-05C clause 12.1. Use when a lot acceptance plan has to be laid out or judged: derive each group's sample size from a fixed count or a proportional share rounded up in integer arithmetic, total what the destructive groups consume, test the remainder against the contract delivery quantity, grade each group on its sample and its accept number, and return the arrangement, the destructive burden and one batch disposition. Trigger: ecss, q-st-60-05c, hybrid-lot-acceptance-test-arrangement, hybrid-destructive-sample-allocation, hybrid-lat-group-sample-size, hybrid-destructive-burden-ratio, hybrid-lot-acceptance-disposition."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-hybrid-lot-acceptance-general, hybrid-lot-acceptance-test-arrangement, hybrid-destructive-sample-allocation, hybrid-lat-group-sample-size, hybrid-destructive-burden-ratio, hybrid-lot-acceptance-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Lot Acceptance Arrangement (space-systems/ecss/q6005-hybrid-lot-acceptance-general)

Use when the task is clause 12.1 of ECSS-Q-ST-60-05C: the purpose and the
overall shape of the destructive sampling a finished batch of hybrids is put
through before any of it is delivered — how the groups are sized, what they
cost the lot, and what their results say about the units that were not
tested.

## Domain quick reference

- Lot acceptance is an argument about units nobody will ever test. The
  sample is destroyed to say something about its siblings, so every part of
  the arrangement exists to make that inference defensible: the size of the
  sample, where it was drawn from, and how many failures still leave the
  argument standing.
- A sample size comes from a rule, not from a habit. A fixed count is
  independent of the batch; a proportional share tracks it, with a floor so
  a small lot is not under-sampled and a ceiling so a large one is not
  consumed to prove a point already proved.
- Proportional sizing is integer arithmetic. A share taken as a floating
  point product lands a hair above a whole number often enough that a plan
  computed that way quietly asks for one more unit than the rule requires,
  every time the share divides the lot exactly.
- Destructive and non-destructive groups cost the lot differently. Only the
  destructive ones reduce what can be shipped, and a plan that totals all
  groups against the batch over-states its own burden and refuses feasible
  arrangements.
- A plan has to leave the deliverables behind. The batch must cover the
  destructive demand and the contract quantity together; discovering
  otherwise after the samples are consumed turns a sampling plan into a
  shortfall.
- A short sample is not a lenient sample. Drawing fewer units than the rule
  requires does not weaken the conclusion, it removes it — the group has to
  be re-drawn, and reporting it as a pass or a fail asserts something the
  sample cannot support.
- The states are not two. A batch can be accepted, rejected, still being
  tested, sampled invalidly, or arranged in a way that was never feasible,
  and each of those calls for a different action from a different person.

## Workflow

1. Validate the lot header: a positive batch size, a non-negative contract
   quantity and at least one sampling group. Refuse duplicate group
   identities, because two groups with one name cannot both be evidenced.
2. Validate each group's rule. A fixed rule names its units; a proportional
   rule names a share in parts per thousand with a floor and a ceiling, and
   a share above the whole lot or an inverted floor and ceiling is an input
   error.
3. Size every group against the batch, rounding a proportional share up with
   integer arithmetic so an exactly-dividing share does not acquire an extra
   unit from floating point.
4. Total what the destructive groups consume, subtract it from the batch and
   compare the remainder with the contract quantity. Report a demand larger
   than the batch separately from a remainder short of the contract — they
   are corrected by different people.
5. Report the destructive burden as a fraction of the lot, so two candidate
   arrangements can be compared on what they cost rather than on their
   group counts.
6. Grade each group in order: undrawn, drawn but not yet resulted,
   short-sampled, failed beyond its accept number, or passed. A short sample
   is settled before any pass or fail is asserted.
7. Return one batch disposition with the arrangement and every group's
   state, so an incomplete run reads as incomplete rather than as a
   provisional acceptance.

## Pitfalls

- Computing a proportional sample size in floating point. Two percent of
  five hundred is ten, and the float product is not; rounding it up asks for
  eleven units of flight hardware that the rule never required.
- Totalling every group against the batch. Non-destructive groups give their
  units back, and counting them as consumed rejects arrangements that would
  have delivered.
- Checking the destructive demand against the batch and stopping. The batch
  also has to cover the contract, and a plan that leaves two units against
  an order for ninety-eight is infeasible even though the sampling itself
  fits.
- Grading a short sample as a pass or a fail. It is neither: the group was
  not performed as specified, and either verdict claims support the sample
  does not give.
- Collapsing "not yet tested" into "not accepted". An arrangement whose
  results have not been entered is a plan, and reporting it as a rejection
  sends the batch to a review board that has nothing to review.
- Comparing the destructive burden strictly against a target. The burden is
  a quotient of counts that lands exactly on simple fractions, and a strict
  comparison against one of them answers differently on different machines.
- Reading an accept number of zero as a formality. It is the whole
  inference: with one failure permitted the argument is about a rate, and
  with none it is about the absence of the mechanism altogether.

## Behavior contract (gate 3)

The sample-rule validation, the integer round-up of a proportional sample
size, the destructive demand against the batch and the contract quantity,
the burden fraction, the per-group grading and the batch disposition are
exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_lot_acceptance_general.py against
scripts/q6005_hybrid_lot_acceptance_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hybrid_lot_acceptance_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
