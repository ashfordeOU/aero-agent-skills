---
name: kepler-orbit-propagation
description: "Use when you must determine the time propagation of a spacecraft orbit from its classical orbital elements: mean motion from the semimajor axis, the Kepler equation M = E - e sin E solved by Newton iteration for the eccentric anomaly, the branch-safe half-angle conversion to true anomaly, the radius at any anomaly, the time since periapsis for a given true anomaly, and the inertial position and velocity vectors after an elapsed time from an element state (a, e, i, RAAN, argp, nu0). Produces the propagated mean, eccentric and true anomalies, radius, r vector, v vector and orbital period for ground-track and event timing. Trigger: keplerian propagation, kepler equation, mean anomaly, eccentric anomaly, time since periapsis, orbit propagation."
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
  tags: [kepler-orbit-propagation, keplerian-propagation, kepler-equation, mean-anomaly, eccentric-anomaly, time-since-periapsis]
  version: 0.1.0
  author: AeroSkills
---

# Kepler Orbit Propagation (space-systems/orbit-mechanics/kepler-orbit-propagation)

Use when you must propagate a spacecraft orbit in time from its
classical orbital elements: mean motion from Kepler's third law, the
Kepler equation M = E - e sin E solved by Newton iteration, the
eccentric-to-true anomaly conversion, the radius at any anomaly, the
time since periapsis, and the full inertial position and velocity
after an elapsed time. This leaf implements the standard two-body
propagation model in pure Python, stdlib only. It pairs with
space-systems/orbit-mechanics/keplerian-elements, which extracts
elements from a state; this leaf is the forward direction, elements
to state in time. It does NOT extract elements from a state vector,
add perturbation drift, size impulsive maneuvers or solve two-position
targeting; those are sibling leaves.

## Domain quick reference

- Inputs: semimajor axis a (km), eccentricity e in [0, 1),
  inclination i, RAAN, argument of periapsis argp and initial true
  anomaly nu0 (rad), elapsed time dt (s), mu in km^3/s^2 (default
  398600.4418, Earth).
- Mean motion: n = sqrt(mu / a^3); period T = 2 pi / n.
- Initial mean anomaly from nu0: E0 via the inverse half-angle map,
  then M0 = E0 - e sin E0. Propagation: M = M0 + n dt.
- Kepler equation: M = E - e sin E, solved for E by Newton iteration
  E -= (E - e sin E - M) / (1 - e cos E) from E = M + e sin M to a
  1e-12 residual (cap 100 iterations).
- Eccentric anomaly to true anomaly: nu = 2 atan2(sqrt(1 + e)
  sin(E / 2), sqrt(1 - e) cos(E / 2)), branch-safe, folded to
  (-pi, pi]; the inverse map uses the mirrored half-angle form.
- Radius: r = a (1 - e cos E), identical to the conic form
  r = a (1 - e^2) / (1 + e cos nu).
- Inertial state: perifocal position r (cos nu, sin nu) and velocity
  sqrt(mu / p) (-sin nu, e + cos nu) with p = a (1 - e^2), rotated by
  M = R3(-RAAN) R1(-i) R3(-argp) (classical rotation matrix forms).
- Time since periapsis: t = (E - e sin E) / n for the anomaly nu,
  folded into [0, T).
- Non-physical inputs raise ValueError: a <= 0, mu <= 0, e outside
  [0, 1), dt < 0.

## Workflow

1. Validate the element state and mu; fix a > 0, e in [0, 1), dt >= 0.
2. Get the mean motion and period with mean_motion and orbital_period.
3. Map the starting true anomaly nu0 back to E0 with
   eccentric_anomaly_from_true, then form M = M0 + n dt.
4. Solve the Kepler equation with kepler_solve(M, e) for E.
5. Convert E to nu with true_anomaly_from_eccentric and read the
   radius from r = a (1 - e cos E), cross-checked by
   radius_at_anomaly with the conic form.
6. Call propagate_kepler for the packed result: mean, eccentric and
   true anomaly, radius, position_km, velocity_kms and period_s.
7. For event timing, get the time since periapsis of any anomaly with
   time_since_periapsis; confirm the Kepler identities with the
   contract test scripts/test_kepler_orbit_propagation.py.

## Worked example

Reference orbit a = 12000 km, e = 0.35, i = 30 deg, RAAN = 45 deg,
argp = 20 deg, starting at periapsis (nu0 = 0), dt = 3600 s, Earth mu.
Module outputs:

- n = 4.80283e-4 rad/s; T = 13082.262 s (3.634 h).
- M = 1.729018 rad; E = 2.041030 rad; nu = 2.336674 rad
  (133.8815 deg).
- r = 13902.9969 km; speed = 4.911570 km/s, consistent with the
  specific orbital energy relation v^2 = mu (2 / r - 1 / a).
- Inertial state: r = (-12575.051, -5079.004, 3060.248) km,
  v = (-0.292236, -4.579770, -1.750378) km/s.
- After one period (dt = T): nu returns to 0.000000 (mod 2 pi) and
  r = 7800.000000 km = a (1 - e); M = E = 2 pi.
- time_since_periapsis of the propagated nu recovers
  3600.000000 s (inverse time of flight).
- Radius identity: a (1 - e cos E) equals a (1 - e^2) / (1 + e cos nu)
  to 1.8e-12 km. Recovering a and e from the propagated r, v state
  (energy and angular momentum identities) gives a to 3.0e-16
  relative and e to 1.1e-16 absolute.

## Verification

- Confirm kepler_solve(1.729018..., 0.35) returns E = 2.041030 rad
  with a residual below 1e-12 and that E = M exactly for e = 0.
- Confirm the radius from r = a (1 - e cos E) matches the conic form
  to 1e-9 relative at the worked state.
- Confirm a full-period propagation returns the initial anomaly and
  radius a (1 - e) to 1e-9, and that dt = 0 leaves the state unchanged.
- Confirm time_since_periapsis inverts the propagation for any dt
  inside one period (to 1e-6 and better).
- Confirm the propagated r, v lie in the orbital plane: the angular
  momentum direction equals (sin RAAN sin i, -cos RAAN sin i,
  cos i) to 1e-9 and |h| = sqrt(mu a (1 - e^2)).
- Confirm ValueError rejection of a <= 0, mu <= 0, e < 0 or e >= 1,
  dt < 0 and malformed vectors.
- Run the contract test offline: python3
  scripts/test_kepler_orbit_propagation.py (35 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/keplerian-elements: the inverse map,
  a position and velocity state back to classical elements; this leaf
  is elements to state in time.
- gnc-autonomy/space/orbit-dynamics: the two-body mission context
  that consumes propagated states.
- space-systems/orbit-mechanics/lambert-transfer: two-position
  targeting, the boundary case this leaf does not cover.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_kepler_orbit_propagation.py

The test covers the worked-example anchors (mean motion, period, M,
E, nu, radius, speed), the Newton solver residual across anomaly and
eccentricity grids including e = 0.99, exact e = 0 behavior, the
anomaly maps and their round trips, the radius identity, the
one-period return, dt = 0 invariance, the inverse time of flight, the
perifocal rotation against the closed-form periapsis direction, the
angular momentum direction and magnitude, orbit-plane membership,
determinism, and ValueError rejection of every non-physical input
class.

## Compliance

- Standards referenced, not reproduced: ECSS series text is copyright
  ESA and freely downloadable (standards-map.yaml); the two-body
  propagation relations above are common astrodynamics methodology,
  summary-only.
- compliance: STANDARDS-REF, gated: false.
