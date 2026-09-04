---
name: cylindrical-shell-buckling
description: "Use when you must compute the buckling of a curved unstiffened circular cylindrical shell with the NASA SP-8007 knockdown method: the axial-compression knockdown factor from the shell radius and thickness, the axial critical buckling stress 0.605*gamma*E*t/r, the bending knockdown factor, the bending critical moment, the cross-section ovalization collapse moment, and the plasticity correction factor. Produces the knockdown factors, the critical stress and moments, and the governing verdict between bifurcation and ovalization collapse for a curved-shell stability check. Trigger: cylindrical shell buckling, SP-8007 knockdown, shell axial compression, cylinder bending, ovalization collapse, curved panel stability, fuselage barrel buckling."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [cylindrical-shell-buckling, sp-8007-knockdown, shell-axial-compression, external-shell-bending, cross-section-ovalization, shell-plasticity-correction]
  version: 0.1.0
  author: AeroSkills
---

# Cylindrical Shell Buckling (structures/fem/cylindrical-shell-buckling)

Use when the task is the elastic stability of a curved, unstiffened
circular cylindrical shell (fuselage barrel, pressure-vessel or tank
shell, duct) under axial compression or bending. This leaf implements
the NASA SP-8007 empirical knockdown method ("Buckling of Thin-Walled
Circular Cylinders", 1968 original / 2023 NTRS revision 20205011530,
public domain): the axial knockdown factor gamma_axial from the shell
radius r and thickness t, the axial critical stress, the bending
knockdown factor gamma_bending, the bending critical moment, the
cross-section ovalization collapse moment, and the plasticity
correction factor eta. It pairs with the flat-panel leaf
structures/fem/plate-buckling, which explicitly defers the curved case
here, and with structures/fem/buckling-analysis for slender straight
members. The SP-8007 knockdowns are empirical fits for thin shells with
r/t below about 1500; the classical stress terms are elastic, so the
plasticity correction eta is reported separately and applied by the
user when the material is beyond its proportional limit.

## Domain quick reference

- Curvature parameter: phi = (1/16)*sqrt(r/t). It sets the knockdown
  sensitivity: very thin shells (large r/t) carry larger knockdowns.
- Axial knockdown factor: gamma_axial = 1 - 0.901*(1 - exp(-phi)),
  monotonic decreasing in r/t and always in (0, 1).
- Axial critical stress: sigma_cr = 0.605*gamma_axial*E*t/r, where the
  0.605 coefficient is the classical value 1/sqrt(3*(1-nu^2)) at
  nu = 0.3.
- Bending knockdown factor: gamma_bending = 1 - 0.731*(1 - exp(-phi)).
- Bending critical moment: M_cr = pi*0.605*gamma_bending*E*t**2*r. The
  axial critical stress acts over the full wall section (area pi*r*t)
  at the extreme-fiber arm r, giving M = sigma_cr*(pi*r*t)*r.
- Ovalization collapse moment: M_ov = 0.987*E*r*t**2/sqrt(1-nu**2),
  the Brazier-style collapse of the cross section under bending.
- Governing verdict: "bifurcation" when M_cr < M_ov, else
  "ovalization". SP-8007 notes the bending bifurcation precedes
  collapse for shells in the validity band.
- Plasticity correction: eta = sqrt(E_sec*E_tan)/E with the secant and
  tangent moduli at the acting stress; eta = 1 in the elastic range.
- SI units throughout: m, Pa, N*m.
- Validity guard: r/t must be below 1500 for the empirical knockdowns.

## Workflow

1. Fix the geometry and material: radius_m, thickness_m, e_mod_pa and
   the Poisson ratio (default 0.3). Confirm r/t < 1500.
2. Get the knockdown factors: knockdown_axial and knockdown_bending,
   or read gamma_axial and gamma_bending from
   shell_buckling_assessment.
3. Compute the axial critical stress with axial_critical_stress
   (gamma defaults to the internal axial knockdown).
4. Compute the bending critical moment with bending_critical_moment
   (gamma defaults to the internal bending knockdown).
5. Compute the ovalization collapse moment with
   ovalization_collapse_moment.
6. When the material may be beyond the proportional limit, pass the
   secant and tangent moduli to plasticity_correction and scale the
   elastic margins by eta (SP-8007 stresses are elastic).
7. Run shell_buckling_assessment for the full dict including the
   governing verdict between bifurcation and ovalization collapse.
8. Confirm the deterministic checks with the contract test
   scripts/test_cylindrical_shell_buckling.py.

## Worked example

Aluminum barrel: E = 70 GPa, r = 1.5 m, t = 0.005 m (r/t = 300),
nu = 0.3. Real module outputs:

- curvature_parameter = 1.0825 (sqrt(300)/16).
- gamma_axial = 0.4042, in the 0.35-0.45 bound.
- sigma_cr_axial = 57.06 MPa, in the 50-65 MPa bound.
- gamma_bending = 0.5166, in the 0.45-0.60 bound.
- M_cr_bending = 2.578 MN*m, in the 2.2-3.0 MN*m bound.
- M_cr_ovalization = 2.716 MN*m, in the 2.4-3.1 MN*m bound.
- Governing: "bifurcation" (bending bifurcation moment below the
  ovalization collapse).
- Check geometry r = 1.0 m, t = 0.01 m (r/t = 100): gamma_axial =
  0.5813 and gamma_bending = 0.6603; the same barrel at r/t = 1600
  raises ValueError on the 1500 validity guard.
- eta_plasticity = 1.0 when E_sec = E_tan = E.

The bending knockdown is higher than the axial one at equal r/t, so
the bending critical moment sits above the axial stress level scaled
by the full section; the ovalization collapse is the cross-section
limit that bifurcation must beat to be governing.


## Pitfalls

- Using the knockdowns outside the validity band: the SP-8007
  empirical fits hold for r/t below about 1500, and every
  geometry-dependent function raises ValueError at r/t >= 1500 -
  including the exact boundary.
- Reading the bending moment as a stress: M_cr scales as
  gamma_bending * E * t^2 * r over the full wall section while the
  axial case is a stress 0.605 * gamma * E * t / r; comparing the two
  critical quantities across units invites a wrong governing
  verdict.
- Assuming bifurcation always governs: the verdict is
  "ovalization" when the Brazier collapse moment M_ov falls below
  the bending bifurcation moment; the worked barrel is
  "bifurcation", but thicker or softer shells can flip it.
- Applying the plasticity correction twice: the classical stress
  terms are elastic and eta (sqrt(E_sec E_tan)/E, unity at
  E_sec = E_tan = E) is reported for the user to apply; scaling the
  elastic margin by eta once is the intended use.
- Confusing this geometric knockdown with material knockdowns:
  gamma_axial and gamma_bending come from r/t geometry; the strength
  reduction factors of composites/cmh17-allowables are material
  factors for fiber-reinforced laminates.
- Treating the unstiffened barrel as a stiffened fuselage: this leaf
  covers the curved UNSTIFFENED shell; stiffened pressurized
  fuselage modeling belongs to
  vehicle-design/structures-integration/fuselage-skin-stringer.
## Verification

- Confirm curvature_parameter(1.5, 0.005) = 1.0825 and gamma_axial in
  the 0.35-0.45 band, sigma_cr in the 50-65 MPa band, M_cr_bending in
  the 2.2-3.0 MN*m band, M_cr_ovalization in the 2.4-3.1 MN*m band,
  and the governing verdict "bifurcation".
- Confirm gamma_axial(1.0, 0.01) = 0.5813 and gamma_bending(1.0,
  0.01) = 0.6603 (r/t = 100).
- Confirm both knockdown factors stay in (0, 1) and decrease
  monotonically as r/t grows.
- Confirm the identities sigma_cr = 0.605*gamma*E*t/r and
  M_ov = 0.987*E*r*t**2/sqrt(1-nu**2) hold exactly, and eta = 1.0 at
  E_sec = E_tan = E.
- Confirm non-positive radius, thickness or modulus, nu outside
  (-1, 1), an out-of-range explicit gamma, and r/t >= 1500 all raise
  ValueError.
- Deterministic: no RNG, identical float results run to run.
- Run the contract test offline: python3
  scripts/test_cylindrical_shell_buckling.py (34 tests).

## Related leaves

- structures/fem/buckling-analysis: straight slender members under
  Euler-style compression; this leaf covers the curved shell instead.
- structures/fem/plate-buckling: flat plate and skin panel buckling;
  it defers the curved unstiffened shell case to this leaf.
- structures/thermal-structures/thermal-buckling: restrained flat
  panels under thermal load.
- vehicle-design/structures-integration/fuselage-skin-stringer: the
  stiffened pressurized fuselage model; this leaf covers the
  unstiffened curved barrel.
- structures/composites/cmh17-allowables: material strength reduction
  factors for fiber-reinforced laminates; the knockdown here is
  geometric, that leaf's is material.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cylindrical_shell_buckling.py

The 34 tests cover the worked example within the spec magnitude
bounds, the r/t = 100 knockdown values, unit-interval and monotonicity
properties of both knockdown factors, closed-form knockdown identity,
ValueError rejection of non-positive geometry/modulus, out-of-range nu,
the r/t >= 1500 validity guard (including the exact boundary) on every
geometry-dependent function and on the assessment dict, the explicit
and default-gamma identities for the axial stress and bending moment,
the exact ovalization formula, the plasticity correction (elastic and
half-modulus cases plus scale invariance and ValueError), run-to-run
determinism, and the assessment dict key and eta contract.

## Compliance

- Standards referenced, not reproduced: NASA SP-8007 (public domain;
  named in the body with the pinned coefficients and the r/t validity
  band, paraphrased) and FAR-25 airframe loads context per
  standards-map.yaml. No proprietary handbook text is reproduced.
- compliance: STANDARDS-REF, gated: false.
