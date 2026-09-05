# Wave-41 leaf spec: regular-shock-reflection (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/regular-shock-reflection/
- Pack: high-speed (verified present at prep with aerodynamic-heating,
  bow-shock-standoff, flat-plate-skin-friction-heating, hypersonic-flow,
  normal-shock, oblique-shock, prandtl-meyer, shock-expansion-airfoil,
  supercritical-airfoil, swept-wing-aerodynamics, transonic-similarity,
  wave-drag-area-rule). Closest siblings: oblique-shock (single-turn only;
  its frontmatter claim is "compute the wave angle beta from the upstream
  Mach number M1 and the flow deflection angle theta with the theta-beta-M
  relation, find the weak and strong solutions, the maximum deflection angle
  for an attached shock, and the downstream Mach number, static pressure,
  density, temperature, and stagnation pressure ratios across the shock.
  Covers shock polar basics", with the trigger list "oblique shock, shock
  wave, wave angle, deflection angle, theta-beta, wedge, compression corner,
  detached shock, shock polar, weak solution, strong solution, supersonic
  flow"; one shock at one turn only, no wall impingement and no second
  shock), normal-shock (a single normal shock, five ratios, no wave angle),
  shock-expansion-airfoil ("patch oblique-shock and Prandtl-Meyer relations
  over the four planar surfaces at a freestream Mach number and angle of
  attack" and "Implements theta-beta-M (weak solution), oblique-shock
  ratios, and the Prandtl-Meyer function internally for the turn-by-turn
  surface states" for the airfoil section only, no wall or symmetry-plane
  impingement), prandtl-meyer (expansion fans only, no shocks). Whole-tree
  greps at prep: "reflected shock", "mach reflection" and "regular
  reflection" = 0 hits in skills/ (exit 1; the few 'reflected' hits under
  ground-effect leaves are image-vortex sense only, e.g. reflected
  vortices). GENUINE AERO gap (fresh probe): the two-shock wall interaction
  (incident shock plus its reflection turning the flow back parallel to the
  wall, with the regular-versus-Mach verdict) is claimed by no leaf in the
  tree.
- Standards id: naca-tr-824 (reference-only). Ledger Standard:
  naca-tr-824.
- Family: aerodynamics

## Claim

When an oblique shock impinges on a wall or symmetry plane in supersonic
flow, compute the regular reflection of the two-shock interaction: solve the
theta-beta-M relation for the incident weak shock at the given Mach number
and deflection angle, obtain the full state behind the incident shock, then
solve theta-beta-M again on that downstream state for the reflected shock
that turns the flow back parallel to the wall by the same deflection angle,
and assemble the post-reflection state from the product of the two sets of
oblique-shock ratios. Judge the reflection as regular when the required
reflected deflection stays below the reflected-shock detachment limit (the
maximum deflection angle at the Mach number behind the incident shock) and
as Mach reflection (irregular) when it reaches or exceeds that limit.
Produces the incident and reflected wave angles, the intermediate and
post-reflection Mach numbers, the pressure, density, temperature and
stagnation-pressure ratios across each shock and across the pair, the
reflected-shock detachment limit with its margin, and the regular-versus-
Mach verdict. Does NOT do: single-shock wave-angle and weak/strong-branch
analysis (oblique-shock); normal-shock relations (normal-shock);
Prandtl-Meyer expansion fans (prandtl-meyer); the four-surface shock-
expansion airfoil solution with lift and wave-drag coefficients (shock-
expansion-airfoil). Scope: the classical two-shock regular reflection of a
weak incident shock only. Mach-reflection flow details (triple point, Mach
stem, slip line) are NOT modeled; the verdict is the detachment-criterion
flag and the von Neumann transition criterion is not implemented. A detached
incident shock (deflection at or above the maximum for M1) is non-physical
here and raises ValueError. Deterministic, pure stdlib.

## Model (implement exactly)

Functions (pure stdlib, math only, gamma defaults to the module constant
GAMMA = 1.4):
- deflection_angle(M1, beta_deg, gamma = GAMMA) -> float theta_deg from the
  theta-beta-M relation solved for the deflection at a given shock angle,
  tan(theta) = 2 cot(beta) (M1^2 sin^2(beta) - 1) / (M1^2 (gamma +
  cos(2 beta)) + 2); ValueError if M1 <= 1 or beta_deg is not strictly
  between the Mach angle asin(1 / M1) and 90 degrees.
- maximum_deflection_angle(M1, gamma = GAMMA) -> float theta_max_deg: the
  peak of deflection_angle over shock angles from the Mach angle to 90
  degrees (the attached-shock detachment limit, computed by a deterministic
  golden-section maximizer on the interior bracket); ValueError if M1 <= 1.
- shock_angle_weak(M1, theta_deg, gamma = GAMMA) -> float beta_deg: the weak
  branch of theta-beta-M by bisection over the shock-angle interval from the
  Mach angle to the detachment angle, where the deflection rises
  monotonically from 0 to theta_max (bisection tolerance module constant
  SHOCK_SOLVE_TOL_RAD = 1e-13 radians); returns the Mach angle exactly when
  theta_deg is 0; ValueError if M1 <= 1, theta_deg < 0, or theta_deg >=
  maximum_deflection_angle(M1) (a detached or strong incident shock is out
  of scope).
- oblique_shock_state(M1, theta_deg, gamma = GAMMA) -> dict with keys
  "beta_deg", "Mn1", "Mn2", "M2", "p2_p1", "rho2_rho1", "T2_T1",
  "p02_p01": beta from shock_angle_weak, Mn1 = M1 sin(beta), density ratio
  rho2_rho1 = (gamma + 1) Mn1^2 / ((gamma - 1) Mn1^2 + 2), pressure ratio
  p2_p1 = 1 + 2 gamma (Mn1^2 - 1) / (gamma + 1), temperature ratio T2_T1 =
  p2_p1 / rho2_rho1, Mn2^2 = (Mn1^2 + 2 / (gamma - 1)) / (2 gamma Mn1^2 /
  (gamma - 1) - 1), M2 = Mn2 / sin(beta - theta), and p02_p01 from the
  normal-shock total-pressure formula evaluated at Mn1 (name and paraphrase
  only, standard compressible-flow relations; no verbatim source text).
  ValueErrors as in the component functions.
- shock_reflection(M1, theta_deg, gamma = GAMMA) -> dict with keys
  "verdict", "theta_deg", "M2", "theta_max_ref_deg", "incident",
  "reflected", "reason". Incident state via oblique_shock_state(M1,
  theta_deg). The reflected shock must turn the flow back parallel to the
  wall, so the deflection across it equals the incident deflection
  theta_deg (straight-wall geometry). Verdict "regular" when M2 > 1 and
  theta_deg < theta_max_ref_deg, where theta_max_ref_deg =
  maximum_deflection_angle(M2) is the reflected-shock detachment limit;
  verdict "mach" when M2 <= 1 or theta_deg >= theta_max_ref_deg (at the
  limit the reflected shock sits at its detachment condition and regular
  reflection cannot be sustained; the verdict flag is the detachment
  criterion, the von Neumann criterion is not implemented). For verdict
  "regular", "reflected" is oblique_shock_state(M2, theta_deg) and "reason"
  is None; for verdict "mach", "reflected" is None and "reason" is a fixed
  string reporting that the required deflection reaches the reflected-shock
  detachment limit at M2. "incident" is always the oblique_shock_state dict
  at (M1, theta_deg). The post-reflection state is the product of the two
  stages: M3 = reflected["M2"] (regular only), p3_p1 = incident["p2_p1"] *
  reflected["p2_p1"], rho3_rho1, T3_T1 and p03_p01 = incident["p02_p01"] *
  reflected["p02_p01"] (the builder assembles these products in the SKILL
  workflow; no extra dict key is required). ValueErrors as in the component
  functions (a detached incident shock at theta_deg >=
  maximum_deflection_angle(M1) raises, it does not return a verdict).
Module constants: GAMMA = 1.4, SHOCK_SOLVE_TOL_RAD = 1e-13.

Identity to test: theta-beta-M round trip (deflection_angle(M1,
shock_angle_weak(M1, theta)) == theta within 1e-9); zero deflection returns
the Mach angle with unit ratios and M2 = M1; in a regular reflection the
flow leaves the reflected shock parallel to the wall (net turning zero by
construction, checked via the round trip at each stage) and pressures climb
strictly, p3 > p2 > p1, while total pressure falls, p03 < p02 < p01, with
p3_p1 and p03_p01 equal to the products of the stage ratios; the verdict
flips from regular to mach as the required deflection crosses the
reflected-shock detachment limit.

## Worked example

Standard gamma = 1.4 air. Run your module and take the real outputs as
assert targets; the anchors below are prep-verified bounds, computed by
running the prep anchor script /tmp/w41spec/anchor_shock_reflection.py
(prep-verified by stdlib math).

- Regular reflection, M1 = 3.0, theta = 15 deg: incident shock angle
  beta_inc = 32.240400 deg, Mn1 = 1.600418, M2 = 2.254902, p2/p1 =
  2.821562, rho2/rho1 = 2.032449, T2/T1 = 1.388258, p02/p01 = 0.895044.
  Reflected-shock detachment limit theta_max(M2) = 26.860810 deg, margin
  = 11.860810 deg, so verdict "regular". Reflected shock angle beta_ref =
  40.349015 deg (about 8.1 deg steeper than the incident wave), Mn1_ref =
  1.459918, M3 = 1.671849, p3/p2 = 2.319922, rho3/rho2 = 1.793230, T3/T2 =
  1.293712, p03/p02 = 0.941981. Post-reflection state over freestream:
  p3/p1 = 6.545805, p03/p01 = 0.843115, M3 = 1.671849, with the flow
  parallel to the wall. The reflected shock is weaker than the incident
  shock (smaller Mn1_ref, total-pressure ratio 0.941981 closer to 1).
- Mach reflection verdict, M1 = 2.0, theta = 20 deg: incident shock angle
  beta_inc = 53.422941 deg, M2 = 1.210218 (the strong incident shock
  leaves little supersonic margin), theta_max(M2) = 4.214110 deg. The
  required reflected deflection of 20 deg far exceeds the 4.214110 deg
  limit, verdict "mach", reflected = None. This is the detachment-criterion
  flag only; the Mach stem and triple point are not computed.
- Verdict boundary probe at M1 = 3.0: theta = 5 deg (M2 = 2.749709, limit
  32.171032 deg, margin +27.171032 deg), theta = 10 deg (M2 = 2.505001,
  limit 29.850539 deg, margin +19.850539 deg), theta = 20 deg (M2 =
  1.994132, limit 22.872253 deg, margin +2.872253 deg) all verdict
  "regular"; theta = 25 deg (M2 = 1.717258, limit 17.400245 deg, margin
  -7.599755 deg) verdict "mach". The transition deflection for M1 = 3.0
  lies between 20 and 25 deg.
- Reference detachment limits: maximum_deflection_angle at M1 = 1.2 is
  3.944187 deg, M1 = 1.5 is 12.112669 deg, M1 = 2.0 is 22.973532 deg,
  M1 = 3.0 is 34.073440 deg, M1 = 5.0 is 41.117663 deg (the limit rises
  with Mach number toward the asymptotic maximum).
- Degenerate zero deflection: shock_angle_weak(3.0, 0.0) = 19.471221 deg,
  the Mach angle for M1 = 3.0; oblique_shock_state(3.0, 0.0) gives M2 =
  3.0 and unit ratios; shock_reflection(3.0, 0.0) verdict "regular" with
  unit ratios throughout.
- Round-trip identities: shock_angle_weak(3.0, 15.0) = 32.240400 deg and
  deflection_angle(3.0, 32.240400) = 15.0; shock_angle_weak(2.0, 10.0) =
  39.313932 deg; shock_angle_weak(2.0, 20.0) = 53.422941 deg;
  shock_angle_weak(5.0, 25.0) = 35.779435 deg; shock_angle_weak(1.5, 5.0)
  = 47.889264 deg; each back-check recovers the deflection angle within
  1e-9.

## Validation list (contract test must include)

- shock_angle_weak(3.0, 15.0) = 32.240400 within 1e-6; (2.0, 10.0) =
  39.313932; (2.0, 20.0) = 53.422941; (5.0, 25.0) = 35.779435; (1.5, 5.0)
  = 47.889264.
- Round trip: deflection_angle(M1, shock_angle_weak(M1, theta)) equals
  theta within 1e-9 for those five pairs and for (3.0, 15.0).
- shock_angle_weak(3.0, 0.0) = 19.471221 (Mach angle asin(1/3)); (2.0,
  0.0) = 30.0 exactly; ValueError at theta_deg negative; ValueError when
  theta_deg >= theta_max, e.g. shock_angle_weak(2.0, 22.973532) and
  shock_angle_weak(3.0, 35.0) both raise (detached incident shock).
- maximum_deflection_angle: 3.944187 (M1 = 1.2), 12.112669 (1.5),
  22.973532 (2.0), 34.073440 (3.0), 41.117663 (5.0) within 1e-6;
  ValueError at M1 = 1.0 and below.
- oblique_shock_state(3.0, 15.0): beta_deg 32.240400, Mn1 1.600418, M2
  2.254902, p2_p1 2.821562, rho2_rho1 2.032449, T2_T1 1.388258, p02_p01
  0.895044, each within 1e-6; T2_T1 equals p2_p1 / rho2_rho1 within 1e-12;
  dict keys exactly as documented.
- shock_reflection(3.0, 15.0): verdict "regular"; theta_max_ref_deg
  26.860810 within 1e-6; incident as above; reflected beta_deg 40.349015,
  M2 1.671849 (i.e. M3), p2_p1 2.319922, rho2_rho1 1.793230, T2_T1
  1.293712, p02_p01 0.941981 within 1e-6; reason None.
- Product identities for the regular case: p3_p1 6.545805 within 1e-6 of
  the product of the stage pressure ratios and p03_p01 0.843115 within
  1e-6 of the product of the stage total-pressure ratios; M3 > M2 is
  false (M3 = 1.671849 < M2 = 2.254902, the shock chain decelerates) while
  p2_p1 > 1, p3_p2 > 1, and p02_p01 < 1, p03_p02 < 1 hold stage by stage.
- shock_reflection(2.0, 20.0): verdict "mach"; M2 1.210218,
  theta_max_ref_deg 4.214110 within 1e-6; reflected None; reason string
  non-empty and mentions the detachment limit; verdict "mach" also when
  theta_deg >= theta_max_ref_deg exactly (construct the equality case from
  the (M2, theta_max_ref_deg) pair of any regular incident state and assert
  the reflected branch is not attempted).
- Verdict flip at M1 = 3.0: theta 20.0 regular with margin +2.872253,
  theta 25.0 mach with margin -7.599755 (theta_max_ref_deg 22.872253 and
  17.400245 within 1e-6).
- shock_reflection(3.0, 0.0): verdict "regular", unit ratios, M3 = 3.0.
- Monotonicity identities: for the regular example the flow behind the
  reflected shock is parallel to the wall (net zero turning: the
  deflection round trip at each stage recovers 15 deg exactly); total
  pressure falls across every shock, p03_p01 < p02_p01 < 1.
- Determinism and ValueError coverage across the module: M1 <= 1, negative
  theta, beta outside the open interval, detached incident deflection.
- Fixed verdict and reason strings; no randomness; pure math import only.

## Corpus fragment (eval/hit1-wave41-regular-shock-reflection.yaml)

Query 1 (copy verbatim):
  "compute the regular reflection when the oblique shock from the wedge impinges on the wall, find the reflected shock angle and the post-reflection state, and decide regular versus mach reflection from the reflected-shock detachment limit"
  intent: "high-speed aerodynamics; two-shock regular reflection at the wall, reflected shock angle and post-reflection state, reflected-shock detachment limit verdict"
  expected_skill: "aerodynamics/high-speed/regular-shock-reflection"
Query 2 (copy verbatim):
  "check whether the two-shock interaction of the incident and reflected shocks at the symmetry plane stays regular or turns mach by comparing the required deflection with the reflected-shock detachment limit"
  intent: "high-speed aerodynamics; regular versus mach reflection verdict from the reflected-shock detachment limit at the symmetry plane"
  expected_skill: "aerodynamics/high-speed/regular-shock-reflection"
Task ids: w41-regular-shock-reflection-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the regular reflection of an
oblique shock impinging on a wall or symmetry plane:" and include the
outputs in the Claim (incident and reflected wave angles, intermediate and
post-reflection states, the reflected-shock detachment limit and the
regular-versus-Mach verdict). First tag: regular-shock-reflection.
Additional tags ONLY: reflected-shock, mach-reflection,
two-shock-interaction, post-reflection-state. NEVER single generic words
(shock, reflection, wall, mach, wedge, beta, theta, deflection, wave,
angle). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): wave-angle, theta-beta, weak-
solution, strong-solution, shock-polar, detached-shock, compression-corner
(oblique-shock); normal-shock-relations, stagnation-pressure-loss,
supersonic-inlet (normal-shock); prandtl-meyer, expansion-fan,
expansion-angle, turning-angle (prandtl-meyer); shock-expansion,
diamond-airfoil, double-wedge, surface-pressure-integration,
wave-drag-coefficient, angle-of-attack (shock-expansion-airfoil);
bow-shock-standoff, aerodynamic-heating, hypersonic-flow,
transonic-similarity, swept-wing, supercritical-airfoil,
wave-drag-area-rule, flat-plate-skin-friction-heating (other high-speed
pack leaves). The corpus queries above route on reflection tokens only and
do not collide with the os1/os2 oblique-shock tasks, which route on
wave-angle, weak/strong-branch and stagnation-pressure-loss phrasings.
