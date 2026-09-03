---
name: thermal-buckling
description: "Use when you must compute the thermal buckling of restrained aerospace structure from a temperature rise: the elastic buckling stress of a uniformly compressed flat plate, the compressive stress built by a constrained temperature change under uniaxial or biaxial restraint, the critical-temperature-rise that drives a skin panel to its buckling stress, and the critical-temperature-rise of an Euler column between rigid supports. Produces the buckling stress, the compressive stress at a given rise, and the critical temperature rise, plus the thermal-buckling-margin that gates a thermal-stability check. Trigger: thermal-buckling, critical-temperature-rise, restrained-temperature, thermal-buckling-margin, skin panel, hot structure, Euler column."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: thermal-structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: thermal-structures
  tags: [thermal-buckling, critical-temperature-rise, restrained-thermal-expansion, thermal-buckling-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# Thermal Buckling (structures/thermal-structures/thermal-buckling)

Use when the task is the thermal buckling of a restrained aerospace
structure: a skin panel or column whose free expansion is blocked, so a
temperature rise builds an in-plane compressive load that can buckle
the member at a critical temperature. This leaf computes the elastic
buckling stress of a flat plate under uniform compression, the
compressive stress developed by a constrained temperature change under
uniaxial or biaxial restraint, the critical temperature rise that
drives a plate or an Euler column to buckling, and the resulting
margin. The logic module is pure Python standard library (no numpy, no
FEA software) and deterministic. Units are SI: E in Pa, alpha in 1/K,
thickness, width and lengths in m, stresses in Pa, temperature rise in
K. It pairs with structures/thermal-structures/thermal-stress-analysis
for fully constrained and bimetallic members and with
structures/fem/plate-buckling for mechanically loaded plates.

## Domain quick reference

- Plate flexural rigidity:

      D = E * t**3 / (12 * (1 - nu**2))

- Elastic buckling stress of a flat plate under uniform compression
  (long simply supported plate):

      sigma_cr = k * pi**2 * D / (b**2 * t)

  with b the loaded-width direction dimension and the edge condition
  coefficient k = 4.0 for a long plate simply supported on all edges.
  The plate buckles when the compressive stress reaches sigma_cr.

- Compressive stress from a restrained temperature rise. Free thermal
  strain alpha * dT is blocked, so the restraint converts it into
  stress. Uniaxial restraint:

      sigma = E * alpha * dT

  Biaxial restraint (restraint in both in-plane directions):

      sigma = E * alpha * dT / (1 - nu)

- Critical temperature rise of a restrained plate: set the thermal
  stress equal to sigma_cr and solve for dT. Uniaxial:

      dT_cr = sigma_cr / (E * alpha)

  Biaxial:

      dT_cr = sigma_cr * (1 - nu) / (E * alpha)

- Euler column between rigid supports: the axial thermal load is
  P = alpha * E * A * dT and buckling occurs at P_cr = pi**2 * E * I /
  L_eff**2. With I = A * r**2 the area and modulus cancel:

      dT_cr = pi**2 * r**2 / (alpha * L_eff**2)

- Margin of a hot panel: margin = sigma_cr / sigma_thermal - 1.
  Positive means the panel is safe at that temperature rise; the sign
  flips when the rise exceeds the critical value.

- FAR 25 frames the airframe strength context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the material and geometry: elastic_modulus E, poisson nu,
   coefficient alpha, plate thickness t and width b, or column
   effective_length L_eff and radius_of_gyration r.
2. Compute the plate elastic buckling stress with
   plate_buckling_stress (k_coefficient defaults to 4.0).
3. Compute the compressive stress developed at the operating
   temperature rise: thermal_stress_uniaxial for restraint in one
   direction or thermal_stress_biaxial when both in-plane directions
   are blocked.
4. Find the temperature rise that buckles the panel with
   critical_temp_plate, passing restraint = "uniaxial" or "biaxial";
   for a column between rigid supports use column_critical_temp.
5. Run the full check with thermal_buckling_assessment, which returns
   buckling_stress_Pa, thermal_stress_Pa, critical_temp_rise_K and the
   margin in one dict.
6. Read the margin: positive margin means the rise is below the
   critical value, negative means the panel buckles.
7. Confirm the deterministic checks with the contract test
   scripts/test_thermal_buckling.py.

## Worked example

Aluminum skin panel: E = 72 GPa, nu = 0.33, alpha = 23e-6 /K,
t = 1.6 mm, b = 150 mm, k = 4.0, uniaxial restraint.

- Plate buckling stress: sigma_cr = 30.24 MPa (30.244 MPa, inside the
  25 to 40 MPa band of the hand estimate).
- Compressive stress at dT = 10 K: E * alpha * dT = 72e9 * 23e-6 * 10
  = 1.656e7 Pa exactly (16.56 MPa).
- Critical temperature rise: uniaxial 18.26 K; biaxial
  18.26 * (1 - 0.33) = 12.24 K, ratio exactly 0.67. Both inside the
  15 to 25 K band for the uniaxial case.
- Margin at dT = 10 K: 30.24 / 16.56 - 1 = +0.83, panel safe. At
  dT = 30 K: 30.24 / 49.68 - 1 = -0.39, panel buckles.
- Euler column (steel, alpha = 12e-6 /K, r = 25 mm, L_eff = 2.0 m):
  dT_cr = pi**2 * 0.025**2 / (12e-6 * 2.0**2) = 128.5 K (110 to 150 K
  band).

## Verification

- Confirm plate_buckling_stress(72e9, 0.33, 1.6e-3, 0.150) returns
  3.024e7 Pa, inside 25 to 40 MPa.
- Confirm thermal_stress_uniaxial(72e9, 23e-6, 10.0) returns exactly
  1.656e7 Pa.
- Confirm critical_temp_plate returns 18.26 K uniaxial and that the
  biaxial value divided by the uniaxial value equals 0.67 within 1e-9
  relative.
- Confirm column_critical_temp(200e9, 12e-6, 2.0, 0.025) returns
  128.5 K and is independent of the modulus.
- Confirm the round trip: the thermal stress evaluated at the critical
  temperature rise equals the plate buckling stress.
- Confirm every non-positive modulus, thickness, width, length,
  k_coefficient, every poisson outside (-1, 0.5), alpha of zero in the
  critical rise functions, a negative temperature rise, an invalid
  restraint string, and a zero rise in the assessment raise ValueError.
- Run the contract test offline: python3
  scripts/test_thermal_buckling.py (35 tests, deterministic).

## Related leaves

- structures/thermal-structures/thermal-stress-analysis: constrained
  thermal stress of fully restrained members, bimetallic strips and
  their curvature; the companion leaf for members that do not buckle.
- structures/fem/plate-buckling: plate buckling under applied
  mechanical compression or shear with edge condition k coefficients.
- structures/materials/creep-rupture: material response limits for hot
  structure beyond elastic behavior.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_thermal_buckling.py

The test covers the worked-example anchors (plate buckling stress
30.24 MPa in the 25 to 40 MPa band, exact 1.656e7 Pa thermal stress at
dT = 10 K, critical temperature rise 18.26 K in the 15 to 25 K band,
uniaxial-to-biaxial ratio 0.67, column 128.5 K in the 110 to 150 K
band), the scaling identities of each closed-form relation, the
round-trip identity between thermal stress at the critical rise and the
buckling stress, positive and negative margin sign cases, determinism,
and ValueError rejection of every non-physical input listed above.

## Compliance

- Standards referenced, not reproduced: FAR 25 (airframe strength) is
  referenced by name only; the thermal buckling relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
