---
name: point-mass-trajectory
description: "Use when you must simulate the point-mass trajectory of an aircraft climbing out in the vertical plane: propagate speed, flight-path angle and altitude with the energy-state point-mass equations, integrate the state with a fixed time-step RK4 scheme, apply the thrust altitude lapse and parabolic drag polar, and report the speed-altitude history, load factor and steady-climb consistency versus the closed-form excess-thrust climb angle. Produces the time histories of V, gamma, h and x with per-step lift, drag, thrust and load factor. Trigger: point-mass trajectory, flight-path angle, RK4 integration, time-step integration, vertical-plane profile, speed-altitude history, point-mass equations, fixed-alpha climb."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-dynamics-sim
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: flight-dynamics-sim
  tags: [point-mass-trajectory, point-mass-equations, flight-path-angle, trajectory-simulation, rk4-integration, time-step-integration, vertical-plane-profile, speed-altitude-history, fixed-alpha-climb, thrust-altitude-lapse]
  version: 0.1.0
  author: Aero Agent Skills
---

# Point-Mass Trajectory (flight-mechanics/flight-dynamics-sim/point-mass-trajectory)

Use when the task is the numerical trajectory simulation of an aircraft
climbing out in the vertical plane with the point-mass equations of
motion: propagate speed, flight-path angle and altitude along the
flight path with a thrust model that has altitude lapse and a parabolic
drag polar, and check the result against the closed-form steady-climb
excess-thrust angle. The trajectory oscillates in the classical phugoid
sense when the constant lift coefficient leaves excess thrust: the
aircraft pitches up as speed grows, decelerates, and the cycle repeats,
while the net climb persists. This leaf pairs with
flight-mechanics/flight-dynamics-sim/six-dof-simulation, the full
rigid-body counterpart that keeps the body-axis state; with
flight-mechanics/performance/energy-height for the analytic energy
state; and with flight-mechanics/performance/climb-performance for the
analytic steady climb.

## Domain quick reference

State vector (V, gamma, h, x): true airspeed V in m/s, flight-path
angle gamma in radians, altitude h in m, range x in m.

- dV/dt = (T - D)/m - g0*sin(gamma)
- dgamma/dt = (L - W*cos(gamma))/(m*V)
- dh/dt = V*sin(gamma)
- dx/dt = V*cos(gamma)

with W = m*g0, L = q*S*CL, D = q*S*CD, q = 0.5*rho*V^2,
CD = CD0 + K*CL^2, K = 1/(pi*e*AR). The load factor is n = L/W.

- Thrust altitude lapse: T = T_sl*(rho(h)/rho_sl)^0.7 at the default
  exponent, with T_sl the total sea-level installed thrust.
- ISA atmosphere: troposphere T_K = 288.15 - 0.0065*h,
  p = 101325*(T_K/288.15)^5.2561, rho = p/(287.05*T_K) below 11000 m;
  isothermal stratosphere above with p = 22632*exp(-(h-11000)/6341.62).
- Closed-form steady-climb angle (L = W, cos(gamma) ~ 1):
  CL = 2*W/(rho*V^2*S), CD from the polar, sin(gamma) = (T - D)/W.
- RK4 fixed-step integration: state update combines the derivative
  evaluations k1..k4 with the weights (k1 + 2k2 + 2k3 + k4)/6.
- Simulation holds a constant lift coefficient CL, a fixed-alpha
  climb assumption: the load factor evolves with speed, and a
  stall/limit event is flagged when the commanded or level-flight trim
  CL would exceed the input CL_max.

## Workflow

1. Fix the aircraft: mass m, wing area S, CD0, Oswald efficiency e,
   aspect ratio AR (the induced drag factor K = 1/(pi*e*AR) follows),
   total sea-level thrust T_sl, and the constant lift coefficient CL.
2. Set the initial state (V0, gamma0, h0, x0) and the integrator
   settings dt and n_steps.
3. Get the atmosphere at the current altitude with isa_atmosphere and
   the thrust with thrust_at_altitude; per step the dynamic pressure
   q, the drag coefficient drag_polar_cd and the forces L, D follow.
4. Propagate one step with rk4_step (point_mass_derivs supplies the
   four derivatives) and record the derived q, CL, CD, L, D, T, load
   factor and stall event.
5. Run the full profile with simulate_trajectory and read the state
   and derived histories; the altitude is clamped at the ground
   reference so a phugoid trough cannot drive the ISA lookup negative.
6. Cross-check the steady climb: end_of_sim_summary gives the final
   state, net climb and range, and steady_climb_angle gives the
   closed-form excess-thrust climb angle at the end-state speed and
   altitude. Compare sin(gamma) of the closed form with the mean
   sin(gamma) over the last 50 s of the propagated flight-path angle.
7. Confirm the deterministic checks with the contract test
   scripts/test_point_mass_trajectory.py.

## Worked example

Transport-like climb-out: m = 70000 kg, S = 122.6 m^2, CD0 = 0.021,
e = 0.81, AR = 9.3, T_sl = 2*110000 N, rho_sl = 1.225 kg/m^3,
CL = 1.07 (tuned fixed-alpha value), from h0 = 0, V0 = 90 m/s,
gamma0 = 0, with dt = 0.5 s over n_steps = 600 (t = 300 s).

- Initial acceleration: dV/dt = 2.54 m/s^2 at t = 0, so the airplane
  accelerates into the climb with the excess thrust.
- Altitude at t = 300 s: h = 4788 m (inside the 1500-5000 m band),
  V = 172.7 m/s, net climb 4788 m over 29221 m of range. The
  trajectory carries a phugoid oscillation (flight-path angle swings
  roughly -20 deg to +43 deg) around a persistent climb trend; the
  ground-reference clamp keeps the troughs at the runway plane.
- Load factor peaks near 2.1 as the fixed CL over-lifts at high speed;
  stall/limit events are flagged in the low-speed troughs where the
  level-flight trim CL would exceed CL_max = 1.5.
- Steady-climb consistency at the end state: closed-form
  sin(gamma) = (T - D)/W gives gamma = 9.49 deg at V = 172.7 m/s,
  h = 4788 m; the mean sin(gamma) over the last 50 s of the run is
  0.128, a ratio of 0.78 against the closed-form value, well inside
  the 30% consistency band.

## Verification

- Confirm isa_atmosphere gives rho = 1.225 kg/m^3 at h = 0 (within
  0.5%) and rho = 0.3639 kg/m^3 at h = 11000 m (within 1%), with
  density monotonically decreasing to 20000 m.
- Confirm the level cruise identity: with CL set so L = W and T = D
  at the cruise speed, dV/dt and dgamma/dt are zero, and 10 RK4 steps
  at that state keep the speed within 0.5% of the cruise value.
- Confirm the worked-example anchors: dV/dt(t=0) > 0, h(t=300) = 4788
  m inside the 1500-5000 m band, and the mean sin(gamma) over the
  last 50 s within 30% of the closed-form excess-thrust climb angle.
- Confirm every non-physical input raises ValueError: non-positive
  mass, wing area, thrust, dt or n_steps, V0 <= 0, negative altitude,
  CD0 < 0, e outside (0, 1], AR <= 0.
- Run the contract test offline: python3
  scripts/test_point_mass_trajectory.py (34 tests, deterministic).

## Related leaves

- flight-mechanics/flight-dynamics-sim/six-dof-simulation: full
  rigid-body six degree of freedom counterpart with the body-axis
  state vector.
- flight-mechanics/performance/energy-height: analytic energy-state
  analysis without integration.
- flight-mechanics/performance/climb-performance: analytic steady
  climb and rate-of-climb relations.
- flight-mechanics/performance/descent-performance: the descent
  counterpart of the analytic climb legs.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_point_mass_trajectory.py

The test covers the ISA atmosphere anchors, the parabolic drag polar,
the thrust altitude lapse, the point-mass derivatives, the fixed-step
RK4 propagator with the ground-reference clamp, the worked-example
climb-out anchors (initial acceleration positive, h(t = 300 s) =
4788 m inside the 1500-5000 m band), the level-cruise force balance
identity and RK4 round trip, the steady-climb consistency ratio against
the closed-form excess-thrust angle, the stall/limit event records, and
ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 frame the
  transport climb and performance context; the point-mass relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
