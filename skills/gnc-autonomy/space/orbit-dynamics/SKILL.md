---
name: orbit-dynamics
description: "Use when analyzing spacecraft orbital mechanics with two-body and J2-perturbed motion: compute velocities with the vis-viva equation, size Hohmann transfer delta-v and transfer time between coplanar circular orbits, and sanity-check LEO-to-GEO transfer budgets (about 3.9 km/s total delta-v). Flags nodal-regression drift from J2 that exceeds an allowed rate for orbit maintenance planning. Uses Earth gravitational parameter 3.986004418e14 m^3/s^2. Trigger: orbit, orbital mechanics, hohmann transfer, delta-v, vis-viva, orbital elements, j2 perturbation, propagation, transfer time."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: space
  tags: [orbit, orbital-mechanics, hohmann-transfer, delta-v, vis-viva, orbital-elements, j2-perturbation, propagation, transfer-time]
  version: 0.1.0
  author: AeroSkills
---

# Orbit Dynamics (gnc-autonomy/space/orbit-dynamics)

Use when the task is two-body and J2-perturbed orbital mechanics:
velocities, Hohmann transfer sizing, and drift checks.

## Domain quick reference

- Two-body dynamics with Earth gravitational parameter mu =
  3.986004418e14 m^3/s^2.
- Vis-viva: v = sqrt(mu * (2/r - 1/a)); a circular orbit (r == a)
  gives v = sqrt(mu/r), about 7.61 km/s at 500 km altitude
  (r = 6878 km).
- Hohmann transfer between coplanar circular orbits: two burns at
  the ends of the half-ellipse transfer arc; total LEO (6878 km)
  to GEO (42164 km) about 3.9 km/s.
- Transfer time is half the period of the transfer ellipse; LEO to
  GEO takes about 5.3 hours.
- The J2 term drives secular nodal-regression drift (deg/day) that
  matters for repeat-ground-track and formation maintenance.

## Workflow

1. Compute orbital speeds with the vis-viva equation.
2. Size Hohmann transfer delta-v (dv1, dv2, total) and transfer
   time for the two circular radii.
3. Check the total against the LEO-to-GEO sanity band (3.5-4.3
   km/s) with scripts/orbit_dynamics_logic.py.
4. Compare the J2 nodal-regression drift rate against the allowed
   rate and flag orbit-maintenance needs.

## Pitfalls

- Using circular-orbit speed for elliptical segments.
- Summing dv1 and dv2 with the wrong sign convention.
- Forgetting that Hohmann applies to coplanar circular orbits.
- Ignoring J2 drift in repeat-ground-track planning.

## Behavior contract (gate 3)

The vis-viva, Hohmann, and J2-drift logic is exercised by the gate
3 contract test: scripts/test_orbit_dynamics.py against
scripts/orbit_dynamics_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_orbit_dynamics.py

## Compliance

- ECSS series is freely downloadable (ESA); summary-only per
  standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
