---
name: unidirectional-lamina-micromechanics
description: "Use when you must predict the engineering constants of a unidirectional composite lamina from the fiber and matrix constituent properties and the fiber volume fraction: compute the longitudinal modulus E1 and the major Poisson ratio nu12 by the rule of mixtures, the transverse modulus E2 by the Halpin-Tsai closed form with the xi equal to 2 shape factor on the fiber transverse modulus, the in-plane shear modulus G12 by the Halpin-Tsai closed form with the xi equal to 1 shape factor on the fiber shear modulus, and the density by the rule of mixtures. Produces the lamina engineering constants in the material axes and the Voigt-Reuss and Hashin-Shtrikman bound bands on E2 and G12 as the verification envelope predictions fall inside. Constituent properties are inputs; no property tables are reproduced. Trigger: unidirectional lamina micromechanics, fiber volume fraction, rule of mixtures, halpin tsai transverse and shear moduli, hashin shtrikman bounds."
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
  tags: [unidirectional-lamina-micromechanics, rule-of-mixtures, halpin-tsai-equations, fiber-volume-fraction, constituent-property-prediction, voigt-reuss-bounds, hashin-shtrikman-bounds]
  version: 0.1.0
  author: AeroSkills
---

# Unidirectional Lamina Micromechanics (structures/composites/unidirectional-lamina-micromechanics)

Use when the task is predicting the four lamina engineering constants,
E1, nu12, E2 and G12, of a unidirectional composite ply from the fiber
and matrix constituent properties and the fiber volume fraction, the
producer side of the lamina-constant chain that
structures/composites/laminate-stiffness takes as a given input at its
workflow step 1. This leaf implements the rule of mixtures for the
longitudinal modulus, major Poisson ratio and density, and the
Halpin-Tsai closed form for the transverse modulus and in-plane shear
modulus, with the Voigt-Reuss and Hashin-Shtrikman bound bands as the
verification envelope. Pure Python, stdlib only. It pairs with
structures/composites/laminate-stiffness for the downstream ply
stiffness and laminate A matrix, and with
structures/materials/material-selection for constituent property
context.

## Domain quick reference

- Rule of mixtures (exact for the composite cylinder assemblage): E1 =
  V_f E_f + V_m E_m and nu12 = V_f nu_f + V_m nu_m, with V_m = 1 - V_f.
  The fiber axial modulus E_f and major Poisson ratio nu_f enter the
  longitudinal arm directly.
- Matrix shear modulus (isotropic matrix): G_m = E_m / (2 (1 + nu_m)).
- Halpin-Tsai shared form: eta = (Mr - 1) / (Mr + xi) with Mr the
  constituent property ratio; P / P_m = (1 + xi eta V_f) / (1 - eta V_f).
- Transverse modulus E2: the Halpin-Tsai closed form against the fiber
  TRANSVERSE modulus ratio E_fT / E_m with the circular-fiber shape
  factor xi_E2 = 2.0. A carbon fiber is transversely isotropic; using
  the fiber axial modulus in this arm overpredicts E2 by roughly a
  factor of two.
- In-plane shear modulus G12: the Halpin-Tsai closed form against G_f /
  G_m with the circular-fiber shape factor xi_G12 = 1.0, which equals
  exactly the composite-cylinder-assemblage longitudinal shear solution.
- Density: rho_c = V_f rho_f + V_m rho_m, when both constituent
  densities are given.
- Voigt/Reuss band: E2_Voigt = V_f E_fT + V_m E_m (iso-strain upper
  bound) and E2_Reuss = 1 / (V_f / E_fT + V_m / E_m) (iso-stress lower
  bound); the same two forms with G_f and G_m give the G12 band.
- Hashin-Shtrikman G12 band (anti-plane, circular-cylinder problem): the
  lower endpoint equals the xi_G12 = 1 Halpin-Tsai value exactly.
- Hashin-Shtrikman E2 band (in-plane, Hashin 1965 plane-strain bulk
  modulus k* and transverse shear modulus m* bounds): converted through
  the exact transverse-isotropy identity E2 = 4 k m E1 / (E1 (k + m) +
  4 k m nu12^2) at the exact CCA E1 and nu12.
- Module constants XI_E2 = 2.0 and XI_G12 = 1.0 are the standard
  circular-fiber Halpin-Tsai shape factors (Halpin and Tsai, AFML-TR-67-
  423, 1969); the model is closed-form arithmetic in SI units (Pa,
  kg/m^3) on the unidirectional lamina in its material axes.

## Workflow

1. Collect the fiber constituent properties (axial modulus E_f, major
   Poisson ratio nu_f, transverse modulus E_fT, longitudinal shear
   modulus G_f), the matrix constituent properties (modulus E_m,
   Poisson ratio nu_m) and the fiber volume fraction V_f.
2. Derive the matrix shear modulus with shear_modulus_isotropic(E_m,
   nu_m).
3. Predict the longitudinal modulus E1 and major Poisson ratio nu12 by
   the rule of mixtures with e1_longitudinal and nu12_major.
4. Predict the transverse modulus E2 with e2_halpin_tsai, using the
   fiber transverse modulus E_fT and the xi_E2 = 2 shape factor, never
   the fiber axial modulus.
5. Predict the in-plane shear modulus G12 with g12_halpin_tsai, using
   the fiber shear modulus G_f and the xi_G12 = 1 shape factor.
6. Compute the density with rho_composite when both constituent
   densities are given.
7. Verify E2 against the Voigt-Reuss bound band (e2_voigt_upper,
   e2_reuss_lower) and the tighter Hashin-Shtrikman bound band
   (e2_hashin_shtrikman_bounds).
8. Verify G12 against the Voigt-Reuss bound band (g12_voigt_upper,
   g12_reuss_lower) and the Hashin-Shtrikman bound band
   (g12_hashin_shtrikman_bounds), noting the xi_G12 = 1 identity with
   the lower endpoint.
9. Run the one-shot report unidirectional_lamina_constants for the full
   engineering-constants and bound-band dict.
10. Confirm the deterministic checks with the contract test
    scripts/test_unidirectional_lamina_micromechanics.py.

## Worked example

A T300 carbon / epoxy 5208-class unidirectional ply at V_f = 0.60.
Constituent inputs: E_f = 230.0 GPa, nu_f = 0.20, E_fT = 20.0 GPa, G_f =
27.0 GPa (fiber); E_m = 3.5 GPa, nu_m = 0.35 (epoxy matrix); rho_f =
1760.0 kg/m^3, rho_m = 1230.0 kg/m^3.

- Matrix shear modulus: G_m = 3.5 / (2 (1 + 0.35)) = 1.296296 GPa.
- Rule of mixtures: E1 = 0.60 * 230 + 0.40 * 3.5 = 139.400000 GPa;
  nu12 = 0.60 * 0.20 + 0.40 * 0.35 = 0.260000.
- Halpin-Tsai E2: eta = (20 / 3.5 - 1) / (20 / 3.5 + 2) = 0.611111, and
  E2 = 3.5 * (1 + 2 * 0.611111 * 0.60) / (1 - 0.611111 * 0.60) =
  9.578947 GPa.
- Halpin-Tsai G12: G12 = 4.402037 GPa, exactly the composite-cylinder-
  assemblage longitudinal shear solution.
- Density: rho = 0.60 * 1760 + 0.40 * 1230 = 1548.000000 kg/m^3.
- E2 band (GPa): Reuss 6.930693 < Hashin-Shtrikman 8.821709 < 9.578947
  < Hashin-Shtrikman 10.939799 < Voigt 13.400000, with the magnitude
  gate E1 in [135, 145] GPa, E2 in [8, 12] GPa and G12 in [4, 6] GPa
  (Daniel and Ishai textbook T300/5208 values).
- G12 band (GPa): Reuss 3.023033 < 4.402037 = Hashin-Shtrikman lower
  4.402037 < Hashin-Shtrikman upper 12.608295 < Voigt 16.718519, the
  Halpin-Tsai prediction attaining the Hashin-Shtrikman lower endpoint
  exactly.
- Degeneracies: at V_f = 0 the E2 band closes to E_m (3.500000 GPa)
  exactly; at V_f = 1 it closes to 20.758123 GPa, 3.8 percent above
  E_fT because of the cross-section idealization in the k* and m*
  bounds, while the Halpin-Tsai E2 limit at V_f = 1 is exactly E_fT.

## Verification

- Confirm e1_longitudinal(230e9, 3.5e9, 0.6) is within 1e-6 relative of
  139.4e9 and nu12_major(0.2, 0.35, 0.6) is within 1e-9 of 0.26.
- Confirm e2_halpin_tsai(20e9, 3.5e9, 0.6) is within 1e-6 relative of
  9578947368.421053 and g12_halpin_tsai(27e9, 1296296296.2962961, 0.6)
  is within 1e-6 relative of 4402037250.138515.
- Confirm the nested-band ordering at V_f = 0.6: E2 Reuss < E2
  Hashin-Shtrikman lower < E2 Halpin-Tsai < E2 Hashin-Shtrikman upper <
  E2 Voigt, and the analogous G12 ordering with the Halpin-Tsai and
  Hashin-Shtrikman lower endpoint equal.
- Confirm the G12 Halpin-Tsai and Hashin-Shtrikman lower-bound identity
  holds within 1e-9 relative at V_f in {0.3, 0.5, 0.6, 0.7}.
- Confirm the V_f = 0 and V_f = 1 degeneracies and the E2-in-band sweep
  over V_f in [0.3, 0.9].
- Confirm every non-positive or boolean modulus, density and shape
  factor, every Poisson ratio outside [0, 0.5), every fiber volume
  fraction outside [0, 1], and a fiber that is not the stiffer shear or
  cross-section phase raises ValueError.
- Run the contract test offline: python3
  scripts/test_unidirectional_lamina_micromechanics.py (41 tests,
  deterministic).

## Related leaves

- structures/composites/laminate-stiffness: consumes E1, E2, nu12 and
  G12 as workflow step 1 inputs to build the ply stiffness, rotate it
  and assemble the laminate A matrix; this leaf produces those four
  constants, it never assembles stiffness matrices.
- structures/composites/failure-criteria: consumes lamina allowables
  and strength values, not the elastic constants this leaf predicts.
- structures/composites/laminate-hygrothermal-response: owns the
  moisture content, CTE and CME vein from ply-level properties; this
  leaf stops at density.
- structures/materials/material-selection: representative constituent
  property bands for reference, verified against MMPDS, AMS or CMH-17
  before design use; this leaf never looks up or reproduces those
  bands.

## Pitfalls

- Using the fiber axial modulus E_f in the transverse Halpin-Tsai arm
  instead of the fiber transverse modulus E_fT: a carbon fiber is
  transversely isotropic, and this substitution overpredicts E2 by
  roughly a factor of two, the classic bug class here.
- Reading the Voigt/Reuss band as the tight envelope: the
  Hashin-Shtrikman band is always tighter, with the Reuss bound at or
  below the Hashin-Shtrikman lower bound and the Voigt bound at or
  above the Hashin-Shtrikman upper bound (6.930693 GPa Reuss against
  8.821709 GPa Hashin-Shtrikman lower at the worked V_f = 0.6).
- Expecting the E2 Hashin-Shtrikman band to close exactly to E_fT at
  V_f = 1: the in-plane cross-section idealization used to keep the
  band closed-form gives 20.758123 GPa, 3.8 percent above the 20.0 GPa
  E_fT value that the Halpin-Tsai estimator itself reaches exactly.
- Trusting the xi_E2 = 2 estimator below roughly V_f = 0.25: the fixed
  semi-empirical shape factor can dip slightly under the variational
  Hashin-Shtrikman lower bound there (Wall 1997); the verification
  sweep in this leaf deliberately starts at V_f = 0.3.
- Passing engineering constants E1, E2, nu12, G12 into this leaf as
  inputs: they are the OUTPUTS of the constituent-level prediction here,
  never collected inputs; structures/composites/laminate-stiffness is
  the leaf that takes them as given.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_unidirectional_lamina_micromechanics.py

The test covers the T300/5208 worked example (E1, nu12, E2, G12 and
density within tolerance of the real module outputs and inside the
magnitude gates), the matrix shear derivation, the nested Voigt-Reuss
and Hashin-Shtrikman band ordering for both E2 and G12 at the worked
volume fraction, the G12 Halpin-Tsai and Hashin-Shtrikman lower-bound
identity across volume fractions, the V_f = 0 and V_f = 1 degeneracies,
the E2-in-band sweep over V_f in [0.3, 0.9], the isotropic-fiber
collapse, the one-shot report keys and determinism, and ValueError
rejection of every non-physical or boolean input and of a fiber that is
not the stiffer shear or cross-section phase.

## Compliance

- Standards referenced, not reproduced: CMH-17 (Composite Materials
  Handbook, SAE International) frames the constituent and lamina
  property data conventions this prediction feeds, reference-only per
  standards-map.yaml; no CMH-17 table or design value is reproduced.
- compliance: STANDARDS-REF, gated: false.
