---
name: bow-shock-standoff
description: "Use when you must estimate the detached bow-shock standoff distance ahead of a blunt nose: compute the standoff ratio Delta over R with the classical Billig-form correlations for a sphere nose and a circular cylinder leading edge at gamma 1.4, convert the ratio to a physical standoff distance for a given nose radius, and report the trend checks that the standoff decreases with Mach and that the cylinder standoff exceeds the sphere standoff at the same Mach. Produces the standoff ratio, the standoff distance and the sanity flags that gate blunt-body nose-radius trades and shock-layer thickness estimates. Trigger: bow shock standoff, billig correlation, stagnation streamline, shock layer thickness, detached shock distance, blunt body nose radius."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [bow-shock-standoff, billig-correlation, blunt-body-shock-distance, shock-layer-thickness, stagnation-streamline]
  version: 0.1.0
  author: AeroSkills
---

# Bow Shock Standoff Distance (aerodynamics/high-speed/bow-shock-standoff)

Use when the task is estimating the detached bow-shock standoff distance
on the stagnation streamline ahead of a blunt nose in supersonic and
hypersonic flow: the shock stands ahead of a sphere nose or a circular
cylinder leading edge rather than attaching to a sharp point, and the
shock-layer thickness between the nose and the shock sets the local
environment for pressure and heating trades. This leaf implements the
classical Billig-form standoff correlations for gamma = 1.4 in pure
Python, stdlib only: the sphere form for an axisymmetric nose and the
cylinder form for a two-dimensional leading edge, both as an exponential
of 1 over the freestream Mach squared. It pairs with
aerodynamics/high-speed/hypersonic-flow for the force coefficients of
the blunt body behind the shock and with
aerodynamics/high-speed/aerodynamic-heating, whose stagnation-point flux
scales with the same nose radius. The method is the standard engineering
estimate for the shock-layer geometry, not a CFD replacement.

## Domain quick reference

- Sphere standoff ratio (axisymmetric nose): Delta / R = 0.143 *
  exp(3.24 / M^2), with M the freestream Mach number, R the nose
  radius and Delta the standoff distance of the detached shock ahead
  of the stagnation point.
- Cylinder standoff ratio (two-dimensional leading edge): Delta / R =
  0.386 * exp(4.67 / M^2). The coefficient is about 2.7 times the
  sphere coefficient, so at the same Mach the cylinder shock layer is
  the thicker one.
- Physical distance: Delta = (Delta / R) * R, so the standoff distance
  scales linearly with the nose radius.
- Trends: the ratio is monotone decreasing in Mach (more compression
  pushes the shock closer at higher Mach) and the cylinder ratio
  exceeds the sphere ratio at every Mach above 1.
- High-Mach asymptote: as M grows, each ratio approaches its leading
  coefficient from above, exp(3.24 / M^2) and exp(4.67 / M^2) both
  tending to 1.
- Validity floor: the correlations are documented for freestream Mach
  above about 1.5; the ratio grows without bound as M approaches 1,
  where no detached bow shock exists.
- Units are SI throughout: M dimensionless, R and Delta in meters.
- NACA TR-824 frames the compressible-flow context; the standoff
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the flight point and the nose geometry: record the freestream
   Mach number M and the nose radius R in meters and pick the body,
   sphere for an axisymmetric nose or cylinder for a two-dimensional
   leading edge. Feed a Mach at or below 1 or a non-positive radius
   and the functions reject the point with ValueError, because no
   detached shock layer exists at or below Mach 1. (flight-point step)
2. Evaluate the standoff ratio on the stagnation streamline with
   standoff_ratio(mach, body), applying the Billig-form correlation:
   0.143 * exp(3.24 / M^2) for the sphere or 0.386 * exp(4.67 / M^2)
   for the cylinder. The output is the geometry-free ratio Delta / R.
   (ratio-evaluation step)
3. Convert the ratio to the physical standoff distance with
   standoff_distance(mach, radius, body), Delta = (Delta / R) * R in
   meters; the distance scales linearly with the nose radius.
   (distance-conversion step)
4. Run the trend checks with standoff_report(mach, radius, body):
   decreasing_with_mach compares the ratio at M against the ratio at
   1.1 * M and sphere_cylinder_order confirms that the cylinder ratio
   exceeds the sphere ratio at this Mach. Both sanity flags gate the
   blunt-body nose-radius trade and the shock-layer thickness
   estimate. (trend-check step)
5. Respect the validity floor: the correlations are documented for
   freestream Mach above about 1.5, so a ratio computed below the
   floor carries the floor caveat in the report and is never quoted
   as a converged shock-layer size. (validity-floor step)
6. Confirm the deterministic behavior and the non-physical input
   rejection with the contract test scripts/test_bow_shock_standoff.py.
   (contract-test step)

## Worked example

A reentry or cruise nose at M = 8 and a blunt leading edge at M = 4:

- Sphere at M = 8: standoff_ratio(8.0) = 0.143 * exp(3.24 / 64) =
  0.15043; with R = 0.5 m, standoff_distance(8.0, 0.5) = 0.07521 m.
- Sphere at M = 4: standoff_ratio(4.0) = 0.143 * exp(3.24 / 16) =
  0.17510; with R = 0.5 m the standoff distance is 0.08755 m.
- Cylinder at M = 8: standoff_ratio(8.0, "cylinder") = 0.386 *
  exp(4.67 / 64) = 0.41522; with R = 0.5 m the standoff distance is
  0.20761 m.
- Cylinder at M = 4: standoff_ratio(4.0, "cylinder") = 0.386 *
  exp(4.67 / 16) = 0.51683; with R = 0.5 m the standoff distance is
  0.25841 m.
- Trend checks at M = 4, R = 0.5 m, sphere:
  standoff_report(4.0, 0.5) returns ratio 0.17510, distance
  0.08755 m, sphere_cylinder_order True (cylinder ratio 0.51683
  exceeds the sphere ratio 0.17510) and decreasing_with_mach True
  (the ratio at 4.4 is below the ratio at 4.0). The same flags hold
  at M = 8, whose ratio 0.15043 sits below the M = 4 sphere ratio:
  the standoff shrinks as Mach rises.

## Verification

- Confirm standoff_ratio(8.0) returns 0.15043 within 1e-4 and
  standoff_ratio(4.0) returns 0.17510 within 1e-4.
- Confirm standoff_ratio(8.0, "cylinder") returns 0.41522 within
  1e-4 and standoff_ratio(4.0, "cylinder") returns 0.51683 within
  1e-4.
- Confirm standoff_distance(8.0, 0.5) returns 0.07521 m within 1e-4
  and that distance at R = 1.0 m is exactly twice the distance at
  R = 0.5 m (linear scaling identity).
- Confirm the ratio is monotone decreasing: ratio at M = 6 below the
  ratio at M = 4 for both bodies, and the cylinder ratio exceeds the
  sphere ratio at M = 4 and M = 8.
- Confirm every non-physical input raises ValueError: mach 1.0,
  mach 0.8, radius 0, negative radius, and the body string "wedge".
- Confirm standoff_report returns exactly the keys ratio, distance,
  sphere_cylinder_order and decreasing_with_mach, and that two runs
  at the same point agree (determinism).
- Run the contract test offline: python3
  scripts/test_bow_shock_standoff.py (deterministic).

## Related leaves

- aerodynamics/high-speed/hypersonic-flow: the modified Newtonian
  force coefficients of the blunt body behind the shock.
- aerodynamics/high-speed/oblique-shock: attached shock turning on
  sharp-nosed bodies, the regime where no detached standoff exists.
- aerodynamics/high-speed/normal-shock: the stagnation streamline
  jump relations across the detached shock.
- aerodynamics/high-speed/aerodynamic-heating: stagnation-point
  convective flux with nose-radius scaling, the companion trade to
  the shock-layer thickness.
- aerodynamics/high-speed/flat-plate-skin-friction-heating: the
  thin-boundary-layer alternative on slender surfaces.

## Pitfalls

- Quoting a ratio at Mach near 1: the exponential form grows without
  bound as M approaches 1 and the correlations are only documented
  above about Mach 1.5, so a low-Mach ratio needs the validity floor
  caveat (step 5 of the workflow).
- Feeding Mach at or below 1: no detached shock exists there, the
  correlation is not defined, and the functions raise ValueError
  rather than return a meaningless number.
- Using the sphere correlation for a two-dimensional leading edge or
  the cylinder correlation for an axisymmetric nose: the cylinder
  coefficient 0.386 is about 2.7 times the sphere coefficient 0.143,
  so swapping the body inflates or deflates the shock layer by that
  factor.
- Reporting the ratio as a distance: Delta / R is geometry-free and
  dimensionless; the physical distance is the ratio times the nose
  radius, so a 0.15043 ratio at R = 0.5 m is 0.07521 m, not
  0.15043 m.
- Extending the gamma = 1.4 calibration: both exponentials use the
  gamma = 1.4 constants, so applying them to a real-gas flow with a
  different effective gamma needs a re-derived coefficient.
- Scaling the wrong radius: the distance is linear in the nose
  radius, so halving the radius halves the standoff; keep the ratio
  and the radius together in the report.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_bow_shock_standoff.py

The test covers the four worked-example anchors (sphere and cylinder
ratios at M = 8 and M = 4 within 1e-4 of the module outputs), the
standoff distance conversion at R = 0.5 m, the linear scaling
identity in radius, the monotone decrease of the ratio with Mach for
both bodies, the cylinder-over-sphere ordering at M = 4 and M = 8,
the exact standoff_report key set and flag values, determinism, and
ValueError rejection of Mach at or below 1, non-positive radii and
unknown body strings.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the
  compressible-flow reference framework; the Billig-form standoff
  correlations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
