---
name: performance-computation
description: "Use when the task is FMS performance computation, ECON speed selection, cost index, fuel versus time trade, step-climb logic, or top of descent for a flight management system. Compute flight management system performance values: derive the cost index from time and fuel costs, select the ECON cruise Mach that minimizes total fuel and time cost, quantify the fuel-for-time trade between candidate cruise speeds, evaluate step-climb benefit between flight levels, and compute the VNAV top of descent with wind-corrected descent distance for the vertical profile. Produces the ECON Mach and true airspeed, the fuel and time per leg, the step-climb verdict, and the top-of-descent distance from cruise altitude to the arrival constraint. Trigger: cost index, econ cruise speed, fuel time trade, step climb, top of descent, vnav, fms performance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: flight-management
  tags: [performance-computation, cost-index, econ-cruise-speed, fuel-time-trade, step-climb, top-of-descent, vnav, flight-management-system, fms]
  version: 0.1.0
  author: Aero Agent Skills
---

# Performance Computation (avionics/flight-management/performance-computation)

Use when the task is flight management system performance computation:
cost index and ECON cruise speed selection, the fuel and time trade
between candidate speeds, step-climb logic between flight levels, and
the VNAV top of descent for the vertical profile. This leaf is the
performance sibling of avionics/flight-management/flight-planning
(lateral route geometry) and avionics/flight-management/vertical-navigation
(descent path checking); together they cover the FMS performance and
guidance computations that run under the DO-178C airborne software
lifecycle discipline.

## Domain quick reference

- Cost index (CI) is the ratio of time cost per hour to fuel cost per
  kilogram, in kg/h. A high CI means time is expensive, so the FMS
  flies faster; a low CI means fuel dominates, so the FMS flies
  slower. CI = 0 selects the pure fuel-optimal (max range) speed.
- ECON cruise speed is the Mach number that minimizes total cost per
  nautical mile: cruise fuel per nm plus CI times time per nm. The
  optimum sits where the marginal fuel cost of flying faster balances
  the marginal time saving, and is clamped to the aircraft Mach
  envelope (M_MIN to M_MMO).
- Cruise fuel per nm comes from a simplified three-term drag model
  (parasite, induced, compressibility) over the ISA atmosphere; the
  induced term grows with weight squared, so heavier aircraft select
  a faster ECON Mach.
- Fuel and time trade: for a fixed leg, a faster speed saves time but
  usually burns more fuel above the max range speed; the net
  fuel-equivalent cost change is extra fuel minus CI times time
  saved, and is near zero at the ECON speed.
- Step-climb logic trades the extra climb fuel against the lower
  cruise fuel at a higher flight level; the step is advised when the
  cruise saving exceeds the climb penalty plus a margin.
- VNAV top of descent (TOD) is the distance from the descent start to
  the target altitude: altitude to lose divided by the descent
  gradient (about 318 ft/nm for a 3 degree flight path angle),
  corrected for wind by scaling by TAS over groundspeed. A headwind
  lengthens the descent distance, a tailwind shortens it.
- Typical FMS functions in this leaf: cost index derivation, ECON
  Mach selection, cruise speed trade, step-climb benefit, and TOD
  distance with wind correction.

## Workflow

1. Derive the cost index with cost_index from the time cost per hour
   and fuel cost per kg.
2. Select the ECON cruise Mach with econ_mach_from_cost_index for the
   weight and cruise altitude; inspect the detail with
   econ_speed_summary (Mach, TAS, fuel per nm, time per nm, total
   cost per nm).
3. Compare candidate speeds over a leg with fuel_time_trade to get
   the extra fuel, time saved, and net fuel-equivalent cost change.
4. Evaluate a step climb between flight levels with
   step_climb_benefit; step when step_advised is true.
5. Compute the vertical profile descent with top_of_descent to get
   the wind-corrected TOD distance and gradient.
6. Confirm the deterministic checks with the contract test
   scripts/test_performance_computation.py.

## ECON cruise speed model

The cruise fuel burn per nautical mile is modeled as

  fuel_per_nm(V) = SFC * nm * (c1 * V + c2 / V^3 + c3 * V^7)

with V in m/s: the c1 term is parasite drag (linear in speed), the c2
term is induced drag (falls with V^3, proportional to weight squared
over air density), and the c3 term is transonic drag rise (grows with
V^7). The coefficients come from wing area, drag coefficients, span
efficiency, aspect ratio, thrust specific fuel consumption, and ISA
density; they are order-of-magnitude for a mid-size transport and must
be calibrated per aircraft against the FMS performance manual. No
proprietary performance tables are reproduced.

The ECON speed minimizes total cost per nm:

  C(V) = fuel_per_nm(V) + CI * time_per_nm(V)

where time_per_nm is hours per nautical mile. The optimum is found
deterministically by Newton iteration (stdlib only) and clamped into
[M_MIN, M_MMO]. At CI = 0 the optimum collapses to the max range speed
max_range_speed_kts, where fuel per nm is minimum.

## Worked example

A mid-size transport at 70,000 kg, cruise FL350. Time cost is 150
currency units per hour, fuel cost 3 currency units per kg:

- CI = 150 / 3 = 50 kg/h.
- ECON: econ_mach_from_cost_index(50, 70000, 35000) gives Mach 0.8041,
  TAS 463.5 kts, 5.759 kg fuel per nm. At CI = 0 the speed drops to
  Mach 0.8017 (the max range speed); at CI = 999 it clamps at the
  envelope limit Mach 0.82.
- Trade over a 1000 nm leg at Mach 0.80 versus Mach 0.82:
  fuel_time_trade(50, 70000, 35000, 0.80, 0.82, 1000) reports 9.3 kg
  extra fuel and 0.053 h saved, a net cost increase of 6.6 kg
  fuel-equivalent at this CI, so Mach 0.82 is slightly faster than
  economic here; at the ECON speed the trade against either neighbor
  is within 1 kg per 1000 nm.
- Step climb FL350 to FL390 over a 2000 nm leg:
  step_climb_benefit(70000, 35000, 39000, 2000) reports cruise fuel
  11,517 kg at FL350 versus 11,123 kg at FL390, a 280 kg climb
  penalty, and a net benefit of +114 kg, so the step is advised. Over
  an 800 nm leg the benefit is negative and the step is not advised.
- Top of descent FL350 to FL100 at 3 degrees flight path angle, TAS
  450 kts, 60 kt headwind: top_of_descent(35000, 10000, 3.0, 450, 60)
  gives 25,000 ft to lose, gradient 318.4 ft/nm, air distance 78.5
  nm, and wind-corrected ground distance 90.6 nm (the headwind
  lengthens the descent).

## Pitfalls

- Inverting the cost index: CI is time cost per hour divided by fuel
  cost per kg (150 / 3 = 50 kg/h) - a high CI means time is expensive
  and the FMS flies faster, a low CI flies slower, and CI = 0 selects
  the pure fuel-optimal max range speed; swap the ratio and every
  ECON selection points the wrong way.
- Trusting the raw optimum outside the Mach envelope: the ECON speed
  is clamped into [M_MIN, M_MMO], so a very high CI (999) resolves to
  the envelope limit Mach 0.82, not to the unconstrained Newton
  optimum - report the clamped Mach for guidance.
- Judging a speed change on time saved alone: the trade is extra fuel
  minus CI times time saved (Mach 0.82 over 0.80 burns 9.3 kg extra
  for 0.053 h, a net +6.6 kg cost at CI 50), so "faster saves time"
  is not "faster is economic" above the max range speed.
- Advising a step climb without the leg length: step_climb_benefit
  trades the climb penalty against cruise savings over the leg, so
  the step is advised at 2000 nm (+114 kg) but not at 800 nm - a
  step that pays over a long leg can lose money on a short one.
- Dropping the wind correction at TOD: the descent distance scales by
  TAS over groundspeed, so a 60 kt headwind stretches the 78.5 nm air
  distance to a 90.6 nm ground distance - an uncorrected TOD puts the
  aircraft high at the constraint.
- Treating the drag model coefficients as aircraft data: the c1/c2/c3
  terms are order-of-magnitude for a mid-size transport and must be
  calibrated per aircraft against the FMS performance manual - no
  proprietary performance table is reproduced in this leaf.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_performance_computation.py

The test covers the cost index definition and edge cases, ECON Mach
monotonicity in CI, the CI = 0 max range selection, envelope clamps,
weight and altitude effects, fuel and time trade invariants, ECON cost
neutrality, step-climb verdicts and validation, TOD geometry with
wind correction, ISA helper sanity, and invalid-input edge cases.

## Related leaves

- avionics/flight-management/flight-planning: lateral route geometry,
  leg distances, and vertical constraint checks for the plan.
- avionics/flight-management/vertical-navigation: descent path
  gradient and flight path angle, altitude constraint checks.
- The avionics pack router skills/avionics/SKILL.md dispatches to this
  leaf for FMS performance queries.

## Compliance

- Standards referenced, not reproduced: DO-178C text is proprietary
  (RTCA); the performance methodology here is common knowledge,
  summary-only per standards-map.yaml and brief 06. FAR-25 is the
  public airworthiness context for transport category performance.
- compliance: STANDARDS-REF, gated: false.
