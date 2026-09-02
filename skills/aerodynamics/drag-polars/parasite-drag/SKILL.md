---
name: parasite-drag
description: "Estimate the parasite (zero-lift) drag of a fixed-wing aircraft with the component buildup method: compute the flat-plate skin-friction coefficient from the Reynolds number for laminar and turbulent flow, apply the form factor and interference factor to each component, convert the wetted area into a drag coefficient, and sum the wing, fuselage, nacelle, and tail contributions into the total parasite drag. Also back out the equivalent skin-friction coefficient from the total wetted area and the total drag. Use when the task is drag buildup, zero-lift drag estimation, the wetted-area method, skin-friction coefficients, form factor, interference factor, or equivalent skin-friction coefficient in a preliminary drag assessment. Trigger: parasite drag, zero-lift drag, skin friction, wetted area, form factor, interference factor, drag buildup, Reynolds number."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: drag-polars
  tags: [parasite-drag, zero-lift-drag, skin-friction, wetted-area, form-factor, interference-factor, drag-buildup, flat-plate, reynolds-number, equivalent-skin-friction, fuselage, nacelle, wing, tail]
  version: 0.1.0
  author: Aero Agent Skills
---

# Parasite Drag Buildup (aerodynamics/drag-polars/parasite-drag)

Use when the task is estimating the zero-lift (parasite) drag of an
aircraft by the component buildup method: flat-plate skin friction,
wetted areas, form factors, and interference factors for the wing,
fuselage, nacelle, and tail.

## Domain quick reference

- Parasite drag is the drag at zero lift: skin friction, pressure drag
  from separated or thick boundary layers, and miscellaneous excrescences.
  It is the CD0 term of the parabolic drag polar CD = CD0 + k * CL^2.
- The buildup method sums per-component drag coefficients:

      CD_i = Cf * FF * Q * S_wet_i / S_ref

  Cf is the flat-plate skin-friction coefficient, FF the form factor,
  Q the interference factor, S_wet_i the wetted area of the component,
  S_ref the reference area, and CD_parasite = sum of all CD_i.
- Flat-plate skin friction depends on the Reynolds number
  Re = rho * V * L / mu (density, speed, length, viscosity):
  laminar Cf = 1.328 / sqrt(Re); fully turbulent
  Cf = 0.455 / (log10(Re))^2.58. With transition at Re_tr the mixed
  value is Cf = Cf_turb(Re) - (Re_tr/Re) * (Cf_turb(Re_tr) - Cf_lam(Re_tr)).
- Wetted area is the surface actually in contact with the flow. A
  first-order wing estimate is S_wet = 2 * S_exposed * (1 + 0.2*t/c);
  fuselage and nacelle wetted areas come from body dimensions.
- Form factors inflate the flat-plate value for the component shape:
  wing/tail FF = 1 + 2*(t/c) + 100*(t/c)^4; fuselage
  FF = 1 + 60/(l/d)^3 + 0.0025*(l/d); nacelle FF = 1 + 0.35/(l/d).
- The interference factor Q >= 1 accounts for drag added where component
  flows interact (wing-body, nacelle-pylon, tail-body junctions);
  Q = 1.0 for an isolated component.
- The equivalent skin-friction coefficient Cf_e = CD_parasite * S_ref /
  S_wet_total condenses the whole buildup to one number; clean
  subsonic transports fall near 0.0025 to 0.004.

## Workflow

1. Gather the flight condition (rho, V, mu) and the reference area
   S_ref; set the transition Reynolds number (commonly 5e5).
2. For each component (wing, fuselage, nacelle, tail): estimate the
   wetted area S_wet, the characteristic length L, and the geometry
   (t/c for airfoils, l/d for bodies).
3. Compute Re = reynolds_number(rho, v, l, mu) and the flat-plate Cf
   with cf_flat_plate_laminar, cf_flat_plate_turbulent, or
   cf_flat_plate_mixed.
4. Compute the form factor with form_factor(kind, t_over_c=...,
   l_over_d=...) and choose the interference factor Q.
5. Convert each component with component_parasite_drag(cf, ff, q,
   s_wet, s_ref) and sum with total_parasite_drag.
6. Back out the fleet-average friction with equivalent_skin_friction
   and compare against the typical band for the aircraft class.

## Pitfalls

- Using the fully turbulent Cf for a short-chord component whose flow
  is still laminar: the laminar and mixed values are markedly lower.
- Forgetting the (Re_tr/Re) weighting when applying the mixed formula:
  the transition correction scales with the wetted length fraction.
- Applying an airfoil form factor to a body and vice versa: wing and
  tail use t/c, fuselage and nacelle use l/d.
- Using the planform area instead of the wetted area, or forgetting
  the factor of two for two-sided surfaces like the wing and tail.
- Dropping the interference factor: Q = 1 everywhere understates the
  drag of a real installed configuration.
- Dividing by the wrong area: CD_i must be normalized by the same
  S_ref everywhere, while Cf_e uses the total wetted area.
- Accepting negative or zero Reynolds numbers, t/c at or above 0.5,
  or fineness ratios at or below 1: the formulas are undefined there.

## Behavior contract (gate 3)

The buildup logic is exercised by the gate 3 contract test:
scripts/test_parasite_drag.py against scripts/parasite_drag_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_parasite_drag.py

## Compliance

- NACA Report 824 (Abbott, von Doenhoff, Stivers) is US government
  work in the public domain and is cited as a validation reference
  only: physics values and formulas are paraphrased here, never copied.
- 14 CFR Part 25 (FAR-25) is US government work in the public domain;
  this leaf cites it as reference only for the performance and drag
  context of transport-category certification. No text from
  proprietary standards is reproduced anywhere in this leaf.
- compliance: STANDARDS-REF, gated: false.
