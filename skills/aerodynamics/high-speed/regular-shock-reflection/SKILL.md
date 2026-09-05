---
name: regular-shock-reflection
description: "Use when you must compute the regular reflection of an oblique shock impinging on a wall or symmetry plane: solve the weak-branch incident wave angle at the upstream Mach number and deflection, march the state behind it, solve the reflected shock that turns the flow back parallel to the wall, and assemble the post-reflection state from the two shock ratio products. Produces the incident and reflected wave angles, the intermediate and post-reflection Mach numbers, the pressure, density, temperature and stagnation-pressure ratios, the reflected-shock detachment limit and the regular-versus-Mach verdict. Trigger: regular reflection, reflected shock, wall impingement, symmetry plane, two-shock interaction, Mach reflection, post-reflection state."
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
  tags: [regular-shock-reflection, reflected-shock, mach-reflection, two-shock-interaction, post-reflection-state]
  version: 0.1.0
  author: AeroSkills
---

# Regular Shock Reflection (aerodynamics/high-speed/regular-shock-reflection)

When an oblique shock from a wedge impinges on a wall or symmetry plane in
supersonic flow, the wall turns the flow back parallel to itself and a
second oblique shock, the reflected shock, leaves the impingement point.
This leaf computes the classical two-shock REGULAR reflection: it solves
the theta-beta-M relation for the incident weak shock at the upstream Mach
number M1 and deflection angle theta, marches the full state behind the
incident shock, solves theta-beta-M again on that downstream state for the
reflected shock that turns the flow back by the same deflection, and
multiplies the two sets of oblique-shock ratios into the post-reflection
state. It judges the interaction regular when the required reflected
deflection stays below the reflected-shock detachment limit at the
intermediate Mach number M2, and Mach (irregular) otherwise, as the
detachment-criterion flag. It pairs with aerodynamics/high-speed/
oblique-shock for the single-shock weak and strong branch relations it
reuses, with aerodynamics/high-speed/normal-shock for the normal-shock
total-pressure formula evaluated at Mn1, and with aerodynamics/high-speed/
shock-expansion-airfoil where every surface shock is itself an
oblique-shock solve of this kind. Mach-reflection flowfield details
(triple point, Mach stem, slip line) are not modeled, and the von Neumann
transition criterion is not implemented. Deterministic, pure stdlib.

## Domain quick reference

- Theta-beta-M relation solved for the deflection at a shock angle beta:
  tan(theta) = 2 cot(beta) (M1^2 sin^2(beta) - 1) / (M1^2 (gamma +
  cos(2 beta)) + 2), with the Mach angle mu = asin(1 / M1) as the lower
  bound of beta (shock angle strictly between mu and 90 deg).
- Attached-shock detachment limit: maximum_deflection_angle(M1) is the
  peak of that deflection profile over beta from mu to 90 deg, located by
  a deterministic golden-section maximizer. It rises with M1 toward its
  asymptotic maximum: 3.944187 deg at M1 = 1.2, 12.112669 at 1.5,
  22.973532 at 2.0, 34.073440 at 3.0 and 41.117663 at 5.0.
- Weak-branch shock angle: shock_angle_weak(M1, theta) bisects over the
  interval from the Mach angle to the detachment angle, where the
  deflection rises monotonically from 0 to theta_max, with bisection
  tolerance SHOCK_SOLVE_TOL_RAD = 1e-13 radians. It returns the Mach
  angle exactly for theta = 0 and raises ValueError for a detached
  incident deflection (theta at or above theta_max) and for M1 <= 1.
- Oblique-shock ratios behind the incident wave, with Mn1 = M1 sin(beta):
  rho2/rho1 = (gamma + 1) Mn1^2 / ((gamma - 1) Mn1^2 + 2), p2/p1 = 1 +
  2 gamma (Mn1^2 - 1) / (gamma + 1), T2/T1 = p2/p1 / (rho2/rho1),
  Mn2^2 = (Mn1^2 + 2/(gamma - 1)) / (2 gamma Mn1^2/(gamma - 1) - 1),
  M2 = Mn2 / sin(beta - theta), and p02/p01 from the standard
  normal-shock total-pressure formula at Mn1 (name and paraphrase only,
  NACA-TR-824 style compressible-flow relations).
- Reflection geometry: the straight wall forces the reflected shock to
  impose the same deflection as the incident shock, theta_ref =
  theta_inc, on the intermediate state at M2 (oblique_shock_state(M2,
  theta_deg) for a regular verdict).
- Verdict: regular when M2 > 1 and theta < theta_max_ref_deg, where
  theta_max_ref_deg = maximum_deflection_angle(M2) is the reflected-shock
  detachment limit and the margin is theta_max_ref_deg - theta. Mach
  (irregular) when M2 <= 1 or theta reaches or exceeds that limit.
- Post-reflection state (regular only), assembled as products of the two
  stage ratio sets: M3 = reflected M2, p3/p1 = p2/p1(incident) x p2/p1
  (reflected), and likewise rho3/rho1, T3/T1, p03/p01; total pressure
  falls across every shock and static pressure climbs stage by stage.
- Module constants: GAMMA = 1.4, SHOCK_SOLVE_TOL_RAD = 1e-13.

## Workflow

1. Fix the freestream: the upstream Mach number M1 and the flow
   deflection theta_deg that the incident shock must impose, set by the
   wedge or wall geometry (default gamma = GAMMA = 1.4).
2. Solve the incident shock: shock_angle_weak(M1, theta_deg) returns the
   weak-branch wave angle; back-check it with the deflection round trip
   deflection_angle(M1, beta_deg) == theta_deg, and confirm the incident
   shock is attached, theta_deg below maximum_deflection_angle(M1).
3. March the state behind the incident shock: oblique_shock_state(M1,
   theta_deg) returns beta_deg, Mn1, Mn2, M2 and the pressure, density,
   temperature and stagnation-pressure ratios p2_p1, rho2_rho1, T2_T1,
   p02_p01.
4. Evaluate the reflected-shock detachment limit: maximum_deflection_angle
   at the intermediate Mach number M2 gives theta_max_ref_deg; the margin
   is theta_max_ref_deg - theta_deg.
5. Judge the reflection: shock_reflection(M1, theta_deg) returns verdict
   "regular" when M2 > 1 and theta_deg stays below the limit, otherwise
   verdict "mach" with reflected None and a fixed reason string; a
   detached incident deflection raises ValueError, it does not return a
   verdict.
6. Solve the reflected shock and assemble the post-reflection state (for
   a regular verdict): oblique_shock_state(M2, theta_deg) is the
   reflected stage, M3 is its downstream Mach number, and p3_p1, rho3_rho1,
   T3_T1 and p03_p01 are the products of the incident and reflected stage
   ratios; the equal-and-opposite deflections leave the flow parallel to
   the wall (net zero turning).
7. Report the interaction: incident and reflected wave angles, the
   intermediate and post-reflection Mach numbers, the stage and overall
   ratio sets, the reflected-shock detachment limit, the margin and the
   regular-versus-Mach verdict.

## Worked example

Standard air, gamma = 1.4. Values are real module outputs (rounded to six
decimal places), within the spec magnitude bounds.

- Regular reflection, M1 = 3.0, theta = 15 deg (shock_reflection(3.0,
  15.0), verdict "regular"):
  - Incident stage (oblique_shock_state): beta_inc = 32.240400 deg, Mn1 =
    1.600418, M2 = 2.254902, p2/p1 = 2.821562, rho2/rho1 = 2.032449,
    T2/T1 = 1.388258, p02/p01 = 0.895044.
  - Reflected-shock detachment limit: theta_max_ref_deg = 26.860810 deg,
    margin = +11.860810 deg, so the reflection is regular.
  - Reflected stage (oblique_shock_state at M2): beta_ref = 40.349015 deg
    (about 8.1 deg steeper than the incident wave), Mn1 = 1.459918, M3 =
    1.671849, p3/p2 = 2.319922, rho3/rho2 = 1.793230, T3/T2 = 1.293712,
    p03/p02 = 0.941981. The reflected shock is the weaker of the two
    (smaller Mn1, total-pressure ratio closer to 1).
  - Post-reflection state over freestream: p3/p1 = 6.545805, rho3/rho1 =
    3.644571 (product 2.032449 x 1.793230), p03/p01 = 0.843115, M3 =
    1.671849, flow parallel to the wall. The chain decelerates (M3 < M2 <
    M1) while static pressure climbs and total pressure falls at every
    stage.
- Mach reflection verdict, M1 = 2.0, theta = 20 deg: beta_inc = 53.422941
  deg, M2 = 1.210218, theta_max(M2) = 4.214110 deg; the required reflected
  deflection of 20 deg far exceeds the 4.214110 deg limit, verdict "mach",
  reflected None, reason reports the reflected-shock detachment limit.
  This is the detachment-criterion flag only, the Mach stem and triple
  point are not computed.
- Verdict boundary probe at M1 = 3.0: theta 5 deg (M2 = 2.749709, limit
  32.171032, margin +27.171032), theta 10 deg (M2 = 2.505001, limit
  29.850539, margin +19.850539) and theta 20 deg (M2 = 1.994132, limit
  22.872253, margin +2.872253) are all regular; theta 25 deg (M2 =
  1.717258, limit 17.400245, margin -7.599755) is mach. The transition
  deflection for M1 = 3.0 lies between 20 and 25 deg.
- Degenerate zero deflection: shock_angle_weak(3.0, 0.0) = 19.471221 deg,
  the Mach angle for M1 = 3.0; oblique_shock_state(3.0, 0.0) returns M2 =
  3.0 with unit ratios; shock_reflection(3.0, 0.0) is "regular" with unit
  ratios throughout and M3 = 3.0.
- Round trips: shock_angle_weak(3.0, 15.0) = 32.240400 deg and
  deflection_angle(3.0, 32.240400) = 15.0 deg; the same closure holds for
  (2.0, 10.0) -> 39.313932 deg, (2.0, 20.0) -> 53.422941 deg, (5.0, 25.0)
  -> 35.779435 deg and (1.5, 5.0) -> 47.889264 deg, each within 1e-9.

## Verification

- Run the module functions on the worked example above and confirm the
  outputs fall inside the stated bounds, with verdict "regular" at (3.0,
  15.0) and "mach" at (2.0, 20.0).
- Round-trip identity: deflection_angle(M1, shock_angle_weak(M1, theta))
  equals theta within 1e-9 at every stage of a regular reflection, so the
  flow leaves the reflected shock parallel to the wall (net zero
  turning).
- Product identity: p3_p1 and p03_p01 equal the products of the stage
  ratios within 1e-6, with pressures climbing strictly (p3 > p2 > p1) and
  total pressure falling (p03 < p02 < p01).
- Verdict flip: the verdict switches from regular to mach as the required
  deflection crosses the reflected-shock detachment limit (M1 = 3.0,
  between theta 20 and 25 deg).
- ValueError rejection: M1 <= 1, negative deflection, a shock angle
  outside the open interval (Mach angle, 90 deg), and a detached incident
  deflection (theta at or above theta_max) all raise ValueError, in
  deflection_angle, maximum_deflection_angle, shock_angle_weak,
  oblique_shock_state and shock_reflection as applicable.
- Determinism: no randomness anywhere; repeated calls return identical
  dicts. Confirm with the contract test below.

## Related leaves

- aerodynamics/high-speed/oblique-shock: the single-turn theta-beta-M
  solver with weak and strong branches and shock polar basics that this
  leaf reuses for each of its two shocks.
- aerodynamics/high-speed/normal-shock: the five-ratio normal-shock
  relations behind the total-pressure formula evaluated at Mn1 here.
- aerodynamics/high-speed/shock-expansion-airfoil: the four-surface airfoil
  patch whose surface shocks are individual oblique-shock solves.
- aerodynamics/high-speed/prandtl-meyer: the expansion-fan counterpart for
  the corners where the flow turns away from the wall.

## Contract test

Run offline from the leaf directory or the repo root:

    python3 scripts/test_regular_shock_reflection.py

The stdlib unittest contract (35 methods, deterministic, under 1 second)
covers the SKILL.md workflow steps 1 to 7: weak-branch incident shock
angles at the reference Mach numbers, the theta-beta-M deflection round
trip, Mach-angle and zero-deflection degeneracies, the golden-section
detachment limits, the full incident state march and its ratio identities,
the regular verdict with the reflected-shock solve and the post-reflection
product assembly, the mach verdict at the detachment limit with the fixed
reason string, the subsonic-downstream branch, the verdict flip at M1 =
3.0, the detachment-equality boundary, and ValueError rejection of
non-physical inputs, plus module constants and determinism.

## Compliance

- compliance: STANDARDS-REF, gated: false.
- Standards referenced, not reproduced: NACA-TR-824 (id naca-tr-824 in
  standards-map.yaml) frames the oblique-shock and normal-shock relations;
  the formulas above are standard compressible-flow methodology,
  summary-only, never verbatim standard text.

## Pitfalls

- Letting the reflected deflection float: the straight wall fixes the
  reflected deflection equal to the incident one, theta_ref = theta_inc,
  because the flow must leave parallel to the wall. Solving the reflected
  stage at any other deflection produces a state the geometry cannot
  sustain.
- Judging the verdict on the incident limit alone: the reflected shock
  operates at the reduced Mach number M2, so its detachment limit is
  theta_max(M2), not theta_max(M1). At M1 = 3.0 the incident limit is
  34.073 deg, but the reflected limit has already fallen to 17.400 deg by
  theta = 25 deg, which is why that deflection is mach, not regular.
- Calling the reflected solve on a subsonic intermediate state: a
  near-detachment weak incident shock at low Mach can leave M2 <= 1
  (M1 = 1.2, theta 3.74698 gives M2 = 0.994678); no oblique reflected
  shock exists there, shock_reflection returns verdict "mach" with
  theta_max_ref_deg 0.0, and oblique_shock_state on that M2 would raise
  ValueError.
- Reading the mach verdict as a modeled flowfield: the verdict is the
  detachment-criterion flag only. The Mach stem, triple point, slip line
  and the von Neumann transition criterion are not implemented, so the
  result says regular reflection cannot be sustained, not what the
  irregular flow looks like.
- Quoting stage ratios as the overall state: the post-reflection ratios
  over freestream are the products of the two stages (p3/p1 = 6.545805 =
  2.821562 x 2.319922 in the worked example); quoting the incident stage
  alone understates the compression and overstates the total-pressure
  recovery p03/p01 = 0.843115.
- Forgetting that the shock chain decelerates: M3 = 1.671849 is below M2 =
  2.254902, so a "post-reflection Mach number" above the intermediate
  value signals a stage mix-up, not a physical result.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, pure
Python, no network):

    python3 scripts/test_regular_shock_reflection.py

The test must exit 0 with 35 methods passing. It pins the worked-example
outputs (regular verdict at M1 = 3.0, theta 15 deg with the incident and
reflected states, detachment limit 26.860810 deg and margin +11.860810;
mach verdict at M1 = 2.0, theta 20 deg with limit 4.214110), the
theta-beta-M round trips within 1e-9, the post-reflection product
identities, the verdict flip across the reflected-shock detachment limit,
ValueError rejection of every non-physical input class, and deterministic,
fixed-string verdicts with no randomness.
