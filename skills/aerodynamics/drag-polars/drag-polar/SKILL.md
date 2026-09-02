---
name: drag-polar
description: "Use when you must compute the parabolic drag-polar of a wing from the zero-lift-drag coefficient cd0, the Oswald span-efficiency, and the aspect-ratio: calculate the induced-drag factor k with k = 1 / (pi * e * AR), the drag coefficient at a given lift coefficient, the lift-to-drag ratio at a point, and the maximum lift-to-drag ratio with its optimal lift coefficient. Also fit a parabolic drag-polar to two measured lift and drag points to recover cd0 and k. Produces the fitted polar coefficients and the peak performance values that gate the wing aerodynamic efficiency assessment. Trigger: drag-polar, parabolic, Oswald span-efficiency, induced-drag factor, aspect-ratio, cd0, lift-to-drag, max L/D, polar fit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: drag-polars
  tags: [drag-polar, parabolic, oswald, span-efficiency, aspect-ratio, induced-drag, zero-lift-drag, cd0, lift-to-drag]
  version: 0.1.0
  author: Aero Agent Skills
---

# Parabolic Drag Polar Analysis (aerodynamics/drag-polars/drag-polar)

Use when the task is wing-level drag modeling with the parabolic
drag-polar: CD = CD0 + k * CL^2, where k = 1 / (pi * e * AR).

## Domain quick reference

- Parabolic drag polar: CD = CD0 + k * CL^2, k = 1 / (pi * e * AR).
- Oswald span-efficiency e is the ratio of ideal (elliptic loading)
  induced drag to the actual induced drag at the same lift and aspect
  ratio. e = 1 for elliptic loading; typical wings run 0.7 to 0.85.
- AR = span^2 / area, dimensionless. CD0, CD, CL, and k are
  dimensionless coefficients.
- Peak efficiency: cl_opt = sqrt(cd0 / k), L/D max = 1 / (2 * sqrt(cd0 * k)).
- The quadratic fit from two points recovers k = (cd2 - cd1) /
  (cl2^2 - cl1^2) and cd0 = cd1 - k * cl1^2.
- Validation anchor: NACA Report 824 (public domain) supplies measured
  section polars that a parabolic fit should reproduce within fit
  tolerance.

## Workflow

1. Gather CD0, Oswald span-efficiency e, and aspect-ratio AR for the
   wing.
2. Compute k with induced_drag_factor(e, ar).
3. Evaluate the polar at the design CL with drag_coefficient(cd0, cl,
   e, ar).
4. Score the point with lift_to_drag(cl, cd).
5. Find the peak with max_lift_to_drag(cd0, e, ar): cl_opt, ld_max.
6. Fit measured points with fit_parabolic_polar(cl1, cd1, cl2, cd2)
   to recover cd0 and k.

## Pitfalls

- Accepting e <= 0 or e > 1 instead of rejecting it.
- Fitting with coincident or antisymmetric cl points, which vanishes
   the denominator.
- Treating a negative fitted k (drag falling as lift rises) as valid.
- Accepting cd0 <= 0, which no real wing exhibits.
- Dividing by cd = 0 in the lift-to-drag ratio.

## Behavior contract (gate 3)

The polar, peak, and fit logic is exercised by the gate 3 contract
test: scripts/test_drag_polar.py against scripts/drag_polar_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_drag_polar.py

## Compliance

- NACA Report 824 is US government work (public domain); summary and
  physics values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
