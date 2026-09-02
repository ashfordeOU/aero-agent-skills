---
name: tolerance-stackup
description: "Use when you must compute the assembly tolerance stack-up from the part tolerances with the worst case and root sum square methods: sum the absolute tolerances for the worst case total, take the root sum square for the statistical total, sum the signed nominals into the assembly nominal dimension, and produce the assembly limits and the dominant variance share. Produces the worst case total, the RSS total, the assembly limits, and the dominant contributor that gate the fit assessment. Trigger: tolerance stack-up, worst case, root sum square, RSS, assembly limits, dominant contributor, nominal dimension."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9102
    reference-only: true
  - id: as9100
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: tolerancing
  tags: [tolerance-stackup, worst-case-stackup, rss-stackup, assembly-limits, dominant-contributor, dimension-chain, statistical-stackup, fit-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---
# Tolerance Stack-up (cross-cutting/tolerancing/tolerance-stackup)

Use when the task is assembly tolerance stack-up analysis from the
part tolerances: worst case total, root sum square (RSS) total,
signed nominal assembly dimension, assembly limits, and the dominant
variance contributor.

## Domain quick reference

- A linear dimension chain combines signed part nominals n_i with
  direction d_i (plus or minus 1) into the assembly nominal dimension:
  N = sum_i d_i * n_i.
- The worst case stack-up total is the sum of the absolute part
  tolerances: T_wc = sum_i t_i. Every part at its extreme limit
  simultaneously; the assembly limits are N +- T_wc.
- The statistical (RSS) stack-up total assumes independent, centered
  part variations: T_rss = sqrt(sum_i t_i**2). RSS is always less
  than or equal to the worst case total.
- The assembly limits are (N - T, N + T) for the chosen total T.
- The RSS variance share of part i is 100 * t_i**2 / sum_j t_j**2;
  shares sum to 100 and rank the dominant contributor.
- Units: any consistent length unit (mm, inch); all parts must share
  one unit system. Tolerances are bilateral symmetric half-ranges.

## Workflow

1. Collect the part nominals, directions, and tolerances for the
   chain.
2. Sum the signed nominals with nominal_total(nominals, directions).
3. Compute the worst case total with worst_case_total(tolerances).
4. Compute the statistical total with rss_total(tolerances).
5. Produce the assembly limits with stackup_limits(nominal, total).
6. Rank the contributors with rss_shares(tolerances) and report the
   dominant one before gating the fit assessment.

## Pitfalls

- Mixing unit systems in one chain: the stack-up is meaningless
  unless every part shares a unit system; no conversion is performed.
- Negative tolerances: physically meaningless; the logic raises
  ValueError.
- Applying RSS to correlated or biased parts: the independent,
  centered assumption understates the true spread; worst case is the
  conservative bound.
- Mis-signed directions: a subtracted part entered with the wrong
  sign shifts the nominal by twice its value.
- Using the largest tolerance instead of the largest variance share:
  the share squares the tolerance, so a large tolerance on a small
  part may still dominate the RSS total.

## Behavior contract (gate 3)

The stack-up logic is exercised by the gate 3 contract test:
scripts/test_tolerance_stackup.py against
scripts/tolerance_stackup_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_tolerance_stackup.py

## Compliance

- Standards referenced, not reproduced: AS9102 (first article
  inspection) and AS9100 (quality management) frame the characteristic
  tolerance and inspection context; the worst case and RSS stack-up
  methods are generic engineering methodology, summary and formulas
  only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
