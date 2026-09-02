---
name: cfd-convergence
description: "Use when you must judge whether a computational fluid dynamics run has converged: check that residuals drop below tolerance and stay monotone, confirm the Courant number respects the scheme stability limit, and compare mesh refinement levels for answer stability. Produces the residual verdict, the CFL check, and the mesh convergence flag that decide whether results can be trusted. Trigger: cfd convergence, residual convergence, courant number, mesh refinement, solver stability."
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
  subdomain: cfd
  tags: [cfd-convergence, residual-convergence, courant-number, mesh-refinement, solver-stability]
  version: 0.1.0
  author: Aero Agent Skills
---

# CFD Convergence Checks (aerodynamics/cfd/cfd-convergence)

Use when the task is judging computational fluid dynamics
convergence: residual behavior, Courant number stability, and mesh
refinement stability of the answer.

## Domain quick reference

- A converged run has residuals below tolerance and still
  decreasing; oscillating or flat residuals mean the run is not
  converged.
- The Courant number must respect the scheme stability limit:
  about 1 for explicit schemes, higher for implicit schemes.
- Mesh refinement convergence compares the answer across mesh
  levels; small change means the discretization error is bounded.
- Validation against classic data (NACA Report 824) anchors the
  converged answer for airfoil cases.

## Workflow

1. Collect the residual history from the solver log.
2. Check convergence with residual_converged.
3. Confirm the Courant number with cfl_ok.
4. Compare mesh levels with mesh_refinement_ok.
5. Decide whether to trust the run.

## Pitfalls

- Calling a run converged on a flat residual plateau.
- Running explicit schemes at Courant numbers above the limit.
- Reporting an answer that changed on the next mesh level.

## Behavior contract (gate 3)

The residual, CFL, and mesh logic is exercised by the gate 3
contract test: scripts/test_cfd_convergence.py against
scripts/cfd_convergence_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_cfd_convergence.py

## Compliance

- NACA Report 824 is US government work (public domain); summary
  and physics values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
