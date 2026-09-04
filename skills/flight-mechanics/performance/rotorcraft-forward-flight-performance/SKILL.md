---
name: rotorcraft-forward-flight-performance
description: "Use when you must compute the forward-flight power required of a rotorcraft rotor with momentum-theory inflow: the Glauert induced velocity at a given flight speed, the induced power, the parasite power from the equivalent flat-plate drag area, the profile power from rotor blade solidity and tip speed, and the total power, then find the best endurance speed (minimum total power) and the best range speed (minimum power per unit speed) over a speed sweep. Produces the forward induced velocity, the three power components, the total power curve, and the two characteristic speeds that gate a rotorcraft cruise performance assessment. Trigger: rotorcraft forward flight, glauert inflow, induced power model, parasite power, equivalent flat plate area, best endurance speed, best range speed, rotor profile drag."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [rotorcraft-forward-flight-performance, glauert-inflow, parasite-power, best-endurance-speed, best-range-speed, equivalent-flat-plate-area]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Forward-Flight Performance (flight-mechanics/performance/rotorcraft-forward-flight-performance)

Use when you must compute the forward-flight power required of a
rotorcraft rotor with momentum-theory inflow: the Glauert induced
velocity at a given flight speed, the induced power, the parasite
power from the equivalent flat-plate drag area, the profile power
from rotor blade solidity and tip speed, and the total power through
the induced power factor, then find the speed of minimum total power
(best endurance speed) and the speed that minimizes power per unit
speed (best range speed proxy) over a speed sweep. This leaf
implements the standard uniform-inflow momentum theory (Glauert
inflow) in pure Python, stdlib only. It is the forward-flight
companion to skills/flight-mechanics/performance/
rotorcraft-hover-performance, which owns the hover case; this leaf
takes the hover induced velocity only as the shared v_h input and
adds the flight-speed inflow, parasite and profile terms. Uniform
inflow only: no reverse-flow region, no blade-element section polars,
no compressibility. The equivalent flat-plate area f is an input
here, not a drag buildup.

## Domain quick reference

- Hover reference velocity: v_h = sqrt(T / (2 * rho * A)), the
  momentum-theory value at zero flight speed.
- Glauert inflow at flight speed V:
  v = T / (2 * rho * A * sqrt(V**2 + v**2)). The unique positive
  fixed point is found by substitution starting from v0 = v_h,
  stopping when |v_new - v| < tol (TOL = 1e-9, MAX_ITER = 60).
  Near hover the substitution contracts at about v**2 /
  (V**2 + v**2) per pass, so each pass applies the standard
  delta-squared acceleration to the last two substitution images
  when the denominator is usable; this keeps the default 5 to 100
  m/s sweep inside the iteration cap. Both routes converge on the
  same fixed point, and speed 0 returns v_h directly.
- Induced power: P_i = T * v (ideal, before the induced power
  factor).
- Parasite power: P_par = 0.5 * rho * V**3 * f, with f the
  equivalent flat-plate drag area of the airframe in m2.
- Profile power: P_prof = (1/8) * rho * sigma * Cd0 * A * V_tip**3,
  the average section drag model, sigma the rotor solidity and Cd0
  the mean blade drag coefficient (CD0_DEFAULT = 0.012).
- Total power: P_total = k * T * v + P_prof + P_par, with the
  induced power factor k = K_DEFAULT = 1.15.
- Characteristic speeds over the sweep (5 to 100 m/s by default):
  best endurance speed minimizes P_total; best range speed proxy
  minimizes P_total / V. Induced power falls with speed while
  parasite power rises as V**3, so the best range speed always sits
  above the best endurance speed.
- Units are SI throughout: N, kg/m3, m2, m/s, W.
- 14 CFR Part 29 (FAR-29) frames rotorcraft performance
  requirements; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the rotor and flight state: thrust T = weight from mass,
   rotor area A = pi * R**2, air density rho, and the flight speed V
   (hover_induced_velocity gives v_h for the reference point).
2. Solve the Glauert inflow at the flight speed with
   glauert_induced_velocity; it returns the hover value at V = 0 and
   raises ValueError on negative speed and non-positive thrust, area
   or rho, and RuntimeError when max_iter is exhausted.
3. Compute the induced power with induced_power (T * v), the
   parasite power with parasite_power (0.5 * rho * V**3 * f), and
   the profile power with profile_power (the same (1/8) blade drag
   model as the hover leaf).
4. Combine them with total_power through the induced power factor
   k (default 1.15, matching the hover leaf).
5. Sweep the flight speed with power_sweep to get the total power
   curve, then read the two characteristic speeds:
   best_endurance_speed (argmin of total power) and
   best_range_speed (argmin of total power over speed, returns the
   speed and the power-per-speed ratio).
6. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_forward_flight_performance.py.

## Worked example

Same rotor as the hover leaf: R = 5.0 m (A = 78.5398 m2), m = 2200 kg
(T = 21574.63 N), rho = 1.225 kg/m3, solidity 0.08, Cd0 = 0.012,
tip speed 220 m/s, f = 2.2 m2, k = 1.15.

Power breakdown at V = 60 m/s (module outputs):

| quantity | value |
| --- | --- |
| Glauert induced velocity | 1.868 m/s |
| Induced power T * v | 40297 W (40.3 kW) |
| Profile power | 122935 W (122.9 kW) |
| Parasite power | 291060 W (291.1 kW) |
| Total power (k = 1.15) | 460336 W (460.3 kW) |

The hover induced velocity is 10.59 m/s, so forward flight at 60 m/s
cuts the induced velocity by a factor of about 5.7 and the total
power is dominated by parasite drag (63%).

Characteristic speeds over the default sweep (module outputs):
best endurance speed 28.0 m/s, best range speed 45.0 m/s with
P/V = 6832 W per (m/s). The range speed sits strictly above the
endurance speed, as momentum theory requires. Note: the draft spec
window of 50 to 90 m/s for the best range speed is not reachable by
this model at f = 2.2 m2, where the P/V minimum of the parasite plus
induced balance lands near 45 m/s; the module value above is the
authoritative output of the spec model.

## Verification

- Confirm glauert_induced_velocity(21574.63, 78.5398, 1.225, 60.0)
  returns 1.868 m/s (spec bound 1.5 to 2.3 m/s) and that the same
  call at speed 0 returns the hover value 10.5887 m/s within 1e-6.
- Confirm the four power terms fall in the spec magnitude bounds at
  60 m/s: induced 35 000 to 50 000 W, profile 100 000 to 150 000 W,
  parasite 270 000 to 320 000 W, total 420 000 to 500 000 W.
- Confirm best_endurance_speed returns 28.0 m/s (bound 25 to 45 m/s)
  and best_range_speed returns 45.0 m/s strictly above it, with the
  P/V ratio 6832 W per (m/s) equal to the sweep minimum.
- Confirm every non-physical input raises ValueError: speed < 0,
  thrust <= 0, area <= 0, rho <= 0, f < 0, solidity <= 0, Cd0 <= 0,
  tip_speed <= 0, k <= 0.
- Confirm a forced max_iter = 2 on the Glauert iteration raises
  RuntimeError, and that the default cap converges at every default
  sweep speed.
- Run the contract test offline: python3
  scripts/test_rotorcraft_forward_flight_performance.py (34 tests,
  deterministic, no RNG).

## Pitfalls

- Treating the draft spec window as the model answer: the best range speed
  of this model at f = 2.2 m2 lands near 45 m/s (the draft 50-90 m/s window
  is not reachable); the module value is authoritative for the spec model.
- Starving the Glauert iteration: the inflow fixed point is found by
  substitution with a 60-iteration cap (RuntimeError when exhausted); the
  default 5-100 m/s sweep converges, but forcing max_iter = 2 raises
  RuntimeError by contract.
- Expecting induced power to rise with speed: induced velocity falls with
  flight speed (v ~ T/(2 rho A sqrt(V^2+v^2))) while parasite power rises as
  V^3, so best range speed always sits above best endurance speed; a lower
  range speed signals a sweep or formula error.
- Calling at V = 0 for the inflow: speed 0 returns the hover value v_h
  directly; negative speed raises ValueError.
- Using the hover power terms without the induced power factor: total power
  is k*T*v + P_profile + P_par with k = 1.15 default, matching the hover
  leaf convention.

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the
  hover companion leaf; owns the hover induced velocity, figure of
  merit and disk loading, and shares this rotor and k = 1.15.
- flight-mechanics/performance/climb-performance: fixed-wing rate of
  climb and ceilings from excess power, the climb analog.
- flight-mechanics/performance/thrust-required: fixed-wing drag and
  thrust terms against which rotorcraft power is often compared.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_forward_flight_performance.py

The test covers the worked-rotor power contract at 60 m/s (all four
magnitude bounds plus the exact module outputs), the Glauert speed
zero identity, the high-speed v_h**2 / V asymptote, the RuntimeError
failure mode, the parasite power monotonic sanity (20 m/s below
80 m/s), the default sweep shape (96 pairs from 5 to 100 m/s), the
best endurance and best range argmins with the strict ordering
physics check, and ValueError rejection of every non-physical input
class.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 29 (far-29) is
  US government work in the public domain; the momentum-theory
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
