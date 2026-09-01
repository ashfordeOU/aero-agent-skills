---
name: turboprop-cycle
description: "Use when you must analyze the turboprop powerplant cycle and propeller performance: compute the propeller (Froude) efficiency from the flight velocity and the slipstream velocity, the thrust delivered from the shaft power at the flight speed, the static thrust from the shaft power and the propeller disk area at zero speed, the equivalent shaft power that credits the residual jet thrust, the advance ratio and the power and thrust coefficients at the propeller speed, the specific fuel consumption based on shaft power, and the overall efficiency from the thermal, propeller, and mechanical efficiencies. Produces the turboprop performance dict that gates the powerplant assessment. Trigger: turboprop cycle, propeller efficiency, static thrust, equivalent shaft power, advance ratio, power coefficient, thrust coefficient, slipstream velocity."
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
  tags: [turboprop-cycle, propeller-efficiency, froude-efficiency, static-thrust, equivalent-shaft-power, advance-ratio, power-coefficient, thrust-coefficient, specific-fuel-consumption, overall-efficiency, slipstream-velocity, propeller-disk-area]
  version: 0.1.0
  author: AeroSkills
---

# Turboprop Cycle (propulsion/turboprop/turboprop-cycle)

Use when the task is turboprop cycle analysis: converting the shaft
power of the gas generator into propeller thrust, static thrust, and
equivalent shaft power, and sizing the propeller operating point.

## Domain quick reference

- Propeller (Froude) efficiency: the propeller accelerates the air
  from the free-stream velocity vf to the slipstream velocity vj, and
  the ideal efficiency is eta_p = 2 / (1 + vj / vf). When vj = vf
  there is no acceleration and eta_p = 1; when vj = 2 * vf the
  efficiency falls to 2/3. Real propellers reach 0.80 to 0.88 at
  cruise.
- Thrust from shaft power: at flight speed the useful thrust power is
  T * V, so T = eta_p * P / V with P the shaft power delivered to the
  propeller in W, V in m/s, and T in N. A 1 MW shaft at 100 m/s with
  eta_p 0.8 gives 8000 N.
- Static thrust: at zero flight speed the whole shaft power goes into
  the induced velocity, and actuator-disk momentum theory gives
  T0 = (2 * rho * A * P^2)^(1/3), with disk area A = pi/4 * D^2. A 1
  MW shaft on a 3 m propeller at sea level (rho 1.225) gives about
  25.9 kN, well above the cruise thrust.
- Equivalent shaft power: the residual jet thrust of the turboprop
  exhaust adds thrust power Tj * V, credited at the propeller
  efficiency: ESP = P + Tj * V / eta_p. ESP compares the whole
  powerplant with a pure propeller drive.
- Advance ratio: J = V / (n * D) with n = rpm / 60 in rev/s and D the
  propeller diameter in m. J measures the distance travelled per
  revolution in diameters.
- Power and thrust coefficients: Cp = P / (rho * n^3 * D^5) and
  Ct = T / (rho * n^2 * D^4) are the dimensionless forms of the shaft
  power and thrust; propeller performance charts plot Cp and Ct
  against J.
- Specific fuel consumption on shaft power: SFC = mf / P in kg/(kW h),
  converting the fuel flow in kg/s to fuel per kilowatt-hour of shaft
  power.
- Overall efficiency: eta_o = eta_th * eta_p * eta_m, the thermal
  efficiency of the gas generator cycle times the propeller efficiency
  times the mechanical efficiency of the shaft and gearbox.

## Workflow

1. Establish the operating point: flight velocity V, shaft power P,
   fuel flow mf, air density rho, propeller diameter D and speed rpm.
2. Estimate the slipstream velocity and compute the propeller
   efficiency with propeller_efficiency.
3. Compute the cruise thrust with thrust_from_shaft_power and the
   static thrust with static_thrust; the stand thrust is the
   sizing load for the propeller and gearbox.
4. Credit any residual jet thrust with equivalent_shaft_power to
   compare the powerplant against a pure propeller drive.
5. Compute the advance ratio, power coefficient, and thrust
   coefficient with advance_ratio, power_coefficient, and
   thrust_coefficient to place the operating point on the propeller
   chart.
6. Close the loop with specific_fuel_consumption and
   overall_efficiency for the powerplant assessment.

## Pitfalls

- Using the slipstream velocity below the flight velocity: the
  propeller accelerates the air, so vj must be >= vf; a vj below vf
  is unphysical and would return an efficiency above 1.
- Confusing static and cruise thrust: the static thrust from the
  actuator-disk relation is far larger than the cruise thrust at
  speed, and it is the stand condition that loads the propeller and
  gearbox.
- Forgetting the disk area in static thrust: T0 scales with the cube
  root of the area, so doubling the diameter raises static thrust by
  the cube root of 4, about 1.59.
- Using rpm instead of rev/s in the coefficients: n = rpm / 60
  everywhere, or the power and thrust coefficients come out wrong.
- Crediting the jet thrust without the propeller efficiency: the
  equivalent shaft power divides Tj * V by eta_p, because the jet
  thrust is worth more shaft power the worse the propeller is.
- Dropping the mechanical efficiency: eta_o multiplies the thermal
  and propeller efficiencies by the gearbox and shaft efficiency,
  typically 0.97 to 0.99.
- Sizing the propeller at cruise only: the advance ratio and
  coefficients must be checked at the climb and stand conditions,
  where J approaches zero and the coefficients peak.

## Behavior contract (gate 3)

The turboprop cycle logic is exercised by the gate 3 contract test:
scripts/test_turboprop_cycle.py against
scripts/turboprop_cycle_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_turboprop_cycle.py

## Compliance

- FAR-33 is cited as reference only for the engine certification
  context; the propeller and actuator-disk relations are common
  propulsion methodology, paraphrased here. No proprietary or
  copyrighted text is reproduced.
- compliance: STANDARDS-REF, gated: false.
