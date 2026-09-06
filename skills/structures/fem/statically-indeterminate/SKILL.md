---
name: statically-indeterminate
description: "Use when you must find the elastic end moments and support reactions of statically indeterminate beams and continuous beams: compute the fixed-end moments (uniform w*L^2/12 and central P*L/8 hogging at both fixed ends; w*L^2/8 and 3*P*L/16 hogging at the fixed end of a propped cantilever), solve the interior support moments with the three-moment (Clapeyron) equation, apply the moment distribution (Hardy-Cross) method with distribution factors and the 1/2 carry-over, and the slope-deflection and consistent deformation (force) methods with flexibility coefficients for propped cantilevers and frames. Produces the fixed-end moments, interior support moments, member end moments, joint rotations, support reactions and the equilibrium and method-agreement checks in a stdlib-only elastic redundancy analysis. Trigger: moment distribution, three-moment equation, slope deflection, fixed-end moment, consistent deformation, statically indeterminate beam, continuous beam support moment."
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
  tags: [statically-indeterminate, three-moment-equation, moment-distribution, fixed-end-moment, slope-deflection, consistent-deformation, continuous-beam-support-moment]
  version: 0.1.0
  author: Aero Agent Skills
---

# Statically Indeterminate Analysis (structures/fem/statically-indeterminate)

Use when you must find the elastic end moments and support reactions of
statically indeterminate beams and continuous beams. This leaf computes the
elastic force distribution of redundant flexural members by the classical
hand methods, pure stdlib and deterministic: the fixed-end moments of the
standard load cases for a both-ends-fixed member, the propped-cantilever
fixed-end results that follow when one end is released, the interior support
moments of continuous beams from the three-moment (Clapeyron) equation, the
member end moments by the moment distribution (Hardy-Cross) method and the
slope-deflection equations, the redundant reactions by the consistent
deformation (force) method with flexibility coefficients, and the end moments
and joint rotations of one symmetric no-sway fixed-base frame under a central
beam load. The limit-load end moments and reactions produced here are exactly
the elastic moment peaks that the limit-state complement consumes, and the
distribution is what downstream strength and margin checks, including the 1.5
ultimate-factor check of FAR 25.303 / CS 25.303, are applied to. It pairs
with plastic-collapse-analysis (the limit-state complement), with
beam-frame-analysis (the numeric 6x6 stiffness complement, which distributes
no moments) and with truss-analysis (the pin-jointed axial complement).

## Domain quick reference

- Sign conventions: beam internal moment M(x) is SAGGING POSITIVE across each
  span, so hogging support moments are negative floats. Member end moments in
  moment distribution and slope-deflection are CLOCKWISE POSITIVE on the
  member end: for a downward transverse load on a both-ends-fixed member
  FEM_left = -|M_FE| and FEM_right = +|M_FE|. Joint rotations theta are
  CLOCKWISE POSITIVE. The sagging-positive interior support moment M_j equals
  -end_moments[j-1][1] of the span to its left and end_moments[j][0] of the
  span to its right; joint equilibrium makes the two member-end moments at a
  joint sum to zero.
- Fixed-end moment magnitudes (both ends fixed, hogging at each end):
  uniform w over the span: |M_FE| = w*L**2/12; central load P: |M_FE| =
  P*L/8. These are the Roark fixed-end table values for the two standard
  cases of this leaf.
- Propped cantilever (one end released): the fixed-end moment magnitude
  grows to w*L**2/8 (uniform) or 3*P*L/16 (central), equal to the
  both-ends-fixed FEM plus the 1/2 carry-over of the released end
  (w*L**2/12 + w*L**2/24, P*L/8 + P*L/16), the classic moment-distribution
  identity of the prop release.
- Clapeyron load terms t = A*xbar/L of the simple-span free bending moment
  diagram: uniform w: A = w*L**3/12, xbar = L/2, t = w*L**3/24; central P:
  A = P*L**2/8, xbar = L/2, t = P*L**2/16.
- Three-moment (Clapeyron) equation over the adjacent spans j and j + 1
  between supports j - 1, j and j + 1, M_j the sagging-positive interior
  support moment and M_0 = M_n = 0 at the simple ends:
  M_{j-1}*L_j + 2*M_j*(L_j + L_{j+1}) + M_{j+1}*L_{j+1} = -6*(t_j + t_{j+1}).
  Table values reproduced: two equal spans under uniform w give M_interior =
  -w*L**2/8; three equal spans give -w*L**2/10 at each interior support.
- Span reactions from the support moments with R0 the simple-span reaction
  (w*L/2 uniform, P/2 central): R_left = R0 + (M_right_end - M_left_end)/L
  and R_right = R0 + (M_left_end - M_right_end)/L, with 0.0 at the simple
  ends. Example: the two-span end reaction w*L/2 - |M_B|/L.
- Slope-deflection member end moments (no settlement, no sway term in this
  catalog): M_ab = (2*E*I/L)*(2*theta_a + theta_b) + FEM_ab and M_ba =
  (2*E*I/L)*(2*theta_b + theta_a) + FEM_ba. Propped cantilever: the roller
  condition M_ba = 0 fixes theta_B = -FEM_ba*L/(4*E*I).
- Consistent deformation (force method) on the propped cantilever: release
  the prop B; the redundant R_B closes the released-cantilever tip
  deflection delta_B against the unit-load flexibility f_BB = L**3/(3*E*I),
  R_B*f_BB = delta_B, with the Shigley A-9 cantilever cases: uniform
  delta_B = w*L**4/(8*E*I) giving R_B = 3*w*L/8; central delta_B =
  5*P*L**3/(48*E*I) giving R_B = 5*P/16.
- Moment distribution (Hardy-Cross): member ends start at their fixed-end
  moments; each joint in turn is released by adding the negative of its
  unbalanced sum, split by the distribution factors DF_e = k_e/sum(k) with
  k = 4*E*I/L (common E*I, so DFs are proportional to 1/L), carrying one
  half of each balancing moment to the far end of the same member; simple
  end supports have DF = 1. The release cycle converges to the exact joint
  solution, so the support moments agree with the three-moment equation to
  the tolerance.
- Symmetric fixed-base frame (the one frame case): beam span Lb between the
  top joints B and C, columns of height h fixed at the bases, common E*I,
  central load W on the beam, no sidesway by symmetry. FEM = W*Lb/8 hogging
  at each beam end; top-joint distribution factors 0.6 (column) and 0.4
  (beam) at h = 4 m, Lb = 6 m from the 4*E*I/h and 4*E*I/Lb stiffnesses; the
  bases never release, so the base moment equals one half of the column top
  moment (carry-over). Closed form: theta_B = (W*Lb/8)/(4*E*I/h + 2*E*I/Lb)
  = -theta_C, column top moment magnitude (4*E*I/h)*theta_B, beam end moment
  magnitude W*Lb/8 - (2*E*I/Lb)*theta_B, beam midspan sagging moment
  W*Lb/4 minus the beam end moment magnitude, base vertical reactions W/2
  each and zero horizontal reactions.
- Units are SI throughout: m, N, N/m, N m, rad, Pa. The relations above are
  the classical elastic methods of Roark's fixed-end and continuous-beam
  tables, the Shigley A-9 deflection cases and the Bruhn redundant-structure
  presentation, named and paraphrased, never reproduced.

## Workflow

1. Set up the catalog: span lengths, one (kind, magnitude) load pair per
   span ('uniform' w in N/m or 'central' P in N at midspan) and the common
   bending stiffness E*I of all members.
2. Compute the fixed-end moments of the standard load cases with
   fixed_end_moment_uniform and fixed_end_moment_central: |M_FE| = w*L**2/12
   or P*L/8 hogging at each end of a both-ends-fixed member.
3. Compute the Clapeyron load terms t = A*xbar/L with clapeyron_term_uniform
   and clapeyron_term_central (w*L**3/24, P*L**2/16).
4. For a propped cantilever, run the consistent deformation (force method)
   traverse with propped_cantilever(config, q, length, ei): the released
   cantilever deflection delta_B closed against the flexibility coefficient
   f_BB = L**3/(3*E*I) gives the redundant prop reaction, and the dict
   reports the fixed reaction, the hogging fixed-end moment, the prop
   rotation, the peak sagging moment and its location. Confirm the carry
   over identity: fixed_end_moment equals the both-ends-fixed FEM plus
   FEM/2, and the Hardy-Cross and slope-deflection fixed-end moments agree.
5. For a continuous beam on simple end supports, solve the interior support
   moments with three_moment_support_moments(lengths, terms), which solves
   the Clapeyron set for the n - 1 sagging-positive interior moments.
6. Recover the n + 1 support reactions with
   support_reactions_continuous(lengths, loads, moments) and verify that the
   reaction sum equals the applied load sum.
7. Cross-check the continuous beam with the moment distribution (Hardy-Cross)
   method, hardycross_beam(lengths, loads): the distribution factors from
   the 1/L-proportional stiffnesses and the 1/2 carry-over factor reproduce
   the three-moment support moments, the member end moments at each interior
   joint balance to zero and the simple-end member end moments vanish.
8. Compute member end moments and joint rotations with
   slope_deflection_member(ei, length, theta_left, theta_right, fem_left,
   fem_right) in the clockwise-positive convention, e.g. the propped
   cantilever roller condition M_ba = 0.
9. For the symmetric no-sway fixed-base frame under a central beam load, run
   portal_frame_fixed_base(total_load, span, height, ei): moment distribution
   over the two top joints with the fixed bases and the 4*E*I/h, 4*E*I/Lb
   stiffnesses gives the beam end, column top and column base (carry-over)
   moment magnitudes, the beam midspan sagging moment, the joint rotations
   and the base reactions. Cross-check with slope_deflection_frame_solve,
   the direct solve of the two joint-equilibrium slope-deflection equations,
   and with the closed form theta_B = (W*Lb/8)/(4*E*I/h + 2*E*I/Lb).
10. Confirm the deterministic checks: every non-physical input raises
    ValueError, repeated runs return identical bits, and the contract test
    scripts/test_statically_indeterminate.py passes offline.

## Worked example

E = 200 GPa, I = 2.0e-4 m**4, so E*I = 4.0e7 N m**2 throughout. All values
below are the real outputs of scripts/statically_indeterminate_logic.py
(pure stdlib math, deterministic), which sit within float noise of the
closed forms (worst observed agreement 4e-15 relative; e.g. the two-span
interior support moment prints -30833.333333333332 N m).

- Fixed-end moments and Clapeyron terms: fixed_end_moment_uniform(12000, 5)
  = 25000.0 N m hogging at each end (w*L**2/12), (10000, 6) = 30000.0;
  fixed_end_moment_central(30000, 4) = 15000.0 (P*L/8).
  clapeyron_term_uniform(12000, 5) = 62500.0 N m**2 and
  clapeyron_term_central(30000, 4) = 30000.0 N m**2.
- Propped cantilever, central load P = 20000 N, L = 4 m: consistent
  deformation gives delta_B = 5*P*L**3/(48*E*I) = 0.00333333333333 m,
  f_BB = L**3/(3*E*I) = 5.33333333333e-07 m/N and R_B = delta_B/f_BB =
  6250.0 N (5*P/16) with consistency residual 0.0; statics give R_A =
  13750.0 N (11*P/16) and the hogging fixed-end moment 15000.0 N m
  (3*P*L/16). prop_rotation = -2.5e-4 rad, peak sagging 5*P*L/32 =
  12500.0 N m under the load at x = 2.0 m. The Hardy-Cross release of the
  prop end (balance -10000.0, carry -5000.0 to A on top of the FEM
  -10000.0) and the slope-deflection roller condition give the same
  15000.0 N m, sd_prop_end_moment = 0.0, and the carry-over identity
  3*P*L/16 = P*L/8 + P*L/16 holds with residual 0.0.
- Propped cantilever, uniform w = 12000 N/m, L = 4 m: R_B = 3*w*L/8 =
  18000.0 N, R_A = 5*w*L/8 = 30000.0 N, fixed-end moment w*L**2/8 =
  24000.0 N m, prop_rotation -4.0e-4 rad, delta_B = 9.6e-03 m (consistency
  residual 1.73472347598e-18), peak sagging 9*w*L**2/128 = 13500.0 N m at
  x = 5*L/8 = 2.5 m; carry-over identity 24000.0 = 16000.0 + 8000.0.
- Two-span continuous beam, L1 = 5 m uniform 12000 N/m, L2 = 4 m central
  30000 N, simple ends: three_moment_support_moments returns M_B =
  -30833.3333333333 N m, the closed form -3*(t1 + t2)/(L1 + L2) of the
  single Clapeyron equation; support_reactions_continuous returns
  23833.3333333333, 58875.0 and 7291.6666666667 N (sum 90000.0 N, the
  applied load). Moment distribution agrees with the three-moment support
  moment in 23 iterations with the simple-end member end moments below
  5e-10 N m.
- Three-span continuous beam, three equal spans L = 6 m, uniform 10000 N/m:
  M_1 = M_2 = -36000.0 N m, the Roark/Shigley table value -w*L**2/10;
  reactions 24000.0, 66000.0, 66000.0, 24000.0 N (sum 180000.0 = 3*w*L,
  residual 0.0); moment distribution agrees within 3.2e-10 N m in 25
  iterations.
- Symmetric fixed-base frame, W = 60000 N central on the beam, Lb = 6 m,
  h = 4 m: FEM = 45000.0 N m hogging at each beam end, distribution factors
  0.6 (column) and 0.4 (beam); moment distribution converges in 12
  iterations to beam end moment magnitude 33750.0 N m at each end, column
  top moment 33750.0 N m, column base moment 16875.0 N m (the carry-over
  half) and beam midspan sagging moment 56250.0 N m (= W*Lb/4 - 33750).
  theta_B = 8.4375e-4 rad = -theta_C from the closed form 45000.0 /
  53333333.3333333; the direct 2x2 slope_deflection_frame_solve reproduces
  every member end moment (maximum difference over the six end moments
  7.3e-12 N m). Base vertical reactions 30000.0 N each, horizontal
  reactions 0.0.

## Verification

- Confirm fixed_end_moment_uniform(12000, 5) = 25000.0 and
  fixed_end_moment_central(30000, 4) = 15000.0, each equal to the closed
  form w*L**2/12 or P*L/8 by construction.
- Confirm three_moment_support_moments on the two-span case returns
  -30833.3333333333 (within 1e-6 relative of -3*(t1 + t2)/(L1 + L2)) and
  on the three equal spans returns -36000.0 at both interior supports
  (within 1e-9 relative of -w*L**2/10).
- Confirm hardycross_beam support moments equal the three-moment results,
  the member end moments at each interior joint sum to zero, the
  simple-end member end moments vanish, and the sagging-positive support
  moment equals -end_moments[j-1][1] and end_moments[j][0] within 1e-9
  relative.
- Confirm slope_deflection_member(EI, 4.0, 0.0, -2.5e-4, -10000.0,
  10000.0) returns (-15000.0, 0.0): the zero prop end moment is the roller
  condition.
- Confirm propped_cantilever reports the anchor reactions, moments,
  rotations and deflections with the consistency residual R_B*f_BB -
  delta_B below 1e-12 N (central) and 1e-15 N (uniform), and that the
  carry-over identity |M_A| - (FEM + FEM/2) holds.
- Confirm portal_frame_fixed_base(60000.0, 6.0, 4.0, EI) reports beam end
  moment magnitude 33750.0, column top 33750.0, column base 16875.0 (=
  top/2 carry-over), midspan sagging 56250.0, theta_B = 8.4375e-4 =
  -theta_C, base vertical reactions 30000.0 each and horizontal reactions
  0.0, and that slope_deflection_frame_solve reproduces every member end
  moment within 1e-6 relative.
- Confirm every non-physical input raises ValueError: nonpositive w, L, P,
  load, term or ei; a one-span three-moment call; arity mismatches on the
  terms, loads or moments; unknown load kinds; an unknown propped-cantilever
  config; and nonpositive frame inputs.
- Run the deterministic contract test offline:
  python3 scripts/test_statically_indeterminate.py (34 tests, exit 0).

## Related leaves

- skills/structures/fem/plastic-collapse-analysis: the limit-state
  complement; its plastic mechanisms consume exactly the elastic end
  moments and reactions this leaf distributes.
- skills/structures/fem/beam-frame-analysis: the numeric 6x6
  Euler-Bernoulli stiffness-method complement for the same rigid-jointed
  frames; it assembles no compatibility equation and distributes no
  moments.
- skills/structures/fem/truss-analysis: the pin-jointed axial-only
  stiffness complement for trusses, no redundancy distribution.
- skills/structures/fem/beam-vibration: natural frequencies of a
  continuous (distributed-mass) member, not a multi-span redundant beam.
- skills/structures/fem/buckling-analysis: elastic stability of
  compression members with effective length and secant-formula checks.

## Pitfalls

- Mixing the sign conventions: the sagging-positive interior support
  moment of a gravity-loaded continuous beam is negative (M_B =
  -30833.3333333333 N m in the two-span example), while the
  clockwise-positive member end moment at that support from the span to the
  right is positive; reading one convention as the other flips the hogging
  moment into a sagging one.
- Reading the both-ends-fixed FEM as the propped fixed-end moment:
  releasing one end raises the fixed end from w*L**2/12 to w*L**2/8
  (uniform) or P*L/8 to 3*P*L/16 (central) by the carry-over of the
  released end; the moment-distribution identity |M_A| = FEM + FEM/2 checks
  the propped result.
- Treating three-moment support moments as magnitudes: the Clapeyron
  equation works in the sagging-positive convention with the simple-end
  condition M_0 = M_n = 0, and the load terms t = A*xbar/L are moments of
  the free moment diagram area, not the areas themselves.
- Forgetting the 1/2 carry-over in moment distribution: a balancing moment
  at a joint carries one half to the far end of the same member, and the
  simple end supports (DF = 1) release fully every cycle; a hand table that
  stops after one balance cycle is not converged.
- Using the frame closed form outside its scope: the single catalog frame
  is symmetric, fixed-base, no-sway, with a central beam load and common
  E*I; a swaying, pinned-base or unsymmetric frame needs the numeric
  stiffness-method leaf (beam-frame-analysis).
- Confusing elastic and plastic: the moments here are the elastic limit
  distribution; the collapse load and plastic hinge checks of the
  limit-state sibling start from these elastic peaks but belong to
  plastic-collapse-analysis.
- Applying the catalog outside its prismatic scope: the continuous-beam
  spans and all frame members share one E*I, loads are only full-span
  uniform or midspan point loads, and there is no support settlement,
  temperature, material nonlinearity or dynamics in this leaf.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_statically_indeterminate.py

The test covers the worked-example contract: fixed-end moments and
Clapeyron terms, the two-span and three-span three-moment interior support
moments with their closed forms, support reactions with the equilibrium
sums, the moment distribution cross-checks (agreement with the
three-moment results, joint equilibrium, vanishing simple-end moments, the
support-moment sign convention), the slope-deflection roller-condition
identities of the propped cantilever, the consistent-deformation solution
with flexibility coefficients and the carry-over identity for both load
configs, the peak sagging moments, the fixed-base frame end moments,
rotations and reactions with the carry-over base moments, the direct 2x2
joint-equation solve cross-check, and the ValueError rejection of every
non-physical input class. 34 tests, all deterministic, exit 0 under both
/usr/bin/python3 and the pre-push hook interpreter.

## Compliance

- Standards referenced, not reproduced: FAR 25.303 and CS 25.303 require
  the structure to withstand 1.5 times the limit loads without failure; the
  elastic end moments and reactions computed here are the limit-load force
  distribution that the downstream strength and margin checks, including
  the 1.5 ultimate-factor check, consume. The classical methods above
  (Roark fixed-end and continuous-beam tables, Shigley A-9 deflection
  cases, Bruhn redundant-structure presentation) are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
