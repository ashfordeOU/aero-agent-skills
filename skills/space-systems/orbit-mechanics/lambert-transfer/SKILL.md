---
name: lambert-transfer
description: "Use when you must solve Lambert's problem for a spacecraft orbit transfer: given two position vectors and a transfer time, find the connecting orbit with the p-iteration method, compute the velocity vectors at both endpoints, the transfer delta-v against circular parking orbits, and the transfer ellipse elements. Produces the semimajor axis, eccentricity, semilatus rectum, the required endpoint velocities, the delta-v budget, and the time-of-flight check, with short-way and long-way branches, the 180-degree case reducing to the Hohmann transfer as a sanity check, and multi-revolution transfers as an extension. Trigger: lambert-transfer, lambert-problem, p-iteration, time-of-flight, two-position, transfer-time, short-way, long-way, multi-revolution."
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
  tags: [lambert-transfer, lambert-problem, p-iteration, transfer-time, time-of-flight, two-position-transfer, short-way, long-way, multi-revolution, delta-v]
  version: 0.1.0
  author: Aero Agent Skills
---

# Lambert Transfer (space-systems/orbit-mechanics/lambert-transfer)

Use when the task is solving Lambert's problem: given two position
vectors and a transfer time, find the connecting orbit, the required
velocity vectors at both endpoints, the transfer delta-v, and the
transfer ellipse elements. Covers the p-iteration method, the short-way
and long-way branches, the degenerate 180-degree Hohmann case, and the
multi-revolution extension.

## Domain quick reference

- The Lambert problem: given the two position vectors r1 and r2 (km)
  and the transfer time tof (s), find the conic orbit that connects
  them in that time. With mu the gravitational parameter
  (398600.4418 km^3/s^2 for Earth), the orbit plane is the plane of r1
  and r2 and the sweep angle is the angle between the vectors.
- Transfer geometry: the chord c = sqrt(r1^2 + r2^2 - 2 r1 r2 cos(delta))
  and the semiperimeter s = (r1 + r2 + c) / 2 frame the problem; the
  minimum-energy ellipse has semimajor axis a = s / 2.
- p-iteration: for a trial semilatus rectum p the conic through the two
  points is fully determined (the eccentricity follows from the radii
  and the sweep angle), the time of flight follows from Kepler's
  equation through the eccentric anomalies at both endpoints, and p is
  iterated until the computed time matches tof. The elliptic range of p
  sits between the two parabolic limits where e = 1.
- Time of flight: t = sqrt(a^3 / mu) * ((E2 - E1) - e (sin E2 - sin E1))
  with E the eccentric anomaly at each endpoint. A 90-degree transfer
  between 7210 km and 10499 km on the ellipse a = 12000 km, e = 0.4
  takes about 1736 s (28.9 min).
- Endpoint velocities: v_r = sqrt(mu / p) e sin(nu) radial and
  v_theta = sqrt(mu / p) (1 + e cos(nu)) transverse, resolved in the
  motion frame at both true anomalies. The velocity vectors at r1 and
  r2 are the burns the spacecraft must fly.
- Delta-v against circular parking orbits: dv = sqrt(v_r1^2 +
  (v_theta1 - v_c1)^2) + sqrt(v_r2^2 + (v_theta2 - v_c2)^2) with v_c the
  circular speeds, assuming the parking orbits match the transfer
  direction. The 90-degree example above totals about 3.88 km/s.
- Short way vs long way: the short-way branch sweeps the smaller angle
  delta < 180 degrees, the long-way branch the complement
  2*pi - delta; both are valid Lambert solutions and the solver takes a
  direction argument. The same ellipse (a = 20000 km, e = 0.4, nu1 =
  30 degrees) gives a 120-degree short-way arc of about 8391 s (2.33 h)
  and a 240-degree long-way arc of about 23651 s (6.57 h).
- 180-degree case: r2 anti-parallel to r1 degenerates the p-iteration
  (cos(delta/2) = 0) and is solved in closed form as the Hohmann
  transfer, the sanity check for the whole method. A half-orbit coast
  at 7000 km radius takes 2914 s (48.6 min) with zero delta-v, and the
  low-earth to geostationary 180-degree transfer (6878 km to 42164 km)
  takes 19107 s (5.31 h) with 3.82 km/s total, matching the Hohmann
  budget.
- Multi-revolution extension: for very long transfer times the orbit
  may wind M full revolutions plus the connecting arc, tof = M * T +
  t_arc with T the orbit period; the solver returns the multi-revolution
  solution when max_revs requests it.
- Vis-viva: v^2 = mu * (2 / r - 1 / a) ties each endpoint speed to the
  semimajor axis and is the energy-consistency check for any returned
  velocity pair.
- Specific orbital energy: epsilon = -mu / (2 a) identifies the transfer
  conic; the endpoint speeds must satisfy the same energy.

## Workflow

1. Establish the two position vectors r1 and r2 in km (3-vectors in any
   inertial frame) and the transfer time tof in seconds, plus the
   gravitational parameter mu of the central body.
2. Confirm the problem is well posed: the vectors must not be collinear
   (a 180-degree anti-parallel pair is allowed and handled as the
   Hohmann case) and the time of flight must be positive.
3. Choose the branch: direction="short" for the small transfer angle,
   direction="long" for the complementary angle.
4. Run lambert_solve(r1, r2, tof, mu, direction) to iterate p until the
   time of flight matches; read the semimajor axis, eccentricity,
   semilatus rectum, and the endpoint true and eccentric anomalies.
5. Read the endpoint velocity vectors v1 and v2 (km/s) and the transfer
   delta-v against circular parking orbits; these size the propulsion
   budget for the transfer.
6. Check the result: the endpoint speeds must satisfy vis-viva
   v^2 = mu * (2 / r - 1 / a) and the angular momentum
   |r1 x v1| = |r2 x v2| = sqrt(mu * p) must be conserved.
7. Sanity-check against the 180-degree Hohmann case: a half-orbit coast
   at 7000 km radius takes 2914 s with zero delta-v, and the LEO-GEO
   180-degree transfer totals 3.82 km/s over 19107 s.

## Pitfalls

- Confusing the Lambert transfer with the Hohmann transfer: the Hohmann
  transfer assumes two coplanar circular orbits and a half-ellipse
  180-degree arc; Lambert handles arbitrary two-position, time-of-flight
  transfers. At exactly 180 degrees the Lambert solution IS the Hohmann
  transfer, and the p-iteration is singular there, so the closed-form
  branch is used instead of the general solver.
- Confusing the Lambert problem with keplerian-elements: converting a
  state vector (r, v) into orbital elements is the rv2coe direction of
  the keplerian-elements skill; Lambert is the inverse, finding the
  orbit from two positions and a time, and does not consume a velocity
  vector as input.
- Confusing the two-body transfer with orbital-perturbations: the
  p-iteration is the unperturbed two-body solution; J2, drag, and third-
  body effects bend the trajectory, and the perturbed motion needs
  propagation, not a re-solve of the two-body boundary-value problem.
- Confusing the transfer design with rendezvous-phasing: rendezvous
  phasing sizes drift rates, phase angles, and phasing orbits to meet a
  target on a known orbit; Lambert solves the connecting-orbit boundary
  value. The phasing skill owns the lead-angle problem, Lambert the
  two-position transfer.
- Taking the wrong branch: short-way and long-way give different orbits
  for the same time of flight; pick the branch that matches the mission
  geometry or compare both delta-v budgets.
- Using the wrong units: the solver works in km, km^3/s^2, and km/s; an
  Earth orbit at 7000 km radius with mu = 398600.4418 km^3/s^2 flies at
  7.546 km/s, and mixing in meters or m^3/s^2 scales every result.
- Ignoring the degenerate cases: collinear position vectors have no
  unique orbit plane and raise ValueError, and the 180-degree
  anti-parallel pair must go through the Hohmann branch, not the
  p-iteration.
- Expecting a transfer for any time of flight: a time of flight below
  the minimum arc time for the geometry has no elliptic solution and
  raises ValueError; a long time of flight is always feasible, either
  as a direct arc or as a multi-revolution transfer.
- Misreading the delta-v: the delta-v is measured against circular
  parking orbits whose motion matches the transfer direction; a plane
  change or a different parking direction adds its own impulse.
- Forgetting the sanity check: a 180-degree transfer must reproduce the
  Hohmann numbers (2914 s half-orbit coast at 7000 km, 19107 s and
  3.82 km/s for LEO-GEO); a result far from those anchors signals a
  branch or units error.

## Behavior contract (gate 3)

The Lambert math is exercised by the gate 3 contract test:
scripts/test_lambert_transfer.py against
scripts/lambert_transfer_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_lambert_transfer.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames mission analysis and orbit
  transfer design within the ECSS lifecycle, and the Lambert p-iteration
  and vis-viva relationships above are common astrodynamics methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
