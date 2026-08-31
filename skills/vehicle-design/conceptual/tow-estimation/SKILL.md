---
name: tow-estimation
description: "Use when you must estimate the takeoff gross weight in conceptual aircraft sizing: apply the fuel-fraction method to payload and class-based empty and fuel fractions, iterate the estimate to convergence, and check the weight breakdown balances. Produces the takeoff gross weight estimate, the convergence verdict, and the breakdown check that gate the sizing iteration. Trigger: takeoff gross weight, conceptual sizing, fuel fraction, empty weight fraction, sizing iteration."
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
  subdomain: conceptual
  tags: [takeoff-gross-weight, conceptual-sizing, fuel-fraction, empty-weight-fraction, sizing-iteration]
  version: 0.1.0
  author: AeroSkills
---

# Takeoff Gross Weight Estimation (vehicle-design/conceptual/tow-estimation)

Use when the task is conceptual takeoff gross weight estimation:
the fuel-fraction method, iteration convergence, and weight
breakdown balance.

## Domain quick reference

- Fuel-fraction sizing: W0 = payload / (1 - empty fraction - fuel
  fraction).
- Empty and fuel fractions are class-based estimates from similar
  aircraft; the sizing iteration refines them.
- The iteration converges when successive estimates change by less
  than a tolerance.
- The breakdown (empty + fuel + payload) must balance the total.

## Workflow

1. Collect payload and class-based empty and fuel fractions.
2. Estimate W0 with tow_estimate.
3. Iterate and check convergence with tow_converged.
4. Balance the breakdown with weight_breakdown_ok.
5. Gate the sizing on the convergence verdict.

## Pitfalls

- Empty plus fuel fraction at or above 1.0.
- Claiming convergence after one estimate.
- Sizing to a payload of zero.

## Behavior contract (gate 3)

The estimate, convergence, and balance logic is exercised by the
gate 3 contract test: scripts/test_tow_estimation.py against
scripts/tow_estimation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_tow_estimation.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  sizing method is common conceptual design practice, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
