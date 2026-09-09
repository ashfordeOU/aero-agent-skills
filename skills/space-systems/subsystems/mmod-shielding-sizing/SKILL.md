---
name: mmod-shielding-sizing
description: "Use when you must size meteoroid and orbital debris (MMOD) impact protection: compute the Cour-Palais cratering penetration depth and critical projectile diameter of a single aluminum wall, size a Whipple shield bumper and rear wall so a design projectile at its design impact produces no rear-wall penetration, evaluate the Christiansen ballistic limit across low, intermediate, and hypervelocity regimes with the 3 and 7 km/s normal-velocity transitions and the 65 degree obliquity cap, and grade an impact as penetration or no penetration against the critical diameter. Produces the required rear-wall thickness for the no-penetration condition, the ballistic-limit curve over velocity, and the mission penetration probability from the expected number of penetrating impacts. Debris fluence and expected-impact inputs come from the space environment leaf; no environment model is built. Trigger: micrometeoroid, whipple shield, hypervelocity impact, ballistic limit, bumper sizing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: subsystems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: subsystems
  tags: [mmod-shielding-sizing, mmod-protection, hypervelocity-impact, whipple-shield, ballistic-limit, micrometeoroid-shielding, debris-penetration-risk]
  version: 0.1.0
  author: AeroSkills
---

# MMOD Shielding Sizing (space-systems/subsystems/mmod-shielding-sizing)

Use when the task is sizing the hypervelocity meteoroid and orbital
debris (MMOD) impact protection of a spacecraft wall with the NASA/JSC
ballistic-limit equation family: the single-wall ballistic limit
through the Cour-Palais cratering equation, and the Whipple shield
through the Christiansen new-non-optimum ballistic limit equations. It
pairs with space-systems/mission-design/radiation-debris for the
debris flux and collision-probability environment inputs, and with
space-systems/subsystems/thermal-design and
space-systems/subsystems/propellant-tank-sizing as sibling spacecraft
bus subsystem sizing leaves.

Units convention (the handbook units, stated once): thicknesses and
diameters in cm, densities in g/cm^3, velocities in km/s, yield stress
in ksi, impact angle in degrees from the target normal, mass in g.

## Domain quick reference

- Single-wall Cour-Palais cratering, eqs (4-1)/(4-2): for the density
  ratio r = rho_p / rho_t, P_inf = 5.24 d^(19/18) BHN^(-1/4) r^n
  (V cos(theta) / C_t)^(2/3), with n = 1/2 for r < 1.5 and n = 2/3 for
  r >= 1.5. C_t is the target sound speed, BHN the target Brinell
  hardness.
- Single-wall damage thresholds, eqs (4-3) to (4-5): required
  thickness t = k P_inf with k = 1.8 (perforation, the default damage
  mode), 2.2 (detached spall), 3.0 (incipient spall); eq (4-6) inverts
  the relation to the critical diameter dc at a given wall thickness.
- Whipple bumper design, eq (4-21): tb = cb d rho_p / rho_b, with
  cb = 0.25 for standoff ratio S/d < 30 and cb = 0.20 for S/d >= 30.
- Whipple rear-wall design, eq (4-22), valid only for a normal impact
  velocity Vn = V cos(theta) >= 7 km/s: tw = 0.16 d^(1/2)
  (rho_p rho_b)^(1/6) Mp^(1/3) Vn (70/sigma)^(1/2) / S^(1/2), with Mp
  the projectile mass (defaulting to the sphere mass (pi/6) rho_p d^3)
  and sigma the rear-wall yield stress in ksi.
- Whipple ballistic limit, three Vn regimes with the impact angle
  capped at 65 degrees (eq 4-26) before Vn is formed: the low-velocity
  equation (eq 4-24) for Vn <= 3 km/s, an exact linear interpolation
  (eq 4-25) between the low-velocity anchor at Vn = 3 and the
  hypervelocity anchor at Vn = 7 for 3 < Vn < 7, and the hypervelocity
  equation (eq 4-23) dc = 3.918 tw^(2/3) rho_p^(-1/3) rho_b^(-1/9)
  Vn^(-2/3) S^(1/3) (sigma/70)^(1/3) for Vn >= 7. The hypervelocity
  regime depends on Vn only, not on V and theta separately.
- Per-impact verdict: margin = d / dc; margin >= 1 is PENETRATION,
  margin < 1 is NO_PENETRATION.
- Mission rollup: penetration_probability(lambda) = 1 - exp(-lambda),
  the Poisson probability of at least one penetrating impact, where
  lambda (the expected number of penetrating impacts) is a GIVEN input
  assembled from the environment leaf's flux at and above dc, not
  computed here.
- All equations are the published closed forms of Christiansen et al.,
  NASA TM-2009-214789 (JSC-64399), summary-only; the aluminum-on-
  aluminum single wall and the aluminum Whipple shield are the only
  configurations modeled.

## Workflow

1. Set the projectile and target parameters (diameter d, densities
   rho_p and rho_t, impact velocity v, obliquity theta) for a single
   aluminum wall and compute the semi-infinite crater depth with
   cour_palais_penetration_depth.
2. Size the single-wall damage-threshold thickness with
   single_wall_required_thickness at the chosen k (K_PERFORATION by
   default), and invert it with single_wall_critical_diameter to
   recover the critical diameter a given wall thickness stops.
3. For a Whipple shield, size the bumper thickness with
   whipple_bumper_thickness from the standoff S and the S/d branch.
4. Size the rear-wall design thickness with
   whipple_rear_wall_thickness at the design projectile and its
   Vn >= 7 km/s design impact, using sphere_mass_g when no explicit
   projectile mass is given.
5. Evaluate the shield's ballistic limit over velocity with
   whipple_critical_diameter, which dispatches across the low,
   intermediate-blend, and hypervelocity regimes with the 65 degree
   obliquity cap.
6. Grade a single impact with penetration_verdict for a single wall or
   whipple_penetration_verdict for a Whipple shield, comparing the
   projectile diameter against the critical diameter margin.
7. Roll the per-impact verdict over the mission with
   penetration_probability from the expected number of penetrating
   impacts, a GIVEN input from the space environment assessment.
8. Confirm the deterministic checks with the contract test
   scripts/test_mmod-shielding-sizing.py.

## Worked example

A thin-aluminum Whipple shield for a 1.0 cm spherical aluminum
projectile (rho_p = 2.70 g/cm^3) at 7 km/s normal impact (theta = 0
deg): rear wall Al 6061-T6 class (sigma = 40.0 ksi), aluminum bumper
(rho_b = 2.70 g/cm^3), standoff S = 11.43 cm (S/d = 11.43 < 30).

- Bumper: whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43) = 0.25 cm
  (cb = 0.25 since S/d < 30).
- Projectile mass: sphere_mass_g(1.0, 2.7) = 1.413716694115407 g.
- Rear wall: whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0,
  7.0, 0.0) = 0.684892875727985 cm.
- Ballistic limit at the design point: whipple_critical_diameter of
  the sized shield at Vn = 7 km/s = 1.000075994715671 cm, matching the
  closed form 3.918 * 0.16^(2/3) * (pi/6)^(2/9) = 1.000075994715671
  (the eq 4-22 sizing is the exact inverse of the eq 4-23 performance
  equation at Vn = 7 km/s). The design case verdict is NO_PENETRATION
  with margin d / dc = 0.999924011059087.
- Same shield at 10 km/s: dc = 0.7884334285317389 cm; the
  hypervelocity scaling dc(10)/dc(7) = 0.7883735163105243, matching
  (7/10)^(2/3) = 0.7883735163105242. Verdict PENETRATION with margin
  1.2683379012255367: a shield sized at 7 km/s does not stop the same
  projectile at 10 km/s.
- Single aluminum wall at 10 km/s: a 0.48 cm monolithic Al 6061-T6
  wall (BHN = 95, rho_t = 2.70 g/cm^3, C_t = 5.0 km/s) against the
  1.0 cm projectile: cour_palais_penetration_depth = 2.664324077003382
  cm, single_wall_required_thickness = 4.795783338606088 cm
  (= 1.8 * P_inf), and single_wall_critical_diameter(0.48, ...) =
  0.11297781552560618 cm, so the 0.48 cm wall stops only sub-
  millimeter-class projectiles at 10 km/s.
- Mission rollup: penetration_probability(0.5) = 0.3934693402873666.

## Verification

- Confirm the design self-consistency: whipple_critical_diameter of
  the sized Case-1 shield at Vn = 7 km/s equals the closed form
  3.918 * 0.16^(2/3) * (pi/6)^(2/9) = 1.000075994715671 within 1e-9
  relative.
- Confirm the single-wall round trip: single_wall_critical_diameter of
  single_wall_required_thickness(d, ...) equals d within 1e-9 relative
  on both density branches (aluminum-on-aluminum and steel-on-
  aluminum).
- Confirm regime continuity at Vn = 3 km/s and Vn = 7 km/s, and the
  hypervelocity scaling dc(V2)/dc(V1) = (V1/V2)^(2/3) for Vn >= 7.
- Confirm the obliquity cap: dc at theta >= 65 degrees equals dc at
  theta = 65 degrees for the same velocity.
- Confirm every non-positive thickness, density, hardness, sound
  speed, yield stress, mass, and velocity raises ValueError, theta
  outside [0, 90) raises ValueError, a rear-wall design below Vn = 7
  km/s raises ValueError, negative lambda raises ValueError, and any
  boolean argument raises ValueError.
- Run the contract test offline: python3
  scripts/test_mmod-shielding-sizing.py (35 tests, deterministic).

## Related leaves

- space-systems/mission-design/radiation-debris: the space environment
  leaf that produces the debris flux, fluence, and collision
  probability this leaf consumes as GIVEN inputs; it never estimates a
  penetration outcome.
- space-systems/subsystems/thermal-design: the thermal control sizing
  sibling of the spacecraft bus.
- space-systems/subsystems/propellant-tank-sizing: another spacecraft
  bus subsystem sizing leaf sharing the ECSS lifecycle context.

## Pitfalls

- Reading the debris collision probability as the penetration
  probability: radiation-debris's collision probability is the chance
  of any impact; this leaf's penetration_probability is the chance of
  an impact exceeding the ballistic limit, a downstream, smaller
  quantity that needs the critical diameter first.
- Using the bumper thickness in the hypervelocity regime: eq (4-23)
  does not take tb as an input; the equation assumes the bumper is
  adequate to disrupt the projectile, so a resized bumper alone never
  changes dc above 7 km/s.
- Forgetting the obliquity cap: feeding theta above 65 degrees into
  the raw cos(theta) terms without capping first understates Vn and
  overstates the ballistic limit; cap theta at 65 degrees before
  forming Vn.
- Assuming a shield sized at one velocity stays adequate at another:
  the Case-1 shield sized for a 7 km/s design impact drops to margin
  1.268 (PENETRATION) at 10 km/s, since dc falls as Vn^(-2/3) in the
  hypervelocity regime.
- Applying the rear-wall design equation below 7 km/s: eq (4-22)
  assumes hypervelocity impact; whipple_rear_wall_thickness raises
  ValueError below Vn = 7 km/s rather than returning an unvalidated
  thickness.
- Summing yearly penetration probabilities instead of compounding:
  penetration_probability uses 1 - exp(-lambda) over the whole mission
  lambda, not a sum of per-year probabilities.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mmod-shielding-sizing.py

The test covers the worked-example contract (bumper and rear-wall
design thicknesses, the design self-consistency identity, the single-
wall penetration depth and required thickness, the critical diameter
at both wall configurations, and the mission penetration probability),
the single-wall round trip on both density branches, regime continuity
at the Vn = 3 and Vn = 7 km/s boundaries, the hypervelocity scaling and
obliquity-cap identities, the per-impact verdict semantics, mission
probability monotonicity, determinism, and ValueError rejection of
every non-physical or boolean input.

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames the spacecraft subsystem
  design lifecycle; NASA TM-2009-214789 (JSC-64399) and the
  Cour-Palais and Christiansen ballistic-limit equation family are
  cited summary-only per standards-map.yaml, never reproduced as
  design data.
- compliance: STANDARDS-REF, gated: false.
