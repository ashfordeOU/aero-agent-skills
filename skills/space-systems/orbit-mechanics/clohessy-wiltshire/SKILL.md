---
name: clohessy-wiltshire
description: "Use when you must propagate and analyze the Clohessy-Wiltshire linearized relative motion of a deputy spacecraft about a chief in a circular orbit: compute the chief mean motion, build the 6x6 relative-motion state-transition-matrix, propagate the deputy-chief relative state (x radial, y along-track, z cross-track), check the bounded relative orbit condition y_dot = -2 n x, and size the two-impulse targeting delta-v to a desired final relative state. Produces the propagated relative trajectory, the bounded-orbit verdict, the impulse budget, and a geometry sanity check with singular one-orbit and cross-track-nulling transfer times flagged. Trigger: clohessy-wiltshire, hill equations, relative-motion state-transition-matrix, deputy-chief, two-impulse targeting, along-track drift, cw propagation, relative orbit injection, cross-track offset."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: orbit-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [clohessy-wiltshire, hill-equations, relative-motion-state-transition-matrix, deputy-chief, two-impulse-targeting, along-track-drift, relative-orbit-injection, cross-track-offset]
  version: 0.1.0
  author: Aero Agent Skills
---

# Clohessy-Wiltshire Relative Motion (space-systems/orbit-mechanics/clohessy-wiltshire)

Use when the task is relative motion of a deputy spacecraft about a chief
on a circular orbit, modeled with the Clohessy-Wiltshire (Hill)
linearized equations in the local-vertical local-horizontal frame: x
radial outward, y along-track, z cross-track (right-handed about the
orbit normal). This leaf propagates the 6-state relative vector with the
closed-form CW state transition matrix, verifies the bounded
(non-drifting) relative orbit condition, and sizes the two-impulse CW
targeting maneuver, including its singular transfer times. It pairs with
gnc-autonomy/space/rendezvous-phasing, which owns the far-field
along-track offset setup that precedes a CW approach, and with
hohmann-transfer and lambert-transfer, which size absolute-orbit
transfers rather than relative motion. The linearization assumes a
circular chief orbit, no perturbations, and deputy-chief separation
small compared with the orbit radius. The model is standard engineering
methodology, summary-only against the ECSS space-engineering corpus.

## Domain quick reference

- Mean motion of the chief: n = sqrt(mu / a^3), with mu = 3.986004418e14
  m^3/s^2 and a the circular orbit radius. Orbit period T = 2*pi / n.
- CW equations of relative motion (primes are time derivatives):
  x'' - 2 n y' - 3 n^2 x = u_x,  y'' + 2 n x' = u_y,
  z'' + n^2 z = u_z.
- State transition matrix Phi(n, tau) over tau = t - t0 maps
  [x, y, z, x', y', z'](t0) to the state at t0 + tau. With C = cos(n*tau),
  S = sin(n*tau), T = n*tau, the closed form is
  x(t) = (4 - 3 C) x0 + (S/n) x'0 + (2 (1 - C)/n) y'0,
  y(t) = 6 (S - T) x0 + y0 - (2 (1 - C)/n) x'0 + ((4 S - 3 T)/n) y'0,
  z(t) = C z0 + (S/n) z'0,
  x'(t) = 3 n S x0 + C x'0 + 2 S y'0,
  y'(t) = 6 n (C - 1) x0 - 2 S x'0 + (4 C - 3) y'0,
  z'(t) = -n S z0 + C z'0.
  At tau = 0 the matrix is the identity.
- Bounded relative orbit condition: a natural-motion trajectory with no
  secular along-track growth requires y'0 = -2 n x0. When violated, the
  deputy drifts along track linearly, y(t) ~ -3 n x0 t per unit x0
  (the -6 (S - T) x0 term grows one way while the -2 (1 - C)/n x'0 term
  stays periodic).
- Two-impulse targeting: partition Phi into 3x3 blocks over the
  position and velocity groups,
  r_f = phi_rr r0 + phi_rv v0+,  v_f- = phi_vr r0 + phi_vv v0+.
  Solve v0+ = phi_rv^-1 (r_f - phi_rr r0), then delta-v0 = v0+ - v0 and
  delta-vf = vf_desired - v_f-. Total delta-v = |delta-v0| + |delta-vf|.
- Singular cases: phi_rv is singular when the transfer time tau_f is an
  integer multiple of the half orbit period. At one full orbit the
  in-plane block loses rank; at any exact half orbit sin(n*tau_f) = 0
  makes the cross-track column of phi_rv vanish, so a cross-track offset
  cannot be nulled there. Both raise ValueError.

## Workflow

1. Fix the chief orbit: semi-major axis a of the circular chief and the
   gravitational parameter mu (default 3.986004418e14). Get the mean
   motion with mean_motion(a, mu) and the period 2*pi/n.
2. Write the deputy initial relative state [x0, y0, z0, x'0, y'0, z'0]
   in the LVLH frame (x radial outward, y along-track, z cross-track).
3. Check the bounded relative orbit condition with
   bounded_orbit_condition(state0, n): it returns the required
   along-track rate -2 n x0 and whether the state already satisfies it.
   If not, either accept the along-track drift (report it) or set
   y'0 = -2 n x0.
4. Build the STM at the propagation time with cw_stm(n, tau) (identity
   at tau = 0) and propagate with cw_propagate(state0, n, tau), or
   sample the natural-motion trajectory over one or several orbits to
   confirm the return and any drift.
5. Run relative_orbit_geometry_check(r_f, min_separation) on the
   propagated position to get the geometry verdict, warning on a
   close approach below the safe standoff radius.
6. To maneuver the deputy, pick the desired final relative state at
   transfer time tau_f and call cw_targeting(state0, state_f_desired,
   n, tau_f). It returns dv0, dvf, v0_plus, vf_minus and total_dv.
7. Flag the singular transfer times: tau_f equal to one full orbit (or
   any integer half orbit with a cross-track nulling demand) raises
   ValueError from the phi_rv inversion, so choose a transfer time away
   from the singularity.
8. Confirm the deterministic checks with the contract test
   scripts/test_clohessy_wiltshire.py.

## Worked example

Chief on a ~500 km circular orbit: a = 6.878e6 m, mu = 3.986004418e14
m^3/s^2, mean motion n = 1.106817e-3 rad/s, period 5676.81 s. Deputy
initial relative state x0 = 1000 m radial, z0 = 500 m cross-track,
y0 = 0, x'0 = 0, y'0 = -2 n x0 = -2.21363 m/s (bounded condition),
z'0 = 0.

- Bounded one-orbit return: propagate one period. x returns to
  1000.000 m, y returns to 7.3e-13 m (no along-track drift, well below
  the 1% = 10 m tolerance), z returns to 500.000 m. Ten orbits still
  show no secular y growth.
- Drift case: with y'0 = 0 the condition is violated and the deputy
  drifts: y(T) = -37699.1 m after one orbit and y(2T) = -75398.2 m,
  linear growth as expected.
- Two-impulse targeting: deputy in-plane state [1000, 0, 0, 0, -2 n x0,
  0] to the chief origin in tau_f = T/2. The impulses are
  dv0 = (-0.652, +0.277, 0) m/s and dvf = (-0.652, -0.277, 0) m/s,
  total 1.857 m/s, on the order of n*|r| ~ 1.11 m/s per km of radial
  offset.
- Singular cases: the same targeting at tau_f = T (one full orbit)
  raises ValueError because phi_rv is singular; targeting with the 500 m
  cross-track offset at exactly T/2 also raises ValueError because
  sin(n*T/2) = 0 leaves no cross-track authority at the endpoint.


## Pitfalls

- Using the model outside its assumptions: CW is linearized about a
  circular chief with no perturbations and needs deputy-chief
  separation small compared with the orbit radius; the 1% return
  tolerances only hold inside that envelope.
- Mis-stating the bounded-orbit condition: y'0 must equal -2 n x0
  exactly; with y'0 = 0 the deputy drifts linearly (y(T) = -37699.1 m
  in the worked example), so "no drift" must be verified, not
  assumed, before a formation or stationkeeping design.
- Targeting at a singular transfer time: tau_f at one full orbit (or
  any integer half orbit when cross-track nulling is demanded) makes
  phi_rv singular and raises ValueError; choose the transfer time
  away from the singularity and treat the error as a design signal,
  not a numeric accident.
- Forgetting the frame: x is radial outward, y along-track, z
  cross-track (right-handed about the orbit normal); swapping the
  radial and along-track channels turns a bounded orbit into a
  drifting one.
- Checking geometry on the raw state: run
  relative_orbit_geometry_check on the propagated position, not the
  velocity or the initial offset, or a close approach below the
  standoff radius goes unnoticed.
- Confusing relative with absolute transfers: this leaf sizes
  deputy-chief maneuvers in the LVLH frame; orbit-raising and
  interplanetary legs belong to hohmann-transfer and lambert-transfer.
## Verification

- cw_stm(n, 0) is the identity within 1e-12.
- mean_motion(6.878e6) returns 1.106817e-3 rad/s, period 5676.81 s.
- The bounded-condition state propagates one orbit with x and z within
  1% of their initial values and y within 1e-6 m.
- cw_targeting to the origin at tau_f = T/2 gives total delta-v
  1.857 m/s; at tau_f = T it raises ValueError, and cross-track nulling
  at an exact half orbit raises ValueError.
- The drift case y(T) = -37699.1 m matches the linear along-track drift
  model.
- ValueError on n <= 0, tau < 0, a <= 0, non-finite states and inputs,
  singular targeting times, and non-positive min_separation.
- Run the contract test offline: python3
  scripts/test_clohessy_wiltshire.py (35 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/hohmann-transfer: absolute coplanar
  orbit transfer between circular orbits, the single-impulse-pair
  context around the chief itself.
- space-systems/orbit-mechanics/lambert-transfer: absolute orbit
  transfers between two points, not relative deputy-chief motion.
- space-systems/orbit-mechanics/low-thrust-spiral: continuous-thrust
  absolute spiral transfers, the alternative to impulsive CW burns.
- space-systems/orbit-mechanics/orbital-perturbations: J2 and drag
  secular effects on the chief orbit that the linearized model ignores.
- gnc-autonomy/space/rendezvous-phasing: the far-field along-track
  offset setup that precedes the linearized CW approach modeled here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_clohessy_wiltshire.py

The test covers the mean motion and period anchors, the STM identity at
tau = 0 and known one-orbit terms, bounded one-orbit and ten-orbit
propagation with no secular drift, the harmonic z channel, the linear
along-track drift case, the bounded-orbit condition verdicts, the
two-impulse half-orbit delta-v anchor with its order-of-magnitude check,
singular one-orbit and half-orbit cross-track rejections, the geometry
verdicts, and ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: the CW model is a standard
  result of astrodynamics (Vallado textbook form); ECSS space-engineering
  standards frame the mission context only, summary per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
