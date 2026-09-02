---
name: keplerian-elements
description: "Use when you must compute classical orbital elements from a position and velocity state vector: derive the specific angular momentum, node vector and eccentricity vector, then convert to semimajor axis, eccentricity, inclination, right ascension of the ascending node (RAAN), argument of periapsis and true anomaly, and derive the orbital period with periapsis and apoapsis radii for an elliptical Earth orbit. Handles circular and equatorial degenerate cases with documented conventions and raises on parabolic or hyperbolic inputs. Uses Earth gravitational parameter 398600.4418 km^3/s^2 by default. Trigger: keplerian elements, orbital elements, rv2coe, state vector, raan, argument of periapsis, true anomaly, semimajor axis, eccentricity, inclination, orbital period, periapsis, apoapsis."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [keplerian-elements, orbital-elements, rv2coe, state-vector, raan, argument-of-periapsis, true-anomaly, inclination, semimajor-axis, eccentricity, orbital-period, periapsis, apoapsis]
  version: 0.1.0
  author: Aero Agent Skills
---

# Keplerian Elements (space-systems/orbit-mechanics/keplerian-elements)

Use when the task is converting a spacecraft position and velocity
state vector into the classical (keplerian) orbital elements:
semimajor axis, eccentricity, inclination, right ascension of the
ascending node (RAAN), argument of periapsis, and true anomaly, plus
the orbital period and the periapsis and apoapsis radii of an
elliptical orbit.

## Domain quick reference

- Input: position r (km) and velocity v (km/s) in an inertial frame,
  gravitational parameter mu in km^3/s^2 (default 398600.4418, Earth).
- Specific angular momentum: h = r x v (km^2/s).
- Node vector: n = k x h with k = (0, 0, 1); zero when equatorial.
- Eccentricity vector: e_vec = (v x h) / mu - r / |r|; e = |e_vec|.
- Specific energy: epsilon = v^2 / 2 - mu / |r| (km^2/s^2).
- Semimajor axis: a = -mu / (2 epsilon); parabolic (epsilon ~ 0)
  raises ValueError, hyperbolic returns negative a.
- Inclination: i = acos(h_z / |h|) in radians, range [0, pi].
- RAAN: Omega = atan2(n_y, n_x); convention 0.0 when equatorial.
- Argument of periapsis: omega = acos(n . e_vec / (|n| e)), corrected
  to 2 pi - omega when e_z < 0; equatorial convention
  atan2(e_y, e_x); circular convention 0.0.
- True anomaly: nu = acos(e_vec . r / (e |r|)), corrected to
  2 pi - nu when r . v < 0; circular convention measured from the
  node vector; circular equatorial atan2(r_y, r_x).
- Orbital period: T = 2 pi sqrt(a^3 / mu) in seconds; elliptical
  orbits only (raises ValueError for a <= 0).
- Periapsis and apoapsis radii: rp = a (1 - e), ra = a (1 + e);
  elliptical orbits only (raises ValueError for e >= 1).

## Workflow

1. Validate r, v and mu; raise ValueError on non-finite entries,
   wrong length, zero radius or mu <= 0.
2. Compute h with specific_angular_momentum and check |h| > 0,
   else ValueError for a rectilinear (radial) trajectory.
3. Compute n, e_vec, epsilon, then a, e, i and Omega with the
   standalone helpers.
4. Apply the circular and equatorial conventions when computing
   omega and nu with argument_of_periapsis and true_anomaly.
5. Compute T, rp and ra with orbital_period and
   periapsis_apoapsis_radii for elliptical orbits.
6. Pack the full solution with keplerian_elements(r, v, mu) and
   check the returned dict for consistency.

## Pitfalls

- Feeding degrees where radians are expected; every angle out is
  radians.
- Skipping the 2 pi corrections: acos alone is sign-ambiguous, the
  r . v test (for nu) and the e_z test (for omega) resolve it.
- Calling orbital_period or periapsis_apoapsis_radii on parabolic or
  hyperbolic orbits: they raise ValueError instead of returning
  nonsense.
- Forgetting that e ~ 0 (circular) or |n| ~ 0 (equatorial) makes
  acos(0/0) undefined, hence the documented conventions.
- Mixing units, e.g. r in km with v in m/s, silently corrupts every
  element.

## Behavior contract (gate 3)

The rv2coe logic is exercised by the gate 3 contract test:
scripts/test_keplerian.py against scripts/keplerian_logic.py (stdlib
unittest, offline). Run: python3 scripts/test_keplerian.py

## Compliance

- Standards referenced, not reproduced: ECSS series text is copyright
  ESA and freely downloadable (standards-map.yaml); the two-body
  rv2coe conversion is common astrodynamics, summary-only.
- compliance: STANDARDS-REF, gated: false.
