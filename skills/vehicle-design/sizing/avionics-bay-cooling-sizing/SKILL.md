---
name: avionics-bay-cooling-sizing
description: "Use when you must size the cooling airflow for the avionics and equipment bay: rolling up the bay heat load from the LRU heat dissipations, sizing the bay cooling mass flow from the allowable cooling air temperature rise so the bay exhaust temperature stays at or below the LRU inlet air temperature limit, converting the mass flow to the volumetric flow and to cubic feet per minute, and checking each LRU case temperature against its case limit from the dissipated power and the case to air conductance. Produces the bay heat load, the required cooling mass flow and CFM, the exhaust temperature, the per LRU case temperature verdicts and the bay cooling PASS or FAIL verdict that gate the bay ventilation layout. Trigger: avionics bay cooling sizing, equipment bay cooling airflow, LRU heat dissipation, LRU case temperature check, cooling air temperature rise, case to air conductance."
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
  tags: [avionics-bay-cooling-sizing, equipment-bay-cooling, lru-heat-dissipation, cooling-airflow-sizing, lru-case-temperature]
  version: 0.1.0
  author: AeroSkills
---

# Avionics Bay Cooling Sizing (vehicle-design/sizing/avionics-bay-cooling-sizing)

Use when the task is sizing the cooling airflow for the avionics and
equipment bay of an aircraft: the LRU heat dissipations must be
carried away by a cooling air flow whose exhaust stays at or below the
LRU inlet-air temperature limit, and each LRU case must stay within
its case temperature limit. This leaf implements the standard bay
cooling model in pure Python, stdlib only: heat load rollup, cooling
mass flow from the allowable temperature rise, volumetric flow and
CFM conversion, and the per-LRU case temperature check. It pairs with
vehicle-design/sizing/environmental-control-sizing (the cabin
conditioning leaf, which stops at the conditioning pack flow and never
sizes bay airflow or LRU case temperatures) and with
avionics/do160/environmental-qualification (the LRU temperature test
specification side, which does not size airflow).

## Domain quick reference

- Bay heat load rollup: Q_total = sum of the LRU heat dissipations
  P_i, each LRU power in W. The bay is a collection of line-replaceable
  units (LRUs) inside the avionics/equipment bay.
- Cooling mass flow: m_dot = Q / (cp * (T_exhaust_limit - T_supply)),
  with cp = 1005 J/(kg K) for dry air. The exhaust temperature is sized
  to equal the LRU inlet-air temperature limit, giving the maximum
  cooling benefit without exceeding the LRU inlet limit.
- Volumetric flow: V_dot = m_dot / rho with rho = 1.2 kg/m3 near sea
  level; CFM = V_dot * 2118.88 (ft3/min per m3/s).
- LRU case temperature: T_case = T_inlet_air + P / (h A), where h A is
  the case-to-air conductance in W/K (default 12 W/K shared across the
  bay). A zero-power LRU sits exactly at the inlet air temperature.
- Case verdict: PASS when T_case <= T_limit, else FAIL; margin is
  T_limit - T_case (positive for PASS, negative for FAIL).
- Bay verdict: FAIL when any LRU case exceeds its limit or the mass
  flow is zero with positive heat, else PASS.
- Units are W, deg C, kg/s, m3/s, ft3/min (CFM), K.
- FAR 25.1309 frames the equipment installation context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Collect the LRU heat dissipations in W and roll up the bay heat
   load with bay_heat_load.
2. Fix the bay cooling supply temperature and the LRU inlet-air
   temperature limit, then size the cooling mass flow with
   cooling_mass_flow; the returned exhaust temperature equals the
   limit by construction.
3. Convert the mass flow to the volumetric flow and CFM with
   volumetric_flow.
4. For each LRU, compute the case temperature from the dissipated
   power and the case-to-air conductance with
   lru_case_temperature, then grade it against the LRU case limit
   with case_verdict.
5. Run the whole bay in one call with bay_cooling_summary to get the
   heat load, flows, exhaust temperature, per-LRU case temperatures,
   case verdicts and the bay PASS/FAIL verdict that gates the bay
   ventilation layout.
6. Confirm the deterministic checks with the contract test
   scripts/test_avionics_bay_cooling_sizing.py.

## Worked example

Reference bay with six LRUs dissipating 400, 350, 300, 550, 450 and
450 W (2500 W total), supply air at 25 C, LRU inlet-air limit 55 C,
air density 1.2 kg/m3, case-to-air conductance 12 W/K for every LRU,
and case limits [60, 60, 60, 65, 60, 60] C.

- Bay heat load: bay_heat_load returns total_w 2500.0 W.
- Cooling mass flow: cooling_mass_flow(2500.0, 25.0, 55.0) returns
  0.08292 kg/s (2500 / (1005 * 30)); exhaust_temp_c 55.0 C.
- Volumetric flow: volumetric_flow returns 0.06910 m3/s and 146.4 CFM.
- 300 W LRU: lru_case_temperature gives rise 300 / 12 = 25.0 K and
  case_temp_c 25 + 25 = 50.0 C, versus the 60 C limit a PASS with
  margin 10.0 K.
- 550 W LRU: rise 550 / 12 = 45.83 K, case_temp_c 70.83 C, versus the
  65 C limit a FAIL with margin -5.83 K; this is the undersized heat
  path the check exists to catch.
- Bay summary: bay_cooling_summary over the six LRUs reports the
  2500.0 W load, 0.08292 kg/s, 146.4 CFM, exhaust 55.0 C, case temps
  {0: 58.33, 1: 54.17, 2: 50.0, 3: 70.83, 4: 62.5, 5: 62.5} C with
  verdicts PASS, PASS, PASS, FAIL, FAIL, FAIL and a bay verdict FAIL,
  so the bay layout must be revised (heat path or limits) before
  release. Re-running the summary with the 550 W LRU reduced to 350 W
  gives an all-PASS set and a bay verdict PASS.

## Verification

- Confirm bay_heat_load([400, 350, 300, 550, 450, 450]) returns total
  2500.0 W.
- Confirm cooling_mass_flow(2500.0, 25.0, 55.0) returns 0.08292 kg/s
  (inside the independently verified 0.08 to 0.09 kg/s bound) and that
  zero heat returns a 0.0 kg/s flow.
- Confirm volumetric_flow converts the reference flow to 0.06910 m3/s
  and 146.4 CFM, and that 1 kg/s at 1.2 kg/m3 gives 0.8333 m3/s and
  1765.7 CFM.
- Confirm the identities: doubling the allowable temperature rise at
  fixed heat halves the mass flow, doubling the heat doubles the flow,
  doubling the case-to-air conductance halves the case rise, and a
  zero-power LRU sits at the inlet air temperature.
- Confirm the 300 W LRU case is 50.0 C (PASS, margin 10.0 K) and the
  550 W LRU case is 70.83 C (FAIL, margin -5.83 K), and that the bay
  verdict is FAIL when any LRU fails and PASS only when every LRU
  passes.
- Confirm every non-physical input raises ValueError: empty LRU list,
  negative power, temperature difference not positive (limit at or
  below supply), density at or below zero, conductance at or below
  zero, and a case limit below absolute zero.
- Run the contract test offline: python3
  scripts/test_avionics_bay_cooling_sizing.py (32 tests,
  deterministic).

## Related leaves

- vehicle-design/sizing/environmental-control-sizing: the cabin
  conditioning leaf; its equipment heat line sits inside the cabin
  load and it stops at the air conditioning pack, it does not size
  bay airflow or LRU case temperatures.
- vehicle-design/sizing/ice-protection-sizing: surface thermal ice
  protection for the aerodynamic surfaces, a different thermal sizing
  problem.
- avionics/do160/environmental-qualification: the test specification
  side of LRU temperature qualification, not airflow sizing.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_avionics_bay_cooling_sizing.py

The test covers the reference bay sizing contract (2500 W heat load,
0.08292 kg/s mass flow, 146.4 CFM, 55.0 C exhaust, 300 W LRU case
50.0 C PASS, 550 W LRU case 70.83 C FAIL and the FAIL bay verdict),
the flow and case scaling identities, the volumetric conversion
references, the convenience dict keys, determinism and the ValueError
rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25.1309 is the equipment
  installation context (case of an avionics bay in an aircraft); the
  bay cooling relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
