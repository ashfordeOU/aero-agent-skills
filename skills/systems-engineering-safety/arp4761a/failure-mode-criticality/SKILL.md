---
name: failure-mode-criticality
description: "Use when you must quantify and rank the failure modes of an item by their rate-based criticality: split the item failure rate into per-mode rates with the mode ratios, compute the MIL-STD-1629A style criticality number C_m = beta * alpha * lambda_p * t for every mode with its failure-effect probability, sum the per-mode criticalities into the item criticality C_r, and rank the modes by C_m with each mode's share of item criticality and a dominant-mode flag. Produces the per-mode rate split, the C_m values, C_r and the sorted rank list that gates maintenance and redesign prioritization. Trigger: failure-mode criticality, fmeca criticality number, mode ratio, failure-effect probability, item criticality."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [failure-mode-criticality, fmeca-criticality, criticality-number, mode-ratio, failure-effect-probability, item-criticality]
  version: 0.1.0
  author: AeroSkills
---

# Failure Mode Criticality (systems-engineering-safety/arp4761a/failure-mode-criticality)

Use when you must quantify and rank the failure modes of an item by
their contribution to the item failure rate over an operating time. The
item failure rate is split into per-mode rates with the mode ratios
(each alpha, the set summing to 1), and every mode receives a
quantitative criticality number C_m = beta * alpha * lambda_p * t from
the conditional failure-effect probability beta, the mode ratio alpha,
the item failure rate lambda_p and the operating time t. The item
criticality C_r is the sum over the modes, and the ranking by C_m with
each mode's share of item criticality and a dominant-mode flag gates
maintenance and redesign prioritization. This is the MIL-STD-1629A
style quantitative FMECA criticality, implemented in pure Python,
stdlib only. It pairs with systems-engineering-safety/arp4761a/fta-fmea,
which catalogues the failure modes, and with
systems-engineering-safety/arp4761a/failure-rate-estimation, which
supplies the item failure rate input.

## Domain quick reference

- Mode ratio partition: every failure mode of the item claims a share
  alpha of the item failure rate, each alpha in (0, 1], and the set of
  mode ratios sums to 1.0 within MODE_RATIO_TOLERANCE (1e-9).
- Per-mode rate: mode rate = alpha * lambda_p. The item failure rate is
  the sum of the per-mode rates.
- Conditional failure-effect probability: beta in [0, 1] is the chance
  that the mode, when it occurs, produces the item-level effect; 0.0
  means no effect, 1.0 a certain effect.
- Criticality number: C_m = beta * alpha * lambda_p * t for each mode
  over the operating time t (mode_criticality).
- Item criticality: C_r = sum of C_m over all modes (item_criticality).
- Ranking: modes sorted by C_m descending, ties broken by mode id
  ascending; share = cm / C_r and dominant = share >= DOMINANT_SHARE
  (0.5) (rank_modes).
- Zero-exposure convention: when no criticality accumulates (zero
  operating time or every beta zero) C_r is 0.0 and every share is 0.0
  with no dominant mode, because cm / C_r is undefined.
- This leaf is rate-based only. It does not reduce fault trees, map
  severity categories to development assurance levels, rank fault-tree
  basic events by importance, model item states over time, or apply
  ordinal rating scales.
- ARP4761A frames the safety assessment context; the criticality number
  follows the quantitative FMECA methodology, summary-only.

## Workflow

1. Gather the item data: the item failure rate lambda_p over the
   operating interval, the operating time t, and the mode ratios alpha
   for every mode, each alpha in (0, 1] and the set summing to 1.0
   within MODE_RATIO_TOLERANCE.
2. Assign the conditional failure-effect probability beta in [0, 1] to
   every mode: 0.0 means the mode produces no effect at the item level,
   1.0 a certain effect.
3. Split the item failure rate into per-mode rates with
   split_item_rate(item_failure_rate, mode_ratios); each per-mode rate
   is alpha times lambda_p, and the partition math is validated against
   the ratio tolerance.
4. Compute the per-mode criticality with mode_criticality(beta, alpha,
   item_failure_rate, operating_time): C_m = beta * alpha * lambda_p *
   t.
5. Sum the per-mode criticalities into the item criticality with
   item_criticality(modes, item_failure_rate, operating_time):
   C_r = sum of C_m over all modes.
6. Rank the modes with rank_modes(modes, item_failure_rate,
   operating_time): sort by C_m descending with ties by mode id
   ascending, attach each mode's share of item criticality and the
   dominant flag at DOMINANT_SHARE, then read the rank list to gate
   maintenance and redesign prioritization.
7. Confirm the deterministic checks with the contract test: python3
   scripts/test_failure_mode_criticality.py.

## Worked example

Pump item with item failure rate lambda_p = 2e-6 per hour over an
operating time t = 5000 hours and three modes:

- runaway: alpha 0.2, beta 1.0, C_m = 1.0 * 0.2 * 2e-6 * 5000 =
  2.0e-3.
- jammed: alpha 0.5, beta 0.05, C_m = 0.05 * 0.5 * 2e-6 * 5000 =
  2.5e-4.
- no-output: alpha 0.3, beta 0.1, C_m = 0.1 * 0.3 * 2e-6 * 5000 =
  3.0e-4.

The per-mode rate split from step 3 is runaway 4e-7, jammed 1e-6,
no-output 6e-7 per hour. Step 5 sums the modes into the item
criticality C_r = 2.55e-3. Step 6 ranks the modes [runaway, no-output,
jammed]; runaway holds a share of item criticality 0.78431 and is the
dominant mode, no-output carries 0.11765, jammed 0.09804, and the
shares sum to 1.0.

Single-mode anchor: alpha = beta = 1 with lambda = 3e-6 per hour over
4000 hours gives C_m = C_r = 1.2e-2, the identity C_r = lambda * t.

## Verification

- Confirm split_item_rate(2e-6, {runaway: 0.2, jammed: 0.5, no-output:
  0.3}) returns the per-mode rates 4e-7, 1e-6, 6e-7.
- Confirm mode_criticality gives 2.0e-3, 2.5e-4 and 3.0e-4 for the pump
  modes and that item_criticality totals 2.55e-3.
- Confirm the single-mode identity: alpha = beta = 1 makes C_r equal
  lambda * t, here 1.2e-2 at 3e-6 per hour and 4000 hours.
- Confirm the rank list orders the pump modes [runaway, no-output,
  jammed] with runaway share 0.78431 within 1e-5 and dominant True, and
  that the shares sum to 1.0.
- Confirm the ties: modes with equal C_m order by mode id ascending.
- Confirm the rejections: alphas summing to 0.99 or 1.01, alpha 0 or
  1.5, empty mode sets, beta outside [0, 1], a non-positive item
  failure rate and a negative operating time all raise ValueError, while
  a zero operating time returns 0.0.
- Run the contract test offline: python3
  scripts/test_failure_mode_criticality.py (34 tests, deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: catalogues the failure
  modes and maps severity categories to development assurance levels;
  the mode set ranked here comes from that catalogue.
- systems-engineering-safety/arp4761a/failure-rate-estimation: the item
  failure rate lambda_p feeding the criticality number.
- systems-engineering-safety/arp4761a/fault-tree-importance-measures:
  importance of fault-tree basic events, a different ranking focus than
  per-mode item criticality.
- systems-engineering-safety/arp4761a/reliability-block-diagram:
  series-parallel reliability across items, complementary to the
  single-item mode analysis.
- manufacturing-quality/as9100/risk-management: owner of the ordinal
  1 to 10 product rating scales used in manufacturing quality work.

## Pitfalls

- Claiming a mode is critical from its rate alone: the criticality
  number combines the mode ratio, the failure-effect probability and
  the operating time, so a frequent mode with a negligible effect
  (jammed at 1e-6 per hour yet only 0.098 of the item criticality in
  the example) ranks below rarer modes with stronger effects.
- Letting the mode ratios drift off unity: the alphas must sum to 1.0
  within 1e-9 or the per-mode rates over- or under-account the item
  failure rate; the partition is rejected instead of silently
  renormalized.
- Reporting the item criticality without the operating time: C_m grows
  linearly in t, so a criticality number is meaningless without its
  exposure interval.
- Confusing this quantitative criticality with ordinal rating scales:
  the 1 to 10 product-style ratings belong to the manufacturing-quality
  risk-management leaf and are never computed here.
- Ignoring the dominant threshold: a share at 0.5 exactly is flagged
  dominant, so the boundary must be checked with the module constant
  DOMINANT_SHARE rather than by eye.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_failure_mode_criticality.py

The test covers the pump partition math and rate split, the worked
criticality numbers 2.0e-3, 2.5e-4, 3.0e-4 and item criticality
2.55e-3 within 1e-12, the single-mode identity C_r = lambda * t, the
rank order and dominant flag with share 0.78431 within 1e-5, shares
summing to 1.0, tie-break determinism by mode id, scale invariance of
the ranking, linearity of C_m in beta, alpha and operating time, and
ValueError rejection of every non-physical input listed in the spec.

## Compliance

- Standards referenced, not reproduced: ARP4761A is a SAE standard
  (sae.org/standards); the criticality number follows the quantitative
  FMECA methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
