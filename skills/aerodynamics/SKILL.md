---
name: aerodynamics
description: "Use when a task concerns aerodynamics: guide the router to the aerodynamics pack, whose airfoil-selection covers family choice, xfoil-analysis covers polar validation, airfoil-geometry covers NACA geometry, cfd-convergence covers residuals, cfd-turbulence-modeling covers model selection, cfd-mesh-generation covers grid types and y-plus, normal-shock covers shock relations, oblique-shock covers theta-beta-M, prandtl-meyer covers expansion relations, drag-polar covers the parabolic polar, parasite-drag covers zero-lift drag buildup, and lift-curve-slope covers wing lift slope. Trigger: aerodynamics, airfoil, NACA, XFOIL, polar, drag polar, Oswald, induced drag, parasite drag, wetted area, lift curve slope, sweep, Prandtl-Glauert, CFD, Courant, turbulence model, mesh generation, y-plus, normal shock, oblique shock, Prandtl-Meyer, Mach, compressible flow."
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

Aerodynamics and CFD: airfoil section selection, geometry, and
analysis with XFOIL, viscous-inviscid modeling, turbulence modeling,
compressible flow (normal and oblique shocks, Prandtl-Meyer
expansions), drag polar construction, and wing lift curve slope
estimation, validated against classic reference data.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| aerodynamics/airfoil/airfoil-selection | Airfoil selection | airfoil family choice, design lift coefficient, thickness ratio, camber, section constraints |
| aerodynamics/airfoil/xfoil-analysis | XFOIL airfoil analysis | polar generation, viscous analysis, lift/drag coefficients, validation bands |
| aerodynamics/airfoil/airfoil-geometry | Airfoil geometry | NACA 4/5/6-series geometry, camber and thickness distribution, leading-edge radius, naming decode |
| aerodynamics/cfd/cfd-convergence | CFD convergence | residual convergence, Courant number, mesh refinement, solver stability |
| aerodynamics/cfd/cfd-turbulence-modeling | Turbulence modeling | turbulence model selection, Reynolds number, near-wall treatment, y-plus |
| aerodynamics/cfd/cfd-mesh-generation | CFD mesh generation | grid types, structured/unstructured/hybrid, prism layers, cell quality, first cell height, y-plus target, domain sizing |
| aerodynamics/high-speed/normal-shock | Normal shock relations | downstream Mach, pressure/density/temperature ratios, stagnation pressure loss, supersonic flow |
| aerodynamics/high-speed/oblique-shock | Oblique shock relations | theta-beta-M solution, deflection limits, weak/strong solutions, pressure ratio across shock |
| aerodynamics/high-speed/prandtl-meyer | Prandtl-Meyer expansion | expansion angle, downstream Mach after turning, total-to-static ratios, expansion fan |
| aerodynamics/drag-polars/drag-polar | Drag polar | parabolic polar CD0 + k, Oswald span efficiency, induced drag, maximum lift-to-drag |
| aerodynamics/drag-polars/parasite-drag | Parasite drag | zero-lift drag buildup, wetted-area method, flat-plate skin friction, form and interference factors, equivalent skin-friction coefficient |
| aerodynamics/drag-polars/lift-curve-slope | Lift curve slope | thin-airfoil 2pi, finite-aspect-ratio correction, sweep correction, Prandtl-Glauert Mach correction, lift coefficient from angle of attack |

## Routing guidance

- Airfoil family and section constraint questions route to the
  airfoil-selection sub-skill; XFOIL runs and polar validation route
  to xfoil-analysis; NACA geometry and naming questions route to
  airfoil-geometry.
- CFD solver-convergence questions (residuals, Courant, mesh
  refinement) route to cfd-convergence; turbulence model and
  near-wall questions route to cfd-turbulence-modeling; grid type,
  prism layer, and first-cell-height questions route to
  cfd-mesh-generation.
- Compressible-flow questions (Mach number, normal shock relations,
  stagnation pressure loss) route to the high-speed normal-shock
  sub-skill.
- Oblique shock and turning questions (theta-beta-M, deflection
  angle, weak/strong solution) route to the high-speed oblique-shock
  sub-skill.
- Supersonic turning and expansion-fan questions (Prandtl-Meyer
  angle, downstream Mach after a turn) route to the high-speed
  prandtl-meyer sub-skill.
- Drag polar construction and peak lift-to-drag questions route to
  the drag-polars drag-polar sub-skill; zero-lift drag buildup and
  wetted-area parasite drag questions route to the drag-polars
  parasite-drag sub-skill.
- Wing lift curve slope questions (thin airfoil, aspect ratio, sweep,
  Mach correction) route to the drag-polars lift-curve-slope
  sub-skill.
- Structural, control, and certification questions route to their
  domain packs (structures, gnc-autonomy, avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
