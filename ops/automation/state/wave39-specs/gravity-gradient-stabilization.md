# Wave-39 leaf spec: gravity-gradient-stabilization (space-systems, adcs pack)

- Path: skills/space-systems/adcs/gravity-gradient-stabilization/
- Pack: adcs. Closest siblings: attitude-control-sizing, reaction-wheel-
  control, magnetorquer-control, control-moment-gyro (active actuation
  leaves), gnc-autonomy/space/attitude-dynamics (owns gravity_gradient_
  torque and full rigid-body propagation: torque and dynamics only, its
  docstring notes the nadir equilibrium as the basis of gravity-gradient
  stabilization but it computes NO inertia-ratio criterion, no libration
  frequency, no boom sizing), three-body-libration (CR3BP Lagrange points,
  unrelated). Whole-tree greps at prep: "gravity" inside adcs = 0 hits;
  "boom" inside adcs = 0 hits; corpus 0 tasks. GENUINE SPACE gap (fresh
  probe).
- Standards id: ecss (reference-only; adcs pack convention). Ledger
  Standard: ecss.
- Family: space-systems

## Claim

Design and analyze passive gravity-gradient stabilization for a nadir-
pointing spacecraft: check the inertia-ratio stability criterion
I_y > I_x > I_z (y along the orbit normal), compute the pitch libration
frequency omega_p = sqrt(3 * n^2 * (I_x - I_z) / I_y) and its period,
estimate the gravity-gradient restoring torque at a pitch offset, and size
a gravity boom tip mass for a target libration stiffness. Produces the
stability verdict, libration period, restoring torque and boom sizing that
gate passive-attitude design. Does NOT do: gravity-gradient torque or
rigid-body attitude propagation (gnc attitude-dynamics); active actuation
with reaction wheels, magnetorquers or CMGs (adcs actuation leaves);
Lagrange-point libration (three-body-libration).

## Model (implement exactly)

Conventions: circular orbit with mean motion n = sqrt(mu / r^3), principal
moments I_x, I_y, I_z about the body axes (x along velocity, y along the
orbit normal, z nadir).

Functions (pure stdlib):
- mean_motion(mu, radius) -> sqrt(mu / r^3); ValueError if mu <= 0 or
  radius <= 0.
- stability_verdict(ix, iy, iz) -> bool: True when iy > ix > iz; also
  return the ordering string via a report dict; ValueError on non-positive
  inertias.
- pitch_libration_frequency(ix, iy, iz, mu, radius) ->
  sqrt(3 * n^2 * (ix - iz) / iy); ValueError if the criterion fails
  (ix - iz <= 0), non-positive inertias, mu or radius <= 0.
- libration_period(...) -> 2 * pi / omega_p.
- restoring_torque(ix, iy, iz, mu, radius, pitch_offset_deg) ->
  (3/2) * n^2 * (ix - iz) * sin(2 * theta) (the pitch restoring torque at
  the offset); ValueError if theta outside (-90, 90) degrees or the
  criterion fails; zero at theta = 0.
- boom_tip_mass_for_stiffness(ix_other, target_ix_minus_iz, boom_length) ->
  m_tip = (target_ix_minus_iz) / (boom_length^2) (tip-mass approximation
  for the boom contribution to I_x - I_z); ValueError on non-positive
  inputs.
- gg_report(...) -> dict with keys stable, omega_p, period_s, period_min,
  torque at the given offset.

Identity to test: the pitch libration period equals the orbital period
divided by sqrt(3 * (ix - iz) / iy), about 1.15 orbital periods at the
worked example (6555 s versus 5677 s); the restoring torque is zero at 0
and 90 degrees and maximal at 45 degrees; doubling the inertia spread
(ix - iz) raises omega_p by sqrt(2).

## Worked example

Circular orbit at 500 km: mu = 3.986004418e14 m3/s2, r = 6,878 km
(radius = 6.878e6 m) -> n = 1.1068e-3 rad/s.
I = (60, 80, 40) kg m2 (ix = 60, iy = 80, iz = 40):
- stability_verdict True (80 > 60 > 40).
- omega_p = sqrt(3 * n^2 * 20/80) = 9.586e-4 rad/s; period = 6554 s =
  109.2 min (about two 96.2 min orbital periods).
- restoring torque at 45 deg pitch offset = 3.68e-5 N m (36.8 uN m).
- boom sizing: target (ix - iz) of 20 kg m2 with a 10 m boom ->
  m_tip = 0.2 kg.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (independently evaluated at prep; the mean
motion and torque values were recomputed at prep).

## Validation list (contract test must include)

- mean_motion at 500 km = 1.1068e-3 rad/s within 1e-6.
- stability verdict on (60, 80, 40) True; on (80, 60, 40) False (ix > iy);
  on (60, 40, 80) False (iz not smallest).
- libration period 6554 s within 20 s (109.2 min within 0.5 min).
- restoring torque at 45 deg = 3.68e-5 N m within 1e-6; at 0 deg = 0.
- boom tip mass 0.2 kg within 0.01.
- Identity: period scales as 1/sqrt(ix - iz).
- ValueErrors: non-positive inertia, violated criterion with negative
  (ix - iz), mu or radius <= 0, offset outside (-90, 90).
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-gravity-gradient-stabilization.yaml)

Query 1 (copy verbatim):
  "check the gravity-gradient-stabilization inertia-ratio criterion and the pitch libration period for the nadir-pointing spacecraft at 500 km"
  intent: "space-systems; passive gravity-gradient stability and libration period"
  expected_skill: "space-systems/adcs/gravity-gradient-stabilization"
Query 2 (copy verbatim):
  "size the gravity-boom tip mass for the required gravity-gradient restoring stiffness of the passive attitude spacecraft"
  intent: "space-systems; gravity boom sizing for stabilization"
  expected_skill: "space-systems/adcs/gravity-gradient-stabilization"
Task ids: w39-gravity-gradient-stabilization-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design or analyze passive
gravity-gradient stabilization:" and include the outputs in the Claim.
First tag: gravity-gradient-stabilization. Additional tags ONLY:
gravity-boom, libration-frequency, inertia-ratio-criterion, passive-
attitude-stabilization, nadir-pointing. NEVER single generic words
(gravity, gradient, stabilization, attitude, torque, frequency, inertia).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): gravity-gradient-torque propagation,
quaternion, euler-equations, nutation (gnc attitude-dynamics); b-dot,
magnetorquer, reaction-wheel, cmg, momentum-wheel (adcs actuation);
lagrange-point, cr3bp (three-body-libration); slew, detumble
(attitude-control-sizing).
