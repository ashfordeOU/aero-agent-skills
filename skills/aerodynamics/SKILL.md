---
name: aerodynamics
description: "Use when a task concerns aerodynamics: guide the router to the aerodynamics pack, whose airfoil-selection sub-skill covers airfoil family selection, xfoil-analysis covers XFOIL polar validation, cfd-convergence covers residual and Courant checks, cfd-turbulence-modeling covers turbulence model selection, normal-shock covers normal shock relations, prandtl-meyer covers Prandtl-Meyer expansion relations, drag-polar covers the parabolic drag polar, and lift-curve-slope covers the wing lift curve slope with aspect ratio, sweep, and Mach corrections. This pack is the aerodynamic analysis and validation layer of the library. Trigger: aerodynamics, airfoil selection, XFOIL, polar, lift coefficient, drag coefficient, drag polar, Oswald span efficiency, induced drag, lift curve slope, aspect ratio, sweep correction, Prandtl-Glauert, CFD convergence, Courant number, turbulence model, normal shock, Prandtl-Meyer, expansion fan, Mach number, compressible flow."
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
flow (normal shocks and Prandtl-Meyer expansions), drag polar
construction, and wing lift curve slope estimation, validated against
classic reference data.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| aerodynamics/airfoil/airfoil-selection | Airfoil selection | airfoil family choice, design lift coefficient, thickness ratio, camber, section constraints |
| aerodynamics/airfoil/xfoil-analysis | XFOIL airfoil analysis | polar generation, viscous analysis, lift/drag coefficients, validation bands |
| aerodynamics/cfd/cfd-convergence | CFD convergence | residual convergence, Courant number, mesh refinement, solver stability |
| aerodynamics/cfd/cfd-turbulence-modeling | Turbulence modeling | turbulence model selection, Reynolds number, near-wall treatment, y-plus |
| aerodynamics/high-speed/normal-shock | Normal shock relations | downstream Mach, pressure/density/temperature ratios, stagnation pressure loss, supersonic flow |
| aerodynamics/high-speed/prandtl-meyer | Prandtl-Meyer expansion | expansion angle, downstream Mach after turning, total-to-static ratios, expansion fan |
| aerodynamics/drag-polars/drag-polar | Drag polar | parabolic polar CD0 + k, Oswald span efficiency, induced drag, maximum lift-to-drag |
| aerodynamics/drag-polars/lift-curve-slope | Lift curve slope | thin-airfoil 2pi, finite-aspect-ratio correction, sweep correction, Prandtl-Glauert Mach correction, lift coefficient from angle of attack |

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
- Supersonic turning and expansion-fan questions (Prandtl-Meyer
  angle, downstream Mach after a turn) route to the high-speed
  prandtl-meyer sub-skill.
- Drag polar construction and peak lift-to-drag questions route to
  the drag-polars drag-polar sub-skill.
- Wing lift curve slope questions (thin airfoil, aspect ratio, sweep,
  Mach correction) route to the drag-polars lift-curve-slope
  sub-skill.
- Structural, control, and certification questions route to their
  domain packs (structures, gnc-autonomy, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
