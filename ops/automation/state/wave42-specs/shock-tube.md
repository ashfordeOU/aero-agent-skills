# Wave-42 leaf spec: shock-tube (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/shock-tube/
- Pack: high-speed (verified present at prep with the 12 sibling leaves
  aerodynamic-heating, bow-shock-standoff, flat-plate-skin-friction-heating,
  hypersonic-flow, normal-shock, oblique-shock, prandtl-meyer,
  regular-shock-reflection, shock-expansion-airfoil, supercritical-airfoil,
  swept-wing-aerodynamics, transonic-similarity, wave-drag-area-rule).
  Closest siblings: normal-shock (stationary shock GIVEN the upstream Mach
  number only: its frontmatter claim is "find the downstream Mach number,
  static pressure, density, and temperature ratios across the shock, and the
  stagnation pressure loss from the upstream Mach number"; it never
  determines the shock Mach number from a diaphragm pressure state, does not
  know the driver gas, and has no moving-shock or unsteady-wave content),
  oblique-shock (steady single-turn waves: "compute the wave angle beta from
  the upstream Mach number M1 and the flow deflection angle theta with the
  theta-beta-M relation, find the weak and strong solutions, the maximum
  deflection angle for an attached shock, and the downstream Mach number,
  static pressure, density, temperature, and stagnation pressure ratios
  across the shock"; its body note "The functions raise instead of returning
  a fake wave angle" and its theta-beta-M inversion are the accepted
  implicit-solve precedent for the one root here), prandtl-meyer (steady
  turning fans only: "derive the expansion angle from the Mach number, find
  the downstream Mach number after the flow turns away from itself by a
  given angle, compute the total turning angle across the expansion fan, and
  the static pressure ratio across it"; its deterministic inversion is
  documented in the body as "Bisection on the bracket [1, 50] is
  deterministic and offline"), isentropic-flow-relations (steady area-Mach
  and choked-mass-flow inversions only, mach_from_area_ratio by bisection:
  no unsteady diaphragm wave motion). Whole-tree greps at prep: "shock tube"
  = 0 hits, "diaphragm" = 0 hits, "contact surface" = 0 hits across all of
  skills/ (SKILL.md bodies and scripts; exit 1). GENUINE AERO gap (fresh
  probe): no leaf solves the unsteady diaphragm-driven wave system of the
  classical shock tube, pairs driver and driven gases, or recovers the
  incident-shock Mach number from a pressure ratio; no propulsion leaf owns
  shock-tube facility analysis (0 token hits).
- Standards id: naca-tr-824 (reference-only, matching every high-speed
  sibling and present in standards-map.yaml). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Solve the classical shock-tube problem: from the driver-to-driven diaphragm
pressure ratio p4/p1, the driver sound-speed ratio a4/a1 and the two
specific heat ratios (gamma4 may differ from gamma1), recover the
incident-shock Mach number Ms by deterministic bisection of the implicit
shock-tube equation that matches pressure across the contact surface, then
produce the post-shock state of the driven gas (p2/p1, T2/T1, rho2/rho1
from the normal-shock relations at Ms plus the absolute post-shock pressure,
temperature, density and sound speed), the contact-surface velocity u2 = u3
(the induced flow speed shared by the shocked driven gas and the expanded
driver gas, the same value from the shock side and from the expansion side)
with the region-2 flow Mach number, the driver expansion-fan ratios
p3/p4, T3/T4, rho3/rho4 with the region-3 absolute state and flow Mach
number, the fan head wave speed into the quiescent driver gas and the fan
tail wave speed (each boundary of the centered expansion is a Mach wave
relative to the gas it propagates into), and the full four-region state
table of pressure, temperature, density, velocity, sound speed and Mach
number. Produces Ms, the post-shock and expansion ratios, the contact
velocity, the fan head and tail speeds, and the region-by-region state
table that gate shock-tube facility design, driver-gas selection and
high-speed gas-dynamics coursework. Does NOT do: static ratios across a
stationary normal shock at a given upstream Mach number (normal-shock);
wave-angle and weak/strong-branch oblique-shock analysis (oblique-shock);
steady Prandtl-Meyer expansion-fan turning (prandtl-meyer); area-Mach and
choked-mass-flow inversions (isentropic-flow-relations); reflected-shock
wall interactions (regular-shock-reflection). Scope: the classical
one-dimensional perfect-gas shock tube with a single incident shock, a
contact surface and a single centered expansion fan; region-4 and region-1
gases initially at rest. Reflected-shock interaction with the end walls
after the first transit is NOT modeled. Deterministic, pure stdlib.

## Model (implement exactly)

Implicit shock-tube equation (pressure match p2 = p3 across the contact
surface; the standard form):

  p2/p1 (normal shock at Ms) = (p4/p1) * [1 - (gamma4 - 1) / (gamma1 + 1)
                              * (a1 / a4) * (Ms - 1 / Ms)] ** (2 gamma4 /
                              (gamma4 - 1))

with p2/p1 = 1 + 2 gamma1 (Ms^2 - 1) / (gamma1 + 1) on the left and the
isentropic unsteady expansion p3/p4 = (1 - (gamma4 - 1) u3 / (2 a4))
** (2 gamma4 / (gamma4 - 1)) with u3 = u2 and u2 / a4 = (2 / (gamma1 + 1))
(a1 / a4) (Ms - 1 / Ms) on the right. The residual, left minus right, is
strictly increasing in Ms over the physical interval, so the root is
unique; the expansion bracket stays positive only for (Ms - 1 / Ms) < C =
(gamma1 + 1) a4_a1 / (gamma4 - 1), giving the Ms ceiling
Ms_lim = (C + sqrt(C^2 + 4)) / 2. Bisection note: deterministic bisection
on [1 + 1e-12, Ms_lim (1 - 1e-12)] to the module tolerance BISECT_TOL =
1e-12 (max MAX_ITER = 200 iterations, no RNG, identical inputs give
identical bits), the sibling-accepted implicit-solve pattern of the
oblique-shock theta-beta-M solve and the prandtl-meyer and
isentropic-flow-relations bisections.

Functions (pure stdlib, math only):
- normal_shock_ratios(shock_mach, gamma = GAMMA_AIR) -> dict with keys
  "p2_p1", "rho2_rho1", "T2_T1": p2_p1 = 1 + 2 gamma (shock_mach^2 - 1) /
  (gamma + 1), rho2_rho1 = (gamma + 1) shock_mach^2 / (2 + (gamma - 1)
  shock_mach^2), T2_T1 = p2_p1 / rho2_rho1 (name and paraphrase only, the
  standard normal-shock relations); ValueError if shock_mach <= 1 or
  gamma <= 1.
- induced_velocity(shock_mach, a1, gamma = GAMMA_AIR) -> float
  u2 = 2 a1 (shock_mach - 1 / shock_mach) / (gamma + 1), the lab-frame
  particle velocity behind a shock moving at shock_mach * a1 into gas at
  rest; ValueError if shock_mach <= 1, a1 <= 0 or gamma <= 1.
- expansion_pressure_ratio(u_over_a4, gamma4) -> float p3/p4 =
  (1 - (gamma4 - 1) u_over_a4 / 2) ** (2 gamma4 / (gamma4 - 1)), the
  unsteady centered-expansion ratio; ValueError if gamma4 <= 1 or the
  bracket 1 - (gamma4 - 1) u_over_a4 / 2 <= 0 (expansion velocity beyond
  the full-expansion limit).
- shock_tube_residual(shock_mach, p4_p1, a4_a1, gamma1 = GAMMA_AIR,
  gamma4 = GAMMA_AIR) -> float: normal_shock_ratios(shock_mach, gamma1)
  ["p2_p1"] minus p4_p1 times expansion_pressure_ratio(u2_over_a4, gamma4)
  with u2_over_a4 = 2 (shock_mach - 1 / shock_mach) / ((gamma1 + 1)
  a4_a1); zero at the physical root; ValueErrors as in the components.
- incident_shock_mach(p4_p1, a4_a1 = 1.0, gamma1 = GAMMA_AIR,
  gamma4 = GAMMA_AIR) -> float Ms by the deterministic bisection above,
  returning the bracket midpoint; ValueError if p4_p1 <= 1 (a driver
  overpressure is required), a4_a1 <= 0, gamma1 <= 1, gamma4 <= 1, or no
  sign change appears on the physical bracket.
- shock_tube_state(p4_p1, a4_a1 = 1.0, gamma1 = GAMMA_AIR,
  gamma4 = GAMMA_AIR, p1 = 101325.0, t1 = 288.15, r_gas = R_AIR) -> dict
  with keys exactly "Ms", "p2_p1", "rho2_rho1", "T2_T1", "u2", "p2", "T2",
  "rho2", "a2", "M2_lab", "a1", "rho1", "p1", "p3_p4", "T3_T4",
  "rho3_rho4", "p3", "T3", "rho3", "a3", "M3_lab", "u3", "p4", "T4",
  "rho4", "a4", "fan_head_speed", "fan_tail_speed", "residual". Builds Ms
  = incident_shock_mach(...), a1 = sqrt(gamma1 r_gas t1), the region-2
  absolute state from the shock ratios and u2 = induced_velocity(Ms, a1,
  gamma1) with M2_lab = u2 / a2; driver-side absolute states assume the
  same specific gas constant for both gases (documented assumption), so
  T4 = t1 a4_a1^2 gamma1 / gamma4 and a4 = sqrt(gamma4 r_gas t4), p4 =
  p4_p1 p1; region 3 sits between the contact surface and the fan tail
  with u3 = u2 and p3 = p2 by construction, T3_T4 = (1 - (gamma4 - 1)
  u3 / (2 a4))^2, p3_p4 = expansion_pressure_ratio(u3 / a4, gamma4),
  rho3_rho4 = p3_p4 / T3_T4, a3 = sqrt(gamma4 r_gas t3), M3_lab = u3 / a3;
  fan_head_speed = a4 (leftward into the quiescent driver gas) and
  fan_tail_speed = u3 - a3 (lab frame, right-positive; both fan boundaries
  are Mach waves relative to the gas they move through); "residual" is
  shock_tube_residual at the returned Ms. ValueErrors if p1 <= 0, t1 <= 0,
  r_gas <= 0, plus all component ValueErrors.
Module constants: GAMMA_AIR = 1.4, R_AIR = 287.0, BISECT_TOL = 1e-12,
MAX_ITER = 200.

Identity to test: at the root the contact-surface match is exact, p3 - p2
below 1e-6 Pa and u3 - u2 exactly 0 in the state dict; the residual
shock_tube_residual(Ms, ...) is below 1e-10; u2 recovered from the
closed form 2 a1 (Ms - 1 / Ms) / (gamma1 + 1) equals the state u2 to
floating point; the shock-frame downstream Mach Mn2 =
sqrt((1 + (gamma1 - 1) Ms^2 / 2) / (gamma1 Ms^2 - (gamma1 - 1) / 2)) with
u2 = Ms a1 - Mn2 a2 recovers the same u2; p2 / (rho2 R T2) = 1.0 (ideal
gas); p2/p1 from the state equals the closed form 1 + 2 gamma1 (Ms^2 - 1)
/ (gamma1 + 1); p3_p4 * p4_p1 equals p2_p1 within bisection tolerance;
Ms grows monotonically with p4_p1 at fixed a4_a1 and gammas and the
contact velocity saturates toward the full-expansion limit.

## Worked example

Air driver and driven gas, gamma1 = gamma4 = 1.4, R = 287.0, a4/a1 = 1
(T4 = T1), p1 = 101325 Pa, T1 = 288.15 K, p4/p1 = 40:
- incident-shock Mach number Ms = 2.057576505; shock speed Ws = Ms a1 =
  700.1164 m/s.
- Post-shock ratios: p2/p1 = 4.772557918, T2/T1 = 1.734842373,
  rho2/rho1 = 2.751003776; absolute state p2 = 483579.43 Pa, T2 =
  499.89 K, rho2 = 3.370600480 kg/m3, a2 = 448.1716 m/s.
- Contact (induced) velocity u2 = u3 = 445.6215 m/s (u2 = 445.621531021
  m/s from the closed form, identical to the printed state to the last
  digit); region-2 lab-frame flow Mach M2_lab = 0.994310161 with
  shock-relative downstream Mach Mn2 = 0.567851523; region-3 flow Mach
  M3_lab = 1.774406595 (the expanded driver stream is supersonic in the
  lab frame while the shocked driven stream is just subsonic, the two
  states meeting at the contact surface).
- Driver expansion ratios: p3/p4 = 0.119313948, T3/T4 = 0.544750315,
  rho3/rho4 = 0.219025019; absolute region-3 state p3 = 483579.43 Pa (=
  p2 to 6e-8 Pa), T3 = 156.97 K, rho3 = 10.734203118 kg/m3, a3 =
  251.1383 m/s, u3 = 445.6215 m/s.
- Fan boundaries: head wave speed 340.2626 m/s leftward into the
  quiescent driver gas (a4 = 340.2626 m/s, a Mach wave relative to the
  driver gas, M_head = 1.0); tail wave speed u3 - a3 = 194.4832 m/s
  rightward in the lab frame (the strong driver has swept the tail
  downstream; still a Mach wave relative to region-3 gas). Sound speeds:
  a1 = a4 = 340.2626 m/s.
- Four-region state table (p Pa, T K, rho kg/m3, u m/s):
  region 1: p = 101325.00, T = 288.15, rho = 1.225225683, u = 0.0000,
  M = 0.000000000
  region 2: p = 483579.43, T = 499.89, rho = 3.370600480, u = 445.6215,
  M = 0.994310161
  region 3: p = 483579.43, T = 156.97, rho = 10.734203118, u = 445.6215,
  M = 1.774406595
  region 4: p = 4053000.00, T = 288.15, rho = 49.009027310, u = 0.0000,
  M = 0.000000000
  Contact check from the state dict: p3 - p2 = -6.041955e-08 Pa, u3 - u2
  = 0.000000e+00 m/s, pressure-match residual at Ms = 5.959677e-13.
- Driver-strength family (air/air, a4/a1 = 1, T1 = 288.15 K): p4/p1 =
  1.2 gives Ms = 1.039831292, p2/p1 = 1.094790636, u2 = 22.1559 m/s,
  T2 = 295.71 K; p4/p1 = 2.0 gives Ms = 1.159478862, p2/p1 =
  1.401789770, u2 = 84.2214 m/s, T2 = 317.70 K; p4/p1 = 5.0 gives Ms =
  1.402408030, u2 = 195.4664 m/s, T2 = 361.99 K; p4/p1 = 10.0 gives Ms =
  1.607525211, u2 = 279.4268 m/s, T2 = 401.44 K; p4/p1 = 100.0 gives Ms
  = 2.371054059, u2 = 552.7285 m/s, T2 = 580.01 K; p4/p1 = 1000.0 gives
  Ms = 3.150486214, u2 = 803.3246 m/s, T2 = 824.23 K (Ms and u2 grow
  monotonically with the driver overpressure).
- General-gamma case, helium driver (gamma4 = 5/3) at p4/p1 = 40,
  a4/a1 = 2.4 over air: Ms = 2.698174185, p2/p1 = 8.326834585, T2/T1 =
  2.340950220, u2 = 659.9828 m/s, p3/p4 = 0.208170865, T3 = 744.20 K
  (the light fast driver gas nearly doubles the contact velocity of the
  air/air case at the same pressure ratio).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor script
/tmp/w42spec/anchor_shock_tube.py (prep-verified by stdlib math; the
p4/p1 = 2.0 row cross-checks the standard chart value p2/p1 ~ 1.40 at
Ms ~ 1.16).

## Validation list (contract test must include)

- incident_shock_mach(40.0, 1.0) = 2.057576505 within 1e-9; the residual
  shock_tube_residual at that Ms is below 1e-10.
- shock_tube_state(40.0, 1.0): p2_p1 4.772557918, rho2_rho1
  2.751003776, T2_T1 1.734842373 each within 1e-9; u2 445.6215 m/s
  within 1e-3 (and equal to induced_velocity(Ms, a1) within 1e-9);
  p3_p4 0.119313948, T3_T4 0.544750315, rho3_rho4 0.219025019 within
  1e-9; p3 equals p2 within 1e-3 Pa and u3 equals u2 exactly;
  p3_p4 * 40.0 equals p2_p1 within 1e-9; dict keys exactly as
  documented.
- Driver-strength family: incident_shock_mach values 1.039831292 (1.2),
  1.159478862 (2.0), 1.402408030 (5.0), 1.607525211 (10.0),
  2.371054059 (100.0), 3.150486214 (1000.0) each within 1e-9, with p2_p1
  and u2 matching the worked-example rows within 1e-6 relative; Ms and u2
  strictly increasing in p4_p1.
- General-gamma path: incident_shock_mach(40.0, 2.4, 1.4, 5.0/3.0) =
  2.698174185 within 1e-9 with p2_p1 8.326834585, T2_T1 2.340950220,
  u2 659.9828 within 1e-3, p3_p4 0.208170865 within 1e-9.
- Identity checks: p2 / (rho2 R T2) = 1.0 within 1e-9; p2_p1 equals the
  closed form 1 + 2 gamma1 (Ms^2 - 1) / (gamma1 + 1) within 1e-12;
  u2 equals 2 a1 (Ms - 1/Ms) / (gamma1 + 1) within 1e-9 and equals
  Ms a1 - Mn2 a2 within 1e-6, with Mn2 =
  sqrt((1 + (gamma1 - 1) Ms^2 / 2) / (gamma1 Ms^2 - (gamma1 - 1) / 2));
  M2_lab = u2 / a2 and M3_lab = u3 / a3 to floating point; fan_tail_speed
  = u3 - a3 exactly.
- Edge and domain ValueErrors: p4_p1 = 1.0 and below raise in
  incident_shock_mach and shock_tube_state; a4_a1 = 0 and negative raise;
  gamma1 = 1.0 and gamma4 = 1.0 raise; p1 = 0, t1 = 0, r_gas = 0 raise;
  expansion_pressure_ratio with u_over_a4 at or above 2 / (gamma4 - 1)
  raises (e.g. u_over_a4 = 5.0 at gamma4 = 1.4); normal_shock_ratios at
  shock_mach = 1.0 raises; induced_velocity at a1 = 0 raises.
- Near-limit behavior: at fixed gammas and a4_a1 the root stays below the
  bracket ceiling Ms_lim and approaches it only as p4_p1 grows without
  bound (p4_p1 = 1000.0 row: Ms = 3.150486214 well inside the air/air
  ceiling 6.162277660).
- Determinism: two calls of incident_shock_mach on the same input return
  identical bits; pure math import only; no randomness; fixed dict key
  set.

## Corpus fragment (eval/hit1-wave42-shock-tube.yaml)

Query 1 (copy verbatim):
  "compute the incident-shock-mach number and post-shock state of a shock-tube run from the driver-to-driven diaphragm-pressure-ratio, driver sound-speed ratio and gamma ratio"
  intent: "high-speed aerodynamics; classical shock-tube problem, incident-shock Mach number from the diaphragm pressure ratio and the post-shock state of the driven gas"
  expected_skill: "aerodynamics/high-speed/shock-tube"
Query 2 (copy verbatim):
  "determine the contact-surface-velocity and the expansion-fan head and tail Mach numbers for a given shock-tube driver gas and driven gas condition"
  intent: "high-speed aerodynamics; shock-tube contact-surface velocity and the driver expansion wave head and tail states for a given driver and driven gas pair"
  expected_skill: "aerodynamics/high-speed/shock-tube"
Task ids: w42-shock-tube-1 and -2.
Routing collision notes: both queries carry the shock-tube, diaphragm and
contact-surface vocabulary that has zero pre-existing corpus claims (0
hits repo-wide at prep), so no token set collides with the prandtl-meyer
tasks (which route on steady turning-angle and expansion-fan phrasings
with no shock-tube, diaphragm or contact-surface tokens), the
normal-shock tasks (ratio-table phrasings at a given Mach number), or the
oblique-shock tasks (wave-angle and deflection-angle phrasings). The word
sequence "expansion-fan head and tail Mach numbers" in query 2 is bound to
the shock-tube context by the driver/driven-gas and contact-surface tokens
in the same query.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine the four-region state of
a shock-tube run from the driver-to-driven diaphragm pressure ratio and
driver sound-speed ratio:" and include the outputs in the Claim
(incident-shock Mach number, post-shock and driver-expansion ratios, the
contact-surface velocity and the fan head and tail states). First tag:
shock-tube. Additional tags ONLY: diaphragm-pressure-ratio,
incident-shock-mach-number, contact-surface-velocity. NEVER single generic
words (shock, tube, diaphragm, pressure, ratio, velocity, mach, driver,
driven, gas, region, wave, flow, expansion, compressible, supersonic,
fan). 50-150 words, <=1000 chars, no em dash, no banned content-policy
word, action verb present. The Claim and SKILL body may name "deterministic
bisection" as the implementation note, but description, tags and corpus
queries must route on the diaphragm and shock-tube physics vocabulary and
never on a generic solving method.

FORBIDDEN TOKENS (belong to siblings): normal-shock-relations,
shock-ratios, stagnation-pressure-loss, total-pressure-loss,
supersonic-inlet (normal-shock); theta-beta-m, wave-angle, deflection-
angle, shock-polar, weak-solution, strong-solution, detached-shock,
compression-corner, wedge (oblique-shock); prandtl-meyer-angle,
turning-angle, isentropic-expansion, downstream-mach (prandtl-meyer);
mach-from-area-ratio, choked-mass-flow, total-to-static-ratio
(isentropic-flow-relations); regular-shock-reflection, mach-reflection,
two-shock-interaction, reflected-shock (regular-shock-reflection);
bow-shock-standoff, aerodynamic-heating, hypersonic-flow,
transonic-similarity, swept-wing, supercritical-airfoil,
wave-drag-area-rule, flat-plate-skin-friction-heating (other high-speed
pack leaves). The single-word token "expansion-fan" is prandtl-meyer tag
territory: the description and tags never use it (they say driver
expansion wave states, fan head and tail speeds only in the hyphenated
tag-free claim sense with shock-tube context), and only corpus query 2
carries the bound phrase per the routing note above.
