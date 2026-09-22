---
name: e50-time-distribution
description: "Compute the accuracy a distributed time reference actually delivers to each of its users under ECSS-E-ST-50C clause 5.7.2.8, which asks that time reach the users that need it inside a stated accuracy. Build the budget at the consumer, not at the master: uncompensated transport delay, half the path asymmetry, half the timestamp step and the random jitter of every hop, systematic terms added and random terms root-sum-squared, plus the holdover a consumer accumulates on its own oscillator between distribution messages. Use when sizing a distribution period, grading a chain against a required accuracy, or finding which consumer sets the limit. Trigger: ecss, e-st-50c-clause-5-7-2-8, time-distribution-accuracy-budget, time-reference-distribution-chain, distribution-holdover-drift, timestamp-quantization-error, path-asymmetry-time-error, distribution-period-sizing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.7.2.8
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-clause-5-7-2-8, e50-time-distribution, time-distribution-accuracy-budget, time-reference-distribution-chain, distribution-holdover-drift, timestamp-quantization-error, path-asymmetry-time-error, distribution-period-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Time Distribution (space-systems/ecss/e50-time-distribution)

Use when a time reference has to be distributed to the on-board or proximity
users that need it, per ECSS-E-ST-50C clause 5.7.2.8 — whether what arrives at
each user is still inside the accuracy that user was promised.

## Domain quick reference

- The obligation is met at the consumer, not at the source. A master
  clock holding nanoseconds proves nothing about a user three hops down
  a distribution tree; the number that matters is what is left after the
  chain and the holdover have spent their share.
- Hop contributions split into two kinds and do not combine the same
  way. Uncompensated transport delay, path asymmetry and timestamp
  quantization are biases that repeat every message, so they add;
  jitter is independent per message, so hops combine root-sum-square.
  Adding jitter linearly overstates a long chain badly enough to buy
  hardware nobody needed.
- Asymmetry and quantization each enter at half. A two-way exchange
  cancels the common part of the path and leaves half the difference;
  a timestamp resolved to one step is wrong by at most half a step.
- Compensation changes which number a hop contributes, not whether it
  contributes. A hop declared compensated still carries the residual the
  compensation left behind, and a residual nobody measured is an unknown,
  not a zero.
- Holdover is usually the dominant term and it is the one under design
  control. Between two distribution messages the consumer runs free at
  its own drift rate, so the distribution period and the oscillator
  together decide most of the budget — which makes the period the first
  knob to reach for, and the inverse calculation worth reporting.
- A chain that spends the whole allowance on its own cannot be rescued
  by distributing more often, and saying so is more useful than a period
  that rounds to something unbuildable.

## Workflow

1. Describe the chain hop by hop: transport delay, whether it is
   compensated and with what residual, path asymmetry, timestamp step
   and jitter. Reject an unnamed hop or an unknown field rather than
   silently defaulting it.
2. Reduce each hop to a systematic and a random contribution, taking
   the residual for a compensated hop and the full delay for one that
   is not.
3. Sum the systematic contributions; combine the random ones
   root-sum-square; keep the per-hop breakdown so the dominant hop is
   visible rather than inferred.
4. Add the holdover the consumer accumulates over one distribution
   period at its drift rate. A consumer with no declared drift holds
   over without error, which is a statement about the data, not a
   guarantee.
5. Compare the total against that consumer's required accuracy with a
   relative tolerance, so a budget landing exactly on the allowance
   passes on every build host.
6. Invert the same model for the remedy: the longest distribution
   period that still fits. Report zero where the chain alone exhausts
   the allowance, and report that the period is unconstrained where
   there is no drift to accumulate.
7. Grade every consumer, name the worst, and check the stated period
   remedy back through the model before offering it. Confirm in the same
   pass that the graded set holds every node the network has to serve
   with time, and that all of them trace back to the one reference: a
   node nobody distributes to, or a second source of time alongside the
   first, leaves the network without a single reference however
   comfortably each budget closes.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.2.8a | 7 |

## Pitfalls

- Budgeting at the master clock. Reference stability is an input to the
  budget, not the answer to it, and a distribution tree can lose orders
  of magnitude between the source and the user.
- Adding jitter terms linearly across hops. Independent random terms
  combine in quadrature; summing them makes a compliant chain look
  non-compliant and sends the design after a problem it does not have.
- Taking a compensated hop as contributing nothing. Compensation leaves
  a residual, and an unmeasured residual is a hole in the budget rather
  than a zero in it.
- Charging the full asymmetry or the full timestamp step. Both enter at
  half, and doubling them is the quiet way a correct design fails its
  own review.
- Deciding compliance with a bare inequality on the computed total. Two
  arithmetically identical budgets can straddle the allowance on
  different machines, and the verdict then depends on the build host.
- Answering an exceeded budget with a shorter period without checking
  whether the chain already spends the allowance. Distributing more
  often cannot buy back a bias that is present in every message.

## Behavior contract (gate 3)

Hop and consumer validation, the systematic and root-sum-square split,
the compensated-hop residual, the holdover term, the exact-allowance
boundary, the longest-period inverse and its zero and unconstrained
cases, and the worst-consumer selection are exercised by the gate 3
contract test:
scripts/test_e50_time_distribution.py against
scripts/e50_time_distribution_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_time_distribution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
