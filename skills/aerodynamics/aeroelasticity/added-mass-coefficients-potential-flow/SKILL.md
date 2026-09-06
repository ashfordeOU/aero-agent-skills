---
name: added-mass-coefficients-potential-flow
description: "Use when you must determine the added-mass-coefficients-potential-flow virtual mass (apparent mass) of a body accelerating through an inviscid irrotational fluid from the kinetic energy of the irrotational flow it sets up: the 2-D circular cylinder rho pi R^2 and normal flat plate rho pi a^2 per unit span, the 3-D sphere two-thirds rho pi R^3, the elliptic cylinder and the prolate and oblate spheroid coefficients, plus the kinetic-energy and acceleration-reaction relations. Produces the added mass of the requested shape, its ratio to the displaced fluid mass, the fluid kinetic energy at a translation speed, the virtual mass with the body mass, and the acceleration-reaction force for the fluid inertia of unsteady motion. Trigger: added mass coefficients, virtual mass, apparent mass, acceleration reaction force, kinetic energy of irrotational flow, body accelerating in fluid, airship hull added mass, ditching float added mass, spheroid added mass."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aeroelasticity
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: aeroelasticity
  tags: [added-mass-coefficients-potential-flow, virtual-mass, apparent-mass, acceleration-reaction-force, kinetic-energy-catalog, displaced-fluid-inertia]
  version: 0.1.0
  author: AeroSkills
---

# Added Mass Coefficients, Potential Flow
(aerodynamics/aeroelasticity/added-mass-coefficients-potential-flow)

Use when you must determine the added mass coefficient (virtual mass,
apparent mass) of a body accelerating rectilinearly through an inviscid
irrotational fluid, from the kinetic energy of the irrotational flow the
body sets up.  An accelerating body must drag a surrounding mass of fluid
with it, and that fluid inertia is a real load: the catalog below gives
the coefficient m_a per shape from T = (1/2)*rho*oint_S phi*(dphi/dn)
dS (Lamb Hydrodynamics Art. 136 form, normal derivative positive into
the body), which for translation at speed U equals (1/2)*m_a*U^2.  This
leaf is the fluid-inertia counterpart of the unsteady siblings of this
pack: aeroelastic-gust-response and flutter-speed-prediction both
document neglecting apparent-mass terms at their level, and the
coefficient an accelerating body carries is exactly the content they
disclaim.  Method provenance is the classical literature (Lamb,
Hydrodynamics, Art. 136 kinetic-energy integrals and Art. 114 ellipsoid
coefficients; Brennen, "A Review of Added Mass and Fluid Inertial
Forces"), cited by name only, with NACA Report 824 as reference-only
context for the thin-airfoil potential-flow methodology this catalog
complements.

## Domain quick reference

- Kinetic-energy definition: for a body translating at speed U along a
  principal direction, T = (1/2)*rho*oint_S phi*(dphi/dn) dS = (1/2)*m_a
  *U^2 fixes the added mass m_a of the shape.  The anchor evaluates the
  integral on the exact dipole potentials of the moving circle and
  sphere and recovers the catalog coefficients below.
- Displaced fluid mass and coefficient ratio: M_disp = (4/3)*rho*pi*a*b*c
  for an ellipsoid of semi-axes a, b, c; k = m_a/M_disp.  Sphere k = 1/2
  exactly; flat bodies can exceed unity (an oblate disk at rest in its
  plane carries zero, but pushed edge-on it drags more than its own
  displaced mass).
- 2-D catalog per unit span (kg/m): circular cylinder rho*pi*R^2 (any
  in-plane direction); normal flat plate of half-width a (rho*pi*a^2
  normal, EXACTLY 0.0 tangential); elliptic cylinder x^2/a^2 + y^2/b^2 =
  1 with rho*pi*b^2 along a and rho*pi*a^2 along b (motion along one
  semi-axis couples to the other squared), containing the circle and
  plate limits.
- 3-D catalog (kg): sphere (2/3)*rho*pi*R^3, exactly half its displaced
  mass; prolate and oblate spheroids via the elementary reduction of the
  Lamb ellipsoid coefficients alpha0, beta0, gamma0 (which sum to 2),
  with the translation added mass along a principal semi-axis equal to
  M_disp*alpha/(2 - alpha) for the coefficient alpha of that axis.
- Prolate spheroid (axial a >= equatorial b = c), e = sqrt(1 - (b/a)^2):
  alpha0 = 2*(1 - e^2)/e^3*(0.5*ln((1+e)/(1-e)) - e), beta0 = gamma0 = 1
  - alpha0/2.  Axial m_a = M_disp*alpha0/(2 - alpha0), transverse m_a =
  M_disp*beta0/(2 - beta0).  Limits: sphere e = 0 gives 2/3 and k = 1/2;
  a needle e -> 1 gives axial k -> 0, transverse k -> 1.
- Oblate spheroid (equatorial a = b >= polar c), e = sqrt(1 - (c/a)^2):
  gamma0 = 2*(e - (c/a)*asin(e))/e^3, alpha0 = beta0 = 1 - gamma0/2.
  Polar m_a = M_disp*gamma0/(2 - gamma0), equatorial m_a = M_disp*alpha0/
  (2 - alpha0).  Limits: sphere e = 0 gives 2/3; a thin disk c -> 0 gives
  gamma0 -> 2 and polar m_a -> the finite classical (8/3)*rho*a^3 while
  the equatorial coefficient vanishes.
- Energy and reaction relations at a translation speed U and an
  acceleration: fluid kinetic energy T = (1/2)*m_a*U^2 (kinetic energy
  of translation); acceleration-reaction force F = m_a*acceleration the
  body must supply, with the opposing reaction on the body its negative;
  virtual mass m_body + m_a; added-mass fraction m_a/(m_body + m_a).
  Simultaneous orthogonal translation components superpose in the
  kinetic energy T = (1/2)*sum(m_i*U_i^2).
- Units are SI: rho in kg/m^3, lengths in m, speeds in m/s,
  accelerations in m/s^2; 2-D results per unit span in kg/m, 3-D results
  in kg.  Motion is rectilinear along a principal direction; the flow is
  fully attached and irrotational by construction.

## Workflow

1. Fix the translation problem: the shape, the principal direction of
   motion (which semi-axis), the fluid density rho, the translation
   speed U and the acceleration, and the body mass m_body for the
   inertia model.  Note whether the result must be per unit span (2-D
   section) or total (3-D body).
2. Catalog coefficient lookup: select the catalog function of the shape
   (cylinder_added_mass, flat_plate_added_masses,
   elliptic_cylinder_added_masses, sphere_added_mass,
   prolate_spheroid_added_masses or oblate_spheroid_added_masses), call
   it at (rho, dimensions), and report m_a plus the ratio k = m_a/M_disp
   against the displaced fluid mass (4/3)*rho*pi*a*b*c of the shape.
   The sphere branches a = b and a = c are handled exactly with no
   division by the eccentricity.
3. Energy picture: close the energy balance with
   kinetic_energy_of_translation(m_a, speed), the fluid kinetic energy
   (1/2)*m_a*U^2 the translation speed carries; compare it against the
   work the launch or impact must supply.
4. Inertia model: build the effective mass of the accelerating body with
   virtual_mass(m_body, m_added) and added_mass_fraction(m_added,
   m_body); in water the fluid share is typically the larger half.
5. Acceleration-reaction check: size the reaction the body must supply
   with acceleration_reaction_force(m_added, acceleration), whose
   Newton third-law partner on the body opposes the acceleration.
6. Deterministic offline check: confirm the catalog values, the anchors
   and the ValueError rejections with the contract test
   scripts/test_added_mass_coefficients_potential_flow.py.

## Worked example

Two fluids exercise the catalog: water at rho = 1000 kg/m^3 (fresh-water
nominal, the seaplane ditching and underwater housing context) and air
at rho_air = 1.225 kg/m^3 (the airship hull).  All values are the real
outputs of the module.

- Surface-integral derivation (R = 1 m, rho = 1000, U = 2 m/s): the
  translating-circle dipole potential gives T = 6283.185307 J/m from the
  kinetic-energy surface integral, equal to (1/2)*m_a*U^2 with m_a =
  rho*pi*R^2 = 3141.592654 kg/m; the translating-sphere doublet gives T
  = 4188.790205 J with m_a = (2/3)*rho*pi*R^3 = 2094.395102 kg.  The
  catalog coefficients ARE the integrated kinetic-energy result.
- 2-D catalog per unit span, rho = 1000 kg/m^3: circular float cylinder
  R = 0.5 m, 785.398163 kg/m; ditching flat plate of half-width a = 0.75
  m (1.5 m wide), normal 1767.145868 kg/m and tangential 0.000000 kg/m
  exactly; elliptic float section a = 1.0 m, b = 0.5 m, m_along_a =
  785.398163 kg/m and m_along_b = 3141.592654 kg/m; the circle limit a =
  b = 0.5 m returns 785.398163 kg/m both ways, difference from the
  cylinder 0.000e+00.
- 3-D catalog: sphere R = 0.5 m, rho = 1000, 261.799388 kg, exactly
  half the displaced mass (ratio 1.000000000).  Oblate underwater
  housing a = 1.0 m, c = 0.35 m: displaced fluid mass 1466.076572 kg;
  polar m_a = 2422.924052 kg with k = 1.652659 ABOVE unity (the flat
  dome carries more fluid inertia than the mass of the fluid it
  displaces) and equatorial m_a = 340.526959 kg with k = 0.232271.
  Airship hull as a prolate spheroid a = 35 m, b = 7 m (70 m hull, 14 m
  diameter) in air: displaced air mass 8800.124621 kg; axial m_a =
  520.273672 kg (k = 0.059121, under 6 percent of the displaced air
  mass, why a conventional aircraft can neglect it) and transverse m_a =
  7869.604193 kg (k = 0.894261, which a 15.3-times-slender-than-a-sphere
  hull cannot neglect).
- Energy and reaction relations (rho = 1000, sphere R = 0.5 m, m_a =
  261.799388 kg): fluid kinetic energy at U = 4 m/s, 2094.395102 J;
  acceleration reaction to sustain 4 m/s^2, 1047.197551 N; virtual mass
  on a 200 kg body, 461.799388 kg with added-mass fraction 0.566912 (the
  fluid inertia is the larger half of the virtual mass in water).  The
  airship hull on a 6000 kg structure has an axial virtual mass of
  6520.273672 kg and an axial added-mass fraction of 0.079793; the axial
  acceleration reaction at 0.2 m/s^2 is 104.054734 N versus a transverse
  1573.920839 N, a 15.1 times gap any pitch or heave inertia model must
  carry.
- Read-off: the plate normal coefficient 1767.145868 kg/m is the
  per-unit-span inertia the ditching impact load sees while the
  tangential 0.0 confirms the plate slides without disturbing the flow;
  k_polar = 1.652659 of the oblate housing shows flattening toward a
  disk RAISES the polar coefficient toward the (8/3)*rho*a^3 thin-disk
  asymptote (the module reproduces 0.999970 of it at c/a = 1e-4) while
  the equatorial coefficient collapses to 0; the airship axial/transverse
  k pair 0.059121/0.894261 brackets the sphere's 0.5 exactly as the
  slender-body limits predict (at a/b = 10 the pair is 0.020706/0.960235).

## Verification

- Confirm the catalog entries of the worked example: the module returns
  cylinder 785.398163 kg/m at R = 0.5 m, plate (1767.145868, 0.0) kg/m
  at a = 0.75 m with the tangential entry EXACTLY 0.0, sphere 261.799388
  kg at R = 0.5 m, oblate polar 2422.924052 kg and the airship axial
  520.273672 kg, all within the tolerances asserted in the contract
  test.
- Confirm the sphere branches: prolate_spheroid_added_masses(rho, R, R)
  and oblate_spheroid_added_masses(rho, R, R) equal
  sphere_added_mass(rho, R) on both entries, difference 0.000e+00.
- Confirm the Lamb reductions: the closed-form alpha0/beta0/gamma0 match
  the independently quadrature-pinned rows (prolate a/b = 2, 5, 10:
  alpha0 0.347127995, 0.111641940, 0.040571761; oblate a/c = 2, 5, 10:
  gamma0 1.054400565, 1.500967825, 1.721608553) within 1e-9 and obey
  alpha0 + 2*beta0 = 2 and gamma0 + 2*alpha0 = 2 on every row.
- Confirm the limit branches: alpha0 at a/b = 1 + 1e-6 is 0.666666133
  and gamma0 at a/c = 1 + 1e-6 is 0.666667200, each within 1e-5 of 2/3;
  gamma0 at c/a = 1e-4 is 1.999685881; the slender prolate k pair at
  a/b = 10 is 0.020706/0.960235.
- Confirm every non-physical input raises ValueError: rho 0 and negative
  rho on every shape function; R 0 on the cylinder and sphere; a 0 on
  the flat plate; b 0 on the elliptic cylinder; b 0 and b > a on the
  prolate spheroid; c 0 and c > a on the oblate spheroid; m_added 0 on
  the four scalar relations; m_body 0 on the virtual mass and the
  added-mass fraction; a negative speed on the kinetic energy.
- Confirm determinism: repeat runs reproduce the coefficients exactly;
  the module imports only math and never seeds an RNG.

## Related leaves

- aerodynamics/aeroelasticity/aeroelastic-gust-response: dynamic gust
  response of the flexible typical section with Wagner and Kussner
  lag-state lift; it documents neglecting apparent-mass terms at its
  level, the gap this catalog fills.
- aerodynamics/aeroelasticity/flutter-speed-prediction: the V-g flutter
  sweep with the complex lift-deficiency function, where fluid inertia
  appears only as embedded terms of the oscillatory section loads.
- aerodynamics/aeroelasticity/divergence-speed: the static torsional
  divergence condition, no fluid inertia content.
- aerodynamics/airfoil/thin-airfoil-section-theory: steady thin-airfoil
  section loads, the steady counterpart of the flow this catalog
  integrates.
- aerodynamics/cfd/panel-method: steady 3-D doublet and source panel
  solutions; it holds the tag potential-flow for steady work.
- structures/loads/gust-maneuver-loads: the rigid discrete-gust load
  factor of the certification method; it applies gust velocities, not
  body acceleration inertia.

## Pitfalls

- Importing a steady-flow coefficient for an accelerating body: steady
  panel or airfoil loads carry no kinetic-energy term; the added mass of
  the accelerating body must be added separately, and in water it is
  usually the larger half of the virtual mass (fraction 0.566912 on the
  worked sphere).
- Mixing the displaced fluid mass with the added mass: k = m_a/M_disp is
  1/2 for a sphere but 1.652659 for the worked oblate housing, so
  quoting M_disp as the inertia of a flat body understates the reaction
  by more than 60 percent.
- Assigning a tangential coefficient to a plate: the normal flat plate
  moving in its own plane disturbs no irrotational flow, so its
  tangential coefficient is EXACTLY 0.0.
- Swapping the spheroid axes: the prolate call needs a >= b (axial
  semi-axis first) and the oblate call a >= c; the guards raise
  ValueError on b > a and c > a instead of silently evaluating the wrong
  shape.
- Reaching beyond the catalog: oscillatory thin-airfoil load
  coefficients, the complex C(k) machinery, indicial gust states,
  viscous or compressible or free-surface effects, rotating-body added
  moments and general triaxial ellipsoids (whose Lamb integrals are
  elliptic) are all outside this leaf.
- Reporting per-unit-span values as totals: the 2-D cylinder, plate and
  elliptic cylinder results are in kg/m per unit span, the sphere and
  spheroid results in kg; a 2-D coefficient must be multiplied by the
  span to enter a 3-D inertia model.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_added_mass_coefficients_potential_flow.py

35 tests: the kinetic-energy worked example and the two surface-integral
anchors, the acceleration-reaction worked example and the airship
axial/transverse reaction gap, the virtual mass and added-mass fraction
of the worked sphere and airship, the full 2-D and 3-D catalog entries
with their limits (circle, plate and sphere branches, the thin-disk
asymptote at 0.999970 of (8/3)*rho*a^3, the slender a/b = 10 k pair),
the closed-form Lamb coefficients against the quadrature-pinned rows and
their sum rules, sphere-limit continuity, ValueError rejection of every
non-physical input, and repeat-run determinism.  The test also passes
under the pre-push hook interpreter (~/.pyenv/versions/3.13.12).

## Compliance

- compliance: STANDARDS-REF, gated: false.
- Standards referenced, not reproduced: NACA Report 824 (Summary of
  Airfoil Data, public domain) is reference-only context for the
  thin-airfoil potential-flow methodology this catalog complements; no
  standard text appears anywhere in this leaf.
- Method provenance is the classical literature by name only: Lamb,
  Hydrodynamics, Art. 136 (kinetic-energy surface integrals) and Art.
  114 (ellipsoid coefficients), and Brennen, "A Review of Added Mass and
  Fluid Inertial Forces" (1982) for the engineering catalog class.
