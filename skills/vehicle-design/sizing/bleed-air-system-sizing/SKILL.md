---
name: bleed-air-system-sizing
description: "Use when you must size the aircraft bleed air system: roll up the total bleed offtake mass flow from the fixed consumer demands (ECS pack flows, wing anti-ice flow, pressurization trim flow), split the offtake per engine, compute the bleed thermal budget the precooler must reject between the bleed supply temperature and the consumer supply temperature, and size each engine bleed duct diameter from compressible pipe flow at a fixed design Mach number. Produces the total and per-engine offtake mass flow, the per-engine and total thermal budget, the duct flow area and diameter, and a fit verdict against the nominal duct diameter limit. Trigger: bleed air sizing, bleed offtake mass flow, per engine offtake, bleed duct diameter, duct Mach sizing, precooler heat load, bleed thermal budget, pneumatic bleed manifold, bleed supply temperature."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [bleed-air-system-sizing, bleed-offtake-mass-flow, bleed-duct-diameter, bleed-thermal-budget, pneumatic-bleed-manifold, precooler-heat-load]
  version: 0.1.0
  author: AeroSkills
---

# Bleed Air System Sizing (vehicle-design/sizing/bleed-air-system-sizing)

Use when the task is sizing the aircraft pneumatic bleed distribution
system of a twin-engine transport at the conceptual level: the bleed
air bled from the engine offtakes is distributed to the ECS packs,
the wing anti-ice system and the pressurization trim through a bleed
manifold and per-engine ducts. This leaf rolls up the total bleed
offtake mass flow from the fixed consumer demands, splits the offtake
evenly across the two engines, computes the thermal budget the
precooler and conditioning system must reject in cooling the bleed
from the offtake supply temperature to the consumer supply
temperature, and sizes each engine bleed duct diameter from
compressible pipe flow at a fixed design Mach number. The pack flows,
the wing anti-ice flow and the trim flow are INPUTS here (values
computed by the sibling environmental-control and ice-protection
leaves); nothing downstream of the offtakes is recomputed. The module
implements the model in pure Python, stdlib only. It pairs with
vehicle-design/sizing/environmental-control-sizing (pack flow demand
and pressurization trim demand) and
vehicle-design/sizing/ice-protection-sizing (the anti-ice bleed
demand). The regulatory context is FAR 25.863 bleed and flammable
fluid plumbing, referenced but not reproduced.

## Domain quick reference

- Bleed offtake rollup: m_total = sum(pack flows) + m_anti_ice +
  m_trim; with two engines the per-engine offtake is m_eng =
  m_total / 2. The consumer flows are fixed demands computed by the
  sibling leaves, so the rollup is pure summation.
- Bleed thermal budget: q = m * CP_AIR * (T_bleed - T_supply), the
  sensible heat the precooler and conditioning system must reject to
  cool the bleed from the engine offtake total temperature T_bleed to
  the consumer supply temperature T_supply (288 K sea level standard
  day by default). CP_AIR = 1005.0 J/(kg K).
- Duct flow state at the fixed design Mach number M: density rho =
  p / (R_AIR * T_bleed), sonic speed a = sqrt(GAMMA_AIR * R_AIR *
  T_bleed), duct velocity V = M * a, with R_AIR = 287.0 J/(kg K) and
  GAMMA_AIR = 1.4.
- Duct geometry: flow area A = m / (rho * V), diameter D =
  sqrt(4 * A / pi). The duct is sized at the per-engine offtake flow
  at the nominal duct static pressure (350 kPa default) and the fixed
  design Mach number (0.30 default).
- Fit verdict: PASS when the sized duct diameter is at or below the
  nominal duct diameter limit the installation can accommodate, else
  FAIL.
- Units are SI throughout: kg/s, K, Pa, m, m/s, W.
- FAR 25.863 frames the bleed plumbing safety context (flammable
  fluid lines); the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Collect the fixed consumer bleed demands: each ECS pack flow in
   kg/s (environmental-control-sizing output), the wing anti-ice bleed
   flow in kg/s (ice-protection-sizing output), and the pressurization
   trim flow in kg/s.
2. Roll the offtake up with total_bleed_offtake(pack_flows_kg_s,
   anti_ice_kg_s, trim_kg_s): the total and the per-engine offtake
   (total split over the two engines).
3. Fix the bleed supply temperature T_bleed (engine offtake total
   temperature) and the consumer supply temperature T_supply.
4. Compute the precooler rejection load per engine and total with
   bleed_thermal_budget on the per-engine and total offtake flows.
5. Size each engine duct with bleed_duct_diameter at the per-engine
   flow, the bleed temperature and the duct static pressure; the
   design Mach number and pressure default to the module constants.
6. Judge the architecture with bleed_system_summary: pass the
   consumer flows, T_bleed and the nominal duct diameter limit; read
   the total and per-engine offtake, the thermal budgets, the duct
   area and diameter, and the PASS/FAIL fit verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_bleed_air_system_sizing.py.

## Worked example

Reference twin-engine transport: two ECS packs at 0.80 kg/s each,
wing anti-ice 0.0179 kg/s (ice-protection-sizing anchor value),
pressurization trim 0.05 kg/s, bleed supply 450 K, duct pressure
350 kPa, design duct Mach 0.30, nominal duct diameter limit 0.06 m.

- Offtake rollup: total = 2 * 0.80 + 0.0179 + 0.05 = 1.6679 kg/s;
  per-engine = 0.83395 kg/s (total_bleed_offtake real output
  1.6679 kg/s total, 0.83395 kg/s per engine).
- Per-engine thermal budget: q = 0.83395 * 1005 * (450 - 288) =
  135775.4 W (135.8 kW class); total = 1.6679 * 1005 * 162 =
  271550.8 W (271.6 kW class, 271551 W rounded). The total is exactly
  twice the per-engine value.
- Duct flow state at 350 kPa and 450 K: rho = 350000 / (287 * 450) =
  2.7100 kg/m3; a = sqrt(1.4 * 287 * 450) = 425.22 m/s; V = 0.30 *
  425.22 = 127.57 m/s (module outputs 2.7100 kg/m3 and 127.57 m/s).
- Duct geometry at the per-engine flow: A = 0.83395 / (2.7100 *
  127.57) = 0.002412 m2; D = sqrt(4 * 0.002412 / pi) = 0.0554 m
  (55.4 mm, module output 0.05542 m).
- Fit verdict at the 0.06 m limit: PASS (0.0554 <= 0.06). At a 0.05 m
  limit the verdict flips to FAIL.

## Pitfalls

- Feeding total flow into the duct sizing: the duct is a per-engine
  component sized at the per-engine offtake 0.83395 kg/s, not at the
  total 1.6679 kg/s; sizing at the total flow overstates the diameter
  by sqrt(2).
- Recomputing consumer demands: the pack flows, anti-ice flow and
  trim flow are fixed inputs produced by the sibling
  environmental-control and ice-protection leaves; this leaf rolls
  them up and never recomputes them from heat loads or icing flux.
- Treating T_bleed as the duct static temperature: the duct flow
  state uses the bleed supply total temperature for the density and
  sonic speed at the stated static pressure, consistent with the
  fixed design Mach number model.
- Confusing the thermal budget with a heat exchanger size: q is the
  precooler rejection load only; it sets the conditioning duty, not
  the pack flow demand or any pressurization quantity.
- Sizing at a non-fixed Mach number: the duct Mach number is a fixed
  design parameter (0.30 default); lowering it at fixed flow and
  state enlarges the required area.

## Verification

- Confirm total_bleed_offtake([0.80, 0.80], 0.0179, 0.05) returns a
  total of 1.6679 kg/s with 2 * per_engine == total within 1e-9.
- Confirm bleed_thermal_budget(1.6679, 450) returns 271550.8 W, that
  doubling the mass flow doubles the budget, and that the dict keys
  are exactly q_w, mass_kg_s, t_bleed_k, t_supply_k.
- Confirm bleed_duct_diameter(0.83395, 450) returns a diameter of
  0.0554 m within 1e-3 and that the area round-trips through
  A = pi * D^2 / 4 within 1e-9.
- Confirm bleed_system_summary verdicts PASS at the 0.06 m limit and
  FAIL at the 0.05 m limit.
- Confirm every negative flow, every non-positive mass, temperature
  or pressure, every Mach number outside (0, 1) and every bleed
  temperature at or below the supply temperature raises ValueError.
- Confirm identical inputs give identical outputs.
- Run the contract test offline: python3
  scripts/test_bleed_air_system_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/environmental-control-sizing: the ECS pack
  flow demand and pressurization trim demand that feed this rollup.
- vehicle-design/sizing/ice-protection-sizing: the wing anti-ice
  bleed demand input (0.0179 kg/s anchor value).
- vehicle-design/sizing/engine-sizing: main-engine performance sizing
  that consumes bleed for its thrust bookkeeping.
- vehicle-design/sizing/apu-fuel-burn-sizing: the APU-side offtake
  and fuel accounting for the auxiliary power installation.
- propulsion/engine-airframe/engine-airframe-integration: bleed as a
  thrust-loss term at the engine-airframe interface.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_bleed_air_system_sizing.py

The test covers the twin-engine transport worked example (offtake
1.6679 kg/s total, per-engine budget 135775.4 W, duct diameter
0.0554 m inside the 1e-3 bound), the offtake identity
2 * per_engine == total, the duct area round trip through
A = pi * D^2 / 4, thermal budget doubling with mass flow, the duct
state relations (rho = p/(R T), V = M * a), the summary fit verdicts
at the 0.06 m and 0.05 m limits, dict key contracts for every
function, output determinism, and ValueError rejection of negative
flows, non-positive mass, temperature and pressure, Mach numbers
outside (0, 1), and bleed temperatures at or below the supply
temperature.

## Compliance

- Standards referenced, not reproduced: FAR 25.863 (bleed and other
  flammable fluid plumbing context) is named for context only; the
  sizing relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
