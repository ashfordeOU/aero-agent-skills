---
name: honeycomb-core-micromechanics
description: "Use when you must predict the equivalent mechanical properties of a hexagonal honeycomb core from the cell geometry and the foil material: compute the relative density of the hexagonal cell with double-thickness vertical walls, the core density from the foil density, the stabilized out-of-plane compressive modulus E3 from the foil modulus, the out-of-plane shear moduli G13 and G23 from the foil shear modulus, and the in-plane cell-wall-bending moduli E1, E2 and G12 by the Gibson and Ashby hexagonal-cell closed forms. Produces the equivalent core properties the sandwich panel workflow collects as given inputs; the foil shear modulus derives from the foil modulus and Poisson ratio of the isotropic foil. Cell geometry and foil properties are inputs; no core property tables are reproduced. Trigger: honeycomb core micromechanics, hexagonal honeycomb cell, gibson ashby closed forms, equivalent core properties, out of plane shear modulus, stabilized compressive modulus, relative density."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [honeycomb-core-micromechanics, hexagonal-honeycomb-cell, gibson-ashby-closed-forms, equivalent-core-properties, out-of-plane-shear-modulus, stabilized-compressive-modulus, relative-density, double-thickness-cell-walls, core-density-prediction]
  version: 0.1.0
  author: AeroSkills
---

# Honeycomb Core Micromechanics (structures/composites/honeycomb-core-micromechanics)

Use when the task is predicting the equivalent mechanical properties of
an aerospace hexagonal honeycomb core, relative density, core density,
the stabilized out-of-plane compressive modulus E3, the out-of-plane
shear moduli G13 and G23, and the in-plane cell-wall-bending moduli E1,
E2 and G12, from the cell geometry and the foil material, the producer
side of the core-property chain that
structures/composites/sandwich-panels takes as a given input at its
workflow step 1. This leaf implements the Gibson and Ashby hexagonal-
cell closed forms for the double-thickness-vertical-wall honeycomb
convention, pure Python, stdlib only. It pairs with
structures/composites/sandwich-panels for the downstream panel-level
bending, core shear and face wrinkling analysis, and with
structures/composites/unidirectional-lamina-micromechanics as the
in-pack precedent for a constituent-to-property producer leaf.

## Domain quick reference

- Relative density of the double-thickness-wall hexagonal cell:
  rho*/rho_s = (t/l)(h/l + 2)/(2 cos(theta)(h/l + sin(theta))), which
  reduces to the classic (2/sqrt(3))(t/l) at the regular hexagon
  h/l = 1, theta = 30 deg.
- Core density: rho* = rho_s (rho*/rho_s), the foil density scaled by
  the relative density.
- Stabilized out-of-plane compressive modulus: E3 = E_s (rho*/rho_s),
  linear in the foil modulus at fixed geometry, the in-service
  stabilized condition (not the unstabilized crush strength).
- Out-of-plane shear moduli: G13/G_s = (t/l) cos(theta)/(h/l +
  sin(theta)) in the ribbon plane and G23/G_s = (t/l)(h/l +
  sin(theta))/((h/l)^2 cos(theta)(2 h/l + 1)) in the transverse plane;
  both coincide at the regular hexagon, G13 = G23 = G_s (rho*/rho_s)/2.
- In-plane cell-wall-bending moduli (the cell walls bend as beams, the
  (t/l)^3 stiffness scaling): E1*/E_s = (t/l)^3 cos(theta)/((h/l +
  sin(theta)) sin^2(theta)), E2*/E_s = (t/l)^3 (h/l +
  sin(theta))/cos^3(theta), G12*/E_s = (t/l)^3 (h/l +
  sin(theta))/((h/l)^2 (1 + 2 h/l) cos(theta)); at the regular hexagon
  E1* = E2* and G12* = E1*/4, the in-plane Poisson ratio of the
  regular hexagonal cell being exactly 1.
- Isotropic foil shear modulus: G_s = E_s/(2(1 + nu_s)), derived when
  only the foil modulus and Poisson ratio are given.
- Geometry conventions (Gibson and Ashby, Cellular Solids, 2nd ed.,
  CUP 1997, ch. 4): axis 1 the ribbon direction of the vertical
  double walls, axis 2 the transverse in-plane direction, axis 3 the
  out-of-plane core thickness; h the vertical double-wall length, l
  the inclined wall length, t the foil wall thickness, theta the
  inclined wall angle to axis 1.
- Units are SI throughout: moduli in Pa, density in kg/m^3, length
  ratios dimensionless, theta in degrees.

## Workflow

1. Fix the foil material inputs (modulus E_s, Poisson ratio nu_s,
   density rho_s) and derive the foil shear modulus with
   shear_modulus_isotropic when only E_s and nu_s are given.
2. Fix the cell geometry (wall thickness to edge-length ratio t/l,
   cell aspect ratio h/l, cell angle theta in degrees) and compute the
   relative density with relative_density, then the core density with
   core_density.
3. Predict the stabilized out-of-plane compressive modulus with
   compressive_modulus_e3, and the two out-of-plane shear moduli with
   shear_modulus_g13 and shear_modulus_g23.
4. Predict the in-plane cell-wall-bending moduli with
   inplane_modulus_e1, inplane_modulus_e2 and
   inplane_shear_modulus_g12.
5. Run the one-shot report honeycomb_core_properties for the full
   equivalent-core-properties dict, letting it derive the foil shear
   modulus when g_s is not supplied.
6. Confirm the deterministic checks and the ValueError rejection of
   non-physical geometry or foil inputs with the contract test
   scripts/test_honeycomb_core_micromechanics.py.

## Worked example

Case A, the main worked example: a regular-hex 1/8-inch-class 5056
aluminum foil core, h/l = 1, theta = 30 deg, t/l = 0.02, E_s = 72.0
GPa, nu_s = 0.33, rho_s = 2640.0 kg/m^3.

- Foil shear modulus: G_s = 72.0e9/(2(1 + 0.33)) = 27067669172.9323 Pa.
- Relative density: rho*/rho_s = 0.023094010767585, matching the
  regular-hexagon reduction (2/sqrt(3))(0.02) to the 3e-16 relative
  level.
- Core density: rho* = 60.9681884264245 kg/m^3, about 61 kg/m^3.
- Stabilized compressive modulus: E3 = 1662768775.26612 Pa, about
  1.66 GPa.
- Out-of-plane shear moduli: G13 = G23 = 312550521.666564 Pa, equal at
  the regular hexagon and equal to G_s (rho*/rho_s)/2.
- In-plane cell-wall-bending moduli: E1* = E2* = 1330215.0202129 Pa
  and G12* = 332553.755053225 Pa = E1*/4.

Case B, the 3.2 mm cell, 0.038 mm foil 5056 core (l = 3.2/sqrt(3) mm,
t/l = 0.020568103): relative_density = 0.02375, E3 = 1710000000 Pa,
core density = 62.700000 kg/m^3, G13 = G23 = 321428571.4285714 Pa.

Case C, an elongated cell on 7075 foil (E_s = 71.7 GPa, nu_s = 0.33,
rho_s = 2810.0 kg/m^3, h/l = 1.5, theta = 30 deg, t/l = 0.02):
rho*/rho_s = 0.0202072594216369, core density = 56.782399 kg/m^3, E3 =
1448860500.53137 Pa, G13 = 233436170.869715 Pa, G23 =
138332545.700572 Pa, with G13/G23 = 1.687500000 exactly the
closed-form ratio at h/l = 1.5.

## Verification

- Confirm relative_density(0.02, 1.0, 30.0) is within 1e-9 relative of
  0.023094010767585 and equals (2/sqrt(3))(0.02) exactly within 1e-9.
- Confirm shear_modulus_g13 and shear_modulus_g23 coincide at the
  regular hexagon and equal g_s (rho*/rho_s)/2 within 1e-9 relative at
  t/l in {0.01, 0.02, 0.05}.
- Confirm the G13/G23 ratio equals the closed-form algebraic identity
  within 1e-12 relative at h/l in {0.5, 0.8, 1.0, 1.2, 1.5, 2.0} with
  theta = 30 deg, sitting below 1 for h/l below 1 and above 1 for h/l
  above 1.
- Confirm inplane_modulus_e1 equals inplane_modulus_e2 and
  inplane_shear_modulus_g12 equals e1/4 at the regular hexagon.
- Confirm compressive_modulus_e3 is exactly linear in the foil modulus
  at fixed geometry (doubling E_s doubles E3 within 1e-12 relative).
- Confirm honeycomb_core_properties with g_s omitted matches the dict
  built with an explicit shear_modulus_isotropic value within 1e-12
  relative on every one of the eleven keys.
- Confirm every t/l outside (0, 1), h/l at or below 0, theta outside
  (0, 90) degrees, non-positive foil modulus, Poisson ratio outside
  [0, 0.5), non-positive foil density, non-positive explicit shear
  modulus, and a boolean in place of any numeric input raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_honeycomb_core_micromechanics.py (25 tests,
  deterministic).

## Related leaves

- structures/composites/sandwich-panels: consumes the core modulus Ec
  and core shear modulus Gc as workflow step 1 given inputs for the
  panel-level bending stiffness, face stress and deflection analysis;
  this leaf produces those equivalent core properties from the cell
  geometry, it never analyzes the panel or selects a core type.
- structures/composites/unidirectional-lamina-micromechanics: the
  in-pack precedent for predicting engineering constants from
  constituent inputs, fiber and matrix there, foil and cell geometry
  here.
- structures/materials/material-selection: foil alloy property
  context (modulus, Poisson ratio, density) for reference, verified
  against MMPDS or CMH-17 before design use; this leaf never looks up
  or reproduces those values.

## Pitfalls

- Feeding the fiber-side unidirectional-lamina-micromechanics outputs
  or panel-level Ec/Gc values into this leaf as inputs: cell geometry
  (t/l, h/l, theta) and the isotropic foil properties are the only
  inputs; the equivalent core properties are the outputs this leaf
  produces, not collected data.
- Treating E3 as an unstabilized strength property: the stabilized
  compressive modulus E3 = E_s (rho*/rho_s) describes the in-service
  loaded core, not an empirical strength property of a specific core
  grade, which this leaf never predicts.
- Using the axial G13 form for the transverse direction or vice versa:
  the two closed forms only coincide at the regular hexagon (h/l = 1,
  theta = 30 deg); at an elongated cell (Case C, h/l = 1.5) G13 is
  1.6875 times G23, so swapping them misstates the shear stiffness in
  the weaker direction.
- Passing the fiber axial or transverse convention from the composite
  siblings into the foil shear derivation: the foil is an isotropic
  aluminum sheet, so G_s = E_s/(2(1 + nu_s)) always, never a
  Halpin-Tsai or rule-of-mixtures form.
- Reporting these predicted properties as design allowables: the
  outputs are closed-form cell-geometry arithmetic, not a specific
  vendor's published core property values or CMH-17 design values;
  core defects, node bond quality, moisture and statistical scatter
  are out of scope.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_honeycomb_core_micromechanics.py

The test covers the Case A worked example (relative density, core
density, E3, G13, G23, E1, E2 and G12 within tolerance of the real
module outputs and inside the magnitude gates), the regular-hexagon
reduction and shear-coincidence identities, the G13/G23 ordering sweep
against the closed-form ratio, the in-plane isotropy degeneracy, the
Case B and Case C corpus geometries, the E3 linear scaling in the foil
modulus, the one-shot report keys, its g_s-omitted versus explicit-g_s
identity, determinism, and ValueError rejection of every non-physical
or boolean geometry and foil input.

## Compliance

- Standards referenced, not reproduced: CMH-17 (Composite Materials
  Handbook, SAE International) frames the core property conventions
  this prediction feeds, reference-only per standards-map.yaml; no
  CMH-17 table or design value is reproduced.
- compliance: STANDARDS-REF, gated: false.
