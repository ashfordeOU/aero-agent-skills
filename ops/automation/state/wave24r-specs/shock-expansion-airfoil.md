# Wave-24R leaf spec: shock-expansion-airfoil (aerodynamics)

- Path: skills/aerodynamics/high-speed/shock-expansion-airfoil/
- Pack: high-speed (existing: normal-shock, oblique-shock,
  prandtl-meyer, supercritical-airfoil, swept-wing-aerodynamics,
  transonic-similarity, wave-drag-area-rule)
- Standards ids: naca-tr-824  (Ledger Standard: naca-tr-824)
- Family: aerodynamics

## Claim

Shock-expansion theory applied to a supersonic airfoil: compute the
surface pressure distribution on a diamond (double-wedge) or flat-sided
airfoil at a supersonic Mach number by patching oblique-shock and
Prandtl-Meyer expansion relations over each surface, then integrate the
surface pressures to get the lift coefficient, the wave drag
coefficient, and the moment coefficient about the leading edge. Produces
the sectional CL, CD_wave, Cm_le and the surface pressure table for a
given airfoil half-angle, angle of attack, and Mach number.

Does NOT do: the standalone local relations (oblique-shock and
prandtl-meyer leaves own shock angle / expansion angle computations for
a single turn), transonic/supercritical flow (supercritical-airfoil,
transonic-similarity), three-dimensional swept effects
(swept-wing-aerodynamics), the zero-lift wave drag of a volume
(wave-drag-area-rule). This leaf is the two-dimensional
shock-expansion airfoil pressure integration.

## Model (implement exactly)

Diamond airfoil: semi-wedge angle eps (half-angle of the diamond, deg),
chord c (m, mostly for normalization; results are sectional and
nondimensional), freestream Mach M1, angle of attack alpha (deg).

Geometry of the four surfaces (standard diamond-airfoil
shock-expansion):
- Upper front: flow deflects by (eps - alpha)? document your sign
  convention: the upper surface leading edge turns the flow INTO itself
  by angle theta_uf = eps - alpha (oblique shock if positive, expansion
  if negative). Lower front: theta_lf = eps + alpha (shock for alpha > 0
  conventional). Upper rear: flow turns away by 2*eps (expansion).
  Lower rear: turns away by 2*eps (expansion).
Implement with the general rule: a compression turn uses the oblique
shock relations across theta (weak solution, small deflection), an
expansion turn uses the Prandtl-Meyer relations across theta. Reuse
local implementations inside the leaf (do NOT import other leaf code;
implement theta-beta-M and Prandtl-Meyer internally with module
constants: air gamma = 1.4).
Compute for each surface region the post-turn Mach, pressure ratio, then
pressure coefficient Cp = (p/p_inf - 1) / (0.5*gamma*M1^2).
Surface pressures:
- p_uf, p_ur (upper front/rear), p_lf, p_lr (lower front/rear) after
  each turn in sequence (front surface state is the inlet to the rear
  surface turn).
Integration on the diamond planform (per unit span):
- Normal force: N' = sum over surfaces of p_i * (surface projected
  normal area per unit span) ~ for a diamond with surfaces at +/-eps to
  the chord: the axial and normal force coefficients from the pressure
  acting on each inclined panel:
  Use the standard result (document the geometry): for each panel the
  force coefficient contributions are
  cn_i = Cp_i * (panel length / chord) * cos(panel angle to normal)...
  Simpler robust approach used in textbooks: lift and drag from
  pressures on the four panels with panel angles: for the diamond with
  half-angle eps:
    c_n = (Cp_lf - Cp_uf) * (panel_proj) ... 
  Use the clean method: panel force per unit span
  dF = (p - p_inf) * ds acting normal to the panel; resolve into
  lift/drag with the panel geometric angle. With upper panels at angle
  -eps and lower at +eps to the chord (document):
    L' = integral over x of (p_l - p_u) dx (projected on chord)
    D' = integral (p_l * slope_l + ...) ~ wave drag from the axial
  components: for a diamond, D' = (p_lf - p_uf)*c*tan(eps)?  Implement
  the panel-resolution method precisely and assert the flat-plate
  check below; the method is what the tests verify.
- Section coefficients: cl = L'/(q_inf c), cd_wave = D'/(q_inf c),
  cm_le = moment/(q_inf c^2) (about the leading edge, from panel force
  centers; document nose-up positive or nose-down? state your sign
  convention).
- Small-alpha linear check: for eps = 0 (flat plate at small alpha) the
  shock-expansion result should approach the linear supersonic result
  cl ~ 4*alpha/sqrt(M^2 - 1) for thin airfoils at moderate Mach
  (assert within a few percent at M = 2, alpha = 3 deg, eps small).

Functions:
- theta_beta_m(m1, theta_deg, gamma) -> beta_deg (weak solution; bisect
  the theta-beta-M relation or implement the standard polynomial;
  deterministic; ValueError if theta > theta_max)
- oblique_shock_ratios(m1, theta_deg, gamma) -> (m2, p2_p1)
- prandtl_meyer_angle(m, gamma), prandtl_meyer_turn(m1, theta_deg,
  gamma) -> (m2, p2_p1)
- panel_state(...) turn-by-turn calculator
- surface_pressures(m1, alpha_deg, eps_deg, gamma) -> dict of Cp per
  surface
- shock_expansion_airfoil(m1, alpha_deg, eps_deg, gamma=1.4) ->
  summary dict (cl, cd_wave, cm_le, surface Cp table)
ValueError on: M1 <= 1 (supersonic only; raise for M1 <= 1.0 + 1e-9),
alpha/eps outside physical ranges (|alpha| < 90, 0 <= eps < 45),
non-finite inputs, theta above the max deflection for a shock.

## Worked example

Diamond airfoil eps = 5 deg at M1 = 2.0, alpha = 3 deg, gamma = 1.4.
Run your module for exact anchors, then verify against these ballparks
(textbook Anderson-style results for a 10-deg included-angle diamond at
Mach 2, 3 deg alpha give cl ~ 0.3-0.5 and cd_wave ~ 0.03-0.06; assert
your values lie in these bands and quote them exactly):
- Upper front is an expansion (theta = -2 deg? flow turns away):
  p drops; lower front is a shock (theta = 8 deg): p rises. Verify the
  sign logic: cl > 0 for alpha > 0.
- Flat-plate check: eps = 0.1 deg (thin), M = 2, alpha = 3 deg:
  cl within 5% of 4*alpha_rad/sqrt(M^2-1).
- Symmetry: alpha = 0 on the symmetric diamond gives cl ~ 0 and a
  positive cd_wave (assert cl magnitude < 0.01 and cd_wave > 0).
- Mach trend: at fixed alpha/eps, cl and cd_wave fall as M rises from
  1.5 to 3 (assert monotonic decrease of cd_wave).
- ValueError: M1 = 1.0 raises; theta beyond the max deflection raises.
Test identities and ValueErrors as listed.

## Corpus tasks (2 tasks, ids w24r-shock-expansion-airfoil-1/2)

Distinctive tokens: shock-expansion, supersonic airfoil, diamond
airfoil, double-wedge, surface-pressure integration, wave drag
coefficient. Avoid: "shock angle for a wedge", "expansion fan angle"
(oblique-shock/prandtl-meyer single-turn claims), "area rule",
"transonic", "swept".

1. "compute the lift and wave drag of the 10 degree included angle
   diamond airfoil at Mach 2 and 3 degrees angle of attack with the
   shock-expansion method: get the surface pressure on each panel and
   integrate to the section lift, wave drag, and leading edge moment
   coefficients"
2. "apply shock-expansion theory to the supersonic double-wedge section
   across the Mach range 1.5 to 3 at fixed angle of attack and report
   the surface pressure table and the trend of the wave drag
   coefficient"

## SKILL body notes

Pair with oblique-shock, prandtl-meyer (the local relations this leaf
patches), wave-drag-area-rule (volume contribution), swept-wing-
aerodynamics (3D effects). Worked example uses the values above.
Compliance: NACA-style classical supersonic airfoil theory summarized,
not reproduced.
