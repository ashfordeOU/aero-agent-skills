---
name: hertzian-contact-stress
description: "Use when you must compute the Hertzian contact stress between curved elastic bodies pressed together: determine the contact patch radius or half-width for sphere pairs, sphere-on-flat, ball-in-socket, cylinder pairs, cylinder-in-bore, roller-in-race or crossed cylinders from the load, the equivalent radius of curvature and the equivalent elastic modulus with 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2; compute the maximum contact pressure p0 = 3P/(2 pi a^2) (circular) and p0 = 2P/(pi b L) (strip); report the subsurface shear and von Mises maxima with depth and magnitude; and run the yield-limit load check with p0_yield = 3.3 sigma_y (point) and 1.6 sigma_y (line). Produces patch size, peak pressure, subsurface stress location and magnitude, and yield-limit load and margin in SI units. Trigger: hertzian contact stress, hertz contact patch, contact pressure ellipse, subsurface shear stress, equivalent elastic modulus, equivalent radius of curvature, maximum contact pressure, contact yield limit."
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
  tags: [hertzian-contact-stress, hertz-contact-patch, contact-pressure-ellipse, subsurface-shear-stress, contact-yield-limit-load, equivalent-contact-modulus]
  version: 0.1.0
  author: AeroSkills
---

# Hertzian Contact Stress (structures/fem/hertzian-contact-stress)

Use when you must compute the analytic Hertzian contact stress between
curved elastic bodies pressed together: the contact patch and the peak
contact pressure that a finite element contact run is validated against.
This leaf implements the standard Hertz closed form in pure Python,
stdlib only, deterministic and offline. It sits beside
structures/fem/contact-analysis (the FEA numerical contact leaf, whose
penalty pressure is a Lagrange multiplier of the discretized constraint
and has no closed form) and complements structures/fem/calculix-linear
and calculix-nonlinear, which host the FE runs this analytic solution
benchmarks.

## Domain quick reference

- Equivalent elastic modulus: 1/E* = (1-nu1**2)/E1 + (1-nu2**2)/E2, with
  E* = E/(2*(1-nu**2)) for identical materials (the steel reference pair
  210 GPa/0.3 gives E* = 115.385 GPa). Material properties enter only
  through E* and the yield strength sigma_y.
- Equivalent radius of curvature: 1/Re = 1/r1 + 1/r2, where r1 is the
  convex (positive) radius of the first body, r2 is positive for a convex
  partner, negative for a concave internal partner (socket, bore, race,
  magnitude = concave radius) and +inf for a flat. The curvature sum must
  stay positive, so a concave partner must be larger than the convex body
  it surrounds.
- Crossed cylinders at right angles have the per-plane curvature sum
  A + B = (1/r1 + 1/r2)/2; the patch is circular only for equal radii
  r1 = r2 = r, where A + B = 1/r, exactly the sphere-on-flat closed form
  with Re = r (point_patch with re = r, never the sphere-pair 1/r1 +
  1/r2 sum, which would halve the patch radius). Unequal crossed radii
  give the general elliptical patch of the Hertz elliptic integrals,
  out of scope here.
- Point contact (sphere pair, sphere on flat, ball in socket, crossed
  equal cylinders): a = (3*P*Re/(4*E*))**(1/3) and p0 = 3*P/(2*pi*a**2),
  equivalently p0 = (6*P*E*^2/(pi^3*Re^2))**(1/3).
- Line contact (cylinder on flat, parallel cylinder pair, cylinder in
  bore, roller in race, axial length L): b = (4*P*Re/(pi*L*E*))**(1/2)
  and p0 = 2*P/(pi*b*L), equivalently p0 = (P*E*/(pi*Re*L))**(1/2).
- Inverse load forms: P = 2*pi*a**2*p0/3 (point) and P = pi*b*L*p0/2
  (line); these invert the load-pressure closed form for P_yield.
- Subsurface state of the half-space under the patch, nu = 0.3 in both
  solids (module constants, anchor-verified against the exact elastic
  field scans): point contact max shear 0.31*p0 at depth z = 0.48*a and
  max von Mises 0.62*p0 at the same depth; on the axis of symmetry the
  von Mises stress equals exactly twice the max shear. Line contact max
  shear 0.30*p0 at z = 0.78*b and max von Mises 0.557*p0 at z = 0.70*b,
  the plane-strain intermediate principal stress separating the two
  depths. At the surface center the contact is nearly hydrostatic, so
  yielding always initiates subsurface.
- Yield-limit relations: p0_yield = 3.3*sigma_y for point contact and
  p0_yield = 1.6*sigma_y for line contact. For line contact the
  subsurface Tresca condition tau_max = 0.30*p0 = sigma_y/2 gives
  p0 = sigma_y/0.60 = 1.67 sigma_y (the 1.6 of the standard relation), so
  first subsurface yield and the yield-limit pressure coincide; for point
  contact first subsurface yield initiates when the max von Mises 0.62*p0
  reaches sigma_y at p0 = 1.6*sigma_y, while the standard spherical
  static check allows 3.3*sigma_y, where the grown subsurface plastic
  zone and bounded permanent deformation set the load limit. The
  yield-limit load inverts the p0(load) closed form: point
  P_y = pi^3*Re^2*p0_y^3/(6*E*^2), line P_y = pi*Re*L*p0_y^2/E*.
- SI units throughout (m, N, Pa).

## Workflow

1. Gather the contact inputs: applied load P, geometry radii with the
   sign convention above (convex r1, partner r2, axial length L for line
   contact), material properties (E, nu of each body) and the yield
   strength sigma_y; fix the contact class as point (circular patch) or
   line (strip) from the geometry.
2. Compute the equivalent elastic modulus with equivalent_modulus(e1,
   nu1, e2, nu2), or use the same-material degeneracy E/(2*(1-nu**2)).
3. Compute the equivalent radius of curvature with equivalent_radius(r1,
   r2); the flat (+inf) and concave (negative) limits are handled here.
4. Solve the contact patch: point_patch(load, e_star, re) returns the
   circular patch radius a and the maximum contact pressure p0;
   line_patch(load, e_star, re, length) returns the strip half-width b
   and p0. Cross-check p0 against the equivalent load forms.
5. Read the subsurface stress state: point_subsurface(p0, a) or
   line_subsurface(p0, b) returns the max shear and max von Mises
   stresses with their depths under the patch.
6. Run the yield-limit load check: yield_limit_pressure(sigma_y, ...)
   gives p0_yield = 3.3 sigma_y (point) or 1.6 sigma_y (line),
   yield_limit_load(sigma_y, e_star, re, ...) inverts the closed form for
   P_yield (length required for line contact), and
   check_yield_margin(p0, sigma_y, ...) returns the margin p0_yield/p0
   with the below_yield_limit verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_hertzian_contact_stress.py.

## Worked example

Steel on steel throughout: E = 210 GPa, nu = 0.3, E* = 1.1538461538e11 Pa
= 115.385 GPa. Values are the real outputs of the module logic.

- Identity block: Re = 50 mm for the 50 mm roller on a flat; Re = 16.667
  mm for the 10 mm ball in the 25 mm concave socket (1/0.010 - 1/0.025);
  Re = 60 mm for the 15 mm roller in the 20 mm bore; Re = 180 mm for the
  450 mm wheel on the 300 mm convex rail crown; crossed 10 mm cylinders
  give a = 0.319125 mm and p0 = 2344.17 MPa, identical to the 10 mm
  sphere on a flat to 1e-12 relative.
- Case A, steel roller on steel flat (line): r1 = 50 mm, L = 100 mm,
  P = 50 kN, sigma_y = 900 MPa. Re = 50 mm; b = 0.525232 mm; p0 =
  606.037 MPa; max shear 181.81 MPa at z = 0.4097 mm (0.78 b); max von
  Mises 337.56 MPa at z = 0.3677 mm (0.70 b). p0_yield = 1.6 * 900 =
  1440.0 MPa; margin = 2.3761; P_yield = 282.291 kN, so the roller
  carries 5.6 times the applied load before the line yield limit.
- Case B, ball in socket (point, conformal): r1 = 10 mm ball, concave
  r2 = -25 mm socket, P = 700 N, sigma_y = 1200 MPa. Re = 16.667 mm;
  a = 0.423272 mm; p0 = 1865.52 MPa; max shear 578.31 MPa and max von
  Mises 1156.62 MPa at z = 0.2032 mm (0.48 a). p0_yield = 3.3 * 1200 =
  3960.0 MPa; margin = 2.1227; P_yield = 6.696 kN. The applied load keeps
  p0 at 1.55 sigma_y, below the 1.6 sigma_y of first subsurface yield, so
  the contact is fully elastic.
- Case C, wheel-rail-like cylinder pair (line): r1 = 450 mm wheel on
  r2 = 300 mm convex rail crown, P = 80 kN over L = 15 mm, sigma_y =
  700 MPa. Re = 180 mm; b = 3.2547 mm; p0 = 1043.19 MPa; max shear 312.96
  MPa at z = 2.539 mm; max von Mises 581.06 MPa at z = 2.278 mm.
  p0_yield = 1120.0 MPa; margin = 1.0736; P_yield = 92.215 kN: the
  realistic ~1 GPa rail contact runs just under the 1.6 sigma_y line
  limit.
- Case D, crossed equal cylinders (point): r1 = r2 = 10 mm at right
  angles, P = 500 N, sigma_y = 1200 MPa. a = 0.31913 mm; p0 = 2344.17
  MPa; max shear 726.69 MPa and max von Mises 1453.39 MPa at z = 0.15318
  mm. p0_yield = 3960.0 MPa; margin = 1.6893; P_yield = 2.410 kN. Here
  p0/sigma_y = 1.95 sits between the 1.6 sigma_y of first subsurface
  yield (the von Mises 1453.39 MPa already exceeds 1200 MPa) and the
  3.3 sigma_y spherical yield-limit pressure: the elastic-plastic growth
  regime of the standard static check.
- Case E, roller in race (line, concave): r1 = 15 mm roller in the 20 mm
  concave race, P = 10 kN over L = 20 mm, sigma_y = 1200 MPa. Re = 60 mm;
  b = 0.57536 mm; p0 = 553.23 MPa; max shear 165.97 MPa at z = 0.44878
  mm. p0_yield = 1920.0 MPa; margin = 3.4705; P_yield = 120.444 kN: the
  conformal bore spreads the load, the fattest margin of the set.
- Read-off: curved steel pairs at GPa-level p0 are normal; the check that
  matters is the margin of p0 against the geometry-dependent yield-limit
  pressure, 1.6 sigma_y for strips and 3.3 sigma_y for circular patches,
  and the corresponding P_yield.

## Verification

- Confirm equivalent_modulus(210e9, 0.3, 210e9, 0.3) returns
  1.1538461538e11 Pa and equals 210e9/(2*(1-0.3**2)) to float noise.
- Confirm equivalent_radius handles the flat, concave and convex limits:
  (0.050, inf) -> 0.05; (0.010, -0.025) -> 0.0166667; (0.015, -0.020) ->
  0.06; (0.450, 0.300) -> 0.18.
- Confirm crossed equal cylinders give exactly the sphere-on-flat patch
  and that the p0 consistency identities (the equivalent load forms and
  the inverse load round-trips) hold to float noise.
- Confirm the worked-example outputs above fall inside the spec magnitude
  bounds and reproduce on repeat runs (deterministic).
- Confirm every non-physical input raises ValueError: zero or negative
  moduli; Poisson ratios at 0.5 and 0.6; r1 at 0; r2 at 0 and -inf; a
  concave partner not larger than the convex body (1/Re not positive);
  zero load; zero patch size; missing line length; negative p0; zero
  sigma_y.
- Run the contract test offline: python3
  scripts/test_hertzian_contact_stress.py (35 tests, deterministic,
  passes under python3 and the pyenv 3.13 hook interpreter).

## Related leaves

- structures/fem/contact-analysis: the FEA numerical contact leaf; the
  penalty pressure is a discretized-constraint Lagrange multiplier, and
  this analytic Hertz solution is the benchmark the FE run is validated
  against.
- structures/fem/shrink-fit-analysis: the interference-fit contact
  pressure of a concentric Lame thick-cylinder pair with radial
  interference, the full-circumference counterpart of the local Hertz
  patch.
- structures/fem/lug-joint-analysis: the nominal pin bearing stress
  P/(D t) of a pin-loaded lug, the uniform projected-area check with no
  patch curvature.
- structures/materials/multiaxial-yield-criteria: follow-on von Mises or
  Tresca margin work on an arbitrary stress state once the Hertz pressure
  field is known (this leaf reports the standard Hertz subsurface
  characteristics and yield-limit relations only).

## Pitfalls

- Treating the concave radius as positive: a socket, bore or race enters
  with a negative radius, so the curvature sum is 1/r1 - 1/|r2|; a
  concave partner smaller than the convex body makes 1/Re negative and
  the pair cannot contact as modeled (ValueError).
- Feeding crossed cylinders into the sphere-pair sum: crossed equal
  cylinders use the per-plane curvature sum A + B = 1/r, i.e. the
  sphere-on-flat closed form with Re = r1; the 1/r1 + 1/r2 sphere-pair
  sum halves the patch radius.
- Reading the FE contact pressure as a Hertz quantity: the contact
  analysis penalty or Lagrange pressure is a property of the discretized
  constraint (stiffness and penetration), not the elastic p0 of the
  curved pair; use this leaf for the analytic benchmark.
- Expecting a single subsurface depth: for strips the plane-strain
  intermediate principal stress separates the max shear depth 0.78 b from
  the max von Mises depth 0.70 b; only the axisymmetric point field puts
  both at 0.48 a.
- Judging yield from p0 against sigma_y alone: first subsurface yield
  starts at p0 = 1.6 sigma_y (point, von Mises) while the spherical
  static-check limit is 3.3 sigma_y; quote the yield-limit pressure
  p0_yield and the margin, not a bare p0/sigma_y comparison.
- Using the 1.6/3.3 factors outside their regime: they are the standard
  static yield-limit relations for the elastic contact of steel-like
  solids (nu = 0.3), not fatigue, wear, tangential traction or
  rolling-contact limits.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hertzian_contact_stress.py

All 35 tests pass and exit 0 under both the foreground python3 and the
pre-push hook interpreter (~/.pyenv/versions/3.13.12/bin/python3).

## Contract test

The contract test covers, per the wave-43 spec validation list: the
steel-pair equivalent modulus anchor and its identities; the flat,
concave and convex equivalent radius limits; the crossed-cylinder
equivalence to the sphere-on-flat patch; worked example Cases A through E
(patch size, peak pressure, subsurface shear and von Mises depths and
magnitudes, yield-limit pressure, margin and P_yield for roller-on-flat,
ball-in-socket, wheel-rail, crossed cylinders and roller-in-race); the
p0 consistency identities and inverse load round-trips; the
yield_limit_load equals load times margin-power identity; exact-field
scans (Huber axisymmetric point field and plane-strain strip centerline)
reproducing the subsurface constants z/a = 0.4810 with tau/p0 = 0.3100
and vm/p0 = 0.6200, z/b = 0.7862 with tau/p0 = 0.3003 and z/b = 0.7042
with vm/p0 = 0.5575; the margin verdict flip; the full ValueError
rejection surface of non-physical inputs; determinism and the stdlib-only
import scope.

## Compliance

- Standards referenced, not reproduced: FAR 25 (airworthiness, frame for
  the static-strength context of structural checks); the Hertz relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
