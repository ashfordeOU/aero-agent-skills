# Wave-46 leaf spec: elliptical-hertz-contact (structures, fem pack)

- Path: skills/structures/fem/elliptical-hertz-contact/
- Pack: fem (25 leaves present at prep: beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, crippling-analysis,
  curved-beam-analysis, cylindrical-shell-buckling, diagonal-tension-field-
  webs, hertzian-contact-stress, inelastic-column-buckling,
  lug-joint-analysis, metallic-fastener-joints, modal-analysis,
  plastic-collapse-analysis, plate-buckling, pressure-bulkhead,
  restrained-warping, shear-center-analysis, shrink-fit-analysis,
  statically-indeterminate, torsion-shear-flow, truss-analysis;
  elliptical-hertz-contact is a wave-46 addition of the family, the
  task-11 probe GO candidate 1). Claim fences (quoted from the sibling
  frontmatter and bodies at prep; no sibling computes an elliptical
  contact patch with unequal principal radii):
  - hertzian-contact-stress (this pack) is the point (circular patch) and
    line (strip) contact owner and the direct sibling: its Domain quick
    reference states "Crossed cylinders at right angles have the
    per-plane curvature sum A + B = (1/r1 + 1/r2)/2; the patch is
    circular only for equal radii r1 = r2 = r, where A + B = 1/r, exactly
    the sphere-on-flat closed form with Re = r (point_patch with re = r,
    never the sphere-pair 1/r1 + 1/r2 sum, which would halve the patch
    radius). Unequal crossed radii give the general elliptical patch of
    the Hertz elliptic integrals, out of scope here." (SKILL.md lines
    46-52, the leaf's own hand-off of the general case). Its
    description claims "the maximum contact pressure p0 = 3P/(2 pi a^2)
    (circular) and p0 = 2P/(pi b L) (strip)" with the circular and strip
    yield-limit relations p0_yield = 3.3 sigma_y (point) and 1.6 sigma_y
    (line), and its tags hertzian-contact-stress, hertz-contact-patch,
    contact-pressure-ellipse, subsurface-shear-stress,
    contact-yield-limit-load, equivalent-contact-modulus are NOT
    reusable here; its trigger phrases "hertzian contact stress",
    "hertz contact patch", "contact pressure ellipse", "subsurface
    shear stress", "maximum contact pressure", "contact yield limit"
    and "equivalent radius of curvature" must not appear in this leaf's
    description.
  - The wave-43 spec (wave43-specs/hertzian-contact-stress.md, lines
    131-135) repeats the fence: the sibling does NOT do "general
    elliptical patches of unequal crossed principal radii, which need the
    Hertz elliptic integrals". Zero-owner greps at prep (real runs): the
    pattern "elliptical[- ]contact|hertz elliptic|elliptic[- ]integral|
    conforming[- ]groove|raceway[- ]groove|contact[- ]ellipse" over the
    whole skills/ tree hits ONLY the hertzian leaf's two carve-out lines
    (SKILL.md lines 50-51), and the elliptical tokens
    elliptical-contact-patch, hertz-elliptic-integrals,
    ball-in-groove-contact, conforming-raceway-contact,
    crossed-unequal-cylinders, contact-ellipse-eccentricity each match 0
    existing eval/hit1-corpus.yaml tasks (the hertzian tasks
    w43-hertzian-contact-stress-1/2 carry hertz-contact-patch,
    contact-pressure-ellipse and ball-in-socket tokens for the CIRCULAR
    patch and its elliptic pressure PROFILE, no overlap with the
    elliptical patch tokens in either direction).
  - contact-analysis (this pack) is the FEA numerical contact owner whose
    penalty or Lagrange pressure is a discretized-constraint quantity,
    never the elastic p0 of a curved pair; shrink-fit-analysis owns the
    full-circumference Lame interference contact pressure; neither
    computes a Hertz patch.
- Standards id: far-25 (reference-only, present in standards-map.yaml,
  gated false, matching the sibling hertzian-contact-stress which carries
  far-25 reference-only; the FAR 25 static-strength context frames the
  airframe contact checks, summary paraphrase only, never standard
  text). Ledger Standard: far-25.
- Family: structures

## Claim

Compute the general Hertz elliptical contact patch between two smooth
elastic bodies with UNEQUAL principal curvatures pressed together by a
normal load: the per-plane curvature coefficients A and B (A less than
or equal to B) formed from the signed principal curvatures of both
bodies (convex positive, concave negative, flat infinite, principal
frames at a given angle), the eccentricity e of the contact ellipse
solved from the classical Hertz transcendental relation in the complete
elliptic integrals K(e) and E(e) by deterministic bisection, the
contact-ellipse semi-axes a and b with a not equal to b (a the major
semi-axis in the plane of the smaller curvature A, b the minor
semi-axis in the plane of the larger curvature B), the peak contact
pressure p0 = 3P/(2 pi a b) of the half-ellipsoidal pressure
distribution, the mutual approach delta, the elliptic patch area, and
the yield-limit load and margin of the peak pressure under the
circular-arm and line-arm static conventions of the sibling leaf
(p0_yield = 3.3 sigma_y point arm, 1.6 sigma_y line arm, P_y =
2 pi a b p0_yield / 3), for the ball-in-conforming-groove and
ball-in-raceway contacts and the crossed unequal cylinders that the
hertzian-contact-stress sibling hands off in its own text. The solution
reduces exactly to the circular-patch closed form when the curvatures
are equal (e = 0 gives a = b = (3P/(4E*(A+B)))^(1/3), the sibling
sphere closed form with Re = 1/(A+B)). Produces the eccentricity, the
major and minor semi-axes, the peak pressure, the approach, the patch
area, the yield-limit loads and margins and the pass-fail verdicts, in
SI units, stdlib only, deterministic. Does NOT do: the circular patch
(a = b, equal curvature in both planes) as a claimed deliverable, the
strip of line contact of finite length L, the half-width b =
(4P Re/(pi L E*))^(1/2) or p0 = 2P/(pi b L), the point-arm p0 =
3P/(2 pi a^2), the ball-in-socket circular-patch yield relation or the
subsurface shear and von Mises scans with the 0.62 p0 / 0.557 p0
factors and depths of the sibling (hertzian-contact-stress owns the
circular and line degeneracies of the same theory, and its equal-curved
sphere and parallel-cylinder geometries belong there: this leaf takes
the case where the two planes carry unequal combined curvature, A
strictly positive, and evaluates the a = b limit only as the identity
check below); the depth-resolved subsurface stress field of the
elliptical patch, whose maxima interpolate the circular and strip
anchors with the eccentricity through z-dependent incomplete elliptic
integrals, a numerical-integration-only slice that the wave doctrine
declines, so the yield slice of this leaf reports the static arm
conventions that bracket first yield instead of a scanned subsurface
field; the penalty or Lagrange contact pressure of a discretized FE
contact (contact-analysis); adhesive contact, tangential traction,
rolling or sliding fatigue endurance and wear. Scope: isotropic linear
elastic bodies characterized by E and nu entering only through E* with
1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2; smooth surfaces; patch size small
against the body radii and the radii of curvature; SI units (metres,
newtons, pascals). Deterministic, pure stdlib, no RNG, no tables.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants:
E_STEEL = 207.0e9 Pa, NU_STEEL = 0.3 and E_STAR_STEEL =
113736263736.26373 Pa (= 207.0e9 / (2 * (1 - 0.3**2)), the reference
pair used by the worked examples only; all functions take E, nu and
radii as plain float arguments). P0_YIELD_POINT_FACTOR = 3.3 and
P0_YIELD_LINE_FACTOR = 1.6 (the sibling static arm conventions),
PI = math.pi. No imports beyond math. All numbers below that the
contract test asserts are REAL outputs of the prep anchor
/tmp/w46spec/anchor_elliptical_hertz.py (stdlib math, deterministic,
exit 0, byte-identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3; canonical dump sha256
0c7eb35cd1839332faf5b413b25ac599678b748fac58ccb39c425090f48501e8).

Defining relations (pin these exactly; every function below derives from
them):
- Signed curvature of a principal radius r: k = 1/r with the convex
  radius positive, the concave radius negative (magnitude the concave
  radius) and the flat radius infinite, k = 0. The gap between the
  surfaces near the contact is h = A x^2 + B y^2 over the tangent plane
  with A and B the per-plane curvature coefficients (half the combined
  signed curvature of the two bodies in each plane). Contact requires
  A + B > 0 (a concave partner must not be smaller than the convex body
  it surrounds) and the elliptical patch requires A > 0 strictly.
- Curvature coefficients: with the four signed principal curvatures
  k1a, k1b (body 1) and k2a, k2b (body 2) and phi the angle between the
  first principal directions of the two bodies:
    A + B = (k1a + k1b + k2a + k2b) / 2
    B - A = (1/2) * sqrt((k1a - k1b)^2 + (k2a - k2b)^2
            + 2 (k1a - k1b) (k2a - k2b) cos(2 phi))
  ordered A = ((A+B) - (B-A))/2 and B = ((A+B) + (B-A))/2 so that
  A <= B. Aligned frames phi = 0 cover the ball-in-groove and raceway
  contacts; crossed cylinders at right angles use phi = pi/2 with each
  cylinder listed as (r, inf) in its own frame. Equal curvature in both
  planes gives A = B (the circular degeneracy, e = 0); one plane with
  zero combined curvature gives A = 0 (the line/strip degeneracy of the
  sibling, rejected here).
- Hertz eccentricity relation (eccentricity e = sqrt(1 - (b/a)^2) of
  the contact ellipse, a >= b):
    B/A = (E(e) - (1 - e^2) K(e)) / ((1 - e^2) (K(e) - E(e)))
  with K(e), E(e) the complete elliptic integrals of the first and
  second kind at modulus e. The right side is strictly increasing on
  e in (0, 1) from 1 (leading behaviour 1 + 0.75 e^2) to infinity
  (anchor-verified monotone on a 999-point grid, True), so the solve is
  a deterministic bisection on e. It reproduces the classical m/n table
  point: at B/A = 13.93 the solved axis ratio b/a = 0.1805
  (e = 0.9836), the handbook row m = 2.731, n = 0.493 with
  a/b = m/n = 5.54.
- Semi-axes: with E* the equivalent elastic modulus and
  A + B the curvature sum,
    a = (3P / (4 E* (A+B)))^(1/3) * (2 E(e) / (pi (1 - e^2)))^(1/3)
    b = a * sqrt(1 - e^2)
  At e = 0 the scale factor (2 E(0)/pi)^(1/3) = 1 and a = b =
  (3P/(4E*(A+B)))^(1/3), exactly the circular-patch closed form of the
  sibling at the equivalent radius Re = 1/(A+B).
- Peak pressure and area: p0 = 3P/(2 pi a b) (half-ellipsoidal
  pressure, p0 = 3P/(2 pi a b) symmetric in a and b), patch area
  pi a b.
- Mutual approach: delta = p0 b K(e)/E* = 3 P K(e)/(2 pi E* a). At
  e = 0 this is 3P/(4 E* a), the spherical approach a^2/Re.
- Yield-limit relations (the sibling arm conventions applied to this
  patch): p0_yield = 3.3 sigma_y (point arm) or 1.6 sigma_y (line arm);
  the yield-limit load inverts p0 = 3P/(2 pi a b) as
  P_y = 2 pi a b p0_yield / 3; the margin is p0_yield/p0 with the
  verdict pass when the margin is >= 1. The true first-yield and
  contained-yield pressures of the elliptical patch vary continuously
  with the eccentricity between the two arm values (they bracket it);
  interpolating them is out of scope.
- Equivalent elastic modulus: 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2, with
  E* = E/(2 (1-nu^2)) for identical materials (the steel reference pair
  207 GPa/0.3 gives E* = 113736263736.26373 Pa = 113.73626373626374
  GPa).

Functions (implement with exactly these signatures; pure math only):
- complete_elliptic_integrals(m) -> (K, E): the complete elliptic
  integrals of the first and second kind at the parameter m = e^2 in
  [0, 1), computed by the arithmetic-geometric mean iteration with the
  correction sum E = K * (1 - sum_n 2^(n-1) (a_n^2 - b_n^2)) over the
  successive AGM pairs (a_0 = 1, b_0 = sqrt(1 - m), first correction
  term 0.5 * m); K = pi / (2 * AGM). Deterministic fixed-point
  iteration to a difference floor of 1e-16. ValueError: m outside
  [0, 1).
- equivalent_modulus(e1, nu1, e2, nu2) -> float: E* in Pa from
  1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2. ValueError: e1 <= 0, e2 <= 0,
  nu1 or nu2 outside (0, 0.5).
- curvature_sums(r1_a, r1_b, r2_a, r2_b, phi=0.0) -> (A, B): the
  curvature coefficients A <= B in 1/m from the four signed principal
  radii (convex positive, concave negative, flat infinite) and the
  frame angle phi in radians. ValueError: any zero radius, phi outside
  [0, pi/2], curvature sum A + B <= 0 (the pair cannot contact as
  modeled).
- eccentricity(a_curv, b_curv) -> float: e in [0, 1) solved from the
  Hertz relation by deterministic bisection on e over [0, 1 - 1e-13]
  (200 iterations maximum, bracket floor 1e-14; the ratio is evaluated
  by the exact elliptic integrals above e = 1e-6 and by the two-term
  series (8 + e^2)/(8 - 5 e^2), exact to O(e^4), below it, where the
  integral difference K - E is unresolvable at float precision).
  Returns 0.0 when B/A <= 1 + 1e-15. ValueError: a_curv <= 0 (the
  A = 0 strip case belongs to hertzian-contact-stress), b_curv <
  a_curv.
- elliptical_patch(load, e_star, a_curv, b_curv) -> dict with keys
  "e" (float), "a" (m, major semi-axis, plane of curvature A), "b" (m,
  minor semi-axis, plane of curvature B), "ab_ratio" (a/b), "p0" (Pa),
  "delta" (m), "area" (m^2, pi a b). ValueErrors: load <= 0,
  e_star <= 0, a_curv <= 0, b_curv < a_curv, through
  eccentricity.
- yield_limit_pressure(sigma_y, line_arm=False) -> float: 3.3 sigma_y
  (point arm, default) or 1.6 sigma_y (line arm), the sibling
  conventions. ValueError: sigma_y <= 0.
- yield_limit_load(p0_yield, a_val, b_val) -> float:
  2 pi a b p0_yield / 3 in N. ValueError: p0_yield <= 0, a_val <= 0,
  b_val <= 0.
- yield_margin(p0, sigma_y, line_arm=False) -> (margin, verdict):
  p0_yield/p0 with verdict "pass" when the margin is >= 1, else "fail".

Identities to test (closed form, deterministic; all values REAL anchor
outputs of /tmp/w46spec/anchor_elliptical_hertz.py):
- Elliptic-integral consistency: complete_elliptic_integrals at the
  parameters m = e^2 in {0, 0.04, 0.25, 0.64, 0.81,
  0.999999998} returns the anchor rows K = {1.5707963267948966,
  1.5868678474541664, 1.6857503548125961, 1.9953027776647299,
  2.2805491384227703, 11.401353708654765} and E = {1.5707963267948966,
  1.5549685462425293, 1.4674622093394245, 1.2763499431699059,
  1.1716970527816157, 1.0000000109013507} within 1e-12 relative; the
  known values K(0.5) = 1.6857503548125966 and E(0.5) =
  1.4674622093394273 sit within 2e-15 relative (anchor 1.6857503548125961
  and 1.4674622093394245); the region ordering K(e) >= pi/2 >= E(e) > 0
  holds on e in [0, 1) with equality at e = 0 only, K(e) - E(e) >= 0,
  K increasing and E decreasing (anchor row checks).
- Monotonicity of the eccentricity relation: the ratio
  (E - (1-e^2) K) / ((1-e^2) (K - E)) is strictly increasing over the
  999-point grid e = 0.001..0.999 (anchor True), with limits
  r(e) - 1 = 0.0 at e = 1e-15 (the series branch) and
  log10 r(1 - 1e-9) = 7.681880 (anchor outputs).
- Circular degeneracy: at A = B the solver returns e = 0 and
  a = b = (3P/(4E*(A+B)))^(1/3) to float noise. Anchor socket case
  (10 mm ball in a 25 mm spherical socket, P = 700 N, E* = 113.7363
  GPa): A = B = 30 1/m, e = 0, a = b = 0.0004253074907842078 m with
  0.0 relative deviation from the circular closed form
  (3P/(4E*(A+B)))^(1/3), exactly the sibling point_patch value at
  Re = 1/(A+B) = 0.016666666666666666 m; the near-circular pair
  B/A = 1 + 1e-10 solves to e = 0.00012970717601133806 with the patch
  radius 4.189e-09 relative above the circular radius, the expected
  deviation scale of the 1e-14 eccentricity bisection floor at the
  equal-radius limit.
- Approach identity: at the circular degeneracy delta equals
  3P/(4 E* a) exactly (anchor relative deviation 0.0; anchor delta
  1.0853187703029526e-05 m); delta = p0 b K(e)/E* holds by
  construction at every e (anchor relation check passes to float
  noise).
- Pressure-load identity: p0 = 3P/(2 pi a b) reproduces the load
  exactly (anchor relative deviation 0.0), and the inverse load
  P = 2 pi a b p0/3 round-trips.
- Determinism: two identical full runs return identical bits; the
  canonical dump sha256 is
  0c7eb35cd1839332faf5b413b25ac599678b748fac58ccb39c425090f48501e8 on
  both in-process passes and across separate shell runs under both
  interpreters; no imports beyond math; no RNG.

## Worked example

All values below are REAL outputs of the prep anchor
/tmp/w46spec/anchor_elliptical_hertz.py (stdlib math, deterministic,
exit 0, byte-identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3). Steel on steel throughout:
E = 207 GPa, nu = 0.3, E* = 113736263736.26373 Pa = 113.73626373626374
GPa.

Case A, ball in a conforming groove raceway (corpus query 1): ball
radius R_b = 6.35e-3 m (12.7 mm ball) in a raceway groove of transverse
radius r_g = 7.9375e-3 m (concave, entered negative), raceway track
radius R_track = 20.0e-3 m along the rolling direction (convex),
aligned principal frames phi = 0, P = 4450 N, sigma_y = 2000 MPa
(bearing-grade steel).

- Curvature coefficients from curvature_sums(6.35e-3, 6.35e-3,
  20.0e-3, -7.9375e-3, 0.0): A = 15.748031496062993 1/m, B =
  103.74015748031496 1/m, B/A = 6.5875 (the conforming groove nearly
  cancels the transverse curvature: 1/R_b - 1/r_g = 31.496 1/m against
  1/R_b + 1/R_track = 207.48 1/m along the track).
- Eccentricity e = 0.95709921797354292 (K(e) = 2.6606358985778242,
  E(e) = 1.0913512644153627), a strongly elongated patch.
- Semi-axes: a = 0.0012666442469398131 m (1.26664 mm) in the groove
  transverse plane, b = 0.00036702333828792785 m (0.367023 mm) along
  the track, a/b = 3.4511272575972742, b/a = 0.28976039576593726 =
  sqrt(1 - e^2).
- Peak pressure p0 = 3P/(2 pi a b) = 4570387901.1152277 Pa (4.5704
  GPa); patch area = 1.460488725338001e-06 m^2; approach delta =
  3.9240382445150354e-05 m (39.2404 microns).
- Yield slice at sigma_y = 2000 MPa: p0_yield point arm 6.6 GPa with
  margin 1.4440787396600459 and verdict pass; p0_yield line arm 3.2 GPa
  with margin 0.70015938892608276 and verdict fail; yield-limit loads
  P_y = 6426.1503914872046 N (point arm) and 3115.7092807210688 N
  (line arm). The 4.45 kN single-ball load runs the peak pressure at
  2.29 sigma_y, between first yield and the circular static limit,
  exactly the elastic overload regime the sibling discusses for its
  high-load cases; the arm conventions bracket the elliptical
  first-yield pressure.
- Magnitude check: patch semi-axes 1.27 mm and 0.37 mm stay small
  against the ball radius 6.35 mm, p0 in the GPa class for a bearing
  contact, approach tens of microns: physically sane.

Case B, crossed unequal cylinders (corpus query 2): r1 = 25.0e-3 m and
r2 = 40.0e-3 m at right angles (phi = pi/2), each cylinder listed in
its own frame as (r, inf), P = 2000 N, sigma_y = 1200 MPa.

- Curvature coefficients from curvature_sums(25.0e-3, inf, 40.0e-3,
  inf, pi/2): A = 12.5 1/m, B = 20 1/m, B/A = 1.6 (combined curvature
  40 1/m in the 25 mm plane, 25 1/m in the 40 mm plane).
- Eccentricity e = 0.68212392640371822 (K(e) = 1.8257367044193258,
  E(e) = 1.367914901795005), a mild ellipse.
- Semi-axes: a = 0.00087105204631354651 m (0.871052 mm) in the plane
  of the 40 mm cylinder (the smaller curvature), b =
  0.00063694512714920456 m (0.636945 mm) in the plane of the 25 mm
  cylinder, a/b = 1.3675464481722965.
- Peak pressure p0 = 1721175903.0748203 Pa (1.7212 GPa); patch area =
  1.7429944229643266e-06 m^2; approach delta = 1.7598127742320018e-05 m
  (17.5981 microns).
- Yield slice at sigma_y = 1200 MPa: p0_yield point arm 3.96 GPa with
  margin 2.3007526383129111 and verdict pass; p0_yield line arm 1.92
  GPa with margin 1.115516430697169 and verdict pass; yield-limit loads
  P_y = 4601.5052766258223 N (point arm) and 2231.0328613943379 N
  (line arm).
- Read-off: the unequal curvature ratio B/A = 1.6 stretches the patch
  by only 37 percent (a/b = 1.3675), while the conforming groove ratio
  6.5875 stretches it 3.45 times, so the eccentricity solve is what
  separates the elliptical patch from the sibling circular arm, and the
  peak pressure formula p0 = 3P/(2 pi a b) needs both semi-axes.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w46spec/
anchor_elliptical_hertz.py (stdlib math, exit 0).

## Validation list (contract test must include)

1. Worked example A (ball in groove): curvature_sums(6.35e-3, 6.35e-3,
   20.0e-3, -7.9375e-3, 0.0) returns A = 15.748031496062993 and
   B = 103.74015748031496 within 1e-9 relative (B/A = 6.5875);
   elliptical_patch(4450.0, 113736263736.26373, A, B) returns
   e = 0.95709921797354292 within 1e-9 relative, a =
   0.0012666442469398131 within 1e-6 relative, b =
   0.00036702333828792785 within 1e-6 relative, a/b =
   3.4511272575972742 within 1e-6 relative, p0 = 4570387901.1152277
   within 1e-6 relative, delta = 3.9240382445150354e-05 within 1e-6
   relative, area = 1.460488725338001e-06 within 1e-6 relative; the
   identity b = a * sqrt(1 - e^2) holds to 1e-12 relative.
2. Worked example B (crossed unequal cylinders): curvature_sums(25.0e-3,
   inf, 40.0e-3, inf, pi/2) returns A = 12.5 and B = 20 within 1e-12
   relative; elliptical_patch(2000.0, 113736263736.26373, 12.5, 20.0)
   returns e = 0.68212392640371822 within 1e-9 relative, a =
   0.00087105204631354651 within 1e-6 relative, b =
   0.00063694512714920456 within 1e-6 relative, a/b =
   1.3675464481722965 within 1e-6 relative, p0 = 1721175903.0748203
   within 1e-6 relative, delta = 1.7598127742320018e-05 within 1e-6
   relative.
3. Yield slice anchors: yield_limit_pressure(2000.0e6) = 6.6e9 and
   yield_limit_pressure(2000.0e6, line_arm=True) = 3.2e9 exactly;
   yield_limit_load reproduces P_y = 6426.1503914872046 N (point arm,
   Case A), 3115.7092807210688 N (line arm, Case A), 4601.5052766258223
   N (point arm, Case B) and 2231.0328613943379 N (line arm, Case B)
   within 1e-6 relative; yield_margin returns (1.4440787396600459,
   "pass") for Case A point arm, (0.70015938892608276, "fail") for Case
   A line arm, (2.3007526383129111, "pass") and (1.115516430697169,
   "pass") for Case B, each within 1e-6 relative on the margin.
4. Elliptic-integral anchors: complete_elliptic_integrals(m) matches
   the six anchor rows of the Identities section within 1e-12 relative;
   K(0.5) and E(0.5) sit within 2e-15 relative of the published
   1.6857503548125966 and 1.4674622093394273; the ordering K >= pi/2 >=
   E > 0 and K - E >= 0 holds at every grid point e = 0.001..0.999;
   K and E are monotone (K increasing, E decreasing) across the grid.
5. Circular degeneracy: at A = B = 30 (10 mm ball in a 25 mm spherical
   socket, P = 700 N) eccentricity returns 0.0 and elliptical_patch
   returns a = b = 0.0004253074907842078 within 1e-9 relative of the
   closed form (3P/(4E*(A+B)))^(1/3), the sibling circular-patch value
   at Re = 1/(A+B); delta equals 3P/(4 E* a) = 1.0853187703029526e-05
   within 1e-9 relative; p0 = 3P/(2 pi a^2) with a = b within 1e-9
   relative.
6. Near-circular identity: at B/A = 1 + 1e-10 the solved eccentricity is
   0.00012970717601133806 within 1e-6 relative and the patch radius
   sits 4.189e-09 relative above the circular radius, the expected
   deviation of the 1e-14 eccentricity bisection floor at the
   equal-radius limit (assert the relative deviation between
   1e-10 and 1e-7); at exact equality B/A = 1 the e = 0 branch makes
   the deviation 0.0 to float noise.
7. Monotonicity and range of the Hertz relation: the solved e is
   strictly increasing in B/A over a sweep of ratios from 1.01 to 100
   (anchor monotone True), and eccentricity solves the relation back:
   B/A recomputed from the returned e matches the input B/A within
   1e-6 relative across the sweep.
8. Geometry limits: curvature_sums returns A = B for the equal-radius
   cases: ball in a spherical socket, and crossed equal cylinders at
   phi = pi/2, whose per-plane combined curvature 1/r in both planes
   gives A = B = 1/(2r) with A + B = 1/r, matching the sibling
   equal-radius crossed-cylinder closed form with Re = r, so the patch
   is the circular arm of the sibling; crossed unequal cylinders
   satisfy A + B = (1/r1 + 1/r2)/2 exactly (anchor Case B: 32.5 1/m); a
   concave partner smaller than the convex body gives a non-positive
   curvature sum and raises ValueError.
9. Yield-load inverse identity: P_y = 2 pi a b p0_yield/3 inverts
   p0 = 3P/(2 pi a b): p0 recomputed from P_y and the patch equals
   p0_yield within 1e-9 relative at both arm conventions; the margin
   equals p0_yield/p0 exactly.
10. ValueErrors across the module: complete_elliptic_integrals(-0.1)
    and (1.0) raise; equivalent_modulus(0.0, 0.3, 207.0e9, 0.3),
    (207.0e9, 0.0, 207.0e9, 0.3), (207.0e9, 0.5, 207.0e9, 0.3),
    (207.0e9, 0.3, -1.0e9, 0.3) raise; curvature_sums(0.0, 1.0, 1.0,
    1.0), curvature_sums with phi = pi (outside [0, pi/2]) and
    curvature_sums(6.35e-3, 6.35e-3, -5.0e-3, 20.0e-3) (concave partner
    smaller than the convex body, A + B <= 0) raise; eccentricity(0.0,
    10.0) and (10.0, 5.0) raise (A <= 0 is the strip/line case of
    hertzian-contact-stress); elliptical_patch(0.0, e_star, A, B),
    (P, 0.0, A, B), (P, e_star, 0.0, B) and (P, e_star, B, A) raise;
    yield_limit_pressure(0.0) raises; yield_limit_load(0.0, a, b),
    (p0_y, 0.0, b) and (p0_y, a, 0.0) raise (15 anchor cases, each
    raises ValueError).
11. Determinism: two identical full runs return identical bits (anchor
    canonical dump sha256
    0c7eb35cd1839332faf5b413b25ac599678b748fac58ccb39c425090f48501e8 on
    both in-process passes and across two separate shell runs); no
    imports beyond math; no RNG. Test passes under BOTH interpreters
    (/usr/bin/python3 3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3).
    No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere. Contract test file named
    test_elliptical_hertz_contact.py (underscores), unittest, offline
    in under 20 seconds.

## Corpus fragment (2 verbatim queries for
eval/hit1-wave46-elliptical-hertz-contact.yaml)

Query 1 (copy verbatim):
  "compute the elliptical-contact-patch semi-axes of the 12.7 mm ball
  in the 15.875 mm groove-radius raceway under 4.45 kN radial load:
  solve the hertz-elliptic-integrals eccentricity from the unequal
  principal curvature sum and difference, then the contact-ellipse
  major and minor semi-axes, the maximum contact pressure and the
  yield-limit margin"
  intent: "structures; general Hertz elliptical contact patch of the
  12.7 mm ball in the 15.875 mm groove-radius conforming raceway under
  4.45 kN radial load: hertz-elliptic-integrals eccentricity from the
  unequal principal curvature sum and difference, contact-ellipse major
  and minor semi-axes, maximum contact pressure and yield-limit margin"
  expected_skill: "structures/fem/elliptical-hertz-contact"
Query 2 (copy verbatim):
  "find the elliptical-contact-patch of crossed unequal cylinders with
  25 mm and 40 mm radii at right angles under 2 kN: the elliptic-
  integral eccentricity, the contact-ellipse semi-axes, the peak
  pressure p0 = 3P/(2 pi a b) of the general hertz solution and the
  subsurface von Mises check against the yield strength"
  intent: "structures; general Hertz elliptical contact patch of crossed
  unequal cylinders with 25 mm and 40 mm radii at right angles under
  2 kN: elliptic-integral eccentricity, contact-ellipse semi-axes, the
  peak pressure p0 = 3P/(2 pi a b) of the general hertz solution and the
  yield check of the peak pressure against the yield strength under the
  circular-arm and line-arm static conventions"
  expected_skill: "structures/fem/elliptical-hertz-contact"

Task ids: w46-elliptical-hertz-contact-1 and -2. Prep grep and probe:
the distinctive tokens elliptical-contact-patch, hertz-elliptic-
integrals, ball-in-groove-contact, conforming-raceway-contact,
crossed-unequal-cylinders and contact-ellipse-eccentricity each match 0
existing eval/hit1-corpus.yaml tasks (real greps, count 0 each), and
the only skills/ tree hits for the elliptical tokens are the
hertzian-contact-stress carve-out lines 50-51 quoted above, so the two
new tasks steal nothing and nothing routes here by accident; the
existing hertzian tasks w43-hertzian-contact-stress-1/2 carry
hertz-contact-patch, contact-pressure-ellipse and ball-in-socket tokens
for the CIRCULAR patch and its elliptic pressure PROFILE with no
elliptical-patch overlap, so the queries above are collision-free in
both directions.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the general Hertz
elliptical contact patch between two elastic bodies with unequal
principal radii pressed together:" and include the outputs in the
Claim. First tag: elliptical-hertz-contact. Additional tags ONLY the
receipt's gate (f) list, verbatim: elliptical-hertz-contact,
elliptical-contact-patch, hertz-elliptic-integrals,
ball-in-groove-contact, conforming-raceway-contact,
crossed-unequal-cylinders, contact-ellipse-eccentricity. NEVER the bare
single words hertz, contact, ellipse, elliptic, eccentricity, pressure,
patch, ball, groove, raceway, cylinder, load, stress or yield alone,
and NEVER the sibling tokens hertzian-contact-stress,
hertz-contact-patch, contact-pressure-ellipse, subsurface-shear-stress,
contact-yield-limit-load, equivalent-contact-modulus
(hertzian-contact-stress, which owns the circular-patch and line-
contact degeneracies, so its triggers "hertzian contact stress", "hertz
contact patch", "contact pressure ellipse", "subsurface shear stress",
"maximum contact pressure", "contact yield limit", "equivalent elastic
modulus" and "equivalent radius of curvature" must not appear), and
contact-analysis, penalty-method, contact-stiffness, penetration,
master-slave (contact-analysis, the FE contact leaf). The description
must not claim the circular-patch or strip deliverables (p0 =
3P/(2 pi a^2), p0 = 2P/(pi b L), the 0.62 p0/0.557 p0 subsurface
factors or the 3.3/1.6 yield relations as owned output): the equal-
curvature and zero-curvature degeneracies of this leaf are the sibling
arms, and this leaf claims only the unequal-principal-curvature
elliptical patch with its a not equal to b semi-axes, evaluating the
a = b limit solely as an identity check. 50-150 words, <=1000 chars,
no em dash, no content-policy sweep term, action verb present.
Recommended wording (outputs in Claim order): "Use when you must
compute the general Hertz elliptical contact patch between two elastic
bodies with unequal principal radii pressed together: form the
per-plane curvature sums A and B from the signed principal curvatures
(convex positive, concave negative, flat infinite), solve the
hertz-elliptic-integrals eccentricity e of the contact ellipse from the
complete elliptic integrals, then the contact-ellipse major and minor
semi-axes a and b of the unequal-curvature patch, the peak pressure
p0 = 3P/(2 pi a b), the mutual approach and the patch area of a ball
in a conforming groove or raceway and of crossed unequal cylinders.
Produces the eccentricity, the semi-axes, the peak contact pressure,
the approach, the patch area and the yield-limit load and margin
against the peak pressure under the circular-arm and line-arm static
conventions. Trigger: elliptical contact patch, hertz elliptic
integrals, contact ellipse eccentricity, ball in groove, conforming
raceway contact, crossed unequal cylinders." The sibling triggers
"hertzian contact stress", "hertz contact patch", "contact pressure
ellipse", "subsurface shear stress", "maximum contact pressure" and
"contact yield limit" must not appear. ZERO em dashes in every file;
no content-policy sweep terms. Standards reference-only: far-25 named
as the certification static-strength context (the FAR 25 structural
rules frame the context; the Hertz elliptic-integral relations are
standard engineering methodology, summary-only), never reproduced
verbatim. Build-time fence note: add one routing bullet to the
hertzian-contact-stress leaf and the structures family router pointing
unequal-crossed-radii and ball-in-groove questions at this leaf,
matching the wave-45 routing-line precedent.
