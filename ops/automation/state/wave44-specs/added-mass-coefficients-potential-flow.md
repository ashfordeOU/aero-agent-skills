# Wave-44 leaf spec: added-mass-coefficients-potential-flow (aerodynamics,
# aeroelasticity pack)

- Path: skills/aerodynamics/aeroelasticity/added-mass-coefficients-
  potential-flow/
- Pack: aeroelasticity (present siblings aeroelastic-gust-response,
  divergence-speed, flutter-speed-prediction; adjacent fences in
  aerodynamics/airfoil (thin-airfoil-section-theory covers the steady
  thin airfoil), aerodynamics/cfd (panel-method carries the tag
  potential-flow for steady 3-D panel solutions, and its corpus rows own
  the doublet/source panel steady-flow wording), aerodynamics/boundary-
  layer (unsteady-laminar-stokes-layers is unsteady viscous diffusion,
  not inviscid acceleration), structures/loads (gust-maneuver-loads owns
  the rigid discrete-gust certification load-factor method)).
- Claim fences (quoted from the sibling frontmatter/body at prep, none
  owns the kinetic-energy added-mass catalog of an accelerating body):
  - aeroelastic-gust-response (this pack) owns the DYNAMIC response of
    the flexible typical section to a discrete gust with indicial lag
    states: its description reads "run the Wagner and Kussner lag-state
    lift model in the time domain, produce the plunge and pitch response
    histories for a one-minus-cosine gust, and report the dynamic
    magnification factor of the peak lift over the quasi-steady value",
    and its body documents the explicit exclusion this leaf fills:
    "apparent-mass and full Theodorsen noncirculatory terms are
    neglected at this level (documented assumption)" (same note in its
    logic script docstring, which adds "apparent-mass and full
    Theodorsen pitch-moment terms are neglected"). The sibling runs its
    plunge/pitch equations with the STRUCTURAL inertia m_s and I_theta
    only; the fluid inertia coefficient an accelerating body carries is
    exactly the content it disclaims. The new leaf produces no gust, no
    time history and no lag state: it catalogs the inertia coefficient
    itself.
  - flutter-speed-prediction (this pack) owns the V-g flutter speed of
    the two-DOF bending-torsion section: its description reads "apply
    Theodorsen unsteady aerodynamics with the complex lift-deficiency
    function C(k), run the V-g method across the reduced frequency
    range, locate the flutter speed where the artificial structural
    damping g crosses zero". Its logic script builds the effective
    inertia of the flutter determinant at harmonic motion, where the
    comment "The apparent-mass damping terms (i/k in the lift, the
    -i(1/2 - a)/k in the moment) are included" shows that fluid inertia
    appears there only as embedded terms of the oscillatory thin-airfoil
    section loads inside a 2 x 2 eigenvalue sweep at a fixed reduced
    frequency. No kinetic-energy surface integral, no 2-D or 3-D shape
    catalog, no displaced-mass ratios: the coefficient of a whole body
    is not computed anywhere in that leaf.
  - divergence-speed (this pack) owns the static divergence condition:
    its description reads "calculate the divergence dynamic pressure
    from the torsional stiffness, the reference area, the chord, the
    lift curve slope, and the aerodynamic-center-to-shear-center offset
    ratio"; no fluid inertia content (whole-body grep at prep: zero
    added/virtual/apparent mass hits).
  - thin-airfoil-section-theory (aerodynamics/airfoil) and panel-method
    (aerodynamics/cfd) own steady attached-flow load and pressure
    solutions; neither evaluates the kinetic energy of the flow set up
    by an accelerating body.
  - gust-maneuver-loads (structures/loads) owns the rigid discrete-gust
    load factor of FAR/CS 25.341; it applies gust velocities, it does
    not evaluate body acceleration inertia.
  Whole-tree greps at prep: "added-mass|virtual-mass|apparent-mass"
  returns matches ONLY inside the two unsteady-aero siblings' notes
  quoted above (aeroelastic-gust-response SKILL.md body line 61 and its
  logic script docstring; flutter-speed-prediction logic script comment
  line 136) and zero ownership hits in any other leaf of the tree; the
  corpus tokens added-mass-coefficients, virtual-mass, apparent-mass and
  acceleration-reaction return 0 hits in eval/hit1-corpus.yaml and in
  every eval/*.yaml fragment (grep -l empty, grep -c 0 per token).
  GENUINE aeroelasticity gap (probe receipt task-6 rank 3, verified
  zero-owner, GO): no leaf reduces the kinetic energy of the irrotational
  flow set up by a body accelerating through an inviscid fluid to the
  added mass coefficient catalog of Lamb Hydrodynamics Art. 136 / the
  Brennen added-mass review class, which is precisely the term the
  gust-response sibling excludes by name.
- Standards id: naca-tr-824 (NACA Report 824: Summary of Airfoil Data,
  reference-data family, public domain, present in standards-map.yaml),
  reference-only context for the thin-airfoil/potential-flow methodology
  this catalog complements; no standard text reproduced anywhere. Ledger
  Standard: naca-tr-824. Method provenance is the classical literature
  (Lamb, Hydrodynamics, Art. 136 kinetic-energy integrals; Brennen,
  "A Review of Added Mass and Fluid Inertial Forces"), cited by name
  only.
- Family: aerodynamics

## Claim

Determine the added mass coefficient (equivalently virtual mass,
apparent mass) of a body accelerating rectilinearly through an inviscid
irrotational fluid, from the kinetic energy of the irrotational flow the
body sets up, T = (1/2)*rho*integral over the body surface of
phi*(dphi/dn) dS (normal derivative positive into the body; Lamb
Hydrodynamics Art. 136 form), which for translation at speed U equals
(1/2)*m_a*U^2 and thereby fixes the coefficient m_a of the shape.
Catalog, closed form per shape: the 2-D circular cylinder at rho*pi*R^2
per unit span (any in-plane direction, by symmetry), the 2-D normal flat
plate of half-width a at rho*pi*a^2 per unit span with an exactly zero
tangential coefficient, the 2-D elliptic cylinder at rho*pi*b^2 along
its a semi-axis and rho*pi*a^2 along its b semi-axis per unit span, the
3-D sphere at (2/3)*rho*pi*R^3 (half its displaced fluid mass), and the
3-D prolate and oblate spheroids through the elementary closed-form
reduction of the Lamb ellipsoid integrals alpha0, beta0, gamma0 (which
sum to 2), with the sphere values as the exact e = 0 branch. Every
coefficient is reported against the displaced fluid mass M_disp =
(4/3)*rho*pi*a*b*c through the ratio k = m_a/M_disp (sphere k = 1/2
exactly; flat bodies can exceed unity). Then close the energy picture:
the fluid kinetic energy (1/2)*m_a*U^2 at a translation speed, the
virtual mass m_body + m_a, the added-mass fraction m_a/(m_body + m_a),
and the acceleration-reaction force the body must supply to sustain an
acceleration, m_a*acceleration, with the opposing reaction on the body
as its negative. Does NOT do: oscillatory thin-airfoil load coefficients
or the complex C(k) machinery and the V-g eigenvalue sweep
(flutter-speed-prediction); Wagner/Kussner indicial lag states, gust
response time histories or the dynamic magnification factor (aeroelastic-
gust-response); the static divergence speed (divergence-speed); steady
panel, doublet or source flow solutions (panel-method); the rigid
discrete-gust load-factor method (gust-maneuver-loads); viscous,
compressible or free-surface effects; rotating-body added moments of
inertia; and general triaxial ellipsoids, whose Lamb integrals are
elliptic (the catalog stops at the axisymmetric spheroids, where the
integrals reduce to elementary functions). Catalog entries are for
rectilinear translation along a principal direction; simultaneous
orthogonal components superpose in the kinetic energy T = (1/2)*sum
(m_i*U_i^2). Motion of the fluid is fully attached and irrotational by
construction.

## Model (implement exactly)

Pure stdlib math only, closed form, deterministic. No module constants
beyond the math library; every fluid density rho is passed explicitly in
kg/m^3.

Defining relations (pin these exactly; every function below derives
from them):
- Kinetic energy of the irrotational motion set up by a body translating
  at speed U along a principal direction: T = (1/2)*m_a*U^2, with m_a
  the added mass. The equivalent surface integral of the velocity
  potential, T = (1/2)*rho*oint_S phi*(dphi/dn) dS with dphi/dn positive
  INTO the body (Lamb's Art. 136 form, T = -(1/2)*rho*oint phi*
  (dphi/dn_out) dS with the outward normal), is what the anchor
  evaluates on the exact dipole potentials of the moving circle and
  sphere, recovering m_a = rho*pi*R^2 (2-D, per unit span) and m_a =
  (2/3)*rho*pi*R^3 (3-D): real anchor at R = 1 m, rho = 1000 kg/m^3,
  U = 2 m/s, T = 6283.185307 J/m from the integral versus
  (1/2)*rho*pi*R^2*U^2 = 6283.185307 J/m (residual 1.546e-11 J/m), and
  T = 4188.790205 J versus (1/2)*((2/3)*rho*pi*R^3)*U^2 = 4188.790205 J
  (residual 1.819e-12 J).
- Displaced fluid mass and coefficient ratio: M_disp = (4/3)*rho*pi*a*
  b*c for an ellipsoid of semi-axes a, b, c; k = m_a/M_disp. Sphere:
  k = 1/2 exactly.
- Lamb ellipsoid coefficients (Art. 114 integrals): with Delta =
  sqrt((a^2+u)*(b^2+u)*(c^2+u)),
  alpha0 = a*b*c*integral_0^inf du/((a^2+u)*Delta),
  beta0 = a*b*c*integral_0^inf du/((b^2+u)*Delta),
  gamma0 = a*b*c*integral_0^inf du/((c^2+u)*Delta),
  alpha0 + beta0 + gamma0 = 2, and the added mass for translation along
  the a semi-axis is M_disp*alpha0/(2 - alpha0) (likewise beta0, gamma0
  for the other axes). For the axisymmetric spheroids the integrals are
  elementary. The anchor verifies every closed form below against
  independent high-order deterministic quadrature of these integrals at
  aspect ratios 2, 5 and 10: the largest disagreement is 1.30e-14, and
  the sum rule reproduces 2.000000000 on every row.
- Prolate spheroid (axial semi-axis a >= equatorial b = c), eccentricity
  e = sqrt(1 - (b/a)^2):
  alpha0 = 2*(1 - e^2)/(e^3) * (0.5*ln((1+e)/(1-e)) - e),
  beta0 = gamma0 = 1 - alpha0/2,
  axial m_a = M_disp*alpha0/(2 - alpha0),
  transverse m_a = M_disp*beta0/(2 - beta0).
  Limits: sphere e = 0 gives alpha0 = beta0 = 2/3 and k = 1/2; a slender
  needle e -> 1 gives alpha0 -> 0 (axial k -> 0) and beta0 -> 1
  (transverse k -> 1).
- Oblate spheroid (equatorial semi-axis a = b >= polar c), eccentricity
  e = sqrt(1 - (c/a)^2):
  gamma0 = 2*(e - (c/a)*asin(e))/(e^3),
  alpha0 = beta0 = 1 - gamma0/2,
  polar m_a = M_disp*gamma0/(2 - gamma0),
  equatorial m_a = M_disp*alpha0/(2 - alpha0).
  Limits: sphere e = 0 gives gamma0 = 2/3; a thin disk c -> 0 gives
  gamma0 -> 2, so m_polar/M_disp diverges while m_polar tends to the
  finite classical (8/3)*rho*a^3 (real anchor ratio 0.999970 at c/a =
  1e-4), and the equatorial coefficient vanishes with the thickness
  (an infinitesimally thin disk moving in its own plane disturbs no
  flow). Oblate polar k exceeds 1 for flat shapes (real anchor 1.652659
  at a = 1 m, c = 0.35 m, rho = 1000 kg/m^3).

Functions (implement exactly; all dimensional results in kg, the 2-D
results per unit span in kg/m, rho in kg/m^3, lengths in m, speeds in
m/s, accelerations in m/s^2):
- kinetic_energy_of_translation(m_added, speed) -> float
  0.5*m_added*speed*speed, the fluid kinetic energy of rectilinear
  translation. ValueError if m_added <= 0 or speed < 0; returns 0.0 at
  speed 0.
- acceleration_reaction_force(m_added, acceleration) -> float
  m_added*acceleration, the force the accelerating body must supply to
  the fluid to sustain the acceleration (Newton's third law partner of
  the reaction the fluid exerts on the body, whose force is the
  negative, opposing the acceleration). ValueError if m_added <= 0.
- virtual_mass(m_body, m_added) -> float
  m_body + m_added, the body mass augmented by the fluid inertia.
  ValueError if m_body <= 0 or m_added <= 0.
- added_mass_fraction(m_added, m_body) -> float
  m_added/(m_body + m_added), the fluid-inertia share of the virtual
  mass, dimensionless. ValueError if m_body <= 0 or m_added <= 0.
- cylinder_added_mass(rho, R) -> float
  rho*pi*R*R per unit span, the 2-D circular cylinder, any in-plane
  direction. ValueError if rho <= 0 or R <= 0.
- flat_plate_added_masses(rho, a) -> tuple
  (rho*pi*a*a, 0.0), the 2-D normal flat plate of half-width a per unit
  span: the normal coefficient rho*pi*a*a for motion perpendicular to
  the plate and the tangential coefficient EXACTLY 0.0 for motion in
  the plate plane. ValueError if rho <= 0 or a <= 0.
- elliptic_cylinder_added_masses(rho, a, b) -> dict
  {'m_along_a': rho*pi*b*b, 'm_along_b': rho*pi*a*a} per unit span for
  the section x^2/a^2 + y^2/b^2 = 1: motion along a semi-axis couples
  to the OTHER semi-axis squared (the classical elliptic-cylinder
  result, which contains the circle limit a = b = R giving rho*pi*R^2
  both ways and the plate limit b -> 0 giving (0, rho*pi*a^2)).
  ValueError if rho <= 0 or a <= 0 or b <= 0.
- sphere_added_mass(rho, R) -> float
  (2.0/3.0)*rho*pi*R*R*R, half the displaced fluid mass of the sphere.
  ValueError if rho <= 0 or R <= 0.
- prolate_spheroid_added_masses(rho, a, b) -> dict
  {'axial': ..., 'transverse': ...} kg for the prolate spheroid
  x^2/a^2 + (y^2+z^2)/b^2 = 1, a >= b. When a == b exactly, both entries
  equal the sphere value (2.0/3.0)*rho*pi*a^3 (the exact e = 0 branch;
  no division by e). Otherwise e = sqrt(1 - (b/a)^2), alpha0 =
  2*(1-e*e)/(e**3)*(0.5*ln((1+e)/(1-e)) - e), beta0 = 1 - alpha0/2,
  M_disp = (4.0/3.0)*rho*pi*a*b*b, axial = M_disp*alpha0/(2 - alpha0),
  transverse = M_disp*beta0/(2 - beta0). ValueError if rho <= 0, a <= 0,
  b <= 0 or b > a.
- oblate_spheroid_added_masses(rho, a, c) -> dict
  {'polar': ..., 'equatorial': ...} kg for the oblate spheroid
  (x^2+y^2)/a^2 + z^2/c^2 = 1, a >= c, with polar the motion along the
  z symmetry axis (semi-axis c) and equatorial the motion along a
  (semi-axis a). When a == c exactly, both entries equal the sphere
  value (2.0/3.0)*rho*pi*a^3. Otherwise e = sqrt(1 - (c/a)^2),
  gamma0 = 2*(e - (c/a)*asin(e))/(e**3), alpha0 = 1 - gamma0/2,
  M_disp = (4.0/3.0)*rho*pi*a*a*c, polar = M_disp*gamma0/(2 - gamma0),
  equatorial = M_disp*alpha0/(2 - alpha0). ValueError if rho <= 0,
  a <= 0, c <= 0 or c > a.

Identities to test (closed form, exact or anchor-pinned):
- kinetic_energy_of_translation(m, u) == 0.5*m*u*u exactly and returns
  0.0 at u = 0; the surface-integral derivation of the catalog: at
  R = 1 m, rho = 1000 kg/m^3, U = 2 m/s the moving-circle dipole
  potential integral gives T = 6283.185307 J/m, matching
  (1/2)*cylinder_added_mass(1000, 1)*4 to the 1.546e-11 J/m residual,
  and the moving-sphere doublet integral gives T = 4188.790205 J,
  matching (1/2)*sphere_added_mass(1000, 1)*4 to the 1.819e-12 J
  residual.
- flat_plate_added_masses tangential entry is EXACTLY 0.0; the normal
  entry at a = 0.75, rho = 1000 is 1767.145868 kg/m.
- elliptic circle limit: elliptic_cylinder_added_masses(rho, R, R) has
  both entries equal to cylinder_added_mass(rho, R) with difference
  0.000e+00 (real anchor at R = 0.5: both 785.398163 kg/m).
- Sphere half-mass identity:
  sphere_added_mass(rho, R)/(0.5*(4.0/3.0)*rho*pi*R^3) = 1.000000000
  exactly.
- Sphere branches: prolate_spheroid_added_masses(rho, R, R) and
  oblate_spheroid_added_masses(rho, R, R) both equal
  sphere_added_mass(rho, R) with difference 0.000e+00 on both entries
  (real anchor at R = 0.5, rho = 1000).
- Spheroid formulas versus the Lamb integrals: every closed-form
  alpha0/beta0/gamma0 agrees with the independent deterministic
  quadrature to at most 1.30e-14 at aspect ratios 2, 5 and 10, and
  alpha0 + 2*beta0 = 2.000000000 (prolate) and gamma0 + 2*alpha0 =
  2.000000000 (oblate) on every row.
- e -> 0 continuity: alpha0(prolate, a/b = 1 + 1e-6) = 0.666666133 and
  gamma0(oblate, a/c = 1 + 1e-6) = 0.666667200, each within 1e-5 of
  2/3.
- Thin-disk asymptote of the oblate polar coefficient:
  m_polar/((8/3)*rho*a^3) = 0.999970 at c/a = 1e-4 (a = 1 m, rho =
  1000), within 1e-3 of the classical (8/3)*rho*a^3 disk value; gamma0
  at that aspect is 1.999685881, approaching 2.
- Slender prolate: at a/b = 10 (rho = 1.225 kg/m^3, b = 1 m) the
  coefficient ratios are axial k = 0.020706 and transverse k = 0.960235
  (real anchor), bracketing the k in (0, 1) band around the sphere's
  0.5 and approaching 0 and 1 respectively as the body lengthens.
- Oblate flat-body k above 1: at a = 1 m, c = 0.35 m, rho = 1000 the
  polar k = 1.652659 exceeds unity while the equatorial k = 0.232271.
- Acceleration reaction and kinetic energy: for the sphere R = 0.5 m at
  rho = 1000 the reaction at 4 m/s^2 is m_a*4 = 1047.197551 N and the
  kinetic energy at 4 m/s is 0.5*m_a*16 = 2094.395102 J; virtual mass
  with a 200 kg body is 461.799388 kg and the added-mass fraction is
  0.566912.
- ValueErrors across the module: every function at rho 0 and at negative
  rho; cylinder and sphere at R 0; plate at a 0; elliptic cylinder at
  b 0; prolate at b > a and at b 0; oblate at c > a and at c 0;
  kinetic_energy_of_translation at m_added 0 and speed -1;
  acceleration_reaction_force at m_added 0; virtual_mass and
  added_mass_fraction at m_body 0 and m_added 0.
- Determinism; no imports beyond math; no RNG anywhere.

## Worked example

Two fluids exercise the catalog: the seaplane ditching and water-impact
context at rho = 1000 kg/m^3 (fresh-water nominal) for the 2-D shapes,
the sphere and the oblate housing, and the airship hull in air at
rho_air = 1.225 kg/m^3 for the slender prolate spheroid. All values
below are REAL outputs of the prep anchor /tmp/w44spec/
anchor_addedmass.py (stdlib math, closed form, deterministic, exit 0).

- Surface-integral derivation (R = 1 m, rho = 1000, U = 2 m/s): the
  translating-circle dipole potential gives T = 6283.185307 J/m from
  the kinetic-energy surface integral, equal to (1/2)*m_a*U^2 with
  m_a = rho*pi*R^2 = 3141.592654 kg/m (residual 1.546e-11 J/m); the
  translating-sphere doublet gives T = 4188.790205 J with m_a =
  (2/3)*rho*pi*R^3 = 2094.395102 kg (residual 1.819e-12 J). The catalog
  coefficients ARE the integrated kinetic-energy result.
- 2-D catalog per unit span, rho = 1000 kg/m^3:
  - circular float cylinder R = 0.5 m: 785.398163 kg/m.
  - ditching flat plate of half-width a = 0.75 m (1.5 m wide): normal
    1767.145868 kg/m, tangential 0.000000 kg/m exactly.
  - elliptic float section a = 1.0 m, b = 0.5 m: m_along_a =
    785.398163 kg/m (motion along the LONG semi-axis couples to the
    short semi-axis b) and m_along_b = 3141.592654 kg/m; the circle
    limit a = b = 0.5 m returns 785.398163 kg/m both ways, difference
    from the cylinder 0.000e+00.
- 3-D catalog:
  - sphere R = 0.5 m, rho = 1000: 261.799388 kg, exactly half the
    displaced mass (ratio 1.000000000).
  - oblate underwater housing a = 1.0 m, c = 0.35 m, rho = 1000:
    displaced fluid mass 1466.076572 kg; polar m_a = 2422.924052 kg
    with k = 1.652659 ABOVE unity (the flat dome carries more fluid
    inertia than the mass of the fluid it displaces) and equatorial
    m_a = 340.526959 kg with k = 0.232271.
  - airship hull as a prolate spheroid a = 35 m, b = 7 m (70 m hull,
    14 m diameter) in air rho = 1.225: displaced air mass 8800.124621
    kg; axial m_a = 520.273672 kg (k = 0.059121) and transverse m_a =
    7869.604193 kg (k = 0.894261). The axial fluid inertia is under 6%
    of the displaced air mass, which is why a conventional aircraft
    flying in air can neglect it, and the airship, whose hull is 15.3
    times the slender ratio of a sphere in the transverse sense, cannot.
- Energy and reaction relations (rho = 1000, sphere R = 0.5 m, m_a =
  261.799388 kg):
  - fluid kinetic energy at U = 4 m/s: 2094.395102 J.
  - acceleration reaction to sustain 4 m/s^2: 1047.197551 N.
  - virtual mass of the sphere on a 200 kg body: 461.799388 kg;
    added-mass fraction 0.566912 (the fluid inertia is the larger half
    of the virtual mass in water).
  - airship hull with a 6000 kg structure: axial virtual mass
    6520.273672 kg, axial added-mass fraction 0.079793; the axial
    acceleration reaction at 0.2 m/s^2 is 104.054734 N versus a
    transverse 1573.920839 N at the same acceleration, a 15.1 times
    gap that any airship pitch/heave inertia model must carry.
- Read-off: for the flat plate the normal coefficient 1767.145868 kg/m
  at rho = 1000 is the per-unit-span inertia the ditching impact load
  sees, while the tangential 0.0 confirms the plate slides without
  disturbing the flow; for the oblate housing k_polar = 1.652659 shows
  that flattening a body toward a disk RAISES its polar coefficient
  toward the (8/3)*rho*a^3 thin-disk asymptote (anchor 0.999970 of it
  at c/a = 1e-4) while the equatorial coefficient collapses to 0; for
  the airship the axial/transverse k pair 0.059121/0.894261 brackets
  the sphere's 0.5 exactly as the slender-body limits predict (the
  a/b = 10 anchor pair is 0.020706/0.960235).
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w44spec/anchor_addedmass.py
(stdlib math, closed form, deterministic, exit 0).

## Validation list (contract test must include)

- kinetic_energy_of_translation(261.799388, 4) = 2094.395102 within
  1e-3; at speed 0 returns 0.0; m_added 0 and speed -1 raise.
- acceleration_reaction_force(261.799388, 4) = 1047.197551 within 1e-3;
  m_added 0 raises. virtual_mass(200, 261.799388) = 461.799388 within
  1e-3; added_mass_fraction(261.799388, 200) = 0.566912 within 1e-5.
- cylinder_added_mass(1000, 0.5) = 785.398163 within 1e-3;
  cylinder_added_mass(1000, 1) = 3141.592654 within 1e-3.
- flat_plate_added_masses(1000, 0.75) = (1767.145868, 0.0) within 1e-3
  with the tangential entry EXACTLY 0.0.
- elliptic_cylinder_added_masses(1000, 1.0, 0.5): m_along_a =
  785.398163 within 1e-3 and m_along_b = 3141.592654 within 1e-3;
  elliptic_cylinder_added_masses(1000, 0.5, 0.5) equals the cylinder
  value on both entries within 1e-9.
- sphere_added_mass(1000, 0.5) = 261.799388 within 1e-3; the ratio to
  half the displaced mass is 1.0 within 1e-9.
- prolate_spheroid_added_masses(1.225, 35, 7): axial = 520.273672
  within 1e-2 and transverse = 7869.604193 within 1e-2; the k ratios
  are 0.059121 and 0.894261 within 1e-5 each; at a/b = 10 the k pair is
  0.020706 and 0.960235 within 1e-5.
- prolate_spheroid_added_masses(1000, 0.5, 0.5) and
  oblate_spheroid_added_masses(1000, 0.5, 0.5) each equal
  sphere_added_mass(1000, 0.5) on both entries within 1e-9.
- oblate_spheroid_added_masses(1000, 1.0, 0.35): polar = 2422.924052
  within 1e-2 and equatorial = 340.526959 within 1e-2; k_polar =
  1.652659 within 1e-5 (above 1) and k_equatorial = 0.232271 within
  1e-5; at c/a = 1e-4 the polar result is (8/3)*1000*1.0 within 1e-2
  (the 0.999970 ratio anchor).
- Closed-form spheroid coefficients against the Lamb integrals: at
  aspect ratios 2, 5 and 10 the closed-form alpha0/beta0/gamma0 values
  match the independent quadrature rows below within 1e-9, and
  alpha0 + 2*beta0 = 2 and gamma0 + 2*alpha0 = 2 within 1e-9:
  prolate a/b = 2: alpha0 0.347127995, beta0 0.826436002; a/b = 5:
  alpha0 0.111641940, beta0 0.944179030; a/b = 10: alpha0 0.040571761,
  beta0 0.979714120. Oblate a/c = 2: gamma0 1.054400565, alpha0
  0.472799717; a/c = 5: gamma0 1.500967825, alpha0 0.249516088;
  a/c = 10: gamma0 1.721608553, alpha0 0.139195723.
- Sphere-limit continuity: alpha0(prolate, a/b = 1 + 1e-6) =
  0.666666133 and gamma0(oblate, a/c = 1 + 1e-6) = 0.666667200, each
  within 1e-5 of 2/3; gamma0 at c/a = 1e-4 is 1.999685881, within 1e-3
  of 2.
- ValueErrors: rho 0 and negative rho on every shape function; R 0
  (cylinder, sphere); a 0 (plate); b 0 and b > a (prolate, elliptic
  cylinder at b 0); c 0 and c > a (oblate); m_added 0
  (kinetic_energy_of_translation, acceleration_reaction_force,
  virtual_mass, added_mass_fraction); m_body 0; speed -1.
- Determinism; no imports beyond math; no RNG.

## Corpus fragment (eval/hit1-wave44-added-mass-coefficients-potential-flow.yaml)

Query 1 (copy verbatim):
  "determine the added-mass-coefficients-potential-flow virtual mass of
  a body accelerating through an inviscid irrotational fluid from the
  kinetic energy of the irrotational flow it sets up: the 2-D circular
  cylinder and normal flat plate coefficients per unit span, the 3-D
  sphere coefficient, and the airship hull spheroid coefficients"
  intent: "aerodynamics; added mass coefficients (virtual mass, apparent
  mass) of bodies accelerating through an inviscid irrotational fluid,
  from the kinetic energy T = (1/2)*rho*integral(phi*dphi/dn dS) of the
  irrotational flow: 2-D circular cylinder rho*pi*R^2 and normal flat
  plate rho*pi*a^2 per unit span, 3-D sphere (2/3)*rho*pi*R^3, and the
  prolate and oblate spheroid catalog with the displaced-mass ratios"
  expected_skill: "aerodynamics/aeroelasticity/added-mass-coefficients-
  potential-flow"
Query 2 (copy verbatim):
  "compute the acceleration-reaction force and the fluid kinetic energy
  at a translation speed from the added mass of a ditching float
  cylinder, a slamming plate, and a sphere, and the apparent-mass share
  of the virtual mass against the body mass"
  intent: "aerodynamics; acceleration-reaction force m_a*acceleration
  and fluid kinetic energy (1/2)*m_a*U^2 from the potential-flow added
  mass catalog of a circular float, a normal flat plate and a sphere,
  with the virtual mass and the added-mass fraction against a body
  mass"
  expected_skill: "aerodynamics/aeroelasticity/added-mass-coefficients-
  potential-flow"
Task ids: w44-added-mass-coefficients-potential-flow-1 and -2. Prep
grep (run at spec time): each of the tokens added-mass-coefficients,
virtual-mass, apparent-mass and acceleration-reaction returns 0 matches
in eval/hit1-corpus.yaml and in every eval/*.yaml fragment (grep -c 0,
grep -l empty), and "added-mass|virtual-mass|apparent-mass" appears in
the skills tree only inside the two unsteady-aero sibling notes quoted
in the claim fences above (the gust-response documented-assumption
exclusion and the flutter-speed-prediction E(k) comment), so the
queries above are collision-free; the sibling aeroelasticity tasks
route on the V-g flutter sweep and the C(k) machinery
(flutter-speed-prediction), the Wagner/Kussner indicial gust-response
time histories (aeroelastic-gust-response) and the static divergence
speed (divergence-speed), none of which carry added-mass-coefficients,
virtual-mass, apparent-mass or acceleration-reaction content, and the
steady panel potential-flow rows of panel-method route on doublet and
source panel wording, not on the accelerating-body kinetic-energy
catalog.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine the added-mass-
coefficients-potential-flow virtual mass (apparent mass) of a body
accelerating through an inviscid irrotational fluid from the kinetic
energy of the irrotational flow it sets up:" and include the outputs in
the Claim. First tag: added-mass-coefficients-potential-flow.
Additional tags ONLY: virtual-mass, apparent-mass,
acceleration-reaction-force, kinetic-energy-catalog,
displaced-fluid-inertia. NEVER single generic words (mass, flow,
potential, fluid, inertia, energy, body, cylinder, sphere, plate,
ellipsoid, spheroid, coefficient, catalog, acceleration) and NEVER
potential-flow alone (the tag belongs to panel-method) nor any sibling
token below. 50-150 words, <=1024 chars, no em dash, no content-policy
sweep term (the banned word from the builder kit), action verb present.
Recommended wording (outputs in Claim order, 959 chars, 143 words,
verified by count):
"Use when you must determine the added-mass-coefficients-potential-flow
virtual mass (apparent mass) of a body accelerating through an inviscid
irrotational fluid from the kinetic energy of the irrotational flow it
sets up: the 2-D circular cylinder rho pi R^2 and normal flat plate rho
pi a^2 per unit span, the 3-D sphere two-thirds rho pi R^3, the
elliptic cylinder and the prolate and oblate spheroid coefficients,
plus the kinetic-energy and acceleration-reaction relations. Produces
the added mass of the requested shape, its ratio to the displaced fluid
mass, the fluid kinetic energy at a translation speed, the virtual mass
with the body mass, and the acceleration-reaction force for the fluid
inertia of unsteady motion. Trigger: added mass coefficients, virtual
mass, apparent mass, acceleration reaction force, kinetic energy of
irrotational flow, body accelerating in fluid, airship hull added mass,
ditching float added mass, spheroid added mass."

FORBIDDEN TOKENS (belong to siblings): theodorsen, wagner, kussner,
sears, indicial, lag-state, gust-response, gust time history, dynamic-
magnification-factor, one-minus-cosine-gust (aeroelastic-gust-response);
c-k-deficiency-function, v-g-method, flutter-speed, frequency-
coalescence, flutter-margin, reduced-frequency sweep, theodorsen loads
(flutter-speed-prediction); divergence-speed, divergence-dynamic-
pressure (divergence-speed); doublet-panel, source-panel, vortex-panel,
kutta-condition, panel pressure distribution, steady potential flow
solver (panel-method, tag potential-flow); discrete-gust load factor
(gust-maneuver-loads, structures). The words theodorsen, wagner,
kussner and noncirculatory appear in this spec ONLY inside the verbatim
sibling-fence quotes of the claim section; they never appear in the
description, the tags, or the corpus queries of this leaf.
