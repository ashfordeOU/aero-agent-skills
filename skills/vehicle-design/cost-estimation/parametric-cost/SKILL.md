---
name: parametric-cost
description: "Use when you must compute parametric cost estimates for an aircraft development and production program: derive the learning curve exponent from a learning curve percentage, apply the learning curve to get unit cost and cumulative production cost, estimate development cost from airframe mass with a weight-based cost estimating relationship, and roll the recurring and non-recurring pieces into a total program cost. Produces the unit cost, the cumulative learning factor, the production total, and the program total that gate the program cost assessment. Trigger: parametric cost, cost estimating relationship, cer, learning curve, unit cost, development cost, program cost, cumulative average."
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
  subdomain: cost-estimation
  tags: [parametric-cost, cost-estimation, cost-estimating-relationship, cer, learning-curve, unit-cost, development-cost, program-cost, cumulative-average]
  version: 0.1.0
  author: Aero Agent Skills
---

# Parametric Cost Estimation (vehicle-design/cost-estimation/parametric-cost)

Use when the task is parametric cost estimation for an aircraft
development and production program: learning curve exponents, unit
costs, cumulative production totals, weight-based development cost
estimating relationships, and the total program cost rollup.

## Domain quick reference

- All costs are in program currency units, airframe mass in kg, and
  the learning curve lc is dimensionless (0.85 typical, 80-95% band).
- Learning curve exponent: s = ln(lc) / ln(2). For lc = 0.85, s =
  -0.234465; each doubling of the unit number drops the unit cost to
  lc times the previous doubling.
- Unit cost: c_n = c1 * n**s, with c1 the first-unit cost and n the
  unit number (n >= 1). Defining property: the second unit costs lc
  times the first, c2 = c1 * lc.
- Cumulative learning factor: F(n) = n**(s+1) / (s+1), the closed-form
  cumulative average approximation; production total = c1 * F(n).
- Development cost (weight-based CER): c_dev = a * w**b, with a a
  coefficient, w the airframe mass in kg, and b the exponent (b near
  0.6 for aircraft airframe development).
- Program total = production total + development cost: recurring
  production cost plus the non-recurring development cost.
- FAR-25 and CS-25 are referenced as program context only; the CERs
  and the learning curve are common program cost estimating practice,
  not regulation.

## Workflow

1. Set the program inputs: first-unit cost c1, unit number n, learning
   curve lc, and the development CER coefficient a, mass w, and
   exponent b.
2. Compute the learning curve exponent with learning_curve_exponent;
   it guards lc against out-of-band values.
3. Compute the unit cost of unit n with unit_cost.
4. Compute the cumulative learning factor with
   cumulative_learning_factor.
5. Compute the development cost with development_cost.
6. Roll everything up with total_program_cost; the returned dict
   carries unit_n, cumulative_factor, production_total, and
   program_total.

## Pitfalls

- Passing lc outside (0, 1): lc >= 1 gives a flat or rising curve and
  lc <= 0 is meaningless; both raise ValueError instead of returning a
  wrong exponent.
- Using the unit cost as the production total: the cumulative factor
  sums the learning curve over all units up to n, and c_n alone
  understates the fleet cost.
- Confusing n with the fleet size: n is the unit number of the last
  unit in the production run, not the number of aircraft if the run
  starts elsewhere.
- Mixing development CER units: w must be in kg and a scaled to the
  program currency unit; a per-kg coefficient applied to a mass in lb
  shifts the estimate by orders of magnitude.
- Treating the closed-form cumulative factor as exact: F(n) =
  n**(s+1)/(s+1) is the standard approximation for n >= 1, not the
  exact discrete sum.
- Passing n < 1 to cumulative_learning_factor: the module raises
  ValueError instead of guessing.

## Behavior contract (gate 3)

The learning curve exponent, unit cost, cumulative learning factor,
weight-based development cost, and total program cost rollup are
exercised by the gate 3 contract test:
scripts/test_parametric_cost.py against
scripts/parametric_cost_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_parametric_cost.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the CERs and the
  learning curve are common program cost estimating methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
