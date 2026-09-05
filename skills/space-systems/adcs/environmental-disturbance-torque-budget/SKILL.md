---
name: environmental-disturbance-torque-budget
description: "Use when you must estimate the worst-case environmental disturbance torque budget for a spacecraft: compute gravity-gradient torque from orbit mean motion and principal moment spread at the attitude offset, solar pressure torque from area, incidence cosine and lever arm with reflectivity convention, residual magnetic dipole torque against the local field, and aero drag torque from the free-molecular relation at explicit density. Produces per-source worst-case torques, aligned-axis total with dominant source, per-orbit disturbance impulse and actuator torque margin. Trigger: disturbance torque budget, worst-case disturbance torque, gravity-gradient torque, solar pressure torque, residual magnetic dipole, aero drag torque, per-orbit impulse."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [environmental-disturbance-torque-budget, worst-case-disturbance-torque, gravity-gradient-torque, solar-pressure-torque, residual-magnetic-dipole, aero-drag-torque, disturbance-impulse-per-orbit]
  version: 0.1.0
  author: AeroSkills
---

# Environmental Disturbance Torque Budget (space-systems/adcs/environmental-disturbance-torque-budget)

Use when the task is bounding the disturbance environment of a spacecraft
in low Earth orbit for ADCS actuator budgeting: estimating the worst-case
magnitudes of the gravity-gradient, solar radiation pressure, residual
magnetic dipole and aero drag disturbance torques at an arbitrary
attitude, rolling them into a conservative per-orbit budget, and rating
the reaction wheel and magnetorquer capability against the total. This
leaf implements the four standard disturbance models in pure Python,
stdlib only, with an explicit atmospheric density input: it bounds
torques, it does not model the atmosphere. It pairs with the actuation
and design leaves of this pack: attitude-control-sizing, which sizes
wheel momentum and detumble rate with no disturbance environment;
gravity-gradient-stabilization, whose passive restoring torque shares
this leaf's closed form but demands the passive stability criterion;
magnetorquer-control, which commands the same m x B physics on the
control side; and reaction-wheel-control, which absorbs the per-orbit
disturbance impulse this leaf quantifies. The density input is explicit:
this leaf bounds torques, it does not model the atmosphere.

## Domain quick reference

- Mean motion of the circular orbit: n = sqrt(mu / r^3), with
  orbital_mean_motion(radius_m). The circular speed v = sqrt(mu / r)
  comes from orbital_velocity and the per-orbit horizon from
  orbit_period_s = 2 * pi / n. Radius is Earth radius plus altitude
  (EARTH_RADIUS_M = 6378 km, EARTH_MU = 3.986004418e14 m3/s2).
- Gravity-gradient disturbance magnitude: T = 1.5 * n^2 * |I_zz - I_yy| *
  |sin(2 * theta)| about the third body axis when the in-plane principal
  moments I_zz and I_yy lie in the plane swept between the local vertical
  and the body frame at attitude offset theta. The absolute values keep
  the magnitude sign-free; it peaks at +-45 degrees and vanishes at 0 and
  +-90 degrees. theta_deg = 45.0 (THETA_WORST_DEG) is the worst case.
- Solar radiation pressure torque: T = P_sr * A * cos(i) * (1 + r) * L,
  P_sr = SOLAR_PRESSURE_PA = 4.5e-6 N/m2 at 1 AU. Reflectivity r is the
  surface reflection coefficient: r = 0 is a fully absorbing surface
  (force P * A * cos(i), momentum flux alone), r = 1 a fully specular
  surface (force 2 * P * A * cos(i), momentum doubling); the default 1.0
  is the worst case.
- Residual magnetic dipole torque: T = m_res * B for the worst-case
  orthogonal geometry (m perpendicular to B), the same m x B physics a
  magnetorquer commands, applied here to the spacecraft residual dipole.
- Aero drag torque: T = 0.5 * rho * v^2 * Cd * A * L, the free-molecular
  drag relation at the explicit density rho and the circular-orbit speed
  v from orbital_velocity. Cd ~ 2.2 for a flat plate in free-molecular
  flow.
- Worst-case budget rollup: total_worst_case is the aligned-axis sum of
  the four magnitudes, the conservative assumption that all four act on
  the same control axis at their worst geometry simultaneously;
  dominant_source names the largest; disturbance_impulse_per_orbit =
  total * orbit_period is the wheel momentum the cluster must absorb each
  orbit, the desaturation demand.
- Torque margin: torque_margin(available, disturbance) = available /
  disturbance; a ratio >= 1.0 means the actuator can cancel the
  worst-case disturbance. disturbance_impulse(torque, period_s) gives
  the per-orbit momentum accumulation in N m s.
- Units are SI throughout: m, s, rad/s, kg m2, N m, N m s, A m2, T,
  kg/m3.
- ECSS frames the space environment and system context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the orbit: radius_m = EARTH_RADIUS_M + altitude, then set the
   mean motion with orbital_mean_motion, the circular speed with
   orbital_velocity and the per-orbit horizon with orbit_period_s.
2. Gravity-gradient traverse: gravity_gradient_torque(n_orbital, i_zz,
   i_yy, theta_deg) with the in-plane principal moments and the attitude
   offset; run theta_deg = THETA_WORST_DEG (45 degrees) for the
   worst-case magnitude.
3. Solar-pressure traverse: solar_pressure_torque(area_m2,
   cos_incidence, lever_arm_m, reflectivity) with the sunlit area, the
   incidence cosine in [0, 1], the force lever arm and the reflectivity
   convention above; default reflectivity 1.0 is the worst case.
4. Residual-dipole traverse: magnetic_residual_torque(residual_dipole,
   b_field) against the local field magnitude chosen to bound the orbit
   (a zero dipole is legal and returns 0.0).
5. Aero-drag traverse: aero_drag_torque(rho, velocity_m_s, cd, area_m2,
   lever_arm_m) with the explicit density that bounds the environment
   (the leaf does not model the atmosphere) and the circular-orbit speed
   from step 1.
6. Budget-rollup traverse: worst_case_budget(radius_m, i_zz, i_yy,
   solar_area_m2, cos_incidence, solar_lever_m, residual_dipole, b_field,
   rho, drag_cd, drag_area_m2, drag_lever_m) with theta_deg defaulting to
   45.0 and reflectivity to 1.0, both passable, returns the ten-key dict
   with per-source torques, total_worst_case, dominant_source and
   disturbance_impulse_per_orbit.
7. Actuator-margin traverse: rate the reaction wheel torque (or the
   magnetorquer achievable torque m_max * B) against the total with
   torque_margin, and size the momentum the wheels must dump each orbit
   with disturbance_impulse(torque, period_s).
8. Confirm the deterministic checks with the contract test
   scripts/test_environmental_disturbance_torque_budget.py.

## Worked example

400 km LEO: radius = EARTH_RADIUS_M + 400 km = 6.778e6 m. Mean motion
n = 1.131401e-3 rad/s, circular velocity v = 7668.635675 m/s, orbit
period 5553.455897 s (92.558 min). Body principal moments I_z = 60 and
I_y = 20 kg m2 (spread |I_z - I_y| = 40 kg m2) at the worst-case theta of
45 degrees.

- Gravity gradient: 1.5 * n^2 * 40 * sin(90 deg) = 7.680409e-5 N m
  (76.80 uN m). Exactly 0.0 at 0 degrees and 9.4e-21 N m at 90 degrees
  (the floating-point sin of pi). The same closed form with spread 20 at
  500 km (radius 6.878e6 m) gives 3.675e-5 N m, reproducing the
  gravity-gradient-stabilization restoring-torque anchor.
- Solar pressure: area 2.0 m2 sun-normal (cos_incidence 1.0), lever
  0.6 m, reflectivity 1.0 (fully reflective worst case): force =
  4.5e-6 * 2.0 * 1.0 * 2.0 = 1.8e-5 N, torque = 1.080000e-5 N m
  (10.80 uN m). The absorbing-surface case (reflectivity 0.0) is exactly
  half: 5.4e-6 N m.
- Residual magnetic dipole: m_res = 0.1 A m2 against B = 3.0e-5 T
  (equator magnitude), worst-case orthogonal: 3.000000e-6 N m
  (3.00 uN m). A zero dipole contributes 0.0.
- Aero drag: rho = 3.0e-12 kg/m3 (a mid-activity value in the ~1e-12 to
  ~1e-11 kg/m3 band at 400 km), Cd = 2.2, area 1.0 m2, lever 0.5 m at
  v = 7668.635675 m/s: 0.5 * 3.0e-12 * v^2 * 2.2 * 1.0 * 0.5 =
  9.703316e-5 N m (97.03 uN m).
- Budget rollup: total worst case = 1.876372e-4 N m (187.64 uN m),
  dominant source aero_drag; at 400 km aero drag and gravity gradient
  dominate, solar pressure and the residual dipole sit an order of
  magnitude lower. Per-orbit disturbance impulse = total * 5553.455897 s
  = 1.042035 N m s, the wheel momentum the cluster must absorb every
  orbit and the desaturation demand.
- Margins: a reaction wheel torque capability of 0.2 N m gives
  torque_margin 1065.887: wheel torque authority dwarfs the worst-case
  disturbance, and it is the 1.042035 N m s per-orbit accumulation, not
  the steady torque, that drives desaturation. A magnetorquer dipole of
  30 A m2 in B = 3.0e-5 T achieves 9.000000e-4 N m and torque_margin
  4.796 against the same total.

## Verification

- Confirm orbital_mean_motion(6.778e6) returns 1.131401e-3 rad/s,
  orbital_velocity 7668.635675 m/s and orbit_period_s 5553.455897 s,
  each within the contract tolerances.
- Confirm gravity_gradient_torque at 45 degrees returns 7.680409e-5 N m,
  is exactly 0.0 at 0 degrees, stays below 1e-15 at 90 degrees and is
  equal in magnitude at -45 degrees.
- Confirm the identities: doubling the inertia spread doubles the
  gravity-gradient torque; the solar torque at reflectivity 0 is exactly
  half the reflectivity-1 value and linear in cos_incidence and area; the
  magnetic torque is linear in the residual dipole; the aero torque
  scales with velocity squared; the worst-case total is the sum of the
  four per-source magnitudes; torque_margin returns exactly 1.0 when
  available equals disturbance.
- Confirm every non-physical input raises ValueError: orbit radius at or
  below EARTH_RADIUS_M, non-positive mean motion or inertia, attitude
  offset magnitude above 90 degrees, zero sunlit area or lever, incidence
  cosine and reflectivity outside [0, 1], negative residual dipole,
  non-positive field, and any non-positive aero input.
- Run the contract test offline: python3
  scripts/test_environmental_disturbance_torque_budget.py (34 tests,
  deterministic).

## Related leaves

- space-systems/adcs/attitude-control-sizing: actuator sizing from wheel
  momentum and detumble rate with no disturbance environment; this leaf
  supplies the worst-case environment that gates that sizing.
- space-systems/adcs/gravity-gradient-stabilization: passive nadir design
  whose restoring torque shares this leaf's closed form at a pitch
  offset, sized with its stability criterion and boom relations.
- space-systems/adcs/magnetorquer-control: the control-side m x B solve,
  the dipole from a torque demand and the achievable torque m_max * B
  this leaf rates against the disturbance total.
- space-systems/adcs/reaction-wheel-control: wheel control laws and the
  momentum management that absorbs the per-orbit disturbance impulse
  this leaf quantifies.
- gnc-autonomy/space/attitude-dynamics: full rigid-body attitude dynamics
  propagation with the ambient gravity torque vector state, the dynamic
  alternative to this leaf's worst-case magnitude view.
- cross-cutting/units-atmos/isa-atmosphere: the standard atmosphere
  model, which does not cover the 400 km free-molecular regime that this
  leaf's explicit density input must bound.

## Pitfalls

- Reporting the gravity-gradient term as a restoring torque with a sign:
  this leaf returns the sign-free worst-case magnitude
  1.5 * n^2 * |I_zz - I_yy| * |sin(2 * theta)| at an arbitrary attitude
  for either spread direction; the restoring torque of a passive nadir
  design with a stability criterion is the gravity-gradient-stabilization
  leaf's result, not a budget input here.
- Summing magnitudes as if aligned: total_worst_case assumes all four
  sources act on the same control axis at their worst geometry at once,
  which is conservative for actuator margins; a three-axis environment
  model would distribute the sources per axis instead.
- Choosing an optimistic density or field: the density is an explicit
  input and the leaf does not model the atmosphere, so the user must pick
  the bounding value (roughly 1e-12 to 1e-11 kg/m3 at 400 km), and the
  local field magnitude B varies along the orbit; a worst-case budget
  needs the bounding values, not the mean.
- Sizing desaturation on the steady torque: the wheel torque margin can
  be enormous (1065.887 at the worked example) while the 1.042035 N m s
  per-orbit impulse still accumulates into the wheel momentum budget, so
  the impulse, not the steady torque, drives the desaturation demand.
- Reading the magnetorquer margin as a momentum dump: a margin of 4.796
  says the achievable torque can cancel the steady worst-case total, but
  dumping the accumulated per-orbit impulse is a control command problem
  that belongs to reaction-wheel-control and magnetorquer-control.
- Feeding altitude instead of orbital radius: the orbit functions take
  radius_m = EARTH_RADIUS_M + altitude (6.778e6 m at 400 km) and reject
  any radius at or below the surface; passing 400 km in place of the
  radius overstates the mean motion by orders of magnitude.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_environmental_disturbance_torque_budget.py

It exercises all eight workflow steps: the orbit-fix anchors at 400 km
and the circular-orbit identities, the gravity-gradient traverse
including its zero crossings, sign freedom, scaling identities and the
500 km reproduction of the gravity-gradient-stabilization anchor, the
solar-pressure traverse with the reflectivity and incidence linearity
identities, the residual-dipole traverse, the aero-drag traverse with its
velocity-squared scaling, the budget-rollup traverse with its exact
ten-key structure, deterministic rollup and sum identity, and the
actuator-margin traverse with the worked-example margins. Every
non-physical input listed in the spec raises ValueError.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_environmental_disturbance_torque_budget.py

The test covers the worked-example anchors (mean motion 1.131401e-3
rad/s, circular velocity 7668.635675 m/s, orbit period 5553.455897 s,
gravity-gradient torque 7.680409e-5 N m, solar pressure 1.08e-5 N m,
residual dipole 3.0e-6 N m, aero drag 9.703316e-5 N m, worst-case total
1.876372e-4 N m, per-orbit impulse 1.042035 N m s, wheel margin 1065.886,
magnetorquer margin 4.796), the closed-form identities (v = n * r,
period = 2 * pi / n, exact zero at 0 degrees, magnitude below 1e-15 at
90 degrees, spread doubling, reflectivity halving, cos_incidence and area
linearity, dipole linearity, velocity-squared scaling, exact-sum rollup,
margin exactly 1.0 at equality), the ten documented budget keys, budget
defaults of 45.0 degrees and reflectivity 1.0, run-to-run determinism,
and ValueError rejection of every non-physical input (orbit radius at or
below the Earth surface, non-positive mean motion or inertia, offsets
beyond +-90 degrees, non-positive area or lever, out-of-range incidence
cosine and reflectivity, negative dipole, non-positive field and
non-positive aero inputs).

## Compliance

- Standards referenced, not reproduced: ECSS standards are copyright ESA
  and freely downloadable; this leaf cites ECSS as reference only per
  standards-map.yaml. The logic here is generic space environment
  engineering physics (gravity-gradient, solar pressure, residual dipole
  and free-molecular drag disturbance relations), not ECSS text.
- compliance: STANDARDS-REF, gated: false.
