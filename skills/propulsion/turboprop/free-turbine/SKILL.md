---
name: free-turbine
description: "Size and match a free-turbine turboprop or turboshaft power section: compute the power-turbine exit temperature and shaft power from the gas generator exhaust state (mass flow, inlet temperature, expansion ratio, polytropic efficiency), convert to torque at the power-turbine speed, blade speed from the mean diameter, reduction gearbox ratio to the propeller or rotor, specific fuel consumption, and the flow function that the turbine nozzle must swallow for spool compatibility. Produces the free-turbine matching assessment dict that gates the power section selection. Use when the task is free-turbine sizing, power-turbine matching, turboprop shaft power, or turboshaft cycle estimates. Trigger: free turbine, power turbine, turboprop, turboshaft, gas generator, shaft power, spool matching."
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
  subdomain: turboprop
  tags: [free-turbine, power-turbine, turboprop, turboshaft, gas-generator, spool-matching]
  version: 0.1.0
  author: Aero Agent Skills
---

# Free Turbine (propulsion/turboprop/free-turbine)

Use when the task is free-turbine turboprop or turboshaft power
section sizing: gas generator to power turbine matching, shaft power,
and reduction gearbox selection.

## Domain quick reference

- A free-turbine layout has two mechanically independent shafts: the
  gas generator (compressor plus its turbine) and the power turbine,
  connected only aerodynamically through the exhaust stream. The power
  turbine converts the gas generator exhaust enthalpy drop into shaft
  power and drives the propeller or rotor through a reduction gearbox.
- Power-turbine exit temperature follows the expansion:

  t06 = t05 * (1 - eta_pt * (1 - pr**((1-gamma)/gamma)))

  with t05 the power-turbine inlet (gas generator exhaust) temperature
  in K, pr = p5/p6 the expansion ratio (> 1), eta_pt the polytropic
  efficiency in (0, 1], and gamma air-standard 1.4.
- Shaft power: P = m_dot * cp * (t05 - t06) with m_dot in kg/s and cp
  in J/(kg K); torque Q = P / omega with omega = 2 * pi * rpm / 60.
- Blade speed at the mean diameter: u = pi * diameter * rpm / 60 in
  m/s. Gear ratio G = n_pt / n_prop, normally well above 1 because the
  free turbine runs fast for blade aerodynamics.
- Specific fuel consumption: sfc = mf * 3600 * 1000 / P in kg/(kW h).
- Flow function FF = m_dot * sqrt(t05) / p5 in kg sqrt(K) / Pa is the
  corrected-flow compatibility parameter: the power-turbine nozzle
  must swallow the gas generator exhaust at every operating point.

## Workflow

1. Establish the gas generator exhaust state: m_dot, t05, p5, and the
   chosen expansion ratio and polytropic efficiency.
2. Compute t06 and the shaft power with power_turbine_power.
3. Convert to torque at the power-turbine speed with shaft_torque and
   the blade speed with blade_speed from the mean diameter.
4. Select the reduction gearbox with gear_ratio to the propeller or
   rotor speed.
5. Close the loop with specific_fuel_consumption and flow_function;
   use free_turbine_assessment for the full dict.

## Pitfalls

- Using a pressure ratio below 1: the expansion ratio must exceed 1
  (pressure falls across the turbine).
- Confusing the two shafts: the power turbine speed and the propeller
  speed differ by the gear ratio; torque and SFC must be evaluated at
  the shaft that carries them.
- Ignoring the flow function: the gas generator and power turbine only
  stay matched if the nozzle swallows the exhaust at every point.
- Applying compressor polytropic efficiency signs to the turbine: the
  turbine exit temperature falls as efficiency rises.

## Behavior contract (gate 3)

The free-turbine logic is exercised by the gate 3 contract test:
scripts/test_free_turbine.py against scripts/free_turbine_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_free_turbine.py

## Compliance

- The free-turbine matching relations are common turbomachinery
  methodology, paraphrased here. FAR-33 is cited as reference only for
  the engine certification context; no proprietary or copyrighted text
  is reproduced.
- compliance: STANDARDS-REF, gated: false.
