---
name: ram-air-turbine-sizing
description: "Use when you must size the ram air turbine: computing the RAT rotor swept area from the required emergency power at a fixed emergency airspeed with the wind-power relation P = 0.5 rho V^3 A Cp at a fixed design power coefficient, deriving the rotor disk diameter and checking the round-trip available power at that condition. Produces the required swept area, the disk diameter, the available power and margin at that condition, and a fit verdict against the stowage diameter limit for the emergency power extraction installation. Trigger: ram air turbine sizing, rat disk diameter, ram air turbine rotor, rat swept area, emergency power extraction, wind power rotor sizing, emergency descent airspeed, required emergency power."
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
  tags: [ram-air-turbine-sizing, ram-air-turbine-rotor, rat-disk-diameter, emergency-power-extraction, rat-swept-area, wind-power-rotor-sizing]
  version: 0.1.0
  author: AeroSkills
---

# Ram Air Turbine Sizing (vehicle-design/sizing/ram-air-turbine-sizing)

Use when the task is sizing the emergency ram air turbine (RAT) rotor at
the conceptual level from the required emergency power at a fixed
emergency airspeed. The model is the wind-power relation P = 0.5 rho V^3
A Cp with a fixed design overall power coefficient that absorbs the
blade, ducting and machine efficiency losses, so the swept area follows
directly from the load and the flight condition. This leaf implements the
standard wind-power rotor sizing method in pure Python, stdlib only. The
required emergency power P_req is an input supplied by
vehicle-design/sizing/aircraft-electrical-load-analysis; the emergency
hydraulic side of the installation is covered by
vehicle-design/sizing/hydraulic-system-sizing. RAT machine details
(embedded generator and control laws) are empirical and out of scope.

## Domain quick reference

- Wind-power relation: P = 0.5 * rho * V^3 * A * Cp, with P the
  extracted power in W, rho the air density in kg/m3, V the airspeed in
  m/s at the fixed emergency condition, A the rotor swept area in m2 and
  Cp the overall power coefficient.
- Required swept area: A = P / (0.5 * rho * V^3 * Cp). Sizing the area
  at the emergency speed means a fixed emergency descent speed anchors
  the condition (the classic anchor is a minimum controllable descent
  speed); the density defaults to ISA sea level.
- Rotor disk diameter: D = sqrt(4*A/pi). A round disk sweeps the full
  circle of radius D/2.
- Design power coefficient: Cp = 0.10 fixed for the emergency RAT,
  including efficiency and losses; the ideal actuator-disk upper bound
  (Betz limit) is 16/27 = 0.592593 and physical inputs must stay below
  it.
- Round-trip check: feeding the sized area back through
  0.5 * rho * V^3 * A * Cp must return the required power exactly; the
  margin is available power minus required power.
- Stowage verdict: PASS when the disk diameter fits within the stowage
  diameter limit of the installation bay, else FAIL.
- Units are SI throughout: W, m/s, kg/m3, m2, m.
- FAR 25.1351 frames the emergency electrical and essential power
  context (reference-only); the relations above are standard
  engineering methodology, summary-only.

## Workflow

1. Fix the emergency condition: the required emergency power P_req in W
   (from the electrical load analysis input) and the emergency airspeed
   V in m/s at which the RAT must deliver it.
2. Keep the defaults (ISA sea level density 1.225 kg/m3, design power
   coefficient 0.10) or pass explicit rho and cp values to
   rat_swept_area.
3. Compute the required swept area with rat_swept_area(P_req, V) and
   the rotor disk diameter with disk_diameter(area).
4. Run the round-trip power check with rat_available_power(area, V):
   it must equal P_req within numerical tolerance; the margin is the
   difference.
5. Get the fit verdict in one call: rat_sizing_summary(P_req, V,
   max_stowage_diameter_m) returns the area, diameter, available power,
   margin and the PASS/FAIL stowage verdict dict.
6. Confirm the deterministic checks with the contract test
   scripts/test_ram_air_turbine_sizing.py.

## Worked example

Reference installation: the emergency RAT must supply 5000 W at the
fixed emergency descent speed of 100 m/s at ISA sea level with the
design power coefficient 0.10.

- Swept area: A = 5000 / (0.5 * 1.225 * 100^3 * 0.10) = 5000 / 61250 =
  0.081633 m2 (module output 0.081632653 m2).
- Disk diameter: D = sqrt(4 * 0.081633 / pi) = 0.322394 m, about
  322.4 mm (module output 0.322394 m).
- Round-trip power: 0.5 * 1.225 * 100^3 * 0.081633 * 0.10 = 5000.00 W
  exact, so the margin is 0.00 W.
- Stowage verdict: diameter 0.322394 m against the 0.40 m bay limit
  gives PASS; against a 0.30 m limit the same rotor gives FAIL.
- Scaling sanity: doubling the airspeed to 200 m/s at the same area
  multiplies the available power by 2^3 = 8 to 40000 W.

## Verification

- Confirm rat_swept_area(5000, 100) returns 0.081633 m2 within 1e-6
  and disk_diameter gives 0.3224 m within 1e-4 (322.4 mm class rotor).
- Confirm the round trip: rat_available_power(rat_swept_area(P, V), V)
  equals P within 1e-6 for any positive power, and the disk identity
  A = pi * D^2 / 4 holds.
- Confirm the scaling law: doubling V at fixed area multiplies the
  available power by 8, and the required area scales as 1/V^3.
- Confirm the stowage verdict flips from PASS to FAIL as the limit
  drops below the 0.3224 m diameter (PASS at 0.40 m, FAIL at 0.30 m).
- Confirm every non-positive power, airspeed, density, coefficient,
  area and stowage limit raises ValueError, and a coefficient at or
  above the Betz bound 0.592593 (for example 0.60) is rejected.
- Confirm the summary dict keys are exactly area_m2, diameter_m,
  available_w, margin_w, stowage_verdict, and that repeated calls are
  deterministic.
- Run the contract test offline: python3
  scripts/test_ram_air_turbine_sizing.py (29 tests, deterministic).

## Related leaves

- vehicle-design/sizing/aircraft-electrical-load-analysis: supplies
  the required emergency power P_req that is the input here.
- vehicle-design/sizing/hydraulic-system-sizing: the hydraulic power
  side of the emergency installation architecture.
- vehicle-design/sizing/bleed-air-system-sizing: engine bleed
  pneumatic extraction, the unrelated alternative air power source.

## Pitfalls

- Sizing on the emergency airspeed alone: the swept area is extremely
  sensitive to the speed (A goes as 1/V^3), so a low anchor speed can
  demand a rotor that will not fit the bay; always run the stowage
  verdict against the installation limit.
- Confusing the round-trip power with the installed capability: the
  wind-power relation returns the power at the sized condition, not the
  rated machine output; the margin is available minus required at that
  condition.
- Feeding a power coefficient at or above the Betz bound: Cp = 0.60 is
  physically impossible for a wind-driven rotor and the module rejects
  it, so keep the design value at or below the overall 0.10 default.
- Deriving the load here: P_req comes from the electrical load analysis
  leaf; this leaf only converts that requirement into rotor geometry.
- Treating the RAT as a machine model: embedded generator and control
  behavior are empirical and out of scope; the power coefficient is the
  fixed design abstraction for those losses.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ram_air_turbine_sizing.py

The test covers the 5000 W worked example (area 0.081633 m2 within 1e-6,
diameter 0.3224 m within 1e-4, round-trip power 5000.00 W within 1e-6),
stowage verdict PASS at 0.40 m and FAIL at 0.30 m, V^3 and linear power
scaling, the area and diameter round-trip identities, module defaults
(ISA sea level density, 0.10 coefficient, Betz 16/27), summary dict
structure and determinism, and ValueError rejection of non-positive
power, airspeed, density, coefficient, area and stowage limit plus
coefficients at or above the Betz bound.

## Compliance

- Standards referenced, not reproduced: FAR 25.1351 is cited for the
  emergency electrical and essential power context (reference-only per
  standards-map.yaml); the wind-power sizing relations above are
  standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
