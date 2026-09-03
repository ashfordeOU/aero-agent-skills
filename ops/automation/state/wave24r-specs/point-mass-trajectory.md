# Wave-24R leaf spec: point-mass-trajectory (flight-mechanics)

- Path: skills/flight-mechanics/flight-dynamics-sim/point-mass-trajectory/
- Pack: flight-dynamics-sim (existing: six-dof-simulation)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-mechanics

## Claim (what this leaf does, and does NOT)

Point-mass trajectory simulation of an aircraft in the vertical plane:
propagate speed, flight-path angle, and altitude along the flight path
with the energy-state point-mass equations, using a thrust model with
altitude lapse and a parabolic drag polar. Produces the time histories
of V, gamma, h, x, the load factor, and a steady-climb consistency
check against the closed-form excess-thrust climb angle.

Does NOT do: six-DOF rigid-body simulation (six-dof-simulation), analytic
energy-height/Ps analysis without integration (energy-height), or
analytic climb/descent legs (climb-performance, descent-performance).
This leaf is the numerical integration of the point-mass model.

## Equations (implement exactly; module constants at top)

State derivatives (flat Earth, no wind, symmetric flight in the vertical
plane, alpha small so T along the velocity vector):
- dV/dt = (T - D)/m - g0*sin(gamma)
- dgamma/dt = (L - W*cos(gamma))/(m*V)
- dh/dt = V*sin(gamma)
- dx/dt = V*cos(gamma)
with W = m*g0, L = q*S*CL, D = q*S*CD, q = 0.5*rho(h)*V^2,
CD = CD0 + K*CL^2, K = 1/(pi*e*AR).

Thrust model (module constants, simple altitude lapse):
- T = T_sl * (rho(h)/rho_sl)^thrust_lapse_exponent   (default exponent 0.7, input)
  T_sl is the total sea-level installed thrust input.

Atmosphere model (keep inside logic file, do NOT import cross-cutting
skills): ISA troposphere below 11000 m:
- T_K = 288.15 - 0.0065*h;  p = 101325*(T_K/288.15)^5.2561;
  rho = p/(287.05*T_K). Above 11000 m use the isothermal stratosphere:
  p = 22632*exp(-(h-11000)/6341.62); rho = p/(287.05*216.65).

Limits and defaults:
- CL is bounded by the input CL_max (default 1.5) through the load
  factor; if trim CL would exceed CL_max the sim flags a stall/limit
  event and holds CL at CL_max (documented assumption).

Integration: RK4 with a fixed time step dt (default 0.5 s) over n_steps.

## Functions (stdlib logic file <leaf>_logic.py)

- isa_atmosphere(h) -> dict with T_K, p, rho at geopotential altitude h (m)
- drag_polar_cd(cd0, k, cl) -> cd
- thrust_at_altitude(thrust_sl, rho, rho_sl, exponent) -> T
- point_mass_derivs(state, params) -> [dVdt, dgamma_dt, dhdt, dxdt]
- rk4_step(state, params, dt) -> new state
- simulate_trajectory(initial_state, params, dt, n_steps) -> list of states
  and per-step derived values (q, CL, CD, L, D, T, load_factor)
- steady_climb_angle(velocity, thrust, mass, cd0, k, wing_area, rho, g0)
  -> (gamma_deg, cl, cd) closed-form: solve L = W (cos ~ 1 for the check:
  use CL = 2*W/(rho*V^2*S), CD from polar, sin(gamma) = (T-D)/W).
- convergence/consistency: end_of_sim_summary(states) -> dict

ValueError on: non-positive mass, wing area, thrust, dt, n_steps, V0 <= 0;
negative altitude input; CD0 < 0; e outside (0,1]; AR <= 0.

## Worked example (run your module to get exact values, then assert)

Transport-like climb: m = 70000 kg, S = 122.6 m^2, CD0 = 0.021,
e = 0.81, AR = 9.3, T_sl = 2*110000 N, rho_sl = 1.225 kg/m^3,
start at h0 = 0, V0 = 90 m/s, gamma0 = 0, dt = 0.5 s, n_steps = 600.
Sanity anchors you MUST see (tolerances in tests):
- The initial acceleration dV/dt is positive and the airplane climbs.
- At t = 300 s the altitude is between 1500 and 5000 m (exact value from
  your run; the sim should climb roughly 4000-7000 m over 300 s with
  this thrust-to-weight near 0.32).
- Steady-climb consistency: at the end state, closed-form
  sin(gamma) = (T - D)/W at the end-state speed and altitude is within
  30% of the numerically propagated gamma trend late in the run
  (assert a tolerance that your real output satisfies; report the number
  in the SKILL body).

Test identities:
- ISA: at h=0 rho=1.225 (within 0.5%); at h=11000 rho ~= 0.3639 kg/m^3
  (within 1%); density decreases monotonically to 20000 m.
- In level cruise force balance: with CL set so L=W and T=D, dV/dt and
  dgamma/dt are ~0 (feed a cruise state, expect near-zero derivatives).
- RK4 round trip: simulate level flight at the exact cruise speed for
  10 steps; speed stays within 0.5% of the cruise value.
- ValueError rejection tests for each invalid input class.

## Corpus tasks (2 tasks, ids w24r-point-mass-trajectory-1/2)

Distinctive tokens to use in queries (they must appear): point-mass,
trajectory simulation, flight-path angle, RK4 integration (use
"time-step integration" too), vertical-plane profile, speed-altitude
history. Avoid: "six degree of freedom", "quaternion", "body axis",
"energy height", "specific excess power", "breguet" (sibling claims).

1. "simulate the point-mass trajectory of my transport climbing out:
   integrate the vertical-plane speed, flight-path angle and altitude
   with a fixed time-step RK4 scheme from the sea-level takeoff state,
   with the thrust altitude lapse and parabolic drag polar, and report
   the speed and altitude history at 300 seconds"
2. "build a point-mass trajectory simulation for the climb profile of
   the aircraft from the thrust-to-weight and drag polar inputs,
   propagate the flight-path angle and rate of climb over time, and
   compare the late-run flight-path angle with the closed-form
   steady-climb excess-thrust value"

## SKILL body notes

Pair with six-dof-simulation (full rigid-body counterpart), energy-height
(analytic energy state), climb-performance (analytic steady climb).
Worked example section uses the parameters above. Verification section
lists the identities and the contract test command.
