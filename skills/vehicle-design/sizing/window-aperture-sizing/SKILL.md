---
name: window-aperture-sizing
description: "Use when you must size a pressurized-cabin passenger window aperture as a flat circular pane: compute the design pressure differential from the ISA pressures at the cabin and flight altitudes with the certification pressure factor applied, compute the clamped-circular-plate bending stress at the pane edge, invert the relation for the required window-pane-thickness, check the pane-margin against the material allowable, and roll up the pane weight over the window count. Produces the design differential, the pane stress, the required thickness, the margin and the weight that gate the window aperture layout. Trigger: window aperture sizing, window pane thickness, pressure differential stress, clamped circular plate, pane margin check, cabin pressure load."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [window-aperture-sizing, window-pane-thickness, pressure-differential-stress, clamped-circular-plate, pane-margin-check, cabin-pressure-load]
  version: 0.1.0
  author: AeroSkills
---

# Window Aperture Sizing (vehicle-design/sizing/window-aperture-sizing)

Size a pressurized-cabin passenger window aperture as a flat circular
pane clamped at its edge under a uniform pressure differential. This
leaf computes the design differential from the ISA pressures at the
cabin and flight altitudes with the certification pressure factor, the
clamped-edge plate bending stress from the Roark flat-circular-plate
closed form sigma_max = (3/4) * p * (r/t)^2, the required pane
thickness that inverts that relation, the margin against a
designer-supplied allowable stress, and the pane weight rollup over
the window count, in pure Python, stdlib only. It pairs with
fuselage-sizing (the barrel geometry around the aperture) and
fuselage-skin-stringer (the skin and frame grid that surrounds the
window, plus the skin cutout reinforcement context); this leaf owns
the pane itself. It takes the ISA cabin and ambient pressures from
isa-atmosphere (cross-cutting) and does not size the outflow or
relief valves, the bulkheads, or the impact case.

## Domain quick reference

- ISA pressure (paraphrase of the standard pressure formula owned at
  cross-cutting/units-atmos/isa-atmosphere): troposphere (0 to 11 km)
  P(h) = P0 * (1 - L*h/T0)^e with e = g0/(R*L), and isothermal
  stratosphere (11 to 20 km) P(h) = P_tropo * exp(-g0*(h - 11 km) /
  (R*T_tropo)); valid 0 to 20000 m.
- Limit differential: the cabin ISA pressure minus the ambient ISA
  pressure at the flight altitude, dp_limit = P_cabin - P_ambient.
- Design differential: dp_design = dp_limit * certification_factor,
  with the default CERT_PRESSURE_FACTOR = 1.33 applied once as the
  certification pressure factor (the ultimate pressure check applies
  1.33 times the normal operating differential pressure, a paraphrase
  of the FAR 25.365 cabin pressure rule, never a quote).
- Clamped-edge plate stress: sigma_max = (3/4) * p * (r/t)^2 in Pa
  (Roark flat-circular-plate case, clamped edge, uniform load). The
  maximum sits at the clamped edge and the 3/4 constant is independent
  of the Poisson ratio; the center stress 3*(1+nu)*p*(r/t)^2/8 is
  lower at nu = 0.33 (0.49875 versus 0.75 times p*(r/t)^2).
- Required pane thickness: t_req = r * sqrt((3/4) * p / sigma_allow),
  the exact inversion of the stress relation; pick the first standard
  gauge above it.
- Pane margin: margin = sigma_allow / sigma_computed - 1; a negative
  margin means the pane fails at the design differential.
- Pane weight: m = n * rho * pi * r^2 * t per rollup, a function of the
  pane volume only, so it takes no pressure argument.
- FAR-25 (14 CFR Part 25) sets the certification context for
  pressurized-cabin transport aeroplane structure; the closed-form
  plate result above is common conceptual sizing methodology.

## Workflow

1. Collect the inputs: cabin altitude (m), flight altitude (m), pane
   radius r (m), the pane material allowable stress sigma_allow (Pa)
   and density rho (kg/m^3) chosen by the designer, the candidate
   gauge thickness t (m), and the window count.
2. Compute the design pressure differential traverse with
   design_pressure_differential(cabin_altitude_m, flight_altitude_m):
   the ISA cabin and ambient pressures at the two altitudes, the limit
   differential between them, and the design differential that applies
   the certification pressure factor.
3. Compute the clamped-circular-plate stress traverse with
   plate_max_stress_clamped_circular(pressure_pa, radius_m,
   thickness_m): the clamped-edge bending stress of the candidate
   gauge under the design differential.
4. Invert the stress relation for the required pane thickness with
   pane_thickness(pressure_pa, radius_m, allowable_stress_pa), the
   pane thickness inversion that returns the gauge running exactly at
   the allowable.
5. Check the pane margin with pane_margin(pressure_pa, radius_m,
   thickness_m, allowable_stress_pa) for the candidate gauges, and
   select the first standard gauge whose margin is positive at the
   design differential.
6. Roll up the pane weight with window_weight(radius_m, thickness_m,
   material_density_kg_m3, n_windows) for the selected gauge, giving
   the per-window mass and the total over the window count.
7. Run the gauge verification pass at the limit differential (the
   design differential without the certification factor) to confirm
   the design case governs and the selected gauge holds margin in both
   cases.
8. Confirm every result with the deterministic contract test
   scripts/test_window_aperture_sizing.py (step 8 confirmation).

## Worked example

Cabin altitude 8000 ft (2438.40 m), flight altitude 12000 m, pane
radius 0.15 m, acrylic pane (density 1190 kg/m^3) with a
designer-supplied allowable of 50 MPa (the leaf hard-codes no
material). Real module outputs:

- design_pressure_differential(2438.40, 12000.0): cabin pressure
  75262.136558 Pa, ambient pressure 19330.062329 Pa, limit
  differential 55932.074230 Pa, design differential (times 1.33)
  74389.658725 Pa, about 0.744 bar. The outflow-valve sibling quotes
  75262 Pa for the same cabin, cross-consistent.
- plate_max_stress_clamped_circular at t = 6 mm: 34.870153 MPa,
  margin against 50 MPa 0.433891; at t = 5 mm: 50.213020 MPa, margin
  -0.004242.
- pane_thickness(74389.658725, 0.15, 50e6) = 0.005010640 m, so the
  6 mm pane is the first standard gauge with positive margin.
- Limit-pressure (no certification factor) stress at t = 6 mm:
  26.218160 MPa, margin 0.907075.
- window_weight(0.15, 0.006, 1190, 100): 0.504697 kg per window,
  50.469686 kg over 100 windows.
- Sweep at r = 0.10 m: required thickness 3.340426 mm; at t = 10 mm
  the stress is 5.579224 MPa.

## Verification

- Deterministic, offline checks: the contract test asserts the worked
  example anchors above (each pressure within 1 Pa, stresses within
  1e-3 MPa, thickness within 1e-5 m, margins within 1e-4, weights
  within 1e-4 kg), the ISA anchors (sea level 101325 Pa, tropopause
  22631.700910 Pa within 0.5 Pa), the scaling identities (stress
  linear in pressure, quadratic in radius, inverse quadratic in
  thickness; required thickness scales as the square root of the
  pressure and linearly with the radius; doubling the certification
  factor scales the required thickness by sqrt(2)), the round trip
  (the stress at the required thickness returns the allowable within
  1e-6 relative), the clamped-edge-versus-center stress ordering at
  nu = 0.33, and the dict keys exactly as documented.
- Non-physical inputs raise ValueError: negative altitude or altitude
  above 20000 m, a flight altitude at or below the cabin altitude, a
  non-positive certification factor, and non-positive
  pressure/radius/thickness/allowable/density or a window count below
  1.

## Pitfalls

- Leaving the small-deflection regime: the linear small-deflection
  plate stress is the conceptual sizing standard; a very thin, highly
  loaded pane can leave it (deflection of the order of the thickness),
  where membrane stiffening alters the load path. Keep the linear
  closed form and flag such layouts for a refined analysis.
- Sizing the pane on the limit differential alone: the certification
  pressure factor must be applied once to the limit differential to
  form the design differential that the gauge selection runs on; the
  limit-pressure pass is only the step 7 confirmation.
- Forgetting the clamped-edge location: the maximum clamped-edge
  stress sits at the rim, not the center; at nu = 0.33 the center
  stress is only 0.49875 versus 0.75 times p*(r/t)^2, so judging the
  pane on the center stress under-sizes it.
- Using a pane radius where the aperture radius belongs: r is the
  radius of the clamped pane, sized on the clear aperture plus the
  edge support; mixing the two under-sizes the pane.
- Applying the allowable without the material step: the leaf hard-
  codes no material, so the allowable stress and density are designer
  inputs; the weight rollup is density-driven and takes no pressure.
- Mixing units: pressures in Pa, lengths in m, stress in Pa, density
  in kg/m^3; a radius in mm with a thickness in m silently breaks the
  stress and thickness inversions.
- Passing zero or negative inputs; the module raises ValueError
  instead of returning a nonsense thickness or margin.

## Related leaves

- skills/vehicle-design/sizing/fuselage-sizing (barrel geometry)
- skills/vehicle-design/sizing/cabin-outflow-valve-sizing (outflow)
- skills/vehicle-design/structures-integration/fuselage-skin-stringer
  (skin and frame grid around the aperture)
- skills/structures/fem/pressure-bulkhead (pressure dome structure)
- skills/structures/damage-tolerance/bird-strike (impact case)
- skills/cross-cutting/units-atmos/isa-atmosphere (pressure formula)

## Behavior contract (gate 3)

The ISA pressures, design differential, clamped-edge plate stress,
required pane thickness, margin and weight rollup relations are
exercised by the gate 3 contract test: scripts/
test_window_aperture_sizing.py against scripts/
window_aperture_sizing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_window_aperture_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); the clamped-circular-plate closed form is common
  structural methodology and the certification pressure factor is a
  paraphrase of the FAR 25.365 cabin pressure rule, summary-only per
  standards-map.yaml. No regulation text is quoted verbatim.
- compliance: STANDARDS-REF, gated: false.
