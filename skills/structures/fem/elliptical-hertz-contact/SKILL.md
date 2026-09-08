---
name: elliptical-hertz-contact
description: "Use when you must compute the general Hertz elliptical contact patch between two elastic bodies with unequal principal radii pressed together: form the per-plane curvature sums A and B from the signed principal curvatures (convex positive, concave negative, flat infinite), solve the hertz-elliptic-integrals eccentricity from the unequal curvature ratio, then the contact-ellipse major and minor semi-axes a and b, the peak pressure p0 = 3P/(2 pi a b), the approach, the patch area and the yield-limit margin for the elliptical patch. Produces the elliptical contact solution with semi-axes, peak pressure, approach and yield verdicts. Trigger: elliptical contact, unequal principal radii, ball in groove, conforming raceway, crossed unequal cylinders, contact ellipse eccentricity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [elliptical-hertz-contact, elliptical-contact-patch, hertz-elliptic-integrals, ball-in-groove-contact, conforming-raceway-contact, crossed-unequal-cylinders, contact-ellipse-eccentricity]
  version: 0.1.0
  author: Aero Agent Skills
---

# Elliptical Hertz Contact (structures/fem/elliptical-hertz-contact)

Use when the task is computing the general Hertz elliptical contact patch
between two elastic bodies pressed together with UNEQUAL principal radii
(ball in a conforming groove or raceway, crossed unequal cylinders): the
per-plane curvature sums from the signed principal curvatures, the
eccentricity of the contact ellipse from the complete elliptic integrals,
the major and minor semi-axes a and b, the peak pressure
p0 = 3P/(2 pi a b), the approach and the yield-limit margin. This is the
general elliptical-patch solution of the classical Hertz theory (Johnson,
Contact Mechanics, ch. 4 style, paraphrased, never reproduced). Pairing
leaves: hertzian-contact-stress owns the circular-patch (equal radii) and
line-contact (strip) degeneracies only and explicitly fences "Unequal
crossed radii give the general elliptical patch of the Hertz elliptic
integrals, out of scope here"; this leaf claims only the unequal-principal-
curvature elliptical patch and evaluates the a = b limit as an identity
check.

## Domain quick reference

- Equivalent elastic modulus:
  1/E* = (1 - nu1^2)/E1 + (1 - nu2^2)/E2. Steel on steel (E = 207 GPa,
  nu = 0.3): E* = 113.73626373626374 GPa.
- Per-plane curvature sums from the signed principal curvatures of both
  bodies in their own frames (convex positive, concave negative, flat
  infinite), combined at the contact-angle phi between the principal
  planes: A and B, with B/A >= 1 ordering. A + B is the combined
  curvature, B - A its difference.
- Eccentricity e of the contact ellipse solves the classical relation
  between the curvature ratio B/A and the complete elliptic integrals
  K(e), E(e) (bounded deterministic bisection on the standard relation).
- Semi-axes from the elliptic-integral functions of e; the patch is
  elongated (a > b) when the curvatures differ strongly (a/b = 1/sqrt(1 -
  e^2) in the aligned-frame convention).
- Peak pressure p0 = 3P/(2 pi a b); approach delta and patch area follow
  the classical elastic forms.
- First-yield pressure bands (point arm p0_yield = 1.6 * sigma_y for the
  circular limit, line arm 3.2 GPa convention at 2000 MPa reference)
  bracket the elliptical first-yield pressure; yield margin =
  p0_yield/p0 - 1 with the pass/fail verdict. The bands are reported
  reference-only, never enforced.

## Workflow

1. Fix the material pair and geometry: E1, nu1, E2, nu2 and the signed
   principal radii (r1_a, r1_b) and (r2_a, r2_b) of the two bodies in
   their own frames, with the contact angle phi between the principal
   planes. Convex surfaces enter positive, concave negative, flat
   infinite. Non-physical inputs are rejected with ValueError.
2. Compute the equivalent modulus with equivalent_modulus(e1, nu1, e2,
   nu2): E* from the two material pairs.
3. Form the per-plane curvature sums with curvature_sums(r1_a, r1_b,
   r2_a, r2_b, phi): A and B ordered so B/A >= 1.
4. Solve the contact-ellipse eccentricity with eccentricity(a_curv,
   b_curv): the classical elliptic-integral relation solved by bounded
   deterministic bisection over e in (0, 1), returning e with K(e) and
   E(e). Equal curvatures (A = B) return the circular limit e = 0.
5. Compute the patch with elliptical_patch(load, e_star, a_curv, b_curv):
   semi-axes a and b, peak pressure p0 = 3P/(2 pi a b), approach delta
   and patch area.
6. Assess yield with yield_limit_pressure(sigma_y, line_arm=False) for
   the first-yield pressure band, yield_limit_load(p0_yield, a, b) for
   the yield-limit load, and yield_margin(p0, sigma_y, line_arm=False)
   for the margin and pass/fail verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_elliptical_hertz_contact.py.

## Worked example

All values are REAL outputs of the logic module at the spec anchor cases
(steel on steel, E = 207 GPa, nu = 0.3, E* = 113736263736.26373 Pa).

Case A, ball in a conforming groove raceway (12.7 mm ball R_b = 6.35e-3 m
in a groove of transverse radius r_g = 7.9375e-3 m, concave, entered
negative; track radius R_track = 20.0e-3 m convex; P = 4450 N,
sigma_y = 2000 MPa):

- curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0):
  A = 15.748031496062993 1/m, B = 103.74015748031496 1/m,
  B/A = 6.5875.
- Eccentricity e = 0.95709921797354292 (K = 2.6606358985778242,
  E = 1.0913512644153627): a strongly elongated patch.
- Semi-axes a = 0.0012666442469398131 m (1.26664 mm), b =
  0.00036702333828792785 m (0.367023 mm), a/b = 3.4511272575972742.
- Peak pressure p0 = 4570387901.1152277 Pa (4.5704 GPa); patch area =
  1.460488725338001e-06 m^2; approach delta = 3.9240382445150354e-05 m
  (39.2404 microns).
- Yield slice: point arm margin 1.4440787396600459 (pass), line arm
  margin 0.70015938892608276 (fail); yield-limit loads 6426.15 N (point
  arm) and 3115.71 N (line arm).

Case B, crossed unequal cylinders (r1 = 25.0e-3 m and r2 = 40.0e-3 m at
right angles, phi = pi/2, P = 2000 N, sigma_y = 1200 MPa):

- curvature_sums(25.0e-3, inf, 40.0e-3, inf, pi/2): A = 12.5 1/m,
  B = 20 1/m, B/A = 1.6.
- Eccentricity e = 0.68212392640371822 (K = 1.8257367044193258,
  E = 1.367914901795005): a mild ellipse.
- Semi-axes a = 0.00087105204631354651 m (0.871052 mm), b =
  0.00063694512714920456 m (0.636945 mm), a/b = 1.3675464481722965.
- Peak pressure p0 = 1721175903.0748203 Pa (1.7212 GPa); patch area =
  1.7429944229643266e-06 m^2; approach delta = 1.7598127742320018e-05 m
  (17.5981 microns).
- Yield slice: point arm margin 2.3007526383129111 (pass), line arm
  margin 1.115516430697169 (pass).

## Verification

- Deterministic stdlib math only (complete elliptic integrals by the
  arithmetic-geometric mean, bounded bisection for the eccentricity); no
  RNG, no network.
- ValueErrors: non-positive load, radii or modulus; zero curvature sum;
  eccentricity out of (0, 1); non-physical material inputs.
- Identities: equal-curvature limit reproduces the circular-patch radius
  of the sibling closed form within the approximation tolerance;
  K(e) >= E(e) region checks; b/a = sqrt(1 - e^2) in the aligned-frame
  convention; complete-elliptic-integral values match the published
  K = 1.6857503548125966 and E = 1.4674622093394273 at modulus 0.5
  (parameter m = 0.25) to 1e-15.

## Related leaves

- structures/fem/hertzian-contact-stress (circular-patch and line-contact
  degeneracies; the a = b and line limits of this leaf)
- structures/fem/contact-analysis (FE penalty-method contact, contact
  stiffness, penetration)
- structures/loads/lug-joint-analysis and the bearing-stress leaves
  (nominal bearing stress P/(Dt) and lug margins)

## Pitfalls

- Do not claim the circular-patch or strip deliverables (p0 = 3P/(2 pi
  a^2), p0 = 2P/(pi b L), the 0.62 p0/0.557 p0 subsurface factors or the
  3.3/1.6 yield relations as owned output): those are the sibling arms of
  hertzian-contact-stress, and this leaf claims only the unequal-
  principal-curvature elliptical patch.
- Concave surfaces enter with negative radius; flat surfaces are infinite.
  Getting the sign of the groove radius wrong inverts the curvature
  difference and changes the eccentricity solve.
- The conforming-groove case nearly cancels the transverse curvature
  (B/A = 6.59 for the 12.7 mm ball in the 15.875 mm groove): the patch is
  strongly elongated and the a != b distinction is the whole point of the
  leaf.
- Do not use the single-word generic tags hertz, contact, ellipse,
  pressure, patch, ball, groove, raceway, cylinder, load, stress or yield
  alone, and never the sibling tokens hertzian-contact-stress or
  contact-analysis: they steal corpus tasks from the sibling owners.
- The yield bands are reference-only reporting conventions that bracket
  the elliptical first-yield pressure; they are never enforced as
  material limits.

## Behavior contract (gate 3)

The contract test scripts/test_elliptical_hertz_contact.py (30 methods,
stdlib unittest, offline, deterministic) verifies: the complete elliptic
integrals against the published K(0.5) and E(0.5) values to 1e-15; the
equivalent modulus for steel pairs; the curvature sums and B/A ordering
for both worked-example geometries; the eccentricity solve including the
equal-curvature circular limit; both worked-example patches (semi-axes,
peak pressure, approach, area) within 1e-9 relative; the yield margins
and verdicts; the ValueError rejections; and determinism of repeated
calls. The test passes under both /usr/bin/python3 and the pyenv 3.13
interpreter; no exact-float equality is asserted on computed sums.

## Compliance

STANDARDS-REF, gated false. FAR-25 and CS-25 (reference-only) frame
airframe structural substantiation; the Hertz solution itself is
paraphrased public contact-mechanics theory (Johnson, Contact Mechanics,
ch. 4 style) and is never reproduced verbatim.
