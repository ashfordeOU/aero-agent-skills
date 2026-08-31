---
name: weight-estimation
description: "Use when performing class-I or class-II vehicle weight estimation: compute moments and center of gravity from component weights and arms, check the CG against the forward and aft envelope limits, and validate empty-weight fractions against typical band ranges per aircraft category. The skill supports weight and balance calculations in the FAR-25 / CS-25 certification context. Trigger: weight estimation, weight and balance, center of gravity, cg envelope, mass, weight fraction, moment, class-i, class-ii."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [weight-estimation, weight-and-balance, center-of-gravity, cg-envelope, mass, weight-fraction, moment, class-i, class-ii]
  version: 0.1.0
  author: AeroSkills
---

# Vehicle Weight Estimation (vehicle-design/sizing/weight-estimation)

Use when the task is aircraft weight estimation and weight and
balance: moments and center of gravity from component weights and
arms, CG envelope checks, and empty-weight fraction band checks
for class-I / class-II sizing.

## Domain quick reference

- Moment: M = weight * arm (arm is the station distance).
- Center of gravity: CG = sum(weight*arm) / sum(weight).
- CG envelope: the CG must lie between the forward and aft limits.
- Typical empty-weight fractions (class-I bands; validate against
  program data): transport 0.42-0.55, general-aviation 0.55-0.68,
  turboprop 0.50-0.62.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  for weight and balance for transport-category aeroplanes.

## Workflow

1. Collect component weights and arms into matching lists.
2. Compute the CG with cg_from_moments.
3. Check the CG against the forward and aft envelope limits with
   cg_within_envelope.
4. Compute the empty-weight fraction and compare it against the
   category band with check_empty_weight_fraction.
5. Confirm the deterministic checks with the contract test
   scripts/test_weight_estimation.py.

## Pitfalls

- Mismatched weights and arms lists (length mismatch) producing a
  wrong CG.
- Zero total weight (empty or all-zero lists) dividing by zero.
- Reversed forward/aft limits making every CG fail.
- Using a band from one category for another category.

## Behavior contract (gate 3)

The moment, CG, envelope, and band logic is exercised by the gate
3 contract test: scripts/test_weight_estimation.py against
scripts/weight_estimation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_weight_estimation.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; both
  summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
