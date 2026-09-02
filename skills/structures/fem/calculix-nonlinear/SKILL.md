---
name: calculix-nonlinear
description: "Use when you must understand or verify a nonlinear finite element static analysis in the CalculiX (ccx) style: solve the equilibrium of a structure whose stiffness depends on its own state, apply Newton-Raphson iteration with load stepping, check convergence against a residual tolerance, and report the convergence verdict. The scalar model is a bar with state-dependent axial stiffness k(u) = k0 * (1 + alpha * u); the solver iterates u_{n+1} = u_n - r(u_n) / kt(u_n) with residual r(u) = k(u)*u - F and tangent stiffness kt = k0 * (1 + 2*alpha*u). Produces the converged displacement, the iteration count, the final residual norm, and the converged or not-converged verdict. Trigger: calculix, ccx, nonlinear fem, newton-raphson, load stepping, convergence tolerance, residual, tangent stiffness, geometric nonlinearity, material nonlinearity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [calculix-nonlinear, calculix, ccx, nonlinear-fem, newton-raphson, load-stepping, convergence, residual, tangent-stiffness, geometric-nonlinearity]
  version: 0.1.0
  author: Aero Agent Skills
---

# CalculiX Nonlinear Analysis (structures/fem/calculix-nonlinear)

Use when the task is nonlinear finite element statics in the CalculiX
(ccx) style: state-dependent stiffness, Newton-Raphson iteration,
load stepping, and convergence verdicts.

## Domain quick reference

- A nonlinear ccx static run applies when the linear assumption
  breaks: the stiffness of the structure depends on its own state.
- Geometric nonlinearity (large displacement) and material
  nonlinearity (plasticity) both appear as a state-dependent
  stiffness; the scalar model is a bar with k(u) = k0 * (1 + alpha*u).
- The equilibrium residual is r(u) = k(u)*u - F =
  k0 * (u + alpha*u**2) - F; the tangent stiffness is
  kt(u) = dr/du = k0 * (1 + 2*alpha*u).
- Newton-Raphson updates u_{n+1} = u_n - r(u_n)/kt(u_n) until
  abs(r) <= tolerance (converged) or the iteration budget is spent
  (not converged).
- Load stepping splits the total load into equal increments; each
  increment iterates from the previous converged state, mirroring a
  nonlinear run ramping the load.

## Workflow

1. Validate the solver inputs (positive k0, non-negative alpha,
   positive tolerance, at least one load step).
2. Solve the equilibrium by Newton-Raphson, with the load applied in
   load_steps equal increments.
3. Read the converged displacement, the total iteration count, and
   the final residual norm.
4. Check the convergence verdict: residual norm <= tolerance means
   converged; exhausting the budget means not-converged.
5. Compare against the closed-form root where available
   (u = (-1 + sqrt(1 + 4*alpha*F/k0)) / (2*alpha) for alpha > 0).

## Pitfalls

- Applying the whole load in one increment when the increment count
  matters for convergence (stepping accumulates the applied load).
- Declaring convergence from the iteration count instead of the
  residual norm.
- Dividing by a zero tangent stiffness inside an increment; the
  solver must abort that increment cleanly.
- Forgetting that a negative discriminant means no real root.

## Behavior contract (gate 3)

The nonlinear solver logic is exercised by the gate 3 contract test:
scripts/test_calculix_nonlinear.py against
scripts/calculix_nonlinear_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_calculix_nonlinear.py
