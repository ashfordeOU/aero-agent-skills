---
name: life-cycle-cost
description: "Use when you must estimate the total life-cycle-cost of an aircraft program: structure the estimate into the RDT&E, production, operations and support, and disposal phases, apply a power-law CER to a phase cost driver, apply the learning curve to get the Nth unit cost and the cumulative average unit cost, escalate costs for inflation, discount future year costs to present value at the discount rate, and bound the result with an uncertainty range. Produces the phase costs, the present value of the operations and support stream and of the disposal cost, and the total life-cycle cost that gates the affordability assessment. Trigger: life cycle cost, present value, discount rate, operations and support, disposal cost, rdt and e, cost driver, uncertainty, inflation."
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
  tags: [life-cycle-cost, cost-estimation, present-value, discount-rate, operations-and-support, disposal-cost, inflation, uncertainty, cost-driver]
  version: 0.1.0
  author: AeroSkills
---

# Life-Cycle Cost Estimation (vehicle-design/cost-estimation/life-cycle-cost)

Use when the task is a full life-cycle cost (LCC) estimate for an
aircraft program: the RDT&E, production, operations and support, and
disposal phases, present value discounting of future year dollars,
inflation escalation, and an uncertainty bound on the total.

## Domain quick reference

- LCC phases: RDT&E (non-recurring: design, prototypes, test
  articles), production (recurring unit costs under the learning
  curve), operations and support (O&S: crew, fuel, maintenance,
  spares, training over the service life), disposal (end of life:
  demilitarization, recycling, site remediation). For a long-lived
  program O&S dominates; a 20 to 30 year service life typically puts
  50 to 70% of the total in O&S, with RDT&E around 10 to 20% and
  production 20 to 30%. The split is program specific, not a rule.
- Cost estimating relationship (CER): cost = a * x**b, a power law
  with driver x (mass, flight hours, thrust, quantity). The
  coefficients come from historical program data; a CER is valid only
  inside the driver range of its source data. Extrapolation is the
  top source of CER error.
- Learning curve: c_n = c1 * n**s with s = ln(lc) / ln(2), lc the
  learning curve percentage (0.80 to 0.95 for airframe production,
  0.85 typical). Each doubling of the unit number drops the unit cost
  to lc times the previous value, so c2 = c1 * lc.
- Cumulative average unit cost: the exact discrete average of the
  first n unit costs, sum(c_k, k=1..n) / n. The closed form
  n**(s+1)/(s+1) used by parametric-cost is an approximation of the
  cumulative total, not the exact discrete sum.
- Present value: pv = fv / (1+i)**n for a single future amount; for a
  uniform annual series, pv = a * (1 - (1+i)**-n) / i. The discount
  rate i is real (inflation removed): 2 to 3% typical for government
  programs, higher for commercial programs.
- Inflation: escalate a then-year cost with (1+f)**years or deflate
  with a base-year index ratio. Real versus nominal: the subtraction
  r = n - f is an approximation; the exact relation is (1+r) =
  (1+n)/(1+f).
- Cost drivers: airframe mass, complexity and technology readiness,
  production rate and quantity, flight hours and cycles, fuel price,
  labor rates, fleet size, support concept, reliability (MTBF) and
  maintainability (MTTR). Weight and complexity drive RDT&E and
  production; flight hours and cycles drive O&S.
- Uncertainty: an early conceptual LCC point estimate carries wide
  bands, typically +-20 to 30%. Report a range, run sensitivity on
  the dominant drivers, and use Monte Carlo for confidence levels. A
  bare point estimate without a range is a misleading deliverable.
- FAR-25 and CS-25 are program context only; the CERs, learning
  curve, and discounting are common cost estimating methodology, not
  regulation.

## Workflow

1. Set the program inputs: phase costs or CER drivers, learning curve
   lc, discount rate i, service life years, and inflation rate f.
2. Estimate each phase cost. Apply the power-law CER with cer_cost,
   or pass the phase estimates directly.
3. Apply the learning curve with unit_cost for the Nth unit and
   cumulative_average_unit_cost for the average over the production
   run.
4. Escalate then-year costs with escalated_cost and discount future
   year cash flows with present_value and annuity_present_value.
5. Sum the phases with lcc_total; the returned dict carries the
   discounted O&S stream, discounted disposal, and the total LCC.
6. Bound the estimate with uncertainty_range and identify the
   dominant cost drivers from the phase shares.

## Pitfalls

- Mixing real and nominal rates: discount nominal cash flows with a
  nominal rate and real cash flows with a real rate; the two never
  mix in one calculation.
- Discounting O&S as a lump sum instead of a series: O&S is an
  annual stream, so it enters as an annuity, not as a single future
  amount.
- Extrapolating a CER beyond its data range: the power law has no
  built-in validity limit; the estimate silently leaves the region
  the coefficients were fit to.
- Treating the closed-form cumulative factor as exact: the discrete
  sum over units 1..n is the exact average; n**(s+1)/(s+1) is the
  approximation documented in parametric-cost.
- Forgetting disposal: disposal is small but mandatory in a full
  LCC; omitting it understates the total and misses end-of-life
  obligations.
- Reporting the point estimate alone: the uncertainty band and the
  dominant drivers matter as much as the total; a single number
  overstates confidence.
- Passing negative or zero inputs; the module raises ValueError
  instead of returning a nonsense cost.

## Behavior contract (gate 3)

The phase CER, Nth unit cost, cumulative average unit cost, present
value, annuity, inflation escalation, LCC rollup, and uncertainty
range are exercised by the gate 3 contract test:
scripts/test_life_cycle_cost.py against
scripts/life_cycle_cost_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_life_cycle_cost.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the CERs,
  learning curve, and discounting are common cost estimating
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
