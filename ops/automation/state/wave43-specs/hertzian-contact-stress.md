# Wave-43 leaf spec: hertzian-contact-stress (structures,
# fem pack)

- Path: skills/structures/fem/hertzian-contact-stress/
- Pack: fem (verified present at prep with beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, curved-beam-analysis,
  cylindrical-shell-buckling, diagonal-tension-field-webs,
  lug-joint-analysis, modal-analysis, plate-buckling,
  pressure-bulkhead, shear-center-analysis, shrink-fit-analysis,
  torsion-shear-flow, truss-analysis; the same-wave siblings
  crippling-analysis, metallic-fastener-joints and
  plastic-collapse-analysis are planned but NOT on disk at spec time,
  and the new leaf itself is not on disk yet).
- Claim fences (quoted from the sibling frontmatter and quick
  references at prep, none owns the analytic Hertz closed form):
  - contact-analysis (this pack) is the FEA numerical contact leaf: its
    description reads "Use when the task is FEA contact, penalty or
    Lagrange methods, contact stiffness, penetration, friction,
    stick-slip, master-slave contact, node-to-surface, or tied
    interfaces in bolted joints and bearing contacts. Compute finite
    element contact analysis quantities for aircraft structure:
    determine normal contact forces with the penalty method from contact
    stiffness and penetration, estimate penalty stiffness from the
    contacting element properties, check Lagrange multiplier enforcement
    of zero penetration, apply Coulomb friction to categorize stick or
    slip, and run penetration control until penetration is under
    tolerance", and its quick reference pins the penalty law F_n =
    k_pen * p, the stiffness estimate k_pen = alpha * E * A / L, the
    master-slave signed gap and the Coulomb stick-slip limit f_max =
    mu * |F_n|. Its contact pressure is a Lagrange multiplier of the
    discretized constraint, never the Hertz p0 of a curved pair; there
    is no closed form there. The new leaf computes the analytic Hertz
    solution the FEA run is validated against, and must not claim
    penalty, stiffness tuning, penetration control, friction or
    stick-slip quantities.
  - lug-joint-analysis (this pack) owns the NOMINAL pin bearing of a
    pin-loaded lug: its description reads "Use when you must analyze a
    metallic pin-loaded lug fitting under an axial load: compute the
    hole bearing stress, the net section tension stress across the lug
    width, the tearout shear stress on the two planes from the hole
    tangent to the round outer contour, the per-mode margins against
    the material tension, shear and bearing allowables, the governing
    failure mode and the pass/fail verdict, the limiting allowable
    capacity, and the governing-mode map over the edge distance ratio
    for a round-end lug with w = 2e", and its quick reference pins
    sigma_b = P / (D t) with the hole diameter D and lug thickness t.
    That bearing stress is the load divided by the projected hole area,
    a uniform nominal stress with no patch, no curvature and no
    subsurface field. The new leaf does not claim the P/(Dt) bearing
    stress, lug margins or the e/D sweep.
  - shrink-fit-analysis (this pack) owns the interference-fit contact
    pressure: its description reads "Use when you must compute the
    shrink-fit contact pressure and stresses of a two-cylinder
    radial-interference assembly: convert the total radial interference
    into the interface contact pressure from the Lame thick-cylinder
    radial compliance of both members, recover the bore radial and hoop
    stresses at the critical bore of each member, form the von-Mises
    yield margin of each bore against its yield strength, and close
    with the governing member and the maximum allowable radial
    interference before that bore yields". Its trigger contains the
    generic phrase "contact pressure", but in the full-circumference
    radial-interference sense of a concentric Lame pair with no
    equivalent radius of curvature; the new leaf's contact pressure is
    the Hertz ellipse over a finite patch between locally curved
    bodies pressed together, and the interference fit, Lame bore hoop
    stress and allowable-interference quantities stay with
    shrink-fit-analysis.
  - multiaxial-yield-criteria (materials pack) owns the generic yield
    check of an arbitrary stress state: its description reads "Use when
    you must compute the multiaxial yield margin of an isotropic metal
    part: evaluate the von Mises equivalent stress in plane stress
    sqrt(sx^2 - sx*sy + sy^2 + 3*txy^2) and in full 3D, resolve the
    plane-stress principal stresses from the Mohr circle, compute the
    Tresca equivalent stress as the maximum principal stress
    difference including the zero out-of-plane principal, compute the
    yield margin yield/equivalent - 1, run the von Mises combined
    bending-plus-torsion margin for a shaft section, and check whether
    a biaxial tension point falls inside the von Mises yield
    envelope". The new leaf evaluates no arbitrary stress state: it
    reports the standard Hertz subsurface characteristics (max shear
    and max von Mises with their depths under the patch) and applies
    the standard Hertz yield-limit relations to the contact pressure
    itself, then hands any follow-on stress-state margin work to
    multiaxial-yield-criteria.
  Whole-tree greps at prep: "hertzian-contact-stress" = 0 hits in
  skills/ md and py and in the wave-42 spec set; "hertz-contact-patch"
  and "subsurface-shear-stress" = 0 hits anywhere; the generic word
  "contact pressure" appears only inside the FEA penalty workflow of
  contact-analysis and the radial-interference workflow of
  shrink-fit-analysis, never as a Hertz quantity. GENUINE structures
  gap (fresh probe #3): no leaf owns the analytic Hertzian contact
  stress solution, the contact patch, the elliptic pressure peak or
  the subsurface shear field of curved elastic bodies.
- Standards id: far-25 (reference-only, present in standards-map.yaml).
  Ledger Standard: far-25.
- Family: structures

## Claim

Compute the Hertzian contact stress between curved elastic bodies:
determine the contact patch radius (point contact) or half-width (line
contact) for sphere-on-sphere, sphere-on-flat, ball-in-socket,
cylinder-on-flat, parallel-cylinder (wheel-rail-like) pairs,
crossed equal cylinders, and cylinder-in-bore or roller-in-race
geometries from the applied load, the equivalent radius of curvature
Re (1/Re = 1/R1 + 1/R2, with a flat as an infinite radius and a
concave socket or bore as a negative radius, and for crossed equal
cylinders the per-plane curvature sum A + B = (1/R1 + 1/R2)/2 = 1/R)
and the equivalent elastic modulus E* (1/E* = (1-nu1^2)/E1 +
(1-nu2^2)/E2): the circular patch a = (3*P*Re/(4*E*))**(1/3) with
p0 = 3*P/(2*pi*a**2) for point contact, the strip b =
(4*P*Re/(pi*L*E*))**(1/2) with p0 = 2*P/(pi*b*L) for line contact.
Report the subsurface state of the elastic half-space under the
patch (nu = 0.3 ratios): point contact max shear 0.31*p0 at depth
z = 0.48*a and max von Mises 0.62*p0 at the same depth (on the axis
of symmetry the von Mises stress equals twice the max shear); line
contact max shear 0.30*p0 at z = 0.78*b and max von Mises 0.557*p0
at z = 0.70*b. Close with the yield-limit load check against the
material yield: p0_yield = 3.3*sigma_y for point contact and
1.6*sigma_y for line contact (the standard Hertz yield-limit
relations), the yield-limit load P_yield that drives p0 to p0_yield
by inverting the load-pressure closed form, and the margin
p0_yield/p0 with the pass/fail verdict. Does NOT do: FEA penalty or
Lagrange contact, contact stiffness, penetration control, Coulomb
friction or stick-slip (contact-analysis); the nominal pin bearing
stress P/(Dt), net section tension, tearout or the lug margin sweep
(lug-joint-analysis); interference-fit contact pressure from radial
interference with Lame bore hoop stresses (shrink-fit-analysis);
generic von Mises or Tresca margin evaluation of an arbitrary stress
state (multiaxial-yield-criteria); general elliptical patches of
unequal crossed principal radii, which need the Hertz elliptic
integrals. Steel pairs at nu = 0.3 in both solids for the subsurface
ratios; adhesive contact, tangential traction, rolling or sliding
contact with surface shear, wear and fatigue are out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form, deterministic, SI units (m, N,
Pa). Material properties enter only through E* and sigma_y.

Defining relations (pin these exactly; every function below derives
from them):
- Equivalent elastic modulus: 1/E* = (1-nu1**2)/E1 + (1-nu2**2)/E2.
  For identical materials this reduces to E* = E/(2*(1-nu**2)).
- Equivalent radius of curvature: 1/Re = 1/r1 + 1/r2, where r1 is
  always the convex (positive) radius of the first body, r2 is
  positive for a convex partner (sphere pair, cylinder pair), negative
  for a concave internal partner (ball in socket, cylinder in bore,
  roller in race, magnitude = concave radius) and +inf for a flat.
  1/Re must stay positive, so a concave partner must be larger than
  the convex body it surrounds. Crossed cylinders at right angles have
  the separation h = y**2/(2*r1) + x**2/(2*r2), a per-plane curvature
  sum A + B = (1/r1 + 1/r2)/2, and the patch is circular only for
  r1 = r2 = r, where A + B = 1/r: the circular patch is exactly the
  sphere-on-flat closed form with Re = r (call point_patch with
  re = r1, NOT with the 1/r1 + 1/r2 sphere-pair sum, which would halve
  the radius). Unequal crossed radii give an elliptical patch, the
  general Hertz elliptic-integral case, which is out of scope.
- Point contact (sphere pair, sphere on flat, ball in socket, crossed
  equal cylinders): a = (3*P*Re/(4*E*))**(1/3) and
  p0 = 3*P/(2*pi*a**2), equivalently p0 = (6*P*E*^2/(pi^3*Re^2))**(1/3);
  the inverse load form is P = 2*pi*a**2*p0/3.
- Line contact (cylinder on flat, parallel cylinder pair, cylinder in
  bore, roller in race, axial strip length L):
  b = (4*P*Re/(pi*L*E*))**(1/2) and p0 = 2*P/(pi*b*L), equivalently
  p0 = (P*E*/(pi*Re*L))**(1/2); the inverse load form is
  P = pi*b*L*p0/2.
- Subsurface characteristics, nu = 0.3 in both solids (module
  constants, anchor-verified against the exact elastic fields below):
  point contact: z = 0.48*a, tau_max = 0.31*p0 and, at the same depth,
  vm_max = 0.62*p0 (axisymmetric field: on the axis of symmetry the
  von Mises stress is exactly twice the max shear); line contact:
  tau_max = 0.30*p0 at z = 0.78*b and vm_max = 0.557*p0 at
  z = 0.70*b (the plane-strain intermediate principal stress separates
  the two depths). At the surface center the contact is nearly
  hydrostatic, so yielding always initiates subsurface.
- Yield-limit relations (module constants): p0_yield =
  YLD_FACTOR_POINT * sigma_y = 3.3*sigma_y for point contact and
  p0_yield = YLD_FACTOR_LINE * sigma_y = 1.6*sigma_y for line contact,
  the standard Hertz yield-limit relations: for line contact the
  subsurface Tresca condition tau_max = 0.30*p0 = sigma_y/2 gives
  p0 = sigma_y/0.60 = 1.67*sigma_y (the 1.6 of the standard relation),
  so first subsurface yield and the yield-limit pressure coincide; for
  point contact first subsurface yield initiates when the max von
  Mises 0.62*p0 reaches sigma_y at p0 = 1.6*sigma_y, while the
  yield-limit pressure of the standard spherical static check is
  3.3*sigma_y, at which the subsurface plastic zone, initiated at
  about 1.6*sigma_y, has grown through the contact and bounded
  permanent deformation sets the load limit. The yield-limit LOAD
  inverts the p0(load) closed form: point contact
  P_y = pi^3*Re^2*p0_y^3/(6*E*^2) (from p0 = 3P/(2 pi a^2) with
  a^3 = 3P Re/(4 E*)); line contact P_y = pi*Re*L*p0_y^2/E* (from
  p0 = 2P/(pi b L) with b^2 = 4P Re/(pi L E*)).

Functions:
- equivalent_modulus(e1, nu1, e2, nu2) -> float: E* in Pa from
  1/E* = (1-nu1**2)/E1 + (1-nu2**2)/E2. ValueError if e1 <= 0, e2 <= 0
  or nu1, nu2 outside [0, 0.5).
- equivalent_radius(r1, r2) -> float: Re in m from 1/Re = 1/r1 + 1/r2
  with the sign convention above (r2 > 0 convex, r2 < 0 concave,
  r2 = inf flat). ValueError if r1 <= 0, r2 == 0, r2 == -inf, or the
  curvature sum is not positive (concave partner not larger than the
  convex body).
- point_patch(load, e_star, re) -> (a, p0): circular patch from
  a = (3*load*re/(4*e_star))**(1/3) and p0 = 3*load/(2*pi*a**2).
  ValueError if load <= 0, e_star <= 0 or re <= 0.
- line_patch(load, e_star, re, length) -> (b, p0): strip from
  b = (4*load*re/(pi*length*e_star))**(1/2) and
  p0 = 2*load/(pi*b*length). ValueError if any argument <= 0.
- point_subsurface(p0, a) -> dict: {"z_tau": 0.48*a,
  "tau_max": 0.31*p0, "z_vm": 0.48*a, "vm_max": 0.62*p0}. ValueError
  if p0 <= 0 or a <= 0.
- line_subsurface(p0, b) -> dict: {"z_tau": 0.78*b,
  "tau_max": 0.30*p0, "z_vm": 0.70*b, "vm_max": 0.557*p0}. ValueError
  if p0 <= 0 or b <= 0.
- yield_limit_pressure(sigma_y, point_contact=True) -> float:
  3.3*sigma_y (point) or 1.6*sigma_y (line). ValueError if
  sigma_y <= 0.
- yield_limit_load(sigma_y, e_star, re, point_contact=True,
  length=None) -> float: P_y by the inverse closed form above; length
  is required for line contact. ValueError if sigma_y <= 0 or the
  line-contact length is missing or not positive.
- check_yield_margin(p0, sigma_y, point_contact=True) -> dict:
  {"p0_yield": p0_yield, "margin": p0_yield/p0,
  "below_yield_limit": p0 <= p0_yield}, the yield-limit load check
  verdict. ValueError if p0 <= 0.

Identities to test (closed form, exact):
- Same-material degeneracy: equivalent_modulus(e, nu, e, nu) equals
  e/(2*(1-nu**2)) to float noise (anchor assert at 1e-12 relative).
- Flat and concave limits: equivalent_radius(r1, inf) equals r1 to
  float noise; equivalent_radius(r1, -r2) equals 1/(1/r1 - 1/r2) for
  r2 > r1 to float noise.
- Crossed equal cylinders: point_patch(P, E*, r) gives the same patch
  as point_patch(P, E*, equivalent_radius(r, inf)) to float noise
  (anchor relative difference below 1e-12); unequal crossed radii are
  elliptical and out of scope.
- p0 consistency: 3*P/(2*pi*a**2) equals
  (6*P*E*^2/(pi^3*Re^2))**(1/3) and 2*P/(pi*b*L) equals
  (P*E*/(pi*Re*L))**(1/2) to float noise (anchor relative difference
  0.0); the inverse load forms recover the input P to within 1e-9
  (anchor recovered 1000.0 N and 50000.0 N to 1e-12 relative).
- Subsurface constants: the ratios above reproduce the extremes of the
  exact elastic fields under the patch, scanned along the axis of
  symmetry (point contact, Huber closed form sigma_z = -p0/(1+zeta^2),
  sigma_r = -p0*((1+nu)*(1 - zeta*atan(1/zeta)) - 1/(2*(1+zeta^2))))
  and along the centerline (line contact, plane strain sigma_z =
  -p0/sqrt(1+zeta^2), sigma_y = -p0*((1+2*zeta^2)/sqrt(1+zeta^2) -
  2*zeta), sigma_x = -2*nu*p0*(sqrt(1+zeta^2) - zeta)): the anchor
  scans give z/a = 0.4810 with tau/p0 = 0.3100 and vm/p0 = 0.6200 for
  point contact, and z/b = 0.7862 with tau/p0 = 0.3003 plus z/b =
  0.7042 with vm/p0 = 0.5575 for line contact, matching the constants
  to 2e-2.
- ValueErrors across the module: zero or negative moduli; nu at 0.5
  and 0.6; r1 at 0; r2 at 0; a concave partner not larger than the
  convex body; zero load; zero patch size; missing line length;
  negative p0; zero sigma_y.
- Determinism; no imports beyond math; subsurface ratios fixed at
  nu = 0.3.

## Worked example

Steel on steel throughout: E = 210 GPa, nu = 0.3, so E* =
1.1538461538e11 Pa = 115.385 GPa (= E/(2*(1-nu^2)) to float noise). All
values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_hertz.py (pure stdlib math, closed form, exit 0);
the anchor also verifies the subsurface constants against the exact
elastic field scans quoted in the identities above.

- Identity block: Re = 50 mm for a 50 mm roller on a flat; Re =
  16.666667 mm for a 10 mm ball in a 25 mm concave socket (1/0.010 -
  1/0.025); Re = 60 mm for a 15 mm roller in a 20 mm bore (1/0.015 -
  1/0.020); Re = 180 mm for a 450 mm wheel on a 300 mm convex rail
  crown (1/0.45 + 1/0.30); crossed 10 mm cylinders give a = 0.319125
  mm and p0 = 2344.2 MPa, identical to a 10 mm sphere on a flat
  (anchor relative difference below 1e-12).
- Case A, steel roller on steel flat (line): r1 = 50 mm, L = 100 mm,
  P = 50 kN, sigma_y = 900 MPa. Re = 50 mm; b = 0.525232 mm;
  p0 = 606.0368 MPa (606.0); max shear 181.81 MPa at z = 0.4097 mm
  (0.78 b); max von Mises 337.56 MPa at z = 0.3677 mm (0.70 b).
  p0_yield = 1.6*900 = 1440.0 MPa, margin = 2.3761, P_yield =
  282.291 kN: the roller carries 5.6 times the applied load before the
  line-contact yield limit is reached.
- Case B, ball in socket (point, conformal): r1 = 10 mm ball, concave
  r2 = -25 mm socket, P = 700 N, sigma_y = 1200 MPa. Re = 16.666667
  mm; a = 0.423272 mm; p0 = 1865.52 MPa; max shear 578.31 MPa and max
  von Mises 1156.62 MPa at z = 0.2032 mm (0.48 a). p0_yield =
  3.3*1200 = 3960.0 MPa, margin = 2.1227, P_yield = 6.696 kN. The
  applied load keeps p0 at 1.55 sigma_y, below the 1.6 sigma_y point
  of first subsurface yield, so the contact is fully elastic.
- Case C, wheel-rail-like cylinder pair (line): r1 = 450 mm wheel on
  r2 = 300 mm convex rail crown, P = 80 kN over L = 15 mm, sigma_y =
  700 MPa. Re = 180 mm; b = 3.2547 mm; p0 = 1043.2 MPa; max shear
  312.96 MPa at z = 2.539 mm; max von Mises 581.06 MPa at z = 2.278
  mm. p0_yield = 1120.0 MPa, margin = 1.0736, P_yield = 92.215 kN:
  the realistic ~1 GPa rail contact runs just under the 1.6 sigma_y
  line-contact limit.
- Case D, crossed equal cylinders (point): r1 = r2 = 10 mm at right
  angles, P = 500 N, sigma_y = 1200 MPa. The per-plane curvature sum
  gives the sphere-on-flat patch: a = 0.31913 mm; p0 = 2344.2 MPa;
  max shear 726.69 MPa and max von Mises 1453.39 MPa at z = 0.15318
  mm. p0_yield = 3960.0 MPa, margin = 1.6893, P_yield = 2.410 kN.
  Here p0/sigma_y = 1.95 sits between the 1.6 sigma_y point of first
  subsurface yield (the von Mises 1453.39 MPa already exceeds the
  1200 MPa yield) and the 3.3 sigma_y point of the spherical
  yield-limit relation, the elastic-plastic growth regime of the
  standard static check.
- Case E, roller in race (line, concave): r1 = 15 mm roller in a 20 mm
  concave race, P = 10 kN over L = 20 mm, sigma_y = 1200 MPa. Re =
  60 mm; b = 0.57536 mm; p0 = 553.23 MPa; max shear 165.97 MPa at
  z = 0.44878 mm; max von Mises 308.15 MPa. p0_yield = 1920.0 MPa,
  margin = 3.4705, P_yield = 120.444 kN: the conformal bore spreads
  the load, so the margin is the fattest of the set.
- Read-off: curved steel pairs at GPa-level p0 are normal; the check
  that matters is the margin of p0 against the geometry-dependent
  yield-limit pressure, 1.6 sigma_y for strips and 3.3 sigma_y for
  circular patches, and the corresponding P_yield.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_hertz.py
(stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- equivalent_modulus(210e9, 0.3, 210e9, 0.3) = 1.1538461538e11 Pa
  within 1e-3 relative; equals 210e9/(2*(1-0.3**2)) within 1e-9
  relative.
- equivalent_radius: (0.050, inf) = 0.05; (0.010, -0.025) =
  0.016666667 within 1e-6; (0.015, -0.020) = 0.06; (0.450, 0.300) =
  0.18; each within 1e-12 relative.
- Crossed equal cylinders: point_patch(500.0, E*, 0.010) equals
  point_patch(500.0, E*, equivalent_radius(0.010, inf)) within 1e-9
  relative (a = 0.319125 mm, p0 = 2344.2 MPa).
- Case A: line_patch(50000.0, E*, 0.05, 0.1) gives b = 5.25232e-4 m
  and p0 = 6.0603682883e8 Pa within 1e-3; p0 from the load form
  sqrt(P E*/(pi Re L)) identical to 1e-9; line_subsurface gives
  z_tau = 0.4097 mm, tau_max = 181.81 MPa, vm_max = 337.56 MPa;
  check_yield_margin(p0, 900e6, point_contact=False) has margin
  2.3761 and yield_limit_load = 282.291 kN within 1e-3.
- Case B: point_patch(700.0, E*, 0.0166666667) gives a = 4.23272e-4 m,
  p0 = 1.86552e9 Pa; point_subsurface gives z = 0.2032 mm,
  tau_max = 578.31 MPa, vm_max = 1156.62 MPa (below sigma_y = 1200
  MPa, the fully elastic regime); margin 2.1227, P_yield = 6.696 kN.
- Case C: b = 3.2547 mm, p0 = 1043.2 MPa, tau_max = 312.96 MPa at
  z = 2.539 mm, margin 1.0736, P_yield = 92.215 kN within 1e-3; the
  load pressure p0 = 1.49 sigma_y sits below the line yield limit.
- Case D: a = 0.31913 mm, p0 = 2344.2 MPa, vm_max = 1453.39 MPa
  (above sigma_y = 1200 MPa, between first yield at 1.6 sigma_y and
  the 3.3 sigma_y yield-limit pressure), margin 1.6893, P_yield =
  2.410 kN.
- Case E: b = 0.57536 mm, p0 = 553.23 MPa, margin 3.4705, P_yield =
  120.444 kN.
- Subsurface constants against the exact fields: the scan extremes
  match the module constants, z/a = 0.4810 vs 0.48 (2e-2), tau/p0 =
  0.3100 vs 0.31, vm/p0 = 0.6200 vs 0.62; line z/b = 0.7862 vs 0.78,
  tau/p0 = 0.3003 vs 0.30, z/b = 0.7042 vs 0.70, vm/p0 = 0.5575 vs
  0.557 (3e-2).
- Inverse loads: P recovered from the patch is the input P to 1e-9
  (anchor 1.0000000000e3 N and 5.0000000000e4 N); yield_limit_load
  equals the applied load times the margin power (margin**3 for point,
  margin**2 for line) to 1e-6.
- ValueErrors: e at 0; nu at 0.5 and 0.6; r1 at 0; r2 at 0 and -inf;
  equivalent_radius(0.025, -0.010) (concave smaller than convex);
  point_patch and line_patch at zero load; line_patch at zero length;
  line_subsurface at zero b; yield_limit_pressure at zero sigma_y;
  yield_limit_load for line contact without length;
  check_yield_margin at negative p0.
- Determinism; no imports beyond math; nu fixed at 0.3 for the
  subsurface ratios.

## Corpus fragment (eval/hit1-wave43-hertzian-contact-stress.yaml)

Query 1 (copy verbatim):
  "compute the hertzian-contact-stress contact patch half-width and
  maximum contact pressure between a steel roller and a steel flat
  from the applied load and material properties, and the
  subsurface-shear-stress depth and yield-limit load against the
  roller yield strength"
  intent: "structures; analytic Hertz line contact of a cylinder on a
  flat: patch half-width, maximum contact pressure, subsurface max
  shear depth and the yield-limit load from the standard Hertz yield
  relation"
  expected_skill: "structures/fem/hertzian-contact-stress"
Query 2 (copy verbatim):
  "find the hertz-contact-patch radius and the contact-pressure-
  ellipse maximum pressure of a ball in a socket from the applied
  load, the equivalent radius of curvature and the equivalent elastic
  modulus, and check the point-contact yield limit against the ball
  yield strength"
  intent: "structures; analytic Hertz point contact of a sphere in a
  concave socket: circular patch radius, elliptic pressure peak p0 and
  the 3.3 sigma_y point yield-limit check"
  expected_skill: "structures/fem/hertzian-contact-stress"
Task ids: w43-hertzian-contact-stress-1 and -2. Prep grep of
eval/hit1-corpus.yaml: "hertzian-contact-stress", "hertz-contact-
patch", "contact-pressure-ellipse" and "subsurface-shear-stress"
appear in NO existing task (the only "subsurface" tasks route on NDT
ultrasonic pulse-echo, eddy-current depth-of-penetration and
thermography disbond depth in manufacturing-quality/ndt); the
w21-contact-analysis tasks route on penalty contact force,
penetration and Coulomb stick-slip; the w34-lug-joint-analysis tasks
route on hole bearing stress P/(Dt), net section tension, tearout and
the edge distance ratio sweep; the w42-shrink-fit-analysis task
routes on the interference-fit contact pressure of a Lame thick-
cylinder pair; so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the Hertzian contact
stress between curved elastic bodies pressed together:" and include
the outputs in the Claim. First tag: hertzian-contact-stress.
Additional tags ONLY: hertz-contact-patch, contact-pressure-ellipse,
subsurface-shear-stress, contact-yield-limit-load,
equivalent-contact-modulus. NEVER single generic words (contact,
stress, pressure, patch, shear, yield, radius, sphere, cylinder,
roller, steel) and NEVER the sibling tags penalty-method,
contact-stiffness, penetration, coulomb-friction, stick-slip,
master-slave, tie-constraint (contact-analysis), lug-bearing-stress,
lug-net-section-tension, lug-tearout-shear, lug-edge-distance-ratio
(lug-joint-analysis), interference-fit-contact-pressure,
lame-thick-cylinder-stress, bore-hoop-stress (shrink-fit-analysis),
von-mises-equivalent-stress, tresca-margin
(multiaxial-yield-criteria). 50-150 words, <=1000 chars, no em dash,
no content-policy sweep term (the banned word from the builder kit),
action verb present. Recommended wording (outputs in Claim order):
"Use when you must compute the Hertzian contact stress between curved
elastic bodies pressed together: determine the contact patch radius or
half-width for sphere pairs, sphere-on-flat, ball-in-socket, cylinder
pairs, cylinder-in-bore, roller-in-race or crossed cylinders from the
load, the equivalent radius of curvature and the equivalent elastic
modulus with 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2; compute the maximum
contact pressure p0 = 3P/(2 pi a^2) (circular) and
p0 = 2P/(pi b L) (strip); report the subsurface shear and von Mises
maxima with depth and magnitude; and run the yield-limit load check
with p0_yield = 3.3 sigma_y (point) and 1.6 sigma_y (line). Produces
patch size, peak pressure, subsurface stress location and
magnitude, and yield-limit load and margin in SI units. Trigger:
hertzian contact stress, hertz contact patch, contact pressure
ellipse, subsurface shear stress, equivalent elastic modulus,
equivalent radius of curvature, maximum contact pressure, contact
yield limit." The sibling triggers "penalty
contact", "contact stiffness", "penetration", "friction",
"interference fit contact pressure" and "lug bearing stress" must not
appear.

FORBIDDEN TOKENS (belong to siblings): penalty-method, penalty
stiffness, contact-stiffness, penetration, penetration-control,
lagrange-multiplier, coulomb-friction, stick-slip, slip-state,
master-slave, node-to-surface, tie-constraint, contact-force from
stiffness (contact-analysis); lug, pin-loaded, hole-bearing-stress,
lug-bearing, net-section-tension, lug-tearout, tearout-shear,
edge-distance-ratio, bearing-allowable, P/(Dt) nominal pin bearing
(lug-joint-analysis); interference-fit, radial-interference,
press-fit, lame-contact-pressure, thick-cylinder, bore-hoop-stress,
allowable-interference (shrink-fit-analysis); plane-stress von Mises
margin, mohr-circle, biaxial envelope of an arbitrary stress state
(multiaxial-yield-criteria); general elliptical-contact elliptic
integrals, tangential traction, adhesive contact, rolling contact
fatigue, wear, gear-tooth or rolling-element load ratings (outside
structures).
