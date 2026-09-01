---
name: airfoil-optimization
description: "Use when you must optimize an airfoil shape for an aerodynamic objective: set up design variables with NACA or PARSEC parameterization, evaluate objectives such as lift to drag ratio, maximum lift coefficient, and drag bucket width, enforce geometric constraints on thickness and camber, and run trade studies with sensitivity analysis. Produces the parameter sweep, the constraint verdict, the sensitivity ranking, and the recommended design point that feeds section selection and polar analysis. Trigger: airfoil shape optimization, design space, trade study, drag bucket, parsec, sensitivity analysis, geometric constraints."
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
  subdomain: airfoil
  tags: [airfoil-optimization, shape-optimization, design-space, trade-study, drag-bucket-width, parsec-parameterization, naca-parameterization, sensitivity-analysis, geometric-constraints]
  version: 0.1.0
  author: AeroSkills
---

# Airfoil Shape Optimization (aerodynamics/airfoil/airfoil-optimization)

Use when the task is airfoil shape optimization: design variables and
parameterization, aerodynamic objectives, geometric constraints,
trade studies, and sensitivity analysis.

## Domain quick reference

- Design variables: the NACA 4-digit family gives the low-dimensional
  set (camber m, camber position p, thickness t, per NACA Report 824);
  the PARSEC 11-parameter family (open literature) controls the shape
  directly: leading-edge radius, upper and lower crest position,
  ordinate, and curvature, and trailing-edge ordinates and angles.
- Objective: lift-to-drag ratio cl / cd at the design condition,
  maximum lift coefficient clmax requirement margin, or low-drag
  bucket width (the cl range over which cd stays within a tolerance
  of the minimum cd, typical of laminar 6-series sections).
- Geometric constraints: minimum thickness for structural depth,
  camber bounds for hinge-line and pitch behavior, trailing-edge
  thickness floor. Checked with constraint_violations.
- Trade study: sweep one design variable over a grid, evaluate the
  objective at every point, rank the candidates. The grid best is a
  candidate, not a converged optimum.
- Sensitivity: central finite-difference gradient df / dx_i; the
  relative sensitivity (df / dx_i) * (x_i / f) ranks which design
  variable moves the objective most.
- Multi-objective: with two competing objectives (for example
  thickness versus lift-to-drag), keep only the non-dominated designs
  with a Pareto filter.
- PARSEC convention used here: upper surface
  y_u(x) = sum a_i * x^(i - 1/2) for i = 1..6, lower surface
  y_l(x) = sum b_i * x^(i - 1/2), with a_1 = sqrt(2 * r_le),
  b_1 = -sqrt(2 * r_le), crest conditions y(x_top) = y_top,
  y'(x_top) = 0, y''(x_top) = y_xx_top (and the lower analogues), and
  trailing-edge conditions y(1) = y_te_u, y'(1) = tan(alpha_te) (and
  y(1) = y_te_l, y'(1) = tan(beta_te)). Angles are radians. The
  series slope and curvature are singular at x = 0.

## Workflow

1. Choose the parameterization: NACA 4-digit variables (m, p, t) for
   a low-dimensional study, or the 11 PARSEC parameters for shape
   level control. Generate section ordinates with parsec_surface for
   PARSEC; for NACA ordinates use the airfoil-geometry leaf.
2. Define the objective: lift_drag_ratio at the design point,
   clmax_margin against the requirement, or drag_bucket_width from a
   polar table.
3. Define the geometric constraints (thickness floor, camber bounds)
   and check them with constraint_violations.
4. Sweep the design variable with trade_sweep and pick the candidate
   with best_trade_point; inspect the neighbors of the best point.
5. Rank the design variables with central_difference_gradient and
   relative_sensitivity to find which ones move the objective most.
6. With two competing objectives, filter the non-dominated designs
   with pareto_front.
7. Pass the selected section to the xfoil-analysis leaf for polar
   evaluation and iterate.

## Pitfalls

- Treating the objective (lift-to-drag at the design condition) as a
  constraint (clmax requirement); L/D peaks at the design point while
  clmax is a limit that must clear the requirement with margin.
- Driving thickness down to gain L/D while ignoring the structural
  depth floor; always pair the L/D objective with the thickness
  constraint.
- Reading drag bucket width from a single polar point; the bucket is
  a cl range and needs the full polar.
- Reporting the grid best of a coarse trade sweep as the optimum;
  check the neighboring grid points or refine the sweep.
- Using the linear clmax trend model as a physics prediction; it is a
  local trend that needs a slope calibrated from the user's own polar
  data.
- Mixing PARSEC convention variants; trailing-edge ordinate and angle
  definitions differ across the literature, this leaf uses the
  documented convention above.
- Evaluating slope or curvature at x = 0; the PARSEC series is
  singular at the leading edge and raises ValueError there.

## Behavior contract (gate 3)

The optimization logic is exercised by the gate 3 contract test:
scripts/test_airfoil_optimization.py against
scripts/airfoil_optimization_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_airfoil_optimization.py

## Compliance

- NACA Report 824 is US government work (public domain); the PARSEC
  parameterization is common engineering knowledge from the open
  literature. Formulas and summary values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
