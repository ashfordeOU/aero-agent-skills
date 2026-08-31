---
name: turbofan-off-design
description: "Use when you must evaluate turbofan performance away from the design point: correct the inlet mass flow and the spool speed to standard-day conditions, scale the sea-level net thrust to altitude with the density ratio and the ram drag penalty, apply the SFC altitude and throttle behavior, sanity-check the throttle setting, and judge the fan and core component matching. Produces corrected mass flow, corrected speed, altitude net thrust, cruise SFC factor, and the matching verdict that gate the off-design operating assessment in the FAR-33 engine context. Trigger: off-design, corrected mass flow, corrected speed, component matching, altitude thrust, cruise SFC, throttle setting, ram drag."
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
  tags: [turbofan-off-design, off-design, corrected-mass-flow, corrected-speed, altitude-thrust, ram-drag, cruise-sfc, throttle-setting, component-matching, fan-matching, core-matching]
  version: 0.1.0
  author: AeroSkills
---

# Turbofan Off-Design (propulsion/turbofan/turbofan-off-design)

Use when the task is turbofan performance away from the design
point: corrected mass flow and corrected speed at the engine inlet,
altitude net thrust with the ram drag penalty, SFC altitude and
throttle behavior, throttle-setting sanity, and the fan and core
component matching verdict.

## Domain quick reference

- Corrected mass flow (SI, kg/s): m_dot_c = m_dot * sqrt(T_ref / T)
  / (P / P_ref), with m_dot the physical mass flow in kg/s, T the
  inlet total temperature in K, P the inlet total pressure in Pa,
  and the standard-day references T_ref = 288.15 K, P_ref =
  101325 Pa. At the reference condition m_dot_c = m_dot; a hot day
  (T above T_ref) lowers m_dot_c at fixed physical flow, and a low
  inlet pressure raises it.
- Corrected speed (rpm): N_c = N * sqrt(T_ref / T), with N the
  physical rotor speed in rpm and T in K. At T = T_ref, N_c = N.
  The correction removes the temperature effect on the speed of
  sound so that operating points stay comparable.
- Net thrust at altitude: F_alt = F_SL * (rho / rho0) * f_mach -
  D_ram, with F_SL the sea-level static rating in N, rho/rho0 the
  density ratio, f_mach a ram and Mach recovery factor (about 1 at
  low speed, lower at high Mach), and D_ram the ram drag. Ram drag
  is the momentum of the captured air: D_ram = m_dot * V0 with V0
  the flight speed in m/s; it is subtracted from gross thrust to
  give net thrust.
- SFC altitude and throttle behavior: SFC_alt = SFC_SL *
  (rho / rho0)^k with k about 0.1 to 0.2 in a quick model; SFC
  improves (falls) with altitude because the cold air raises the
  cycle efficiency, and it rises again at low throttle. At sea
  level static the factor is 1.
- Throttle-setting sanity: the throttle fraction of the maximum
  rating runs from idle (about 0.05) to max continuous (1.0);
  below idle the combustor is unstable, above max the rating is
  exceeded.
- Component matching verdict: the fan and core corrected-flow
  deltas from their matched operating points must both stay inside
  a band (default plus/minus 10 percent); a component outside the
  band is off-design and the operating point must be reworked.
- FAR-33 (14 CFR Part 33) sets the certification context for
  engine ratings and operating limitations; the corrected-parameter
  and scaling relations above are common off-design performance
  practice.

## Workflow

1. Correct the operating point: corrected_mass_flow and
   corrected_speed from the physical inlet flow, temperature, and
   pressure with the standard-day references.
2. Scale the thrust to the flight condition with
   net_thrust_altitude(sea_level_thrust, rho, rho0, mach_factor,
   ram_drag) and compare it with the aircraft demand at that
   altitude.
3. Apply the SFC altitude factor with
   sfc_altitude_factor(sfc_sea_level, rho, rho0) for the cruise
   fuel-flow estimate.
4. Sanity-check the throttle fraction with throttle_verdict; rework
   the schedule if the verdict is below-idle or over-throttle.
5. Judge the fan and core position with
   component_matching_verdict(fan_matching, core_matching); a
   non-matched verdict flags which component must be reworked.
6. Report corrected flow, corrected speed, altitude net thrust,
   cruise SFC, and the matching verdict.

## Pitfalls

- Mixing corrected and physical quantities: the map and matching
  relations use corrected flow and corrected speed, so physical
  values must be corrected before any comparison across operating
  conditions.
- Forgetting the ram drag: at cruise the ram drag is a large part
  of the gross thrust; scaling sea-level thrust by density alone
  overstates net thrust.
- Reversing the temperature ratio: the corrected flow and speed
  both carry sqrt(T_ref / T), never sqrt(T / T_ref); the hot-day
  direction is a decrease in both corrected values.
- Treating the SFC altitude exponent as a fixed value: 0.1 to 0.2
  is a quick-model range, not a rated figure; the engine program
  supplies the measured or cycle-derived value.
- Assuming thrust scales with pressure ratio instead of density
  ratio: the density ratio drives the mass-flow and thrust scaling
  in the quick model.
- Calling the matching verdict at a single component: fan and core
  must both be inside the band; one in-band component does not make
  the point matched.
- Passing zero or negative inputs, or a throttle fraction outside
  the idle-to-max range; the module raises ValueError instead of
  returning a nonsense number.

## Behavior contract (gate 3)

The off-design relations are exercised by the gate 3 contract test:
scripts/test_turbofan_off_design.py against
scripts/turbofan_off_design.py (stdlib unittest, offline). Run:
python3 scripts/test_turbofan_off_design.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government
  work (public domain) and covers engine ratings and operating
  limitations, not off-design performance methods; the
  corrected-parameter and scaling relations are common engine
  performance methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
