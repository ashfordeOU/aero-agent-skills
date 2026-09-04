---
name: rotorcraft-forward-flight-performance-test
description: "Use when you must reduce a rotorcraft level-flight performance flight test from measured data: convert measured main rotor torque and rotor speed samples into shaft power across a forward-flight speed sweep, correct the measured power-required polar to a reference weight and standard day with the induced and profile power split, fit the corrected polar, and read off the best-endurance speed at the minimum-power point, the best-range speed at the tangent from the origin, and the maximum level-flight speed Vh against the maximum continuous available power. Produces the measured torque-to-shaft-power values, the corrected polar, the fitted curve coefficients, the best-endurance speed, the best-range speed and the Vh verdict that gate a rotorcraft level-flight performance assessment. Trigger: rotorcraft-forward-flight-performance-test, rotorcraft-forward-flight, level-flight-speed-sweep, torque-to-shaft-power, power-required-polar, vh-determination, max-continuous-power."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [rotorcraft-forward-flight-performance-test, rotorcraft-forward-flight, level-flight-speed-sweep, torque-to-shaft-power, power-required-polar, vh-determination, max-continuous-power]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rotorcraft Forward-Flight Performance Test (flight-test-operations/performance/rotorcraft-forward-flight-performance-test)

Use when the task is reducing a rotorcraft level-flight (forward
flight) performance flight test from MEASURED data: measured main
rotor torque and rotor speed samples converted to shaft power across a
level-flight speed sweep, the measured power-required polar corrected
to a reference weight and standard-day density with the induced and
profile power split, the corrected polar fitted, and the
characteristic speeds read off the fitted curve. Every input is a
flight test measurement: torque, rotor speed, airspeed, gross weight,
density. This leaf is the measured-data reduction counterpart to
flight-mechanics/performance/rotorcraft-forward-flight-performance,
which owns the analytic prediction of the forward-flight
power-required curve from rotor geometry; it pairs the same way as the
hover measured reduction pairs with the analytic hover model. It does
NOT reduce hover or climb measured data (rotorcraft-performance-
flight-test owns that) and does NOT touch fixed-wing cruise fuel flow.

## Domain quick reference

- Shaft power from the torque sample:
  shaft_power: P = Q * omega for measured main rotor torque (Nm) at
  measured rotor speed (rad/s). Worked: 12,222 Nm at 27 rad/s gives
  329,994 W (about 330 kW). A zero torque at positive rotor speed is a
  valid measured point (0 W).
- Density correction to standard day:
  density_correct_power: P_std = P * RHO_STD / rho_test, with RHO_STD
  = 1.225 kg/m3. Power required scales with 1/rho at fixed speed and
  weight. Worked: 330,000 W at rho 1.10 corrects to 367,500 W.
- Weight correction with the induced and profile split:
  weight_correct_power: P_ref = P * [ f_i * (W_ref/W_test)^1.5 +
  (1 - f_i) * (W_ref/W_test) ], f_i the induced fraction of the total
  power. The induced share scales with (W_ref/W_test)^1.5 (induced
  velocity ~ sqrt(W), induced power ~ W * v_i); the profile and
  parasite share scales linearly with weight (drag ~ weight at the
  same speed). At the reference weight the correction returns the
  measured power unchanged.
- Reference-condition chain: correct_to_reference applies the density
  correction first, then the weight correction at the standard-day
  power. At standard day AND reference weight the chain is identity.
- Polar fit: fit_power_polar fits P(V) = a*V^2 + b*V + c by quadratic
  least squares (normal equations, stdlib) over the sweep points; the
  hover anchor at zero airspeed is a valid sweep member. Fit is
  rejected when degenerate (a <= 0 on non-constant powers).
- Best-endurance speed: best_endurance_speed: V_ben = -b / (2*a), the
  polar minimum (minimum power-required point). Flat polar (a == 0)
  has no interior minimum: returns None.
- Best-range speed: best_range_speed: V_br = sqrt(c / a) from the
  tangent condition dP/dV = P/V, which reduces to a*V^2 = c. Returns
  None when c == 0.
- Maximum level-flight speed: max_level_speed: largest real root of
  a*V^2 + b*V + c = P_avail, D = b^2 - 4*a*(c - P_avail); Vh =
  (-b + sqrt(D)) / (2*a). None when D < 0 (available power below the
  polar minimum, no level flight). The + root is the high-speed
  intersection.
- Speed ordering: validate_speed_order checks V_ben < V_br < Vh
  (order only, None-safe). reduce_level_flight_sweep returns the
  computed Vh even beyond the measured band and sets
  vh_beyond_measured True so the report marks it an extrapolation.
- Sweeps run 4-40 points; arrays must be equal length.
- Units are SI throughout: Nm, rad/s, W, N, kg/m3, m/s.
- FAR 29 frames the airworthiness context (reference only); the
  relations above are standard rotorcraft flight-test reduction
  methodology, summary-only, and work only from measured data.

## Workflow

1. Gather the measured test day: torque samples at the recorded rotor
   speed across the level-flight speed sweep, test gross weight, and
   the density from the test pressure altitude and outside air
   temperature; take the reference weight, the standard day and the
   maximum continuous available power from the flight manual.
2. Convert every torque sample to shaft power with shaft_power.
3. Correct each shaft power to the reference weight and standard day
   with correct_to_reference and the induced fraction split
   (weight_correct_power, density_correct_power).
4. Fit the corrected polar with fit_power_polar; keep the hover anchor
   (zero airspeed) in the sweep when it was measured.
5. Read the characteristic speeds off the fitted curve:
   best_endurance_speed, best_range_speed, and max_level_speed run
   against the maximum continuous available power.
6. Check the speed ordering with validate_speed_order (V_ben < V_br <
   Vh) and check vh_beyond_measured before quoting Vh in the report.
7. Run the whole sweep end to end with reduce_level_flight_sweep for
   the reduction dict, or run the convenience chain in place of steps
   2-6.
8. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_forward_flight_performance_test.py.

## Worked example

Measured level-flight sweep of a light single-rotor helicopter at
standard day (rho 1.225 kg/m3) at the reference weight (21,000 N), so
the corrections are identity and the raw shaft powers carry the
example. Hover torque 12.222 kN*m at 27.0 rad/s, then torque samples
across V = [0, 12, 24, 36, 48, 60, 72] m/s at omega 27.0 rad/s
(torque per point = power / 27.0). Running the module on the sweep:

- Shaft powers: [330000, 271400, 251800, 259400, 304200, 376000,
  487000] W, each within +-2000 W of the listed value.
- Corrections: identity at standard day and reference weight, so the
  corrected powers equal the shaft powers.
- Fit: P(V) = 114.04*V^2 - 6030.36*V + 329300.0 (a in 100-130
  W/(m/s)^2, b in -7000 to -5000 W/(m/s), c in 320000-340000 W).
- Best-endurance speed: 26.44 m/s (bound 23-30 m/s), polar minimum
  power 249.6 kW (about 250 kW).
- Best-range speed: 53.74 m/s (bound 48-58 m/s), above the
  best-endurance speed and inside the measured band; the tangent
  identity a*V^2 = c holds.
- Maximum level-flight speed at 470 kW maximum continuous power:
  70.40 m/s (bound 66-74 m/s, about 137 kt), inside the measured band
  (top 72 m/s); Vh/V_br about 1.31 and speed_order.order_ok True, so
  no extrapolation flag (vh_beyond_measured False).
- Scale invariance: multiplying every measured power by a constant
  leaves both characteristic speeds unchanged (coefficients scale,
  ratios do not). At 560 kW available the computed Vh reaches
  78.6 m/s, past the 72 m/s top of the band, and the flag
  vh_beyond_measured turns True.

## Verification

- Confirm shaft_power(12222, 27) returns about 330,000 W and that the
  sweep torques recover the listed powers within +-2000 W.
- Confirm the corrections are identity at standard day and reference
  weight, and that density_correct_power(330000, 1.10) returns about
  367,500 W.
- Confirm the fitted coefficients sit in the magnitude bounds (a in
  100-130, b in -7000 to -5000, c in 320000-340000) and reproduce the
  worked-example polar.
- Confirm best_endurance_speed equals -b/(2a) at the vertex, that
  best_range_speed satisfies a*V^2 = c with the tangent condition
  dP/dV = P/V to 1e-6, and that max_level_speed at an available power
  equal to the polar minimum returns the vertex speed (single root).
- Confirm every non-physical input raises ValueError: torque < 0,
  omega <= 0, rho_test <= 0, power < 0, weight <= 0, induced fraction
  outside [0, 1], fewer than 4 sweep points, more than 40 sweep
  points, array length mismatch, negative airspeed, and a degenerate
  downward-curved fit (a <= 0 on non-constant powers).
- Confirm scale invariance: multiplying every measured power by 2.0
  leaves the best-endurance and best-range speeds unchanged to 1e-9.
- Confirm determinism: no RNG anywhere, run-to-run identical floats.
- Run the contract test offline: python3
  scripts/test_rotorcraft_forward_flight_performance_test.py (27
  tests, deterministic, passes in under 20 s).

## Related leaves

- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the analysis sibling (momentum-theory prediction of the forward-
  flight power-required curve from geometry and weight); pair its
  predicted polar with the measured reduction here.
- flight-test-operations/performance/rotorcraft-performance-flight-
  test: the hover and vertical climb measured reduction sibling
  (torque-to-power, measured figure of merit, hover ceiling).
- flight-test-operations/performance/cruise-performance-flight-test:
  the fixed-wing fuel-flow reduction sibling (its quadratic range
  curve versus Mach, not rotorcraft polar data).
- flight-test-operations/performance/climb-performance-flight-test:
  the fixed-wing climb reduction sibling, sharing the weight and
  density correction conventions used here.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_forward_flight_performance_test.py

The test covers the worked-example anchors (shaft powers within +-2000
W of the listed values, identity corrections, fit coefficients in the
spec magnitude bounds, best-endurance 26.44 m/s, best-range 53.74 m/s
with the tangent identity, maximum level-flight speed 70.40 m/s at 470
kW), the closed-form identities (standard-day density identity,
reference-weight identity, density scaling, induced-fraction endpoints
0 and 1, polar-minimum single root), the ValueError rejection of every
non-physical input, scale invariance of the characteristic speeds, the
vh_beyond_measured extrapolation flag, the exact reduction-dict keys,
determinism, and the module constants.

## Compliance

- FAR 29 frames the airworthiness context; it is referenced, not
  reproduced (no verbatim standard text appears here). The relations
  above are standard rotorcraft flight-test reduction methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
