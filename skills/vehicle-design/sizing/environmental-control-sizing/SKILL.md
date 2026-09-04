---
name: environmental-control-sizing
description: "Use when you must size the environmental control system of a transport aircraft: compute the cabin ventilation fresh air flow from the occupant count and per-occupant rate, roll up the cabin heat load from occupants, solar, equipment and skin with a design margin, derive the pack cooling airflow from the heat load and the supply air temperature rise, take the pack airflow as the governing maximum of fresh and cooling flow, and build the cabin pressurization schedule that holds the design cabin pressure altitude until the design differential pressure binds, then clamps at constant differential as the cabin altitude rises. Produces fresh air flow, cabin heat load, pack airflow, cabin differential at cruise and cabin altitude under both regimes. Trigger: environmental control system sizing, ECS, cabin ventilation, fresh air flow, pack cooling airflow, cabin heat load, pressurization schedule, cabin pressure altitude, differential pressure limit."
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
  tags: [environmental-control-sizing, ecs-sizing, cabin-air-conditioning, cabin-heat-load, ventilation-flow, pack-cooling-flow, pressurization-schedule, cabin-altitude-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# Environmental Control System Sizing (vehicle-design/sizing/environmental-control-sizing)

Use when the task is sizing the environmental control system (ECS) of a
transport aircraft: the cabin ventilation fresh air flow from the
occupant count, the cabin heat load rollup (occupants, solar,
equipment, skin) with a design margin, the pack cooling airflow from
the heat load and the pack supply temperature rise, the pack airflow
verdict as the governing maximum of the fresh and cooling flows, and
the cabin pressurization schedule that holds the design cabin pressure
altitude until the design differential pressure binds and then flies
constant differential with the cabin altitude allowed to rise. This
leaf implements the sizing model in pure Python, stdlib only, with FAR
25 as the reference regulatory context. It pairs with
vehicle-design/sizing/ice-protection-sizing (the sibling aircraft-
subsystem sizing leaf; boundary: surface anti-icing bleed heating vs
cabin conditioning) and with cross-cutting/units-atmos/isa-atmosphere,
whose public two-layer atmosphere relation this leaf embeds internally
as private helpers only.

## Domain quick reference

- Fresh air flow: m_fresh = N * rate_per_occupant (default 0.25 kg/min
  per occupant, the 0.55 lb/min practice), converted to kg/s by /60.
- Cabin heat load: Q_occ = N * q_occ; Q_total = Q_occ + Q_solar +
  Q_equipment + Q_skin; Q_design = margin * Q_total (default margin
  1.1).
- Pack cooling flow: m_cool = Q_design / (cp * dT_supply), with default
  cp 1.005 kJ/(kg K) and default supply temperature rise 20 K. Pack
  flow is the governing maximum: m_pack = max(m_fresh, m_cool), and
  cooling_dominates records which side rules.
- Pressurization: p_amb = p_ISA(h_cruise); p_cab = p_ISA(h_cabin
  design). Differential dP = p_cab - p_amb. While dP <= dP_max the
  schedule holds the cabin altitude at the design value; when the
  required differential would exceed dP_max the clamp binds, p_cab =
  p_amb + dP_max * PSI, and the cabin altitude rises per the inverse
  ISA (defaults: 8000 ft design cabin altitude, 8.9 psi design
  differential).
- Internal two-layer ISA (private helpers, not a deliverable): p = P0
  (1 - L h / T0)^(G/(L R)) in the troposphere to 11 km, then an
  isothermal stratosphere at 216.65 K with scale height R T_strat / G.
  The public atmosphere leaf is cross-cutting/units-atmos/isa-atmosphere.
- Units: SI (Pa, kg/s, K, kW, m) with ft and psi accepted at the
  pressurization and altitude interfaces; PSI = 6894.757 Pa, FT =
  0.3048 m.
- FAR 25 frames the cabin conditioning and pressurization context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the occupant count and the per-occupant ventilation rate, and
   get the fresh air flow with fresh_air_flow (returns flow_kgmin and
   flow_kgs).
2. Roll up the heat sources with cabin_heat_load: occupant heat at
   q_occupant_kw each, plus solar, equipment and skin heat, closed by
   the design margin to give design_heat_kw.
3. Size the pack with pack_airflow on the design heat, cp and supply
   temperature rise; pass the fresh flow so the verdict reflects the
   governing maximum of ventilation and cooling (cooling_dominates).
4. Build the pressurization schedule with pressurization_schedule at
   the cruise altitude, design cabin altitude and design differential:
   read differential_limited to know whether the clamp binds, and
   cabin_altitude_ft for the resulting cabin altitude.
5. For a one-call rollup run ecs_summary with every input to get the
   combined dict of all outputs.
6. Confirm the deterministic checks with the contract test
   scripts/test_environmental_control_sizing.py.

## Worked example

Reference transport: 189 occupants at 0.25 kg/min each, 0.12
kW/occupant, solar 15 kW, equipment 12 kW, skin 8 kW, margin 1.1, cp
1.005 kJ/(kg K), supply temperature rise 20 K, design cabin altitude
8000 ft, design differential 8.9 psi, cruise 39000 ft then 50000 ft.

- fresh_air_flow(189): flow_kgmin = 47.25 kg/min, flow_kgs = 0.7875
  kg/s.
- cabin_heat_load(189, 0.12, 15, 12, 8): occupant_heat_kw = 22.68 kW,
  total_heat_kw = 57.68 kW, design_heat_kw = 63.448 kW.
- pack_airflow(63.448): cooling_flow_kgs = 3.156617 kg/s (63.448 /
  (1.005 * 20)), pack_flow_kgs = 3.156617 kg/s, cooling_dominates True.
- pressurization_schedule(39000): p_amb = 19.677 kPa, p_cab = 75.262
  kPa (the 8000 ft cabin), differential = 8.0619 psi, below the 8.9 psi
  limit so the schedule HOLDS: cabin_altitude_ft = 8000.0,
  differential_limited False.
- pressurization_schedule(50000): p_amb = 11.597 kPa; holding 8000 ft
  would need 9.234 psi, above the limit, so the clamp binds:
  differential_limited True, p_cab = 72.960 kPa (ambient + 8.9 psi),
  cabin_altitude_ft = 8809.9 ft, above the 8000 ft design value in the
  differential-limited regime.


## Pitfalls

- Sizing the pack on the fresh-air flow alone: the pack airflow is
  the governing MAXIMUM of the fresh ventilation flow and the
  cooling flow (3.1566 kg/s cooling dominates 0.7875 kg/s fresh in
  the worked example); picking the smaller flow starves the cabin
  heat load.
- Forgetting the design margin in the heat rollup: the design heat
  is margin * total (default 1.1), so an undiscounted total heat
  under-sizes the pack by the margin ratio.
- Reading the differential at cruise as the limit: at 39000 ft the
  8.0619 psi differential holds the 8000 ft cabin below the 8.9 psi
  clamp; only above the altitude where the clamp binds does the
  schedule leave the design cabin altitude (8809.9 ft at 50000 ft).
- Feeding a margin at or below 1: the margin must exceed 1 (the
  design heat carries reserve); a margin of 1.0 or less raises
  ValueError.
- Confusing which flow cools and which ventilates: fresh air
  (occupants at 0.25 kg/min each) is a ventilation requirement,
  while the pack cooling flow derives from the heat load and the
  supply temperature rise; the two answer different questions.
- Mixing pressure units at the interfaces: pressurization accepts ft
  and psi with internal conversions (PSI = 6894.757 Pa), so feeding
  Pa or m into those interfaces silently mis-sizes the schedule.
## Verification

- fresh_air_flow(189) returns 47.25 kg/min and 0.7875 kg/s; flow is
  linear in the occupant count.
- cabin_heat_load rolls the four sources into total_heat_kw and
  design_heat_kw = margin * total exactly; margin 1.5 scales the design
  heat by 1.5/1.1.
- pack_airflow(63.448) returns cooling_flow_kgs 3.156617 kg/s to 1e-6;
  with fresh_flow_kgs = 5.0 the pack flow equals the fresh flow and
  cooling_dominates is False.
- At 39000 ft the schedule holds 8000 ft exactly (differential 8.0619
  psi within 1e-4); at 50000 ft the clamp binds, cabin pressure equals
  ambient plus 8.9 * PSI within 1e-3 Pa and the cabin altitude lands in
  (8800, 8820) ft.
- The internal ISA is continuous at the tropopause and round-trips
  _h_isa_from_p(_p_isa(h)) == h to 1e-6 m in both regions.
- ValueError rejects: occupants <= 0, rate <= 0, margin <= 1, any
  negative heat input, design_heat_kw <= 0, cp <= 0, dT_supply_k <= 0,
  fresh_flow_kgs < 0, cruise_alt_ft < 0, cabin_alt_design_ft < 0 and
  dP_max_psi <= 0.
- Run the contract test offline: python3
  scripts/test_environmental_control_sizing.py (33 tests,
  deterministic).

## Related leaves

- vehicle-design/sizing/ice-protection-sizing: sibling aircraft-
  subsystem sizing leaf; boundary is surface anti-icing bleed heating
  versus cabin conditioning.
- vehicle-design/sizing/battery-sizing: the electric power subsystem
  sizing leaf for the power offtake context around the ECS loads.
- cross-cutting/units-atmos/isa-atmosphere: the public atmosphere leaf
  whose two-layer relation this leaf embeds internally.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_environmental_control_sizing.py

The test covers the worked-example magnitudes (47.25 kg/min fresh
flow, 63.448 kW design heat, 3.156617 kg/s pack cooling flow), the
pressurization hold at 39000 ft with differential 8.0619 psi and the
clamp at 50000 ft with cabin altitude 8809.9 ft, the regime boundary
crossing monotonicity, linearity in occupants, the margin scaling
ratio, internal ISA tropopause continuity and pressure round-trip in
both regions, ecs_summary rollup, run-to-run determinism and ValueError
rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25 frames the cabin
  conditioning and pressurization context; the sizing relations above
  are standard engineering methodology, summary-only per standards-map.
- compliance: STANDARDS-REF, gated: false.
