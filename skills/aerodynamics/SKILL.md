---
name: aerodynamics
description: "Use when a task concerns aerodynamics: guide the router to the aerodynamics pack, whose airfoil-selection sub-skill covers airfoil family selection against design lift and thickness constraints, xfoil-analysis covers XFOIL polar generation and validation of lift and drag coefficients, cfd-convergence covers residual, Courant, and mesh-refinement convergence checks, cfd-turbulence-modeling covers turbulence model selection and near-wall treatment, normal-shock covers the normal shock relations of compressible flow (downstream Mach, static ratios, stagnation pressure loss), and drag-polar covers the parabolic drag polar with induced-drag factor and maximum lift-to-drag. This pack is the aerodynamic analysis and validation layer of the library. Trigger: aerodynamics, airfoil selection, XFOIL, polar, lift coefficient, drag coefficient, drag polar, Oswald span efficiency, induced drag, CFD convergence, Courant number, turbulence model, normal shock, Mach number, compressible flow."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; router/entry point for the aerodynamics domain pack"
metadata:
  domain: aerodynamics
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Aerodynamics domain pack (router)

Route here when the task is aerodynamic analysis, airfoil selection,
compressible flow, or validation of section data.

## Domain

Aerodynamics and CFD: airfoil section selection and analysis with
XFOIL, viscous-inviscid modeling, turbulence modeling, compressible
flow (normal shocks), and drag polar construction, validated against
classic reference data.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| aerodynamics/airfoil/airfoil-selection | Airfoil selection | airfoil family choice, design lift coefficient, thickness ratio, camber, section constraints |
| aerodynamics/airfoil/xfoil-analysis | XFOIL airfoil analysis | polar generation, viscous analysis, lift/drag coefficients, validation bands |
| aerodynamics/cfd/cfd-convergence | CFD convergence | residual convergence, Courant number, mesh refinement, solver stability |
| aerodynamics/cfd/cfd-turbulence-modeling | Turbulence modeling | turbulence model selection, Reynolds number, near-wall treatment, y-plus |
| aerodynamics/high-speed/normal-shock | Normal shock relations | downstream Mach, pressure/density/temperature ratios, stagnation pressure loss, supersonic flow |
| aerodynamics/drag-polars/drag-polar | Drag polar | parabolic polar CD0 + k, Oswald span efficiency, induced drag, maximum lift-to-drag |

## Routing guidance

- Airfoil family and section constraint questions route to the
  airfoil-selection sub-skill; XFOIL runs and polar validation route
  to xfoil-analysis.
- CFD solver-convergence questions (residuals, Courant, mesh
  refinement) route to cfd-convergence; turbulence model and
  near-wall questions route to cfd-turbulence-modeling.
- Compressible-flow questions (Mach number, normal shock relations,
  stagnation pressure loss) route to the high-speed normal-shock
  sub-skill.
- Drag polar construction and peak lift-to-drag questions route to
  the drag-polars drag-polar sub-skill.
- Structural, control, and certification questions route to their
  domain packs (structures, gnc-autonomy, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
