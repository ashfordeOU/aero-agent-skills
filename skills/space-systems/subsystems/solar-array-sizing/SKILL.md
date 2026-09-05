---
name: solar-array-sizing
description: "Use when sizing a spacecraft EPS solar array or photovoltaic panel: array area, power demand, eclipse fraction, cell efficiency, packing factor, degradation, end of life, solar irradiance. Compute spacecraft solar-array sizing: determine the required photovoltaic array area in square meters from the orbit-average power demand, the eclipse fraction, the solar cell efficiency, the packing factor, and the end-of-life degradation over the mission life, then verify the array margin at end of life. Trigger: solar array sizing, array area, cell efficiency, degradation, power demand, eclipse fraction, photovoltaic."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: subsystems
  tags: [solar-array-sizing, array-area, eclipse-fraction, cell-efficiency, power-demand, packing-factor, solar-irradiance, end-of-life, mission-life, photovoltaic-array]
  version: 0.1.0
  author: Aero Agent Skills
---

# Solar Array Sizing (space-systems/subsystems/solar-array-sizing)

Use when sizing the photovoltaic array of a spacecraft EPS: computing the
required array area in square meters from the orbit-average power demand,
the eclipse fraction, the solar cell efficiency, the packing factor, and
the end-of-life degradation over the mission life, and verifying that the
sized array still meets the bus load at end of life.

## Domain quick reference

The array generates only in daylight, so the required daylight power
exceeds the orbit-average demand by the daylight fraction factor:

- Required daylight power: `P_day = P_demand / (1 - f_eclipse) * (1 + margin)`.
  Worked: 500 W demand, eclipse fraction 0.35 -> 500 / 0.65 = 769.23 W;
  with a 0.20 sizing margin -> 923.08 W.
- End-of-life degradation factor: `D = (1 - r_annual) ** mission_years`
  (compound annual loss). Worked: 0.02 per year over 10 years ->
  0.98 ** 10 = 0.8171.
- End-of-life specific power: `p_eol = G * eta * PF * D`, where G is the
  solar irradiance (W/m2), eta the cell efficiency, PF the packing factor.
  Worked: 1367 W/m2 * 0.30 * 0.85 * 0.8171 = 284.82 W/m2.
- Required array area: `A = P_day / p_eol`. Worked: 923.08 / 284.82 =
  3.24 m2.
- Second anchor (no margin): 300 W demand, eclipse fraction 0.40,
  eta = 0.28, PF = 0.90, r = 0.03, 5 years -> P_day = 300 / 0.60 = 500 W;
  D = 0.97 ** 5 = 0.8587; p_eol = 1367 * 0.28 * 0.90 * 0.8587 =
  295.82 W/m2; A = 500 / 295.82 = 1.69 m2.
- Reference irradiance: 1367 W/m2 mean solar constant at 1 AU; an array
  off-pointed from the sun by angle theta receives G * cos(theta).

All worked numbers are verified by running scripts/solar_array_sizing_logic.py
(see scripts/test_solar_array_sizing.py, behavior contract below).

## Workflow

1. Collect the inputs: orbit-average power demand (W), eclipse fraction
   (0 to <1), solar irradiance (W/m2), cell efficiency (fraction), packing
   factor (fraction), annual degradation rate (fraction per year), mission
   years, and the array sizing margin (default 0.20).
2. Compute the required daylight power with
   `daylight_power(power_demand_w, eclipse_fraction, array_margin)`.
3. Compute the end-of-life degradation factor with
   `degradation_factor(annual_degradation, mission_years)` and the
   end-of-life specific power with `eol_specific_power(...)`.
4. Compute the required array area with
   `required_array_area(power_demand_w, eclipse_fraction, solar_irradiance,
   cell_efficiency, packing_factor, annual_degradation, mission_years,
   array_margin)`.
5. Verify the sizing: feed the computed area back through
   `array_power_available(...)` and `power_margin(...)`; a positive margin
   means the array meets the daylight demand at end of life. Confirm the
   deterministic checks with the contract test.

## Pitfalls

- Confusing this leaf with power-thermal-budget: that leaf sizes the
  overall EPS power budget and the battery; this leaf sizes the array
  area from cell efficiency, packing factor, and degradation.
- Confusing this leaf with communication-link-budget: RF link power,
  EIRP, and path loss are unrelated to photovoltaic generation sizing.
- Confusing this leaf with the adcs leaves: sun-pointing computes the sun
  vector geometry, attitude-control-sizing sizes reaction wheels, and
  magnetorquer-control sizes coils; none of them size the array area.
- Using begin-of-life specific power for an end-of-life requirement:
  forgetting the degradation factor D < 1 oversizes the array.
- Omitting the packing factor: the panel area is larger than the bare
  cell area, so A without PF is the cell area, not the panel area.
- Using a linear degradation estimate (1 - r * n) instead of the compound
  form (1 - r) ** n: the two diverge for long missions.
- Sizing from orbit-average power without the 1 / (1 - f_eclipse) factor:
  the array generates only in daylight and must cover the eclipse too.
- Assuming normal-incidence irradiance at all times: off-pointing by
  angle theta reduces the received flux to G * cos(theta).

## Behavior contract (gate 3)

The sizing, degradation, and margin logic is exercised by the gate 3
contract test: scripts/test_solar_array_sizing.py against
scripts/solar_array_sizing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_solar_array_sizing.py

## Compliance

- Standards referenced, not reproduced: ECSS standards are freely
  downloadable (copyright ESA); summary-only per standards-map.yaml
  and brief 06.
- compliance: STANDARDS-REF, gated: false.
