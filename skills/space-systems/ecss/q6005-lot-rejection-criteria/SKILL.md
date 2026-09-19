---
name: q6005-lot-rejection-criteria
description: "Calculate whether the failures charged to a hybrid microcircuit lot have passed the limits that refuse the whole batch under ECSS-Q-ST-60-05C clause 10.4.2: validate that the per-stage record describes one consistent flow of hardware, compute the percentage defective at each screening stage against its stated limit, apply an absolute accept number instead below the small-lot population, add the cumulative percentage over the whole sequence, and return accept or reject naming every limit exceeded. Use when a screening tally has to be turned into a pass or fail. Trigger: ecss, q-st-60-05c, hybrid-lot-percent-defective-allowed, screening-stage-pda-limit, lot-accept-number-small-lot, cumulative-screening-defective-limit, lot-rejection-threshold."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-lot-rejection-criteria, hybrid-lot-percent-defective-allowed, screening-stage-pda-limit, lot-accept-number-small-lot, cumulative-screening-defective-limit, lot-rejection-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Quantitative Lot Rejection Limits (space-systems/ecss/q6005-lot-rejection-criteria)

Use when the task is applying the numeric limits of ECSS-Q-ST-60-05C clause
10.4.2 — deciding, from the failures charged at each screening and acceptance
stage, whether the batch as a whole is refused.

## Domain quick reference

- Each stage carries its own percentage-defective limit, because the stages
  probe different things. A visual stage tolerates more than a hermeticity
  stage; a lot acceptance stage may tolerate nothing at all, and a limit of
  zero means zero failures at any population, not a small percentage rounded
  down.
- The denominator is the units that entered the stage, not the units the lot
  started with and not the units that survived. Using the wrong one moves the
  percentage in a direction that depends on how many failed earlier, so two
  reviewers using different denominators disagree by more as the lot gets
  worse.
- Below a stated population a percentage stops describing the process. One
  failure out of twelve is eight percent and means almost nothing about the
  line; the criterion therefore becomes an absolute accept number, which is
  both easier to defend and harder to game by splitting a lot.
- A cumulative limit exists because stage limits do not compose. A lot can
  sit just inside every stage limit and still shed a quarter of itself across
  the sequence, and it is the sequence total, against the units that entered
  screening, that says whether the process was in control.
- The screening record has to describe one flow of hardware. A stage that
  starts with more units than the previous stage passed on is not a rounding
  question — units were added, or the failures were miscounted — and nothing
  computed from that record can be relied on.
- An observed value sitting exactly on a limit is inside it. That case is
  common, because limits are round numbers and lots are sized to them, and it
  is decided by a tolerance rather than by a strict comparison: the two sides
  are computed by different routes and need not produce the same float on
  every machine that runs the check.

## Workflow

1. Validate the per-stage record: a positive population, a non-negative
   failure count no larger than that population, no stage twice, and a flow
   where each stage starts with no more units than the previous one passed on.
2. For each stage, compute the percentage defective from the failures charged
   over the units that entered.
3. Resolve the limit for that stage from the default table or from the
   procurement override, refusing an override outside zero to one hundred.
4. Pick the criterion: the percentage for a normal population, the absolute
   accept number below the small-lot threshold. A zero limit allows no
   failures under either path.
5. Compare with the limit, treating an exactly-on-limit value as inside, and
   record whether the stage was exceeded.
6. Compute the cumulative percentage — every charged failure over the units
   that entered screening — and compare it with the cumulative limit.
7. Return the per-stage results, the cumulative result and one overall
   verdict, naming each exceeded limit with both numbers so the decision can
   be reproduced.

## Pitfalls

- Dividing by the surviving units. The percentage is about what entered the
  stage; dividing by survivors inflates it, and dividing by the original lot
  size deflates it, each by an amount nobody can reconstruct later.
- Reading a zero limit as "about zero". A stage that allows no failures is
  refused by one failure, whatever the population, and an accept number
  computed from the percentage would wrongly grant it a free unit.
- Applying the percentage to a lot of eight units. The result is dominated by
  the sample size; the accept-number path exists so a tiny lot is neither
  refused for a single failure nor allowed a proportional one.
- Checking only the stages. Every stage inside its limit is not a pass — the
  cumulative criterion is a separate test, and a lot that fails only there is
  exactly the process drift the criterion was written to catch.
- Deciding an on-the-limit case with a strict comparison. The equality is real
  and frequent, and letting a last-bit rounding difference decide it makes the
  same lot pass on one host and fail on another.
- Rebuilding the flow from a partial record. Missing intermediate stages leave
  the denominators unanchored; an inconsistent flow is refused rather than
  patched, because the patch is a guess at which number was wrong.

## Behavior contract (gate 3)

The record validation and flow consistency, the percentage defective, the
accept-number path, the on-the-limit comparison, the cumulative criterion and
the overall verdict are exercised by the gate 3 contract test:
scripts/test_q6005_lot_rejection_criteria.py against
scripts/q6005_lot_rejection_criteria_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_lot_rejection_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
