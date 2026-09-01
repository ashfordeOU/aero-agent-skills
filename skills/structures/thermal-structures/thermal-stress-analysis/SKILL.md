---
name: thermal-stress-analysis
description: "Compute thermal stress and strain in aerospace structures from a constrained temperature change: free thermal strain alpha*dT, fully constrained thermal stress sigma = E*alpha*dT when free expansion is blocked, the bimetallic strip curvature and per-layer thermal stress balance, and the critical temperature rise for thermal buckling of a constrained plate, each with the margin of safety against the allowable stress. Use when a structural member, bonded joint or skin panel is restrained against thermal expansion and must be assessed for thermal load in a stdlib-only environment without FEA software. Units are SI. Trigger: thermal stress, thermal expansion, coefficient of thermal expansion, bimetallic strip, constrained expansion, thermal buckling."
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
  tags: [thermal-stress, thermal-expansion, coefficient-of-thermal-expansion, bimetallic-strip, constrained-expansion, free-expansion, thermal-buckling, temperature-change, thermal-strain, thermal-load]
  version: 0.1.0
  author: AeroSkills
---

# Thermal Stress Analysis (structures/thermal-structures/thermal-stress-analysis)

Use when the task is the thermal stress and strain of a constrained
aerospace structure: a member whose free expansion is blocked and
therefore develops sigma = E * alpha * dT, a bonded bimetallic strip
whose two layers bend under a temperature change, or a plate
constrained against in-plane expansion that may buckle thermally. The
logic module is pure Python standard library (no numpy, no FEA
software) and deterministic. Units are SI: E in Pa, alpha in 1/K, dT
in K, t and b in m, stresses in Pa, curvature in 1/m, force per unit
width in N/m.

## Domain quick reference

- Free thermal strain of an unrestrained member:

      eps = alpha * dT

  If the expansion is free, no stress develops. The stress appears
  only when the structure restrains the expansion.

- Fully constrained member (free expansion blocked in the load
  direction):

      sigma = E * alpha * dT

  Cooling (negative dT) reverses the sign and puts the member in
  tension instead of compression. The constraint can be geometric
  (a member welded or bolted between rigid supports) or kinematic
  (a thermal gradient in a redundant structure).

- Bimetallic strip of two bonded layers with thicknesses t1, t2,
  moduli E1, E2 and coefficients alpha1, alpha2 under a temperature
  change dT. The layers must share the interface strain, so an equal
  and opposite axial force per unit width P develops together with a
  common curvature kappa:

      kappa = (alpha2 - alpha1) * dT /
              ( (t1 + t2)/2 + 2*(E1*I1 + E2*I2)/(t1 + t2)
                * (1/(E1*t1) + 1/(E2*t2)) )
      P     = 2 * kappa * (E1*I1 + E2*I2) / (t1 + t2)

  with I_i = width * t_i^3 / 12 per unit width. The layer with the
  higher coefficient ends up in compression on the concave side. For
  equal thicknesses and equal moduli the result collapses to the
  classic forms kappa = 1.5 * (alpha2 - alpha1) * dT / (t1 + t2) and
  a layer stress of magnitude E * (alpha2 - alpha1) * dT / 8.

- Thermal buckling of a plate constrained against in-plane expansion
  (a long skin panel held between stiffeners): the temperature rise
  generates the compression E * alpha * dT, and buckling occurs when
  that stress reaches the plate critical stress, so

      dT_cr = k * pi^2 / (12 * (1 - nu^2) * alpha) * (t / b)^2

  with k the plate buckling coefficient (4.0 for a simply supported
  long plate, 6.97 clamped). The critical temperature rise scales
  with the square of the thickness-to-width ratio, exactly like the
  elastic buckling stress it is derived from.

Worked anchors (verified by running scripts/thermal_stress_analysis_logic.py):
an aluminum member with E = 70 GPa, alpha = 23e-6 1/K and dT = 100 K
has a free strain of 2300 microstrain and, fully constrained, a
thermal stress of 161 MPa; against an allowable of 250 MPa the margin
of safety is 0.553. A bimetallic strip of steel (alpha = 11e-6 1/K)
and aluminum (alpha = 23e-6 1/K), each 1 mm thick with E = 70 GPa,
under dT = 100 K bends to kappa = 0.9 1/m with a layer stress of
10.5 MPa. Doubling the aluminum modulus to 140 GPa changes the
curvature to 0.8727 1/m and the layer stress to 15.27 MPa. A 2 mm
aluminum skin on 150 mm stiffener pitch with E = 70 GPa, alpha = 23e-6
1/K and nu = 0.33 buckles at a critical temperature rise of 28.54 K.

## Workflow

1. Decide what is being asked. A free member only needs the free
   strain; a member with blocked expansion needs the constrained
   stress; two bonded layers need the bimetallic balance; a
   constrained panel under heating needs the thermal buckling check.
2. For a constrained member, compute the free strain with
   free_thermal_strain(alpha, dT) and the stress with
   constrained_thermal_stress(E, alpha, dT). Run the complete margin
   check with thermal_stress_check(E, alpha, dT, allowable_stress),
   which returns the stress, the strain, the margin of safety and the
   acceptable verdict. Apply the required factor of safety from the
   certification basis before comparing against the allowable.
3. For a bonded pair, call bimetallic_strip(E1, E2, alpha1, alpha2,
   t1, t2, dT, width) and read off the curvature, the interface force
   per unit width and the two layer stresses. Use the returned force
   as the load input for a joint or bondline check.
4. For a constrained plate under a temperature rise, compute the
   critical temperature rise with thermal_buckling_critical_dT(E,
   alpha, nu, t, b, coefficient) or run the full check with
   thermal_buckling_check(E, alpha, nu, t, b, applied_dT,
   coefficient), which returns the critical temperature rise, the
   margin of safety and the stable verdict.
5. Verify the sign convention: positive dT with blocked expansion is
   compression; the layer with the higher coefficient sits on the
   concave side of a heated bimetallic strip.

## Pitfalls

- Routing spacecraft thermal control here: radiator sizing, thermal
  balance and dissipation budgets of spacecraft subsystems belong to
  the space-systems thermal-design leaf; thermal-stress-analysis
  computes mechanical stress and strain from a temperature change in
  a constrained structure.
- Routing column thermal effects here: buckling-analysis handles 1D
  columns with Euler loads and slenderness; thermal-stress-analysis
  never uses a slenderness ratio and the thermal buckling check
  applies to a constrained flat plate only.
- Routing elastic plate buckling here: plate-buckling checks an
  applied mechanical edge load against the critical stress;
  thermal-stress-analysis derives the critical temperature rise from
  the same formula but the load comes from blocked thermal expansion.
- Forgetting the constraint: an unrestrained member carries no
  thermal stress no matter how large the temperature change; sigma =
  E * alpha * dT applies only when the expansion is blocked.
- Applying the biaxial correction blindly: a plate fully restrained
  in both in-plane directions develops E * alpha * dT / (1 - nu); the
  thermal buckling check here assumes the long-panel case restrained
  in one direction, which keeps the stress at E * alpha * dT. State
  the restraint model before choosing the formula.
- Mixing units: E in GPa with t and b in mm silently corrupts the
  stress and the critical temperature rise by factors of 1e9 or 1e6;
  keep everything SI (Pa, m).
- Using a negative coefficient: alpha must be positive for the
  thermal buckling check (the critical temperature rise divides by
  alpha); real materials with negative expansion coefficients need a
  dedicated treatment.
- Reading the bimetallic sign wrong: the layer with the higher
  coefficient is compressed and sits on the concave side; the two
  layer stresses are equal and opposite in magnitude when the
  thicknesses are equal.

## Behavior contract (gate 3)

The thermal stress logic is exercised by the gate 3 contract test:
scripts/test_thermal_stress_analysis.py against
scripts/thermal_stress_analysis_logic.py (stdlib unittest, offline).
It asserts the worked anchors above, the zero-stress case at dT = 0,
the linear scalings with E, alpha and dT, the equal-layer bimetallic
closed form and the unequal-modulus case, the (t/b)^2 scaling of the
critical temperature rise, the margin and verdict outputs, and the
ValueError cases for non-positive, non-finite or unknown inputs. Run:

python3 scripts/test_thermal_stress_analysis.py

## Compliance

- FAR-25 is referenced, not reproduced: standards-map.yaml marks it
  gated: false and reference-only: true; only the summary paraphrase
  above is used, never standard text.
- compliance: STANDARDS-REF, gated: false.
