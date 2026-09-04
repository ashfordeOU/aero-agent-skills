---
name: shock-expansion-airfoil
description: "Use when you must compute the supersonic shock-expansion solution for a diamond (double-wedge) airfoil section: patch oblique-shock and Prandtl-Meyer relations over the four planar surfaces at a freestream Mach number and angle of attack, then integrate the panel pressures into the section lift, wave drag, and leading-edge moment coefficients with a surface pressure table. Implements theta-beta-M (weak solution), oblique-shock ratios, and the Prandtl-Meyer function internally for the turn-by-turn surface states. Produces cl, cd_wave, cm_le and per-surface Cp for a given half-angle, angle of attack, and Mach number. Trigger: shock-expansion, supersonic airfoil, diamond airfoil, double-wedge, surface-pressure integration, wave drag coefficient."
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
  tags: [shock-expansion-airfoil, shock-expansion, supersonic-airfoil, diamond-airfoil, double-wedge, surface-pressure-integration, wave-drag-coefficient]
  version: 0.1.0
  author: Aero Agent Skills
---

# Shock-Expansion Airfoil (aerodynamics/high-speed/shock-expansion-airfoil)

Use when you must compute the supersonic pressure solution over a
diamond (double-wedge) airfoil section by shock-expansion theory:
oblique-shock relations handle the compression turns and Prandtl-Meyer
fans handle the expansion turns on each planar surface, the surface
states are marched turn by turn, and the panel pressures are integrated
into section lift, wave drag, and leading-edge moment coefficients.
This leaf implements the theta-beta-M relation (weak solution), the
oblique-shock jump ratios, and the Prandtl-Meyer function internally in
pure Python, stdlib only, so no sibling-leaf import is needed. It pairs
with aerodynamics/high-speed/oblique-shock and
aerodynamics/high-speed/prandtl-meyer for the local single-turn
relations this leaf patches, with aerodynamics/high-speed/wave-drag-area-rule
for the volume contribution to wave drag, and with
aerodynamics/high-speed/swept-wing-aerodynamics for three-dimensional
sweep effects.

## Domain quick reference

- Diamond geometry: symmetric double wedge with semi-wedge half-angle
  eps on chord c.  Four planar panels, each projecting c/2 on the
  chord: upper front and upper rear at +eps and -eps to the chord,
  lower front and lower rear at -eps and +eps.  Leading-edge included
  angle is 2*eps.
- Sign conventions: angles in degrees; positive alpha means the
  freestream comes from below the chord (nose-up, lower surface
  windward).  A positive deflection compresses the flow (oblique shock,
  weak solution); a negative deflection expands it (Prandtl-Meyer fan).
  Upper-front deflection theta_uf = eps - alpha (weak shock when
  alpha < eps, expansion fan when alpha > eps); lower-front deflection
  theta_lf = eps + alpha (shock for alpha > 0); both rear corners turn
  the flow away by 2*eps (expansion) from the front surface state.
- Theta-beta-M (weak branch): tan(theta) = 2 cot(beta) (M1^2 sin^2(beta)
  - 1) / (M1^2 (gamma + cos 2 beta) + 2), solved for the smaller wave
  angle beta by bisection between the Mach angle and the maximum
  turning point.  Each Mach number has a maximum deflection
  (22.97 deg at M1 = 2, gamma = 1.4); larger deflections detach the
  shock and raise ValueError.
- Oblique-shock jumps: Mn1 = M1 sin(beta), p2/p1 = 1 + (2 gamma /
  (gamma + 1)) (Mn1^2 - 1), and M2 = Mn2 / sin(beta - theta) with
  Mn2^2 = (1 + ((gamma - 1) / 2) Mn1^2) / (gamma Mn1^2 - (gamma - 1) /
  2).
- Prandtl-Meyer function: nu(M) = sqrt((gamma + 1) / (gamma - 1)) *
  atan(sqrt((gamma - 1)(M^2 - 1) / (gamma + 1))) - atan(sqrt(M^2 - 1)).
  A turn of theta raises the function value by theta (nu(2) =
  26.38 deg, gamma = 1.4); p2/p1 follows the isentropic stagnation
  ratio across M1 and M2.
- Pressure coefficient: Cp = (p/p_inf - 1) / (0.5 * gamma * M1^2).
- Panel integration (documented method): each panel carries force
  (p - p_inf) * panel_length along its inward unit normal, applied at
  the panel center.  Body-axis forces are then resolved onto the
  freestream direction, which lies at +alpha to the chord in body axes,
  giving lift L and wave drag D; the moment is taken about the leading
  edge with positive nose-up.  Section coefficients: cl = L/(q c),
  cd_wave = D/(q c), cm_le = M_le/(q c^2), with q = 0.5 * gamma * p_inf
  * M1^2 and chord c as the normalization length.
- NACA-TR-824 frames the compressible-flow function conventions; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the flight state: freestream Mach M1 (supersonic, M1 > 1),
   angle of attack alpha (deg) and half-angle eps (deg, 0 to 45).
2. Get the weak wave angle for a compression turn with
   theta_beta_m(m1, theta_deg), or the downstream state with
   oblique_shock_ratios(m1, theta_deg) -> (m2, p2_p1).
3. For an expansion turn use prandtl_meyer_angle(m) for the function
   value and prandtl_meyer_turn(m1, theta_deg) -> (m2, p2_p1).
4. March the surface states turn by turn with panel_state(m, p_in,
   theta_deg): upper front theta = eps - alpha, lower front theta =
   eps + alpha, then both rears by an expansion of 2*eps from the
   front state of the same side.
5. Build the Cp table with surface_pressures(m1, alpha_deg, eps_deg),
   which returns uf, ur, lf, lr entries with cp, m, p_pinf,
   theta_deg.
6. Integrate the panels with shock_expansion_airfoil(m1, alpha_deg,
   eps_deg) for the summary dict: cl, cd_wave, cm_le, and the surface
   Cp table.
7. Confirm the deterministic checks with the contract test
   scripts/test_shock_expansion_airfoil.py.

## Worked example

Diamond airfoil eps = 5 deg (10 deg included angle) at M1 = 2.0,
alpha = 3 deg, gamma = 1.4:

- Upper front theta_uf = eps - alpha = +2 deg: a weak shock, so p rises
  to p_uf/p_inf = 1.118.  Lower front theta_lf = eps + alpha = 8 deg: a
  shock, p_lf/p_inf = 1.540.  Rear faces expand by 2*eps = 10 deg:
  p_ur/p_inf = 0.622 and p_lr/p_inf = 0.893.
- Surface Cp: Cp_uf = 0.042, Cp_ur = -0.135, Cp_lf = 0.193,
  Cp_lr = -0.038.  The lower-front shock dominates, so cl > 0.
- Section result: cl = 0.1227, cd_wave = 0.0243, cm_le = 0.0552
  (nose-up positive).
- Consistency with linear supersonic theory: at M = 2, eps = 5 deg,
  alpha = 3 deg, shock-expansion gives cl ~ 0.12 and cd_wave ~ 0.024,
  consistent with linear supersonic thin-airfoil theory
  cl = 4*alpha/sqrt(M^2 - 1) = 0.121 (the exact value sits 1.5% above
  it); the higher cl 0.3-0.5 textbook example corresponds to larger
  Mach number and half-angle cases on the same geometry, not to
  M = 2, eps = 5 deg, alpha = 3 deg.

## Verification

- Confirm shock_expansion_airfoil(2.0, 3.0, 5.0) returns cl = 0.1227,
  cd_wave = 0.0243, cm_le = 0.0552, within 10% of the linear value
  4*alpha/sqrt(M^2 - 1).
- Flat-plate limit: eps = 0.1 deg, M = 2, alpha = 3 deg gives cl =
  0.1210, within 5% of the linear supersonic value 0.1209.
- Symmetric diamond at alpha = 0: cl magnitude below 1e-9 and
  cd_wave = 0.0177 > 0.
- Negative alpha mirrors lift: alpha = -3 deg gives cl = -0.1227 and
  the same cd_wave.
- Mach trend at fixed eps and alpha: cd_wave falls monotonically from
  0.0386 at M1 = 1.5 to 0.0150 at M1 = 3.0.
- Sign logic: at alpha = 8 deg above eps the upper front is an
  expansion fan (p_uf/p_inf = 0.842 < 1), at alpha = 3 deg below eps it
  is the weaker of the two front shocks.
- Every non-physical input raises ValueError: M1 at or below 1,
  |alpha| at or above 90 deg, eps outside [0, 45) deg, non-finite
  arguments, deflections above the maximum turning angle (for example
  alpha = 18 deg at M1 = 2, eps = 5 deg, where theta_lf = 23 deg
  exceeds the 22.97 deg limit).
- Run the contract test offline: python3
  scripts/test_shock_expansion_airfoil.py (27 tests, deterministic,
  under 20 s).

## Related leaves

- aerodynamics/high-speed/oblique-shock: the local theta-beta-M and
  single-turn shock computation this leaf patches across surfaces.
- aerodynamics/high-speed/prandtl-meyer: the single-expansion-fan
  relations this leaf patches across surfaces.
- aerodynamics/high-speed/wave-drag-area-rule: the volume (zero-lift)
  contribution to supersonic wave drag.
- aerodynamics/high-speed/supercritical-airfoil and
  aerodynamics/high-speed/transonic-similarity: the transonic
  alternatives this leaf does not cover.
- aerodynamics/high-speed/swept-wing-aerodynamics: three-dimensional
  sweep effects on the same section aerodynamics.

## Pitfalls

- Demanding a result for a detached shock: when a compression turn
  exceeds the maximum deflection (22.97 deg at M1 = 2), the weak
  solution does not exist and the module raises ValueError - the
  worked-example alpha = 18 deg case at eps = 5 deg is exactly this
  boundary and must be caught, not approximated.
- Confusing the compression and expansion sides of the section: with
  alpha above eps the upper front turns into a Prandtl-Meyer expansion
  (p_uf/p_inf = 0.842 < 1) while below eps it is the weaker of the two
  front shocks; the deflection sign convention drives the whole surface
  march.
- Comparing against linear supersonic theory too tightly: at M = 2, eps
  = 5 deg, alpha = 3 deg the shock-expansion cl sits about 1.5% above
  4*alpha/sqrt(M^2 - 1), so use the linear value as a 10% cross-check,
  not as the exact answer.
- Expecting zero drag at zero lift: the symmetric diamond at alpha = 0
  still produces cd_wave = 0.0177 (the zero-thickness identity holds
  only for lift); wave drag comes from the volume and the shocks, so a
  non-zero cd_wave at cl ~ 0 is correct.
- Using the section result outside its validity: eps must stay in [0,
  45) and |alpha| below 90 deg, and every non-finite argument raises
  ValueError - the panel march is only defined for the diamond
  geometry, not for cambered or rounded sections.
- Reading a single Mach point as the trend: cd_wave falls monotonically
  from 0.0386 at M1 = 1.5 to 0.0150 at M1 = 3.0 at fixed eps and
  alpha, so an off-trend value means an input error, not a physical
  anomaly.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_shock_expansion_airfoil.py

The test covers the theta-beta-M weak solution against chart values and
the max-deflection rejection, oblique-shock jump ratios (p2_p1 = 1.540
for theta = 8 deg at M1 = 2), the Prandtl-Meyer function and turn
(M2 = 2.385 for a 10 deg turn from M1 = 2), the turn-by-turn surface
march with the eps = 5 deg worked example (cl = 0.1227, cd_wave =
0.0243, cm_le = 0.0552), the linear-theory cross-check, the flat-plate
limit, alpha = 0 symmetry, the negative-alpha mirror, the Mach trend of
the wave drag coefficient, the zero-thickness identity, and ValueError
rejection of M1 at or below 1, out-of-range alpha and eps, non-finite
inputs, and detached-shock deflections.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 is cited as the
  reference frame for compressible-flow function conventions; the
  theta-beta-M, oblique-shock and Prandtl-Meyer relations and the
  shock-expansion airfoil method are classical engineering methodology,
  summarized here per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
