# Wave-41 leaf spec: environmental-disturbance-torque-budget (space-systems, adcs pack)

- Path: skills/space-systems/adcs/environmental-disturbance-torque-budget/
- Pack: adcs (verified present at prep with attitude-control-sizing,
  attitude-determination-quest, attitude-determination-triad, control-momentum-
  gyro, gravity-gradient-stabilization, gyro-allan-variance, magnetometer-
  calibration, magnetorquer-control, pointing-error-budget, reaction-wheel-
  control, star-tracker, sun-pointing). Closest siblings:
  attitude-control-sizing (its claim is "size the attitude control subsystem
  actuators for a spacecraft: compute the momentum wheel capacity for a
  commanded slew, check the detumble rate against the allowed rate, and verify
  the wheel momentum margin before the ADCS design review"; its body reduces
  sizing to "Slew momentum: H = I * omega" with "Detumble: the post-separation
  angular rate must be reduced to within the allowed rate before pointing
  control", and its whole workflow takes inertia, commanded slew rate, allowed
  detumble rate and margin fraction as inputs, with NO disturbance environment,
  no gravity-gradient, solar, magnetic or aero term anywhere in the file),
  gravity-gradient-stabilization (its claim is "estimate the gravity-gradient
  restoring torque at a pitch offset, and size a gravity boom tip mass for a
  target libration stiffness" for a passive nadir-pointing design gated by the
  "inertia-ratio stability criterion I_y > I_x > I_z"; its body fixes the
  boundary: "Gravity-gradient restoring torque at a pitch offset theta:
  T = (3/2) * n^2 * (I_x - I_z) * sin(2 * theta), from restoring_torque. The
  torque is zero at 0 and 90 degrees and largest in magnitude at 45 degrees",
  i.e. the restoring torque of a passive design at a pitch offset, not a
  worst-case disturbance magnitude for actuator budgeting at an arbitrary
  attitude), magnetorquer-control (its claim is the CONTROL side of the same
  physics: "solve torque = m x B for the required dipole from a torque demand
  and the local magnetic field vector", with "the maximum for a given dipole
  magnitude is |m| |B|, reached when m is perpendicular to B" as achievable
  control torque; no residual-dipole disturbance term exists in it),
  reaction-wheel-control (its claim is the wheel control law and momentum
  management: "command wheel torques from quaternion error feedback and body
  rate with PD gains ... and compute the momentum desaturation command with its
  magnetorquer dipole estimate"; it unloads wheel momentum that this leaf's
  per-orbit disturbance impulse quantifies, but it takes no disturbance
  environment input). Cross-family corpus check: "gravity gradient torque"
  tasks route only to gnc-autonomy/space/attitude-dynamics (w8-2, full
  vector-state propagation with tau = (3 mu / r^3) (r_hat x I r_hat)) and to
  gravity-gradient-stabilization (w39, passive design); whole-tree greps at
  prep: "disturbance torque", "gravity-gradient torque", "srp torque" and
  "solar radiation pressure" = 0 hits in skills/space-systems. GENUINE SPACE
  gap (fresh probe): no leaf in the tree estimates an environmental disturbance
  torque budget, so no ADCS actuator sizing or desaturation demand anywhere in
  the tree is driven by a quantified worst-case disturbance environment.
- Standards id: ecss (reference-only; exists in standards-map.yaml, sibling
  convention across the adcs pack). Ledger Standard: ecss.
- Family: space-systems

## Claim

Estimate the worst-case environmental disturbance torque set for a spacecraft
in low Earth orbit: compute the gravity-gradient torque magnitude 1.5 * n^2 *
|I_z - I_y| * sin(2 * theta) at a given attitude offset theta from the mean
motion of the circular orbit and the in-plane principal moment spread; compute
the solar radiation pressure torque from the projected sunlit area, the cosine
of the sun incidence angle and the force lever arm with an explicit surface
reflectivity convention; compute the residual magnetic dipole disturbance
torque T = m_res * B for the worst-case orthogonal geometry against the local
field magnitude; compute the aero drag torque from the free-molecular drag
relation with an explicit atmospheric density input and the circular-orbit
velocity; roll the four sources up into a per-source worst-case budget with a
conservative aligned-axis total, the dominant source, the orbit period, and
the per-orbit disturbance impulse that the reaction wheels must absorb and the
magnetorquer must dump; and compare the total against an actuator capability
with a torque margin ratio. Produces the per-source torques, the worst-case
total with its dominant source, the per-orbit disturbance impulse for
desaturation demand, and the actuator margin verdict that gate ADCS actuator
sizing and desaturation demand. Does NOT do: passive gravity-gradient design
with the inertia-ratio stability criterion, libration frequency or boom sizing
(gravity-gradient-stabilization); actuator sizing from slew momentum and
detumble rate with no disturbance environment (attitude-control-sizing);
magnetorquer control laws, B-dot detumbling, torque-rod coil sizing or the
dipole-from-torque-demand solve (magnetorquer-control); reaction wheel control
laws, wheel momentum saturation flags or the desaturation command computation
(reaction-wheel-control); full rigid-body attitude dynamics propagation
(gnc-autonomy/space/attitude-dynamics). The density input is explicit: this
leaf bounds torques, it does not model the atmosphere.

## Model (implement exactly)

Functions (pure stdlib, math only):
- orbital_mean_motion(radius_m) -> float sqrt(EARTH_MU / radius_m**3), the
  mean motion n in rad/s of a circular orbit at orbital radius radius_m
  (radius = Earth radius + altitude). ValueError if radius_m <= EARTH_RADIUS_M
  (an orbit must lie above the surface).
- orbital_velocity(radius_m) -> float sqrt(EARTH_MU / radius_m), the
  circular-orbit speed in m/s used by the aero drag term. ValueError if
  radius_m <= EARTH_RADIUS_M.
- orbit_period_s(radius_m) -> float 2 * pi / orbital_mean_motion(radius_m),
  seconds, the per-orbit horizon for the disturbance impulse. ValueError if
  radius_m <= EARTH_RADIUS_M.
- gravity_gradient_torque(n_orbital, i_zz, i_yy, theta_deg) -> float
  1.5 * n_orbital**2 * abs(i_zz - i_yy) * abs(sin(2 * theta_deg_rad)), the
  gravity-gradient disturbance torque magnitude in N m about the third body
  axis when the body z and y principal moments i_zz and i_yy lie in the plane
  swept between the local vertical and the body frame at attitude offset
  theta_deg. The magnitude peaks at +-45 degrees and vanishes at 0 and +-90
  degrees; the absolute values make the magnitude sign-free for either spread
  direction and either theta sign. The closed form is the same one
  gravity-gradient-stabilization uses for its restoring torque (their
  (3/2) * n^2 * (I_x - I_z) * sin(2 * theta) with their axis naming); here it
  is a disturbance magnitude at an arbitrary attitude with no inertia-ratio
  stability criterion. ValueError if n_orbital <= 0, i_zz <= 0, i_yy <= 0 or
  abs(theta_deg) > 90.0.
- solar_pressure_torque(area_m2, cos_incidence, lever_arm_m,
  reflectivity = 1.0) -> float SOLAR_PRESSURE_PA * area_m2 * cos_incidence *
  (1.0 + reflectivity) * lever_arm_m. Reflectivity convention, documented in
  the SKILL body: reflectivity is the surface reflection coefficient r, with
  r = 0 a fully absorbing surface (force P * A * cos(i), the momentum flux
  alone) and r = 1 a fully specularly reflecting surface (force
  2 * P * A * cos(i), momentum doubling); the default 1.0 is the worst case.
  cos_incidence is the cosine of the angle between the sunlit surface normal
  and the sun line, in [0, 1]. ValueError if area_m2 <= 0, cos_incidence
  outside [0, 1], lever_arm_m <= 0 or reflectivity outside [0, 1].
- magnetic_residual_torque(residual_dipole_Am2, b_field_T) -> float
  residual_dipole_Am2 * b_field_T, the residual magnetic dipole disturbance
  torque in N m for the worst-case orthogonal geometry (m perpendicular to B),
  the same m x B physics magnetorquer-control commands with, here applied to
  the spacecraft residual dipole magnitude. ValueError if residual_dipole_Am2
  < 0 (a zero dipole is legal and returns 0.0) or b_field_T <= 0.
- aero_drag_torque(rho, velocity_m_s, cd, area_m2, lever_arm_m) -> float
  0.5 * rho * velocity_m_s**2 * cd * area_m2 * lever_arm_m, the free-molecular
  aero drag disturbance torque in N m at the explicit atmospheric density rho
  (kg/m3) input; feed orbital_velocity(radius_m) for the circular-orbit speed.
  ValueError if any input <= 0.
- worst_case_budget(radius_m, i_zz, i_yy, theta_deg = 45.0, solar_area_m2,
  cos_incidence, solar_lever_m, reflectivity = 1.0, residual_dipole_Am2,
  b_field_T, rho, drag_cd, drag_area_m2, drag_lever_m) -> dict with keys
  mean_motion_rad_s, orbital_velocity_m_s, orbit_period_s, gravity_gradient,
  solar_pressure, magnetic_residual, aero_drag, total_worst_case,
  dominant_source, disturbance_impulse_per_orbit. theta_deg defaults to 45.0
  (the worst-case attitude for the gravity-gradient term) and reflectivity to
  1.0 (worst case); both are passable. total_worst_case is the conservative
  sum of the four per-source magnitudes on the documented assumption that all
  four act on the same control axis at their worst geometry simultaneously.
  dominant_source is the source key with the largest magnitude. disturbance_
  impulse_per_orbit = total_worst_case * orbit_period_s. ValueErrors as in the
  component functions.
- disturbance_impulse(torque, period_s) -> float torque * period_s in N m s,
  the wheel momentum the spacecraft must absorb per orbit at the given
  disturbance torque (a zero torque is legal and returns 0.0). ValueError if
  torque < 0 or period_s <= 0.
- torque_margin(available, disturbance) -> float available / disturbance, the
  dimensionless capability ratio of an actuator (reaction wheel torque in N m,
  or magnetorquer achievable torque m_max * B) against a disturbance torque;
  a ratio >= 1.0 means the actuator can cancel the worst-case disturbance.
  ValueError if available <= 0 or disturbance <= 0.
Module constants: SOLAR_PRESSURE_PA = 4.5e-6, EARTH_MU = 3.986004418e14,
EARTH_RADIUS_M = 6378.0e3 (the 6,878 km at 500 km convention of
gravity-gradient-stabilization), THETA_WORST_DEG = 45.0.

Identity to test: the gravity-gradient term is zero at 0 degrees, maximal at
45 degrees and (in exact arithmetic) zero at 90 degrees; doubling the inertia
spread doubles the gravity-gradient torque, and the torque scales with n^2
(the same closed form reproduces the gravity-gradient-stabilization restoring
torque anchor 3.675e-5 N m at its 500 km, spread-20 example); the solar torque
at reflectivity 0 is exactly half the reflectivity-1 value and linear in
cos_incidence and area; the magnetic torque is linear in the residual dipole;
the aero torque scales with velocity squared; the worst-case total is the sum
of the per-source magnitudes; torque_margin(available, disturbance) returns
exactly 1.0 when available equals disturbance.

## Worked example

400 km LEO: radius = EARTH_RADIUS_M + 400 km = 6.778e6 m. Mean motion n =
orbital_mean_motion(6.778e6) = 1.131401e-3 rad/s, circular velocity =
orbital_velocity(6.778e6) = 7668.635675 m/s, orbit period = 5553.455897 s
(92.558 min). Body principal moments I_z = 60, I_y = 20 kg m2 (spread
|I_z - I_y| = 40 kg m2) at the worst-case theta 45 degrees.

- Gravity-gradient: 1.5 * n^2 * 40 * sin(90 deg) = 7.680409e-5 N m (76.80
  uN m). Zero exactly at 0 degrees and 9.406e-21 N m at 90 degrees (floating
  point sin of pi). Spread 20 at 500 km reproduces the
  gravity-gradient-stabilization anchor 3.675e-5 N m.
- Solar pressure: area 2.0 m2 sun-normal (cos_incidence 1.0), lever 0.6 m,
  reflectivity 1.0 (fully reflective worst case): force =
  4.5e-6 * 2.0 * 1.0 * 2.0 = 1.8e-5 N, torque = 1.080000e-5 N m (10.80 uN m).
  The absorbing-surface case (reflectivity 0.0) is exactly half:
  5.4e-6 N m.
- Residual magnetic dipole: m_res = 0.1 A m2 against B = 3.0e-5 T (equator
  magnitude), worst-case orthogonal: 3.000000e-6 N m (3.00 uN m). A zero
  dipole contributes 0.0.
- Aero drag: explicit density input rho = 3.0e-12 kg/m3 (a mid-activity value
  in the ~1e-12 to ~1e-11 kg/m3 band at 400 km; the user must pick the density
  that bounds the environment, the leaf does not model the atmosphere), Cd =
  2.2 (free-molecular flat plate), area 1.0 m2, lever 0.5 m at v =
  7668.635675 m/s: 0.5 * 3.0e-12 * v^2 * 2.2 * 1.0 * 0.5 = 9.703316e-5 N m
  (97.03 uN m).
- Budget rollup: total worst-case = 1.876372e-4 N m (187.64 uN m), dominant
  source aero_drag; at 400 km aero drag and gravity gradient dominate, solar
  pressure and the residual dipole sit an order of magnitude lower. Per-orbit
  disturbance impulse = total * 5553.455897 s = 1.042035 N m s, the wheel
  momentum the cluster must absorb every orbit and the desaturation demand.
- Margins: a reaction wheel torque capability of 0.2 N m gives torque_margin
  1065.886, which is the steady-state story: wheel torque authority dwarfs the
  worst-case disturbance, and it is the 1.042035 N m s per-orbit accumulation,
  not the steady torque, that drives desaturation. A magnetorquer dipole of
  30 A m2 in B = 3.0e-5 T achieves 9.000000e-4 N m and torque_margin 4.796
  against the same total.
Run your module and take the real outputs as assert targets; the anchors above
are prep-verified bounds, computed by running the prep anchor script
/tmp/w41spec/anchor_env_torque.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- orbital_mean_motion(6.778e6) = 1.131401e-3 rad/s within 1e-9;
  orbital_velocity(6.778e6) = 7668.635675 m/s within 1e-3;
  orbit_period_s(6.778e6) = 5553.455897 s within 1e-3; ValueError at radius
  exactly EARTH_RADIUS_M and below.
- gravity_gradient_torque(1.131401e-3, 60, 20, 45) = 7.680409e-5 within 1e-9;
  exactly 0.0 at theta 0; below 1e-15 at theta 90; equal magnitude at theta
  -45 (sign-free); ValueError at n 0, inertia 0, |theta| above 90.
- Gravity-gradient identities: doubling the spread 20 to 40 doubles the
  torque; the 500 km spread-20 case (orbital_mean_motion(6.878e6) =
  1.10679e-3, torque 3.67497e-5 within 1e-7) reproduces the
  gravity-gradient-stabilization restoring-torque anchor 3.675e-5 N m.
- solar_pressure_torque(2.0, 1.0, 0.6, 1.0) = 1.08e-5 within 1e-10; with
  reflectivity 0.0 = 5.4e-6 exactly half; cos_incidence 0.5 gives exactly
  half of the cos 1.0 value; cos_incidence 0 gives 0.0; ValueErrors at area
  0, cos_incidence -0.1 and 1.1, lever 0, reflectivity -0.1 and 1.2.
- magnetic_residual_torque(0.1, 3.0e-5) = 3.0e-6 within 1e-10; zero dipole
  returns 0.0; doubling the dipole doubles the torque; ValueErrors at dipole
  -0.1 and field 0.
- aero_drag_torque(3.0e-12, 7668.635675, 2.2, 1.0, 0.5) = 9.703316e-5 within
  1e-9; velocity-squared identity: doubling v quadruples the torque;
  ValueErrors at rho 0 and at any non-positive input.
- worst_case_budget on the worked example: per-source keys equal the anchors,
  total_worst_case 1.876372e-4 within 1e-8, dominant_source "aero_drag",
  disturbance_impulse_per_orbit 1.042035 within 1e-6, and the total equals the
  sum of the four sources; dict keys exactly the ten documented keys;
  theta_deg and reflectivity defaults are 45.0 and 1.0.
- torque_margin(0.2, 1.876372e-4) = 1065.886 within 1e-3;
  torque_margin(9.0e-4, 1.876372e-4) = 4.796 within 1e-3; margin 1.0 exactly
  when available equals disturbance; ValueErrors at available 0 and
  disturbance 0.
- disturbance_impulse(1.876372e-4, 5553.455897) = 1.042035 within 1e-6 and
  equals total * period in the budget; zero torque returns 0.0; ValueError at
  negative torque and zero period.
- Determinism; fixed dict keys; module constants as documented.

## Corpus fragment (eval/hit1-wave41-environmental-disturbance-torque-budget.yaml)

Query 1 (copy verbatim):
  "estimate the worst-case environmental disturbance torque budget for the LEO spacecraft at the given attitude: roll up the gravity-gradient, solar pressure, residual magnetic dipole and aero drag worst-case torques against the reaction wheel and magnetorquer capability"
  intent: "space-systems; worst-case environmental disturbance torque budget rollup at LEO for ADCS actuator margin"
  expected_skill: "space-systems/adcs/environmental-disturbance-torque-budget"
Query 2 (copy verbatim):
  "compute the worst-case disturbance torque set at the arbitrary attitude and the per-orbit disturbance impulse the wheels must absorb, then check the total against the wheel torque margin"
  intent: "space-systems; worst-case disturbance torque set and per-orbit disturbance impulse with the wheel torque margin check"
  expected_skill: "space-systems/adcs/environmental-disturbance-torque-budget"
Task ids: w41-environmental-disturbance-torque-budget-1 and -2. Corpus
collision check at prep: no existing task carries "disturbance torque", "solar
pressure" or "torque budget" tokens routed to any space-systems leaf; the only
"disturbance" hit in the corpus is a flight-mechanics airspeed-oscillation
task; the only gravity-gradient tasks route to attitude-dynamics (dynamics
propagation) and gravity-gradient-stabilization (passive design). The two
queries above route on budget-unique compound tokens only.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the worst-case environmental
disturbance torque budget for a spacecraft:" and include the outputs in the
Claim. First tag: environmental-disturbance-torque-budget. Additional tags
ONLY: worst-case-disturbance-torque, gravity-gradient-torque,
solar-pressure-torque, residual-magnetic-dipole, aero-drag-torque,
disturbance-impulse-per-orbit. NEVER single generic words (torque,
disturbance, budget, spacecraft, adcs, attitude, drag, solar, magnetic, wheel,
dipole, density, margin). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present. Do not put "momentum wheel", "slew",
"detumble", "desaturation command" or "coil sizing" in the description.

FORBIDDEN TOKENS (belong to siblings): slew-rate, slew-momentum, momentum-
wheel, detumble, wheel-margin, adcs-sizing (attitude-control-sizing);
inertia-ratio-criterion, libration-frequency, gravity-boom, boom-tip-mass,
passive-attitude-stabilization, nadir-pointing (gravity-gradient-stabilization,
whose corpus tasks route on inertia-ratio criterion and libration period, and
on gravity-boom tip-mass sizing); b-dot, underdetermined-axis, torque-
authority, coil-sizing, torque-rod, dipole-from-torque-demand
(magnetorquer-control, whose corpus tasks route on dipole from torque demand
and B-field, and B-dot detumbling); wheel-torque-command, quaternion-error-
feedback, momentum-desaturation, wheel-momentum-saturation, desaturation-
dipole, reaction-wheel-cluster (reaction-wheel-control, whose corpus task
routes on the momentum desaturation command); quaternion-kinematics, euler-
equations, nutation, inertia-tensor, angular-momentum (gnc-autonomy/space/
attitude-dynamics). "Desaturation demand" as a demand quantity this leaf sizes
is fine in the Claim and body; the desaturation COMMAND computation belongs to
reaction-wheel-control. Aero density stays an explicit input; reference
cross-cutting/units-atmos/isa-atmosphere only as the cross-family standard-
atmosphere model that does not cover the 400 km free-molecular regime, never
as a function dependency.
