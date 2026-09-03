# Wave-24R leaf spec: clohessy-wiltshire (space-systems)

- Path: skills/space-systems/orbit-mechanics/clohessy-wiltshire/
- Pack: orbit-mechanics (existing: eclipse-time, ground-track-repeat,
  hohmann-transfer, keplerian-elements, lambert-transfer, low-thrust-spiral,
  orbital-decay, orbital-perturbations, satellite-coverage,
  sun-synchronous-inclination)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: space-systems

## Claim

Relative motion of a deputy spacecraft about a chief in a circular
orbit using the Clohessy-Wiltshire (Hill) linearized equations:
propagate the relative state (x radial, y along-track, z cross-track)
with the CW state transition matrix, compute the natural-motion
trajectory, check the relative-orbit stability condition, and size a
two-impulse CW targeting maneuver (delta-v for rendezvous or for a
relative orbit injection). Produces the propagated relative trajectory,
the delta-v budget, and a collision/geometry sanity verdict.

Does NOT do: phasing-orbit planning by drift rate (gnc-autonomy/space/
rendezvous-phasing owns the along-track phasing maneuver), full
nonlinear relative motion with J2, Lambert targeting
(lambert-transfer), absolute orbit propagation. This leaf is the
linearized CW model around a circular chief.

## Model (implement exactly)

CW equations (chief circular orbit, mean motion n = sqrt(mu/a^3),
mu = 3.986004418e14 m^3/s^2):
- x'' - 2 n y' - 3 n^2 x = u_x
- y'' + 2 n x' = u_y
- z'' + n^2 z = u_z
(primes are time derivatives; x radial outward, y along-track, z
cross-track; the sign convention documented).

State transition matrix (STM) from t0 to t (tau = t - t0) for the
6-state [x, y, z, x', y', z']:
Classical CW STM (4x4 for in-plane, 2x2 for cross-track; implement the
standard closed form):
- phi_xx = 4 - 3*cos(n*tau); phi_xy = sin(n*tau)/n;
  phi_xvx = sin(n*tau)/n; ... implement the full standard matrix:
  [ x  ]   [ 4-3C    0       0     S/n      2(1-C)/n   0    ]
  [ y  ]   [ 6(S-nT) 1       0    -2(1-C)/n (4S-3nT)/n 0    ]
  [ z  ] = [ 0       0       C     0        0          S/n  ] * state0
  [ x' ]   [ 3nS     0       0     C        2S         0    ]
  [ y' ]   [ 6n(C-1) 0       0    -2S       4C-3       0    ]
  [ z' ]   [ 0       0      -nS    0        0          C    ]
  with C = cos(n*tau), S = sin(n*tau), T = n*tau.
  Verify your matrix against the textbook form (e.g. Vallado) and assert
  the identity: for tau -> 0 the STM -> identity.
- cw_propagate(state0, n, tau) -> state(tau)
Natural motion: bounded relative orbit when x'0 = -n*(2*y0? check the
standard condition: a bounded (non-drifting) relative orbit requires
y_dot0 = -2 n x0 (the along-track rate condition); if violated, the
deputy drifts along track linearly; report drift flag. Verify the exact
sign with the chosen convention and assert that with the condition
satisfied y(t) has no secular term (test by propagating 10 orbits and
checking y returns near its initial value).
Two-impulse targeting (CW rendezvous/targeting):
- Given the initial relative state and the desired final relative state
  at time tau_f, compute the required first impulse delta-v0 and final
  impulse delta-vf via the STM partition:
  [r_f]   [phi_rr  phi_rv] [r_0]     [0]
  [v_f+] = [phi_vr  phi_vv] [v_0+] ;  [delta-v_f]
  Solve for v_0+ = phi_rv^-1 (r_f - phi_rr r_0), then
  delta-v0 = v_0+ - v_0, delta-vf = v_f_desired - v_f- where
  v_f- = phi_vr r_0 + phi_vv v_0+.
  Implement the 3x3 inversion with a small deterministic solver (pure
  stdlib, no numpy: write a 3x3 inverse by cofactors; raise ValueError
  on a singular phi_rv, which happens at integer half-orbit
  rendezvous times, and report the singularity case).
- Total delta-v = |delta-v0| + |delta-vf|.
Functions:
- mean_motion(a, mu)
- cw_stm(n, tau) -> 6x6 matrix (list of lists)
- cw_propagate(state0, n, tau)
- bounded_orbit_condition(state0, n) -> (required_y_dot, flag)
- cw_targeting(state0, state_f_desired, n, tau_f) -> (dv0, dvf,
  v0_plus, vf_minus, total_dv)
- relative_orbit_geometry_check(r_f, min_separation) -> verdict (warn
  on collision radius crossing)
ValueError on: n <= 0, tau < 0, non-finite state, singular phi_rv
(targeting at the half-orbit singularity), a <= 0.

## Worked example

Chief in a 500 km circular orbit (a = 6878.137 km? use
a = 6.878e6 m; mu = 3.986004418e14 -> n = sqrt(mu/a^3) ~= 1.1067e-3
rad/s; period ~ 5677 s). Deputy initial relative state:
x0 = 1000 m (radial), y0 = 0, z0 = 500 m, velocities 0, and set
y_dot0 = -2*n*x0 (bounded condition). Anchors (from your module):
- The bounded-condition trajectory: over one orbit (tau = period), y
  returns to ~0 and x ~1000 m within a small tolerance (assert < 1%
  drift over 1 orbit; the linearized model has a small along-track
  offset over exactly one period: assert the real value and quote it).
- Targeting: from the initial state to the origin (r_f = 0, v_f = 0)
  at tau_f = 0.5*period: assert total delta-v is finite and on the
  order of n*|r| (n*1000 ~ 1.1 m/s per 1000 m of offset; the exact
  value from your run is the anchor).
- Singular case: targeting to r_f = 0 at tau_f exactly one orbit gives
  a singular phi_rv -> ValueError (assert).
- STM identity: cw_stm(n, 0) is the identity matrix (within 1e-12).
- Drift: with y_dot0 = 0 (condition violated) the along-track position
  grows linearly (assert y after 1 orbit differs from y0 by a large
  along-track drift ~ -3*n*x0*T? assert with your computed value).
- ValueError rejections.

## Corpus tasks (2 tasks, ids w24r-clohessy-wiltshire-1/2)

Distinctive tokens: clohessy-wiltshire, hill equations, relative-motion
state-transition-matrix, deputy-chief, two-impulse targeting, along-
track drift. Avoid: "phasing", "drift rate to cover a phase angle",
"rendezvous phasing maneuver", "closing rate" (the gnc rendezvous-
phasing claim), "lambert", "hohmann".

1. "propagate the deputy relative motion about the chief in its 500 km
   circular orbit with the Clohessy-Wiltshire state transition matrix:
   the deputy starts 1 km radial and 500 m cross-track away, check the
   bounded relative orbit condition, and report the trajectory after one
   orbit"
2. "size the two-impulse Clohessy-Wiltshire targeting maneuver to bring
   the deputy to the chief origin at the half-orbit transfer time and
   compute the total delta-v, flagging the singular one-orbit transfer
   case"

## SKILL body notes

Pair with gnc-autonomy/space/rendezvous-phasing (the phasing maneuver
that sets the along-track offset before the CW approach), hohmann and
lambert (absolute-orbit transfers), low-thrust-spiral. Worked example
uses the values above. Document the linearization assumptions (circular
chief, no perturbations, small separation).
