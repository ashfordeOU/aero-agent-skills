---
name: bypass-ratio-trade
description: "Use when you must size the bypass ratio design trade for a turbofan: compute the thrust split between the fan and core streams, the specific thrust, and the thrust-specific fuel consumption across candidate bypass ratios, and weigh them against the fan pressure ratio trend. Produces the per-stream mass flows and thrust shares, the TSFC versus bypass ratio trend, and the fan pressure ratio verdict that feed the engine trade study. Trigger: bypass ratio, bpr, specific thrust, tsfc, fan pressure ratio, turbofan trade."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: turbofan
  tags: [bypass-ratio-trade, bypass-ratio, bpr, specific-thrust, tsfc, fan-pressure-ratio, turbofan]
  version: 0.1.0
  author: AeroSkills
---

# Bypass Ratio Trade (propulsion/turbofan/bypass-ratio-trade)

Use when the task is the bypass ratio design trade for a turbofan:
the thrust split between the fan and core streams, the specific
thrust, and the TSFC across candidate bypass ratios at fixed core
conditions.

## Domain quick reference

Units are SI, with TSFC in g/(kN*s):

- Bypass ratio B = mdot_fan / mdot_core, the fan stream mass flow
  divided by the core stream mass flow; at fixed total mass flow the
  split is mdot_fan = B/(1+B) * mdot_total and mdot_core =
  mdot_total/(1+B).
- Net thrust per stream F = mdot*(Vj - V0), so total thrust is the
  fan share plus the core share; the fan jet velocity runs well
  below the core jet velocity.
- Specific thrust F/mdot_total in m/s (N per kg/s), a fan-size
  loading measure: high specific thrust means a small, highly loaded
  fan.
- Propulsive efficiency eta_p = 2/(1 + Vj/V0) for a stream at jet
  velocity Vj in flight at V0; a lower average jet velocity raises
  eta_p.
- TSFC = mdot_fuel/F with mdot_fuel = f * mdot_core (f = core
  fuel/air ratio), reported in g/(kN*s); at fixed core conditions a
  higher BPR lowers TSFC.
- The gain has a price: a larger fan, weight, and drag, and the fan
  pressure ratio rise with fan jet velocity cuts the efficiency
  gain. The trade sits in the FAR-33 engine design context.

## Workflow

1. Fix the core conditions: total mass flow, core and fan jet
   velocities, flight velocity, and the core fuel/air ratio.
2. Compute the stream split with thrust_split (mdot_fan, mdot_core,
   F_core, F_fan, F_total).
3. Normalize the thrust with specific_thrust (F_total / mdot_total).
4. Compute the fuel burn per unit thrust with tsfc in g/(kN*s).
5. Sweep the candidate bypass ratios with bpr_trend and read the
   thrust split, specific thrust, and TSFC trend.
6. Assess the fan with fan_pressure_ratio_note and fold the fan
   loading penalty into the trade verdict.

## Pitfalls

- Treating bypass ratio as a mass fraction: B is a ratio of two mass
  flows, and the fan share of total flow is B/(1+B), not B.
- Mixing units in TSFC: fuel flow in kg/s and thrust in N must be
  converted before quoting g/(kN*s).
- Forgetting the fixed-core caveat: the TSFC gain with BPR assumes
  constant core and fan jet velocities, while real fans grow
  diameter, weight, and drag as BPR rises.
- Ignoring the fan pressure ratio: a higher FPR raises fan jet
  velocity, which erodes the propulsive efficiency gain.
- Comparing specific thrust across engines with different total mass
  flows.

## Behavior contract (gate 3)

The thrust split, specific thrust, TSFC, and fan pressure ratio logic
is exercised by the gate 3 contract test:
scripts/test_bypass_ratio_trade_logic.py against
scripts/bypass_ratio_trade_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_bypass_ratio_trade_logic.py

## Compliance

- FAR-33 is referenced, not reproduced: US government work (public
  domain); the trade model is common propulsion methodology, summary
  only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
