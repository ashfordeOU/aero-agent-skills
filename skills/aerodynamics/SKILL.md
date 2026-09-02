---
name: aerodynamics
description: "Use when a task concerns aerodynamics: guide the router to the aerodynamics pack: airfoil-selection family choice, xfoil-analysis polars, airfoil-geometry NACA geometry, airfoil-optimization shape trade, cfd-convergence residuals, cfd-turbulence-modeling model selection, cfd-mesh-generation grids and y-plus, vortex-lattice-method VLM, panel-method potential flow, normal-shock shock relations, oblique-shock theta-beta-M, prandtl-meyer expansions, swept-wing-aerodynamics sweep, transonic-similarity Karman-Tsien, supercritical-airfoil aft loading, wave-drag-area-rule area rule, drag-polar polar, parasite-drag zero-lift drag, lift-curve-slope lift slope, boundary-layer-theory flat-plate layers, ground-effect in-ground lift, high-lift-systems flap and slat clmax. Trigger: aerodynamics, airfoil, polar, drag polar, sweep, Mach, boundary layer, ground effect, high lift, vortex lattice, panel method, transonic."
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
| aerodynamics/airfoil/airfoil-optimization | Airfoil optimization | shape trade studies, thickness/camber objectives, drag bucket, L/D targets |
| aerodynamics/boundary-layer/boundary-layer-theory | Boundary layer theory | flat-plate thickness, displacement and momentum thickness, skin friction, transition |
| aerodynamics/cfd/cfd-convergence | CFD convergence | residual convergence, Courant number, mesh refinement, solver stability |
| aerodynamics/cfd/cfd-turbulence-modeling | Turbulence modeling | turbulence model selection, Reynolds number, near-wall treatment, y-plus |
| aerodynamics/cfd/cfd-mesh-generation | CFD mesh generation | grid types, structured/unstructured/hybrid, prism layers, cell quality, first cell height, y-plus target, domain sizing |
| aerodynamics/cfd/vortex-lattice-method | Vortex lattice method | horseshoe vortices, panel lattice, lift distribution, downwash, induced drag |
| aerodynamics/cfd/panel-method | Panel method | source/doublet panels, Neumann/Dirichlet boundary conditions, pressure distribution, potential flow |
| aerodynamics/drag-polars/drag-polar | Drag polar | parabolic polar CD0 + k, Oswald span efficiency, induced drag, maximum lift-to-drag |
| aerodynamics/drag-polars/parasite-drag | Parasite drag | zero-lift drag buildup, wetted-area method, flat-plate skin friction, form and interference factors, equivalent skin-friction coefficient |
| aerodynamics/drag-polars/lift-curve-slope | Lift curve slope | thin-airfoil 2pi, finite-aspect-ratio correction, sweep correction, Prandtl-Glauert Mach correction, lift coefficient from angle of attack |
| aerodynamics/ground-effects/ground-effect | Ground effect | in-ground-effect lift and drag, height-to-span ratio, takeoff and landing performance |
| aerodynamics/high-lift/high-lift-systems | High-lift systems | trailing-edge flaps, leading-edge devices, flap clmax increment, slat increment, wing CLmax, stall speed |
| aerodynamics/high-speed/normal-shock | Normal shock relations | downstream Mach, pressure/density/temperature ratios, stagnation pressure loss, supersonic flow |
| aerodynamics/high-speed/oblique-shock | Oblique shock relations | theta-beta-M solution, deflection limits, weak/strong solutions, pressure ratio across shock |
| aerodynamics/high-speed/prandtl-meyer | Prandtl-Meyer expansion | expansion angle, downstream Mach after turning, total-to-static ratios, expansion fan |
| aerodynamics/high-speed/swept-wing-aerodynamics | Swept wing aerodynamics | leading edge sweep, simple sweep theory, critical Mach increase, effective Mach |
| aerodynamics/high-speed/transonic-similarity | Transonic similarity | Karman-Tsien correction, critical Mach number, compressibility correction |
| aerodynamics/high-speed/supercritical-airfoil | Supercritical airfoil | aft loading, flat upper surface, wave drag reduction, drag divergence Mach |
| aerodynamics/high-speed/wave-drag-area-rule | Wave drag and area rule | transonic wave drag, cross-sectional area distribution, Sears-Haack body, area rule |
| aerodynamics/wing-design/wing-planform-design | Wing planform design | root chord, tip chord, mean aerodynamic chord, taper ratio, spanwise loading, washout |
| aerodynamics/aeroelasticity/divergence-speed | Divergence speed | divergence dynamic pressure, torsional stiffness, shear center offset, aerodynamic center, divergence margin, dive speed |
| aerodynamics/wind-tunnel/windtunnel-data-reduction | Wind tunnel data reduction | wind tunnel data reduction, tare correction, blockage correction, wall interference, Reynolds correction, aerodynamic coefficients, pressure distribution, balance data, uncertainty estimation, experimental aerodynamics |
| aerodynamics/aeroelasticity/flutter-speed-prediction | Flutter speed prediction | flutter speed, v-g method, bending torsion, typical section, damping crossing, frequency coalescence, flutter margin, theodorsen |
| aerodynamics/cfd/cfd-validation | Cfd Validation | cfd validation, validation case selection, richardson extrapolation, grid convergence, naca 0012 drag, onera m6, dlr f6, error metrics, validation uncertainty, validation report. |
| aerodynamics/wind-tunnel/windtunnel-wall-corrections | Wind tunnel wall corrections | wall corrections, solid blockage, wake blockage, lift interference, test section constraint, corrected drag |

## Routing guidance

- Airfoil family and section constraint questions route to the
  airfoil-selection sub-skill; XFOIL runs and polar validation route
  to xfoil-analysis; NACA geometry and naming questions route to
  airfoil-geometry; shape trade and - Cfd validation questions route to the cfd cfd-validation sub-skill.
objective studies route to
  airfoil-optimization.
- CFD solver-convergence questions (residuals, Courant, mesh
  refinement) route to cfd-convergence; turbulence model and
  near-wall questions route to cfd-turbulence-modeling; grid type,
  prism layer, and first-cell-height questions route to
  cfd-mesh-generation; potential-flow and lift-distribution methods
  route to vortex-lattice-method and panel-method.
- Compressible-flow questions (Mach number, normal shock relations,
  stagnation pressure loss) route to the high-speed normal-shock
  sub-skill; oblique shock and turning questions (theta-beta-M,
  deflection angle, weak/strong solution) route to oblique-shock;
  expansion-fan questions (Prandtl-Meyer angle, downstream Mach)
  route to prandtl-meyer.
- Sweep, transonic scaling, wave drag, and critical Mach questions
  route to swept-wing-aerodynamics, transonic-similarity,
  supercritical-airfoil, and wave-drag-area-rule.
- Drag polar construction and peak lift-to-drag questions route to
  the drag-polars drag-polar sub-skill; zero-lift drag buildup and
  wetted-area parasite drag questions route to parasite-drag; wing
  lift curve slope questions (thin airfoil, aspect ratio, sweep, Mach
  correction) route to lift-curve-slope.
- Boundary layer thickness, transition, and skin friction questions
  route to boundary-layer-theory; in-ground-effect performance
  questions route to ground-effect; flap and slat clmax and stall
  speed questions route to high-lift-systems.
- Wing planform reference geometry, root and tip chord, mean aerodynamic chord, taper ratio, and spanwise loading questions route to the wing-design wing-planform-design sub-skill.
- Divergence dynamic pressure, torsional stiffness, aerodynamic center offset, and divergence margin questions route to the aeroelasticity divergence-speed sub-skill.
- Structural, control, and certification questions route to their
  domain packs (structures, gnc-autonomy, avionics).
- Wind tunnel test data reduction, tare, blockage, and wall interference corrections, and coefficient uncertainty estimation route to the wind-tunnel windtunnel-data-reduction sub-skill.
- Classical wing flutter of the two-DOF typical section, the V-g method, structural damping crossing, frequency coalescence, and flutter margin questions route to the aeroelasticity flutter-speed-prediction sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
- Wind tunnel wall and blockage correction questions route to the wind-tunnel windtunnel-wall-corrections sub-skill.
