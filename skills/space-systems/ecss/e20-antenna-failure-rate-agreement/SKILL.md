---
name: e20-antenna-failure-rate-agreement
description: "Use when determine whether a spacecraft antenna retained without redundancy is a single-point-failure item under ECSS-E-ST-20C clause 7.2.1.3, and whether its failure-rate is agreed with the customer, specified in the requirement-baseline and demonstrated by evidence: categorize the redundancy-scheme (none, cold-standby, hot-standby, cross-strapped), confirm a numeric failure-rate in failures-per-billion-hours is on record, check that the demonstrated failure-rate does not exceed the specified value, grade the demonstration evidence (test, in-orbit-heritage, similarity, analysis), and propagate the series-reliability of every retained single-point-failure antenna against the mission reliability-allocation. Trigger: ecss, e-st-20-electrical-scope, e20-antenna-failure-rate-agreement, single-point-failure, antenna-failure-rate, failure-rate-demonstration, reliability-allocation, redundancy-scheme, customer-agreement, failures-per-billion-hours."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-failure-rate-agreement, single-point-failure, antenna-failure-rate, failure-rate-demonstration, reliability-allocation, redundancy-scheme]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical & Optical — Antenna Failure-Rate Agreement (space-systems/ecss/e20-antenna-failure-rate-agreement)

Use when the task is the single-point-failure treatment of an antenna under
ECSS-E-ST-20C clause 7.2.1.3 -- deciding whether the antenna is a retained
single-point-failure item, and whether its failure-rate has been agreed
with the customer, written into the requirement-baseline, and demonstrated
rather than asserted.

## Domain quick reference

- An antenna is rarely duplicated: the aperture, its feed-chain and its
  support-structure usually form one functional string. Clause 7.2.1.3
  does not forbid that; it makes the retained single-point-failure item
  conditional on a failure-rate that is agreed, specified and
  demonstrated. All three conditions are separate obligations -- an
  agreed number that never reached the requirement-baseline is as open
  as a number nobody agreed.
- Categorization comes first. A scheme that leaves one functional string
  (none, single-string) and whose loss removes a spacecraft function is a
  single-point-failure item. The same non-redundant string whose loss is
  absorbed elsewhere is tolerated and carries no agreement obligation,
  and any cold-standby, hot-standby or cross-strapped arrangement is
  outside the clause. Categorizing every antenna as a
  single-point-failure item by reflex inflates the agreement burden and
  hides the ones that genuinely need it.
- Failure-rates are carried in failures-per-billion-hours. The specified
  value is the committed ceiling; the demonstrated value is what the
  evidence supports. Compliance is demonstrated-not-above-specified, not
  the reverse, and the two are distinct records -- a record with only a
  specified value has an open demonstration whatever its evidence field
  says.
- Demonstration routes rank: qualification-test evidence, then in-orbit
  heritage of the same build standard, then similarity to a qualified
  design, then handbook analysis. Analysis alone does not close the
  obligation; it sizes the number that the other routes then have to
  support.
- Retained single-point-failure antennas sit in series with the function
  they serve: the chain survival is the product of the per-item
  exponential survivals over the mission duration, compared against the
  reliability-allocation held for the antenna chain.

## Workflow

1. Categorize each antenna from its redundancy-scheme and whether its
   loss removes a spacecraft function. Reject an unrecognized scheme
   before it enters the assessment; drop redundant and tolerated
   non-redundant items from the agreement checks.
2. For every retained single-point-failure antenna, pull its failure-rate
   record. No record at all is the first finding -- not an assumption of
   zero.
3. Check the three obligations independently: customer agreement,
   presence in the requirement-baseline, and a demonstration route
   ranked at similarity or better with a demonstrated numeric value.
4. Compare the demonstrated failure-rate against the specified one. Use
   the demonstrated value as the effective rate when present, otherwise
   the specified value, and record which one was used.
5. Compute the per-antenna exponential survival over the mission
   duration, compare it against any per-item reliability floor, and
   multiply the retained items into the chain survival.
6. Compare the chain against the reliability-allocation. The antenna set
   is not clause-compliant until every per-item finding list is empty
   and the allocation is met.

## Pitfalls

- Reading "no violation" off an antenna with no failure-rate record --
  an absent record means the agreement never happened, which is the
  finding itself, not a pass.
- Collapsing agreement, specification and demonstration into one flag.
  A supplier datasheet number quoted in a review chart satisfies none of
  the three; each is evidenced separately.
- Comparing specified against demonstrated in the wrong direction. The
  demonstrated rate must stay at or below the specified ceiling; a
  demonstrated rate far below it is fine, while a specified rate below
  the demonstrated one is an open non-conformance.
- Multiplying every antenna into the chain. Redundant and
  loss-tolerant antennas do not belong in a series chain, and including
  them understates the chain survival and can manufacture a false
  allocation miss.
- Treating an exact allocation match as a miss. The chain is a product
  of exponentials while the allocation is often quoted from a lumped
  rate; the two differ by representation error only, so the comparison
  absorbs that error instead of widening the engineering limit.

## Behavior contract (gate 3)

The redundancy-categorization, record-validation, evidence-grading,
rate-comparison, survival and chain roll-up logic is exercised by the
gate 3 contract test:
scripts/test_e20_antenna_failure_rate_agreement.py against
scripts/e20_antenna_failure_rate_agreement_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e20_antenna_failure_rate_agreement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
