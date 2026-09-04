---
name: rocket-turbopump
description: "Use when you must size the centrifugal pump inside a liquid rocket engine turbopump: convert the discharge pressure rise and propellant flow into the pump head, compute the dimensionless specific speed from the shaft speed, flow, and head, estimate the impeller tip speed and diameter from the design head coefficient, compute the pump power at the pump efficiency, assess the suction performance with the available net positive suction head and the suction specific speed, and judge the cavitation margin against the suction specific speed limit. Produces the head, specific speed, tip speed, impeller diameter, pump power, NPSH, and cavitation verdict that gate the turbopump design review. Trigger: rocket turbopump, pump specific speed, suction specific speed, net positive suction head, impeller tip speed, LOX pump sizing, cavitation margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: turbomachinery
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: turbomachinery
  tags: [rocket-turbopump, pump-specific-speed, suction-specific-speed, net-positive-suction-head, impeller-tip-speed, lox-pump-sizing, cavitation-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rocket Turbopump (propulsion/turbomachinery/rocket-turbopump)

Use when the task is pump-level sizing of the turbopump in a liquid
rocket engine: turning a required discharge pressure rise and propellant
flow into the pump head, the dimensionless specific speed, the impeller
tip speed and diameter from the design head coefficient, the pump power
at the pump efficiency, and the suction performance picture from the
available net positive suction head and the suction specific speed. This
leaf implements the standard pump sizing relations in pure Python,
stdlib only, SI units throughout. It pairs with
propulsion/rocket/rocket-engine-cycle, which fixes the feed architecture
and the cycle-level discharge pressure and flow this pump must deliver,
and with propulsion/axial-compressor/turbine-stage, which models the
drive turbine on the same shaft. Boundary: this leaf owns pump geometry,
efficiency bookkeeping, and cavitation; the cycle leaf owns the power
balance. Air compressor stages belong to
propulsion/turbomachinery/centrifugal-compressor.

## Domain quick reference

- Shaft speed: omega = 2 * pi * rpm / 60 (rad/s) from the rotational
  speed in rpm (omega_from_rpm).
- Pump head rise: H = dp / (rho * G0), with dp the discharge pressure
  rise in Pa, rho the propellant density, G0 = 9.80665 m/s^2
  (head_rise_m).
- Dimensionless specific speed: N_s = omega * sqrt(Q) / (G0 * H)^0.75,
  with Q the volume flow in m^3/s (specific_speed). This is the pump
  type number that tells whether an impeller, mixed-flow, or axial pump
  suits the duty.
- Impeller tip speed from the head coefficient: u2 = sqrt(G0 * H / psi)
  with the design head coefficient psi = 0.55 for a centrifugal pump
  impeller (impeller_tip_speed). The head coefficient compares the
  Euler head to the blade speed squared.
- Impeller diameter from the tip speed and shaft speed: D = 2 * u2 /
  omega (impeller_diameter).
- Pump power: P = Q * dp / eta, the hydraulic power at the pump
  efficiency eta, in W (pump_power).
- Available NPSH: NPSH = (p_inlet - p_vapor) / (rho * G0) in meters,
  the suction head above vapor pressure at the pump inlet
  (npsh_available).
- Dimensionless suction specific speed: S = omega * sqrt(Q) / (G0 *
  NPSH)^0.75, the suction analogue of N_s (suction_specific_speed).
- Cavitation verdict: acceptable when S >= S_CRIT, cavitation-risk
  otherwise, with S_CRIT = 3.0 the conventional suction specific speed
  limit for a rocket turbopump stage (cavitation_verdict).
- Units are SI throughout: rad/s, m, m^3/s, Pa, kg/m^3, W.
- ECSS frames the space propulsion context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the pump duty: rpm, volume flow Q, discharge pressure rise dp,
   density rho, and efficiency eta (from the rocket-engine-cycle output
   for the discharge pressure and flow).
2. Convert the shaft speed with omega_from_rpm and the head with
   head_rise_m.
3. Compute the dimensionless specific speed with specific_speed to
   confirm the centrifugal pump type for the duty.
4. Get the impeller tip speed with impeller_tip_speed at the design head
   coefficient, then the diameter with impeller_diameter; compare D with
   the geometric envelope of the engine.
5. Compute the pump power with pump_power and carry it back to the cycle
   power balance (rocket-engine-cycle owns the balance itself).
6. Assess suction performance: npsh_available from the inlet and vapor
   pressures, then suction_specific_speed from omega, Q, and the
   available NPSH.
7. Judge the cavitation margin with cavitation_verdict against S_CRIT.
8. Run the whole chain in one call with size_pump, which returns the
   dict with omega, head_m, specific_speed, tip_speed_ms, diameter_m,
   power_W, npsh_m, suction_specific_speed, and verdict.
9. Confirm the deterministic checks with the contract test
   scripts/test_rocket_turbopump.py.

## Worked example

LOX pump: rpm 18000, Q = 0.04 m^3/s, dp = 10 MPa, rho = 1141 kg/m^3,
eta = 0.68, p_inlet = 0.5 MPa, p_vapor = 0.03 MPa.

- Shaft speed: omega = 2 * pi * 18000 / 60 = 1884.96 rad/s.
- Head: H = 10e6 / (1141 * 9.80665) = 893.70 m.
- Specific speed: N_s = 1884.96 * 0.2 / (9.80665 * 893.70)^0.75 =
  0.4162, a low specific speed typical of a high-head centrifugal
  turbopump stage.
- Tip speed: u2 = sqrt(9.80665 * 893.70 / 0.55) = 126.23 m/s, a
  moderate tip speed for a LOX pump.
- Diameter: D = 2 * 126.23 / 1884.96 = 0.1339 m, about 134 mm.
- Pump power: P = 0.04 * 10e6 / 0.68 = 588235 W, about 588 kW for the
  oxidizer pump.
- Available NPSH: NPSH = (0.5e6 - 0.03e6) / (1141 * 9.80665) = 42.00 m.
- Suction specific speed: S = 1884.96 * 0.2 / (9.80665 * 42.00)^0.75 =
  4.123, above the 3.0 limit, so the verdict is acceptable.
- Flip case: the verdict flips to cavitation-risk when S drops below
  3.0. With the inlet pressure raised to 1.0 MPa the available NPSH
  grows to 86.69 m, S falls to 2.394, and size_pump returns
  cavitation-risk. Model note: in this sizing model S is computed from
  the available NPSH, so S falls as the available suction head grows;
  the deterministic flip case in the contract test raises the inlet
  pressure accordingly.

## Verification

- Confirm omega_from_rpm(18000) returns 1884.96 rad/s within 0.1 and
  that 3000 rpm returns exactly 100 * pi rad/s.
- Confirm head_rise_m(10e6, 1141) returns 893.70 m within 0.1 and is
  linear in the pressure difference.
- Confirm specific_speed(1884.96, 0.04, 893.70) returns 0.4162 within
  0.001 and scales with omega and sqrt(Q).
- Confirm impeller_tip_speed(893.70, 0.55) returns 126.23 m/s within
  0.1 and scales with sqrt(H); impeller_diameter(126.23, 1884.96)
  returns 0.1339 m within 0.001 and is inversely proportional to omega.
- Confirm pump_power(0.04, 10e6, 0.68) returns 588235 W within 10.
- Confirm npsh_available(0.5e6, 0.03e6, 1141) returns 42.00 m within
  0.01 and is linear in the pressure difference; raising the vapor
  pressure to 0.2 MPa lowers it by exactly 0.17e6 / (rho * G0).
- Confirm suction_specific_speed(1884.96, 0.04, 42.00) returns 4.123
  within 0.01 and that the verdict is acceptable at S = 3.0 and flips
  to cavitation-risk below it.
- Confirm size_pump reproduces every anchor in one dict and flips the
  verdict to cavitation-risk at an inlet pressure of 1.0 MPa.
- Confirm every non-positive rpm, flow, pressure rise, density, head,
  NPSH, and omega, every efficiency outside (0, 1], every non-positive
  head coefficient, and every inlet pressure at or below the vapor
  pressure raises ValueError.
- Run the contract test offline: python3
  scripts/test_rocket_turbopump.py (34 tests, deterministic).

## Related leaves

- propulsion/rocket/rocket-engine-cycle: fixes the feed architecture and
  the discharge pressure and flow this pump must deliver; owns the
  cycle-level pump and turbine power balance.
- propulsion/turbomachinery/centrifugal-compressor: the sibling
  turbomachinery design method for air compressor stages.
- propulsion/axial-compressor/turbine-stage: the drive turbine on the
  same shaft as this pump.

## Pitfalls

- Misreading the suction specific speed direction: in this sizing model
  S is computed from the AVAILABLE NPSH, so S falls as the available
  suction head grows — the flip case raises the inlet pressure to 1.0
  MPa, NPSH grows to 86.69 m and the verdict flips to cavitation-risk,
  the opposite of the intuition that more inlet head always helps.
- Reading the verdict boundary as a soft margin: cavitation_verdict is
  acceptable at S >= S_CRIT = 3.0 and flips to cavitation-risk below
  it, so the boundary is exact and deterministic, not a trend to
  eyeball.
- Sizing the pump at the cycle discharge pressure without the pump
  inlet state: npsh_available needs the inlet pressure above the vapor
  pressure; an inlet at or below the vapor pressure raises ValueError
  because the suction head is unphysical.
- Applying the cavitation judgment to the drive turbine or the air
  side: this leaf owns pump geometry, efficiency and cavitation only —
  the cycle power balance belongs to rocket-engine-cycle and air
  compressor stages to centrifugal-compressor.
- Quoting the specific speed without the pump type context: N_s =
  0.4162 is a low specific speed typical of a high-head centrifugal
  turbopump stage, so the number must be read against the impeller,
  mixed-flow or axial pump selection it implies.
- Trusting the 0.55 head coefficient blindly: impeller_tip_speed runs
  at the design head coefficient psi = 0.55, a conventional centrifugal
  value — a different impeller design needs its own psi before the tip
  speed and diameter are quoted.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rocket_turbopump.py

The test covers the LOX worked-example anchors (omega 1884.96 rad/s,
head 893.70 m, N_s 0.4162, tip speed 126.23 m/s, diameter 0.1339 m,
power 588235 W, NPSH 42.00 m, S 4.123, verdict acceptable), scaling and
round-trip identities, the verdict boundary at S = 3.0 and the flip to
cavitation-risk below it (including the size_pump flip case at a 1.0 MPa
inlet pressure), agreement between size_pump and the individual
functions, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA standard
  family (ecss.nl/standards); the pump sizing relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
