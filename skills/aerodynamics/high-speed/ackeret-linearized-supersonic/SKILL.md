---
name: ackeret-linearized-supersonic
description: "Use when you must compute the section coefficients of a thin airfoil at supersonic speed by ackeret linearized supersonic theory: evaluate the ackeret parameter sqrt(M^2 - 1), the surface pressure coefficient Cp = 2*theta/sqrt(M^2 - 1) for a deflection theta, the section lift cl = 4*alpha/sqrt(M^2 - 1), the supersonic lift curve slope, and the wave drag of the flat plate, the thin biconvex circular-arc section and a cambered thin plate from the linearized pressure integral over the surface slopes, with the leading edge moment coefficient cm_le. Produces the ackeret Cp, cl, cd_wave and cm_le values that gate thin supersonic airfoil wave drag estimates, section design cross-checks and gas dynamics coursework. Trigger: ackeret theory, linearized supersonic flow, linear supersonic thin airfoil, biconvex wave drag, supersonic lift curve slope."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [ackeret-linearized-supersonic, ackeret-theory, linear-supersonic-thin-airfoil, supersonic-lift-curve-slope, biconvex-section, cambered-plate-supersonic]
  version: 0.1.0
  author: AeroSkills
---

# Ackeret Linearized Supersonic (aerodynamics/high-speed/ackeret-linearized-supersonic)

Use when you must compute the section coefficients of a thin airfoil at
supersonic Mach by ackeret linearized supersonic theory (Liepmann and
Roshko ch. 10, Anderson sec. 9): the ackeret parameter, the linearized
surface pressure law, and the section lift, wave drag and leading edge
moment of the flat plate, the thin biconvex circular-arc section and a
cambered thin plate. The leaf integrates the linearized pressure
coefficient over the surface slopes by deterministic Simpson quadrature
and exposes the closed forms of the canonical thin sections, in pure
stdlib Python. It pairs with the exact-march sibling
aerodynamics/high-speed/shock-expansion-airfoil, whose diamond
double-wedge march is the exact answer this leaf's linear values
cross-check within 10%, and with the area-Mach duct relations of
aerodynamics/high-speed/isentropic-flow-relations.

## Domain quick reference

- Ackeret parameter: beta = sqrt(M^2 - 1), the divisor of every linear
  supersonic coefficient. beta -> 0 as M -> 1 (the coefficients
  diverge, hence the M <= 1 guard) and beta -> M at large M. All angles
  are RADIANS; positive alpha means the freestream sits above the
  chord, so the lower surface is windward.
- Linearized surface pressure law: on a surface deflected by theta from
  the freestream (theta positive compresses, Cp positive windward),
  Cp = +-2*theta/beta. Upper surface cp_u = 2*(phi_u - alpha)/beta,
  lower surface cp_l = 2*(alpha - phi_l)/beta, with phi = dy/dx the
  surface slope relative to the chord.
- Section lift: cl = (1/c) int_0^c (cp_l - cp_u) dx = 4*alpha/beta for
  every thin CLOSED section: thickness and camber integrate out
  (integral (phi_u + phi_l) dx = 0 around a closed section). Lift-curve
  slope cl_alpha = 4/beta per radian.
- Leading edge moment (nose-up positive): cm_le = -(1/c^2) int_0^c x
  (cp_l - cp_u) dx = -2*alpha/beta - (2/(beta c^2)) int (y_u + y_l) dx.
  Flat and symmetric sections sit at cm_le = -2*alpha/beta with the
  center of pressure at mid-chord, x_cp/c = 0.5 (the supersonic
  linear-theory position, versus quarter-chord subsonically).
- Wave drag by the linearized pressure resolution (drag direction at
  +alpha to the chord): cd = alpha*cl + (2/(beta c)) int_0^c [phi_u^2 +
  phi_l^2 - alpha*(phi_u + phi_l)] dx.
- Closed forms (xhat = x/c): flat plate cd = 4*alpha^2/beta; biconvex
  parabolic-arc of thickness ratio tau, phi_u = 2*tau*(1 - 2*xhat),
  cd = (4*alpha^2 + (16/3) tau^2)/beta; circular-arc cambered plate of
  camber ratio h/c, phi = 4*(h/c)*(1 - 2*xhat), cd = (4*alpha^2 +
  (64/3) (h/c)^2)/beta and cm_le = -2*alpha/beta - (8/3)(h/c)/beta.
- Pressure reconstruction (the only gamma-dependent relation): p/p_inf
  = 1 + (gamma/2) M^2 Cp, gamma default 1.4.
- NACA TR-824 frames the thin-section supersonic aerodynamics context;
  the relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the supersonic flight condition: freestream Mach M > 1 and angle
   of attack alpha in radians. Traverse the ackeret parameter with
   ackeret_parameter(mach) to confirm beta = sqrt(M^2 - 1) and that the
   regime is linear supersonic, not M = 1 or below.
2. Evaluate the ackeret surface pressure law with cp_linear(theta_rad,
   mach) for each local surface deflection theta, and reconstruct the
   surface pressure with surface_pressure_ratio(cp, mach, gamma) when
   p/p_inf is needed.
3. Compute the section lift with lift_coefficient(alpha_rad, mach) and
   the supersonic lift curve slope with lift_curve_slope(mach): cl =
   4*alpha/beta holds for every thin closed section, independent of
   thickness and camber.
4. Take the flat plate reference set with flat_plate(alpha_rad, mach):
   cl, cd_wave = 4*alpha^2/beta, cm_le and the mid-chord center of
   pressure x_cp_over_c = 0.5.
5. Size the wave drag and moment of the closed thin sections with
   biconvex_section(alpha_rad, thickness_ratio, mach) and
   cambered_plate(alpha_rad, camber_ratio, mach), using the additive
   thickness and camber drags on the flat-plate alpha drag.
6. Integrate a general thin section with section_coefficients(alpha_rad,
   mach, slope_upper, slope_lower, chord, panels): pass the surface
   slope callables phi_u(x) and phi_l(x) over the chord and read cl,
   cd_wave and cm_le from the linearized pressure integral over the
   surface slopes by deterministic composite Simpson quadrature
   (SIMPSON_PANELS = 2000 even panels, identical inputs give identical
   bits). Closed-form agreement with the three canonical families is an
   identity of the engine.
7. Cross-check the linear values against the exact shock-expansion march
   result of the sibling leaf (cl ratio ~1.015 at M = 2, 3 deg, the
   sibling's quoted 1.5% handover) and close with the deterministic
   contract test scripts/test_ackeret_linearized_supersonic.py.

## Worked example

Representative point: M = 2.0, alpha = 3 deg = 0.052359877560 rad, with
the biconvex tau = 0.06 (6% thick) and the cambered plate h/c = 0.02
(2% circular-arc camber), gamma = 1.4 where used. All values are real
module outputs.

- Ackeret parameter and pressure law: beta(2.0) = 1.732050807569. A
  surface deflection of theta = +0.05 rad (2.865 deg, compression)
  carries Cp = 0.057735026919, the mirror deflection Cp =
  -0.057735026919. The flat plate's windward lower surface at alpha =
  3 deg: cp_l = 2*alpha/beta = 0.060459978808, so p/p_inf = 1 +
  0.5*gamma*M^2*cp = 1.169287940662 on the lower surface and
  0.830712059338 on the suction upper surface.
- Lift and slope: cl = 4*alpha/beta = 0.120919957616 for the flat
  plate, the biconvex and the cambered plate alike (thickness and
  camber drop out of the lift integral); the supersonic lift-curve
  slope is 4/beta = 2.309401076759 per radian at M = 2.
- Wave drag: flat plate cd_wave = 4*alpha^2/beta = 0.006331354175.
  Biconvex tau = 0.06: zero-lift part (16/3) tau^2/beta =
  0.011085125168, total cd_wave = 0.017416479344 at alpha = 3 deg (the
  additive thickness drag, 2.75 times the flat plate's alpha drag); at
  M = 3, alpha = 0 it falls to 0.006788225099, the M^-2 fall. Cambered
  plate h/c = 0.02: zero-lift part (64/3)(h/c)^2/beta =
  0.004926722297, total cd_wave = 0.011258076472.
- Moments: cm_le = -2*alpha/beta = -0.060459978808 (nose-up positive)
  for the flat plate and the symmetric biconvex, with the center of
  pressure at mid-chord, x_cp_over_c = 0.500000000000. The cambered
  plate adds the nose-down couple (8/3)(h/c)/beta = 0.030792014357,
  giving cm_le = -0.091251993165: camber produces no lift in the linear
  theory but pitches the section nose-down.
- Engine identity: section_coefficients over the slope callables of the
  three families reproduces every closed form above with residuals
  below 4.1e-15 at the worked point (the engine and the closed forms
  are one theory).
- Sibling cross-check: the exact-march diamond of eps = 5 deg (10 deg
  included angle, thickness ratio tau = tan(5 deg) = 0.087488663526) at
  M = 2 has linear zero-lift cd_wave = 4*tau^2/beta = 0.017676770709,
  matching the shock-expansion-airfoil worked-example cd_wave = 0.0177
  inside 0.2%, and cl(exact)/cl(linear) = 1.014720832024 at alpha =
  3 deg, the sibling's quoted 1.5% above handover.

## Verification

- Confirm ackeret_parameter(2.0) = 1.732050807569, beta(1.5) =
  1.118033988750, beta(3.0) = 2.828427124746, beta(sqrt(2)) = 1.0.
- Confirm cp_linear(0.05, 2.0) = 0.057735026919 with the exact
  antisymmetry cp(-theta) = -cp(theta), and lift_coefficient(3 deg, 2.0)
  = 0.120919957616 with the lift-curve slope 2.309401076759 per radian.
- Confirm flat_plate(3 deg, 2.0) returns cl = 0.120919957616, cd_wave =
  0.006331354175, cm_le = -0.060459978808 and x_cp_over_c = 0.5, and
  that cd_wave = alpha*cl at linear order.
- Confirm biconvex_section(3 deg, 0.06, 2.0) cd_wave = 0.017416479344 =
  0.006331354175 + 0.011085125168 (drag additive) and cambered_plate
  cm_le = -0.091251993165 = -0.060459978808 - 0.030792014357 (camber
  couple).
- Confirm section_coefficients reproduces every closed form within 1e-9
  and that cl is identical across the flat plate, biconvex and cambered
  plate within 1e-12 (thickness and camber independence).
- Confirm every mach <= 1.0 (1.0, 0.9, -2.0, non-finite), thickness or
  camber ratio <= 0.0, chord <= 0.0, odd or sub-2 panel count, and
  gamma <= 1.0 raises ValueError.
- Run the deterministic contract test offline: python3
  scripts/test_ackeret_linearized_supersonic.py (35 tests, exit 0,
  under 20 s; also passes under the pyenv 3.13.12 hook interpreter).

## Related leaves

- aerodynamics/high-speed/shock-expansion-airfoil: the exact
  shock-expansion march over the diamond double-wedge section; this
  leaf's linear values are its 10% cross-check.
- aerodynamics/high-speed/isentropic-flow-relations: area-Mach
  relations and total-to-static ratios of the same supersonic flow
  regime, no surface pressure law.
- aerodynamics/high-speed/hypersonic-piston-theory: the M >> 1 surface
  pressure law of unsteady hypersonic surfaces, beyond the moderate
  supersonic regime of this leaf.
- aerodynamics/airfoil/thin-airfoil-section-theory: the subsonic Glauert
  camber-line theory of the M ~ 0 regime, the incompressible cousin.

## Pitfalls

- Applying the linear values where the exact march is required: the
  ackeret coefficients are the first-order answer; at M = 2, alpha =
  3 deg the exact shock-expansion march cl sits 1.47% above the linear
  value (ratio 1.014720832024) and the wave drag differs by the same
  order, so quote the linear set as the cross-check the
  shock-expansion-airfoil sibling assigns it, not as the exact result.
- Using degrees in the ackeret formulas: cl = 4*alpha/beta is a radian
  identity, so alpha = 3 deg must enter as 0.052359877560 rad; feeding
  3.0 directly returns a cl 57 times too large.
- Running the module at M <= 1: beta -> 0 as M -> 1 and every linear
  coefficient diverges, so the module raises ValueError at M <= 1; the
  transonic-similarity leaf owns the near-Mach-1 regime the ackeret
  formulas diverge away from.
- Expecting camber to add lift: in the linear theory the camber terms
  integrate out of the closed-section lift integral, so the cambered
  plate carries the same cl as the flat plate; camber shows up only in
  the nose-down moment couple and the camber drag.
- Summing thickness drag by hand with the wrong slope law: the biconvex
  parabolic-arc slopes run from +2*tau at the leading edge to -2*tau at
  the trailing edge, and only that law gives the (16/3) tau^2/beta
  zero-lift drag; a wedge or double-wedge section instead carries
  4*tau^2/beta (see the sibling diamond cross-check).
- Treating the engine callables as values: section_coefficients takes
  slope callables phi_u(x) and phi_l(x), not fixed slope numbers; the
  upper slope carries the negative-lift suction side and must be passed
  with its own sign.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ackeret_linearized_supersonic.py

The test covers the ackeret parameter table and its M <= 1 rejections,
the linearized surface pressure law table with exact antisymmetry and
the p/p_inf reconstruction with the gamma default, the section lift
coefficient and the supersonic lift curve slope, the flat plate
reference set with its mid-chord center of pressure, the biconvex
section with additive thickness drag and its M^-2 Mach fall, the
cambered plate with the nose-down couple split, the shape independence
of cl across the three canonical families, the section_coefficients
Simpson engine identities against every closed form, engine zero-lift
and determinism checks, the sibling diamond cross-validation, and
ValueError rejection of non-physical mach, thickness, camber, chord,
panel count and gamma inputs.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 frames the thin
  airfoil supersonic aerodynamics context; the ackeret relations above
  are standard engineering methodology (Liepmann and Roshko, Anderson),
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
