---
name: inelastic-column-buckling
description: "Use when you must compute the inelastic column strength of a solid round, tube or extruded compression member in the intermediate slenderness band: the effective slenderness lambda = K*L/r of the member, the euler-johnson-tangent transition lambda_t = sqrt(2*pi^2*E/F_cy) where the yield-anchored Johnson parabola meets the Euler arm at F_cy/2, the johnson-parabola stress F_col = F_cy*(1 - F_cy*lambda^2/(4*pi^2*E)) below the transition and the Euler arm stress above it, the column capacity P_col = F_col*A and the margin of safety against the applied axial load, with the johnson or euler regime verdict. Produces the inelastic column allowable stress and load, the stubby-column-allowable and the pass-fail margin that gate compression checks of 7075-T6 and 2024-T3 actuator rods, tube members and extruded struts. Trigger: inelastic column buckling, Johnson parabola, column strength curve, intermediate slenderness, stubby column allowable."
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
  tags: [inelastic-column-buckling, johnson-parabola, column-strength-curve, intermediate-slenderness, euler-johnson-tangent, yield-anchored-johnson, stubby-column-allowable]
  version: 0.1.0
  author: AeroSkills
---

# Inelastic Column Buckling (structures/fem/inelastic-column-buckling)

Use when the task is the inelastic column strength of a whole solid,
round, tube or extruded compression member in the intermediate
slenderness band: the yield-anchored Euler-Johnson tangent column
strength curve F_col(lambda) whose Johnson parabola arm F_col =
F_cy*(1 - F_cy*lambda^2/(4*pi^2*E)) interpolates between the yield
anchor F_col = F_cy at lambda = 0 and the tangent point F_col = F_cy/2
at the transition lambda_t = sqrt(2*pi^2*E/F_cy), where it meets the
Euler arm F_col = pi^2*E/lambda^2 with equal slope. The curve is the
standard Johnson form of the published Euler-Johnson tangent column
strength curve (Bruhn column analysis chapter, Niu column allowable
curves, Timoshenko and Gere inelastic columns, Roark columns chapter;
public engineering science, summary paraphrase only). The logic module
is pure Python standard library and deterministic. Units are SI: E and
F_cy in Pa, L and r in m, A in m^2, forces in N.

The leaf pairs with the elastic Euler owner of the same member:
structures/fem/buckling-analysis ends its elastic arm at the
yield-crossing classification and hands the inelastic side off; this
leaf takes the effective length factor K as a plain given number and
reports the Euler arm only as the upper arm of the yield-anchored
column strength curve, never as an elastic critical load deliverable.
It re-implements the Johnson arm equation family of
structures/fem/crippling-analysis re-anchored from the local crippling
stress of formed sheet onto the solid-section compressive yield F_cy,
covering the extruded and machined whole sections that leaf excludes.
Materials/ramberg-osgood defines the material stress-strain response;
this leaf consumes only the plain E and F_cy pair. The applied-load
context is the certification compression case under FAR 25.301 and CS
25.301 applied loads with the 1.5 ultimate factor of FAR 25.303 and CS
25.303 (standards named and paraphrased, never reproduced).

## Domain quick reference

- Effective slenderness of the member:

      lambda = K * L / r

  with K the effective length factor (given as a number; resolving K
  from the support type is the buckling-analysis sibling's job), L the
  physical length and r the radius of gyration of the section. Solid
  round rod of diameter d: A = pi*d^2/4, r = d/4. Round tube with
  outer and inner diameters d_o, d_i: A = pi*(d_o^2 - d_i^2)/4,
  I = pi*(d_o^4 - d_i^4)/64, r = sqrt(I/A), which equals
  sqrt((d_o^2 + d_i^2)/16).

- Euler-Johnson tangent transition (tangency of the two arms at
  F_cy/2):

      lambda_t = sqrt(2 * pi^2 * E / F_cy)

  The elastic yield crossing of the Euler owner, lambda_1 =
  pi*sqrt(E/F_cy), equals lambda_t/sqrt(2): the tangent transition
  sits sqrt(2) higher, so the Johnson arm also covers the intermediate
  band where the ideal Euler stress is still below yield but real
  column allowables follow the parabola.

- Johnson parabola arm (lambda <= lambda_t), the inelastic column
  allowable stress:

      F_col = F_cy * (1 - F_cy * lambda^2 / (4 * pi^2 * E))

  Quadratic between the yield anchor F_cy at lambda = 0 and F_cy/2 at
  lambda_t; the drop from yield F_cy - F_col is exactly quadratic in
  lambda, so the drop at lambda_t/2 is one quarter of the drop at
  lambda_t.

- Euler arm (lambda > lambda_t), the elastic hyperbola of the same
  curve:

      F_col = pi^2 * E / lambda^2

- Column capacity and margin of safety:

      P_col = F_col * A        MS = P_col / P_applied - 1

  pass when MS >= 0. Regime: "johnson" at or below lambda_t, "euler"
  above.

- Materials registry pair (shared with crippling-analysis), used by the
  worked examples: 7075-T6 E = 71.7 GPa, F_cy = 462 MPa; 2024-T3
  E = 72.4 GPa, F_cy = 290 MPa. All functions take E and F_cy as plain
  float arguments.

## Workflow

1. Gather the member inputs and section properties: the material
   pair E and F_cy (Pa), the effective length factor K (a plain given
   number; end-condition resolution belongs to buckling-analysis), the
   physical length L in m, the radius of gyration r and gross section
   area A in m^2, and the applied axial compression P_applied in N.
   Solid round rod of diameter d: A = pi*d^2/4 and r = d/4; round tube
   d_o/d_i: A = pi*(d_o^2 - d_i^2)/4, I = pi*(d_o^4 - d_i^4)/64 and
   r = sqrt(I/A).
2. Compute the effective slenderness lambda = K*L/r with
   effective_slenderness(k_factor, length, radius_gyration). A member
   length L = 40*r pins lambda = 40 for the stubby-column regime;
   L = 0.55 m at r = 0.01 m with K = 1.0 pins lambda = 55.
3. Compute the euler-johnson-tangent transition lambda_t =
   sqrt(2*pi^2*E/F_cy) with
   johnson_transition_slenderness(e, f_cy); lambda_t sits sqrt(2)
   above the elastic yield crossing lambda_1 = pi*sqrt(E/F_cy) of the
   buckling-analysis sibling.
4. Classify the regime with column_regime(e, f_cy, lam): "johnson" at
   or below lambda_t, "euler" above it. The intermediate slenderness
   band below lambda_t is where the yield-anchored parabola governs
   and the ideal Euler stress overpredicts.
5. Compute the inelastic column allowable stress F_col with
   column_strength_allowable(e, f_cy, lam): the johnson-parabola
   stress johnson_parabola_stress(e, f_cy, lam) =
   F_cy*(1 - F_cy*lam^2/(4*pi^2*E)) below the transition (the
   stubby-column-allowable) and the euler_arm_stress(e, lam) =
   pi^2*E/lam^2 above it.
6. Compute the column capacity P_col = F_col*A with
   column_capacity(e, f_cy, lam, area).
7. Run the margin of safety and the verdict in one call with
   column_check(e, f_cy, lam, area, applied_load), which returns the
   dict {lambda_t, regime, F_col, P_col, margin, verdict} with verdict
   "pass" when margin >= 0. In the certification compression case,
   compare against the applied load amplified to the 1.5 ultimate
   factor per FAR 25.303 / CS 25.303 (summary paraphrase of the
   requirement, never standard text).

## Worked example

Worked example 1 (corpus query 1): 7075-T6 solid round actuator rod,
d = 0.04 m, E = 71.7 GPa, F_cy = 462 MPa, K = 1.0, L = 0.55 m, applied
axial compression 200 kN. Real module outputs (verified identical
under /usr/bin/python3 3.9.6 and pyenv 3.13.12):

- A = pi*d^2/4 = 1.2566370614359172e-03 m^2, r = d/4 = 0.01 m.
- lambda = K*L/r = 55; lambda_t = sqrt(2*pi^2*E/F_cy) =
  55.348194774118063, so lambda 55 sits just below the transition and
  the regime is johnson.
- Johnson parabola stress F_col = 233897293.82113209 Pa (233.897 MPa).
  The Euler arm of the curve at the same lambda is
  233934094.39937419 Pa (233.934 MPa), 1.573e-4 above the parabola
  near the tangency point; F_cy/2 = 231 MPa is 1.255e-2 below the
  allowable.
- P_col = F_col*A = 293924.00798520073 N (293.9 kN).
- MS = P_col/P_applied - 1 = 0.46962003992600376, verdict pass.

Worked example 2 (corpus query 2): 2024-T3 extruded round tube
compression member, d_o = 0.05 m, d_i = 0.04 m (5 mm wall), E =
72.4 GPa, F_cy = 290 MPa, K = 1.0, applied axial compression 120 kN.
Real module outputs:

- A = pi*(d_o^2 - d_i^2)/4 = 7.0685834705770374e-04 m^2,
  I = pi*(d_o^4 - d_i^4)/64 = 1.8113245143353656e-07 m^4,
  r = sqrt(I/A) = 0.016007810593582122 m (the round-tube identity
  sqrt((d_o^2 + d_i^2)/16) reproduces r exactly).
- Member length L = 40*r = 0.6403124237432849 m pins lambda =
  K*L/r = 40; lambda_t = 70.199683594869498, so lambda 40 is deep in
  the Johnson band (below 0.57*lambda_t) and the regime is johnson.
- Johnson parabola stress F_col = 242922035.66673699 Pa (242.922 MPa,
  0.83766 of F_cy), the stubby-column-allowable. The Euler arm at the
  same lambda is 446599599.14929342 Pa (446.6 MPa), 1.8384482820734314
  times F_col and above F_cy itself, the elastic overprediction the
  parabola corrects.
- P_col = F_col*A = 171711.46859528226 N (171.7 kN).
- MS = P_col/P_applied - 1 = 0.43092890496068548, verdict pass.

Curve shape (real module rows): the 7075-T6 allowable falls from the
462 MPa yield anchor through 454459414.671773 Pa at lambda 10,
341350634.748367 Pa at lambda 40, 233897293.821132 Pa at lambda 55
(johnson regime), then follows the Euler arm 196569620.988363 Pa at
lambda 60, 110570411.805954 Pa at lambda 80 and 70765063.5558107 Pa at
lambda 100 (euler regime). The 2024-T3 curve runs
287057627.229171 Pa at lambda 10 to 242922035.666737 Pa at lambda 40,
200993223.682425 Pa at lambda 55, 145823734.229382 Pa at lambda 70
(johnson, just below the transition) and 88217204.7702308 Pa at lambda
90, 49622177.6832548 Pa at lambda 120 (euler). Both arms return F_cy/2
at lambda_t to float roundoff and the parabola is tangent to the Euler
hyperbola there.

## Verification

- Worked examples: the two cases above are asserted in the contract
  test against the module's real outputs within the tolerances of the
  spec validation list.
- Tangency by construction: at lambda_t both arms return F_cy/2 (the
  Johnson arm, the Euler arm and their cross difference sit within
  1e-12 relative, anchor residuals 2.58e-16 and 1.29e-16 for 7075-T6
  and 0.0 for 2024-T3) and the closed-form slopes agree to 1e-9
  relative.
- Quadratic-decay identity: 4*(F_cy - F_col(lam_t/2)) equals
  F_cy - F_col(lam_t) = F_cy/2 to 1e-9 relative of F_cy.
- Yield anchor: johnson_parabola_stress at lam = lam_t*1e-6 sits
  within 1e-9 relative of F_cy, so F_col approaches F_cy as lambda
  approaches zero.
- Regime flip and continuity: column_regime is johnson at
  lam_t*(1 - 1e-12) and euler at lam_t*(1 + 1e-12), and F_col at the
  upper point stays within 1e-9 relative of F_cy/2.
- The curve is strictly monotone decreasing on a dense lambda grid
  from 1 to 200 for both materials; the Euler arm lies strictly above
  the Johnson parabola inside the Johnson band, the overprediction the
  parabola corrects.
- ValueError rejection of non-physical inputs: zero or negative
  k_factor, length, radius_gyration, e, f_cy, lam, area, allowable or
  applied load all raise ValueError (16 cases in the contract test).
- Determinism: two identical full runs return identical bits; the
  canonical dump sha256 is
  1f3904e5de54c994b725577b30d02c298b726db9a7a2394172f74c6c2c8e1183
  on both in-process passes and under both interpreters.

## Related leaves

- structures/fem/buckling-analysis: the elastic Euler arm of the same
  member with the end-condition effective length factor K table
  (pinned-pinned, fixed-fixed, fixed-pinned, cantilever), the
  radius-of-gyration-from-section workflow and the yield-crossing
  classification at lambda_1 = pi*sqrt(E/sigma_y); this leaf takes K
  as a number and reports the Euler arm only as the upper arm of the
  yield-anchored column strength curve.
- structures/fem/crippling-analysis: the same Johnson arm equation
  family anchored on the LOCAL crippling stress of formed sheet
  stiffeners (never on yield); extruded and machined whole sections
  are exactly the population this leaf serves on the solid-section
  yield.
- structures/materials/ramberg-osgood: the elastic-plastic
  stress-strain curve and tangent-modulus material response; this leaf
  characterizes the material by plain E and F_cy only.
- structures/fem/plate-buckling and structures/fem/
  cylindrical-shell-buckling: local flat-panel and shell wall
  instability, which can govern thin formed sections and thin-walled
  tubes before the column curve.
- structures/fem/beam-column-analysis: the axial-plus-bending
  interaction check; this leaf is compression only.

## Pitfalls

- Routing the elastic Euler instability here: the Euler critical load
  Pcr = pi^2*E*I/(K*L)^2 at resolved end conditions, the slenderness
  ratio from the radius of gyration and the yield-crossing
  classification with the euler_governs flag belong to
  structures/fem/buckling-analysis; this leaf takes K and r as given
  numbers.
- Reading the Euler arm below lambda_t as the allowable: inside the
  Johnson band the ideal Euler stress overpredicts the column strength
  (in the tube example it exceeds F_cy itself), exactly the
  overprediction the yield-anchored parabola corrects; the curve value
  below lambda_t is the johnson-parabola stress.
- Anchoring the parabola on the wrong stress: this leaf anchors on the
  solid-section compressive yield F_cy of a whole solid, round, tube
  or extruded member. Formed sheet stiffeners anchor on the local
  crippling stress F_cc and belong to structures/fem/crippling-
  analysis, whose scope excludes extruded and machined whole sections.
- Confusing the material curve with the column curve: the
  elastic-plastic stress-strain response and the secant or tangent
  modulus of the material itself are the ramberg-osgood leaf's
  content; here E and F_cy are plain material floats.
- Forgetting the wall-stability check: a thin formed section or
  thin-walled tube may cripple or buckle locally (plate-buckling,
  cylindrical-shell-buckling) before the yield-anchored column curve
  governs; this closed form assumes whole-section behavior.
- Mixing units: E in GPa with L and r in mm, or F_cy in MPa with
  A in m^2, silently corrupts F_col and P_col by factors of 1e9 or
  1e6; keep everything SI (Pa, m, m^2, N).
- Applying a bending interaction: the check is axial compression only;
  axial-plus-bending members belong to beam-column-analysis.

## Behavior contract (gate 3)

The inelastic column logic is exercised by the gate 3 contract test
scripts/test_inelastic_column_buckling.py against
scripts/inelastic_column_buckling_logic.py (pure stdlib unittest,
offline, deterministic). It asserts the two worked examples above, the
column strength curve sweeps and monotone shape for both materials,
the F_cy/2 tangency of both arms at lambda_t, the slope tangency, the
quadratic-decay quarter-drop identity, the yield anchor, the regime
flip and continuity across the transition, the Euler-arm
overprediction inside the Johnson band, the capacity and margin
linearities, all ValueError rejections of non-physical inputs, and the
canonical determinism digest. Run:

python3 scripts/test_inelastic_column_buckling.py

## Contract test

The contract test must pass offline under BOTH interpreters used by
the pre-push hook environment (31 test methods, deterministic, under
20 seconds):

/usr/bin/python3 skills/structures/fem/inelastic-column-buckling/scripts/test_inelastic_column_buckling.py

and

~/.pyenv/versions/3.13.12/bin/python3 skills/structures/fem/inelastic-column-buckling/scripts/test_inelastic_column_buckling.py

## Compliance

- FAR-25 and CS-25 are referenced, not reproduced: standards-map.yaml
  marks them gated: false and reference-only: true. Only the summary
  paraphrase of the applied-load and 1.5 ultimate-factor context is
  used (FAR 25.301 / CS 25.301, FAR 25.303 / CS 25.303), never
  standard text.
- The Euler-Johnson tangent column strength curve is standard
  engineering methodology (Bruhn, Niu, Timoshenko and Gere, Roark),
  summary-only.
- compliance: STANDARDS-REF, gated: false.
