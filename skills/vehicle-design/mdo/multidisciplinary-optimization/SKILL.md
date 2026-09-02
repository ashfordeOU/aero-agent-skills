---
name: multidisciplinary-optimization
description: "Use when you must set up a multidisciplinary optimization (MDO) loop for an aircraft or spacecraft: define the design variables, the objective function, and the constraints, identify the coupled disciplines (aerodynamics, structures, propulsion, trajectory), choose a monolithic or distributed architecture, and run the analysis loop that iterates the coupling variables to convergence with a fixed-point scheme and a sensitivity check. Produces the converged coupled state, the constraint feasibility verdict, and the optimum design point that ties the sizing, mass-properties, cost-estimation, and structures-integration leaves together. Trigger: multidisciplinary optimization, mdo, aero-structural coupling, fixed point iteration, design variables, objective function, constraints, coupling, disciplines, design space."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: mdo
  tags: [multidisciplinary-optimization, mdo, aero-structural-coupling, fixed-point-iteration, design-variables, objective-function, constraints, coupling, disciplines, convergence-tolerance, sensitivity-analysis, aerodynamics, structures]
  version: 0.1.0
  author: Aero Agent Skills
---

# Multidisciplinary Design Optimization (vehicle-design/mdo/multidisciplinary-optimization)

Use when the task is multidisciplinary design optimization (MDO) for an
aircraft or spacecraft: the design variables, the objective function,
and the constraints, the disciplines (aerodynamics, structures,
propulsion, trajectory) and their coupling variables, the monolithic or
distributed architecture, and the analysis loop that iterates the
coupling to convergence before the design point is accepted.

## Domain quick reference

- MDO formulation: minimize f(x, y) subject to g(x, y) <= 0 and
  h(x, y) = 0 over the design variables x, with the coupling variables
  y fixed by the discipline residuals R_i(x, y) = 0; f is the
  objective, g the inequality constraints, h the equality constraints.
- Aero-structural coupling: the aerodynamic discipline sees
  CL = CL_alpha * (alpha_geom - delta), where the structural deflection
  index delta reduces the effective angle of attack, and the
  structures discipline sees delta = k_def * q * CL, with q the dynamic
  pressure in Pa. Both hold at the fixed point
  CL* = CL_alpha * alpha_geom / (1 + CL_alpha * k_def * q).
- Worked anchor: CL_alpha = 5.0 1/rad, alpha_geom = 4.0 deg, q = 2000
  Pa, k_def = 2.0e-5 1/Pa gives the contraction factor r = 0.2,
  CL* = 0.290888, delta* = 0.0116355 rad, converged in about 15
  fixed-point iterations at tolerance 1e-10.
- Fixed-point iteration CL_{n+1} = CL_alpha * (alpha_geom -
  k_def * q * CL_n) converges when the contraction factor
  r = CL_alpha * k_def * q < 1; each iteration multiplies the error by
  r, so the iteration count grows as log(tol / error_0) / log(r).
- Optimizer anchor: minimize f(x) = (x - 2.0)^2 subject to x >= 4.0;
  the unconstrained optimum x = 2.0 is infeasible, and the exterior
  penalty 1.0e6 * (4.0 - x)^2 for x < 4.0 moves the grid-search
  optimum to x = 4.0 with f = 4.0.
- Architecture: monolithic runs one optimizer over one coupled model;
  distributed coordinates per-discipline optimizers through the
  coupling variables. Family context: MDO is the optimization
  discipline over the conceptual, sizing, mass-properties,
  cost-estimation, and structures-integration leaves; each leaf
  contributes a discipline model or an objective term to the loop.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  (loads, structural margins) that the MDO constraints encode; the
  formulation is common engineering optimization practice.

## Workflow

1. Define the design variables x and their bounds.
2. Define the objective f(x, y) and the constraints g and h.
3. Identify the disciplines and the coupling variables y, and write
   each discipline residual R_i(x, y) = 0.
4. Choose the architecture: monolithic or distributed.
5. Run the fixed-point coupling loop with aero_structural_fixed_point
   to the convergence tolerance, and check the contraction factor.
6. Optimize the design variable with grid_search_optimize, penalizing
   infeasible points.
7. Check the sensitivity with finite_difference_gradient, then accept
   or refine the design point.

## Pitfalls

- Confusing MDO with ws-tw-trade: ws-tw-trade sets one
  binding-constraint design point at a given wing loading on the
  matching chart; MDO closes the coupled loop and optimizes over the
  design space, and the matching chart result enters as a constraint
  or a start point.
- Confusing MDO with wing-planform-sizing: wing-planform-sizing
  produces the planform geometry from the sizing point; MDO treats the
  planform dimensions as design variables and re-evaluates the coupled
  disciplines at every candidate.
- Confusing MDO with the mass-budget: mass-budget allocates the weight
  statement; MDO consumes the mass estimate as a discipline output and
  couples it to the structural and aerodynamic responses.
- Confusing MDO with trade-study-analysis: a trade study varies one
  factor at a time against fixed alternatives; MDO optimizes
  simultaneously over the design variables with the coupling closed.
- Confusing MDO with engine-sizing: engine-sizing sets the thrust
  requirement from the matching chart; MDO folds propulsion in as a
  discipline whose outputs (thrust, fuel flow) feed the objective and
  the constraints.
- Iterating a fixed point without checking the contraction factor:
  r = CL_alpha * k_def * q must stay below 1 or the loop diverges;
  check r before running.
- Optimizing without a constraint penalty: the unconstrained optimum
  can be infeasible; penalize and verify that the returned point is
  feasible.
- Mixing units: alpha in degrees with CL_alpha in 1/rad, or q in
  non-SI units; keep alpha_geom in degrees, CL_alpha in 1/rad, q in
  Pa, k_def in 1/Pa, delta in rad.

## Behavior contract (gate 3)

The aero-structural fixed-point coupling, the grid-search optimizer
with the constraint penalty, and the sensitivity check are exercised by
the gate 3 contract test: scripts/test_mdo_logic.py against
scripts/mdo_logic.py (stdlib unittest, offline). Run:
python3 skills/vehicle-design/mdo/multidisciplinary-optimization/scripts/test_mdo_logic.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the MDO
  formulation and the coupling equations are common engineering
  optimization methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
