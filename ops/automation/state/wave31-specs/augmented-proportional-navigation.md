# Wave-31 leaf spec: augmented-proportional-navigation (gnc-autonomy, guidance pack)

- Path: skills/gnc-autonomy/guidance/augmented-proportional-navigation/
- Pack: guidance (siblings: command-to-line-of-sight, coverage-path-planning,
  dubins-path-planning, impact-point-prediction, midcourse-guidance,
  proportional-navigation, pursuit-guidance). proportional-navigation owns the
  pure proportional navigation command N'*Vc*lamdot for a planar intercept; it
  contains no target-acceleration augmentation (grep receipt at prep: no
  augmented or target-acceleration term in its body). This leaf is the
  augmented-PN member for maneuvering-target intercepts.
- Standards ids: arp4754a (reference-only, gnc convention). Ledger Standard:
  arp4754a.
- Family: gnc-autonomy

## Claim

Compute augmented proportional navigation (APN) guidance commands for a planar
intercept of a maneuvering target: the line-of-sight rate from relative
position and velocity, the closing velocity, the pure proportional navigation
command, the augmented command that adds the target lateral acceleration
perpendicular to the line of sight with the effective navigation ratio, the
time to go estimate, and the commanded lateral acceleration in g. Produces the
LOS rate, closing velocity, PN and APN commands, time to go, and the g-load
verdict that gate an intercept guidance law assessment against a maneuvering
target.

Does NOT do: pure proportional navigation without the augmentation term as the
primary claim (proportional-navigation owns the unaugmented law, its geometry,
and its corpus tasks); pursuit or line-of-sight guidance laws (pursuit-guidance,
command-to-line-of-sight); midcourse waypoint steering (midcourse-guidance);
impact point prediction (impact-point-prediction); path planning
(dubins-path-planning, coverage-path-planning). The augmentation term is the
distinct output: APN = N' * (Vc * lamdot + a_T_perp / 2) in the planar
constant-speed approximation.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- N_DEFAULT = 4.0 (effective navigation ratio default).

Functions (pure stdlib):
- los_rate(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y) -> float:
  lamdot = (rel_pos_x * rel_vel_y - rel_pos_y * rel_vel_x) /
  (rel_pos_x**2 + rel_pos_y**2) (planar line-of-sight rate, rad/s).
  ValueError on the zero relative position vector.
- closing_velocity(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y) -> float:
  Vc = -(rel_pos_x * rel_vel_x + rel_pos_y * rel_vel_y) /
  sqrt(rel_pos_x**2 + rel_pos_y**2). ValueError on the zero relative position
  vector; Vc may be negative (opening geometry) and is passed through.
- pn_command(navigation_ratio, closing_velocity, los_rate) -> float:
  a_pn = N * Vc * lamdot (m/s2). ValueError if navigation_ratio <= 0.
- apn_command(navigation_ratio, closing_velocity, los_rate,
  target_lateral_accel) -> float:
  a_apn = N * (Vc * lamdot + target_lateral_accel / 2) (m/s2). ValueErrors:
  navigation_ratio <= 0. target_lateral_accel may be any sign.
- commanded_accel_g(accel_m_s2) -> float: accel / G0.
- time_to_go(range_m, closing_velocity) -> float: t_go = range / Vc.
  ValueError if range < 0 or closing_velocity <= 0.
- apn_assessment(rel_pos_x, rel_pos_y, rel_vel_x, rel_vel_y,
  target_lateral_accel, navigation_ratio=N_DEFAULT, range_m=None) -> dict:
  convenience chain returning {los_rate, closing_velocity, pn_command_m_s2,
  apn_command_m_s2, pn_command_g, apn_command_g, time_to_go_s (None when
  range_m is None)}.

## Worked example

Planar intercept: closing velocity 900 m/s, LOS rate 0.005 rad/s, target
lateral acceleration 10 m/s2, navigation ratio 4.0.

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- PN command in 15-21 m/s2 (about 18.0, i.e. about 1.8 g).
- APN command in 34-42 m/s2 (about 38.0, i.e. about 3.9 g).
- The augmentation term adds N/2 * a_T = 20 m/s2 to the PN command.
- With rel_pos = (8000, 6000) m and rel_vel = (-600, -300) m/s: range
  10 000 m, closing velocity about 660 m/s, LOS rate about -1.15e-4 rad/s
  (compute the exact value from your module and assert within its bound of
  -2e-4 to 0).
- t_go at range 10 000 m and Vc 660 m/s in 13-17 s (about 15.2).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: navigation_ratio <= 0, zero relative position, range < 0,
  closing_velocity <= 0 in time_to_go.
- Degenerate: apn_command with target_lateral_accel = 0 equals pn_command.
- Scaling: apn_command with doubled target_lateral_accel grows by exactly
  N/2 times the accel increment.
- LOS rate sign: a target crossing from left gives the opposite sign of the
  same geometry mirrored (rel_vel_y sign flip).
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-augmented-proportional-navigation.yaml)

Query 1 (copy verbatim):
  "compute the augmented-proportional-navigation command for a maneuvering-target-intercept: add the target-lateral-acceleration term to the proportional navigation law"
  intent: "gnc-autonomy; augmented proportional navigation command with target acceleration"
  expected_skill: "gnc-autonomy/guidance/augmented-proportional-navigation"
Query 2 (copy verbatim):
  "determine the line-of-sight rate and the commanded lateral acceleration in g for an augmented-proportional-navigation guidance law against an accelerating target"
  intent: "gnc-autonomy; APN guidance law geometry and g-load command"
  expected_skill: "gnc-autonomy/guidance/augmented-proportional-navigation"
Task ids: w31-augmented-proportional-navigation-1 and -2.

Forbidden tokens that belong to siblings: do NOT claim the unaugmented
proportional navigation geometry as the primary output, do NOT use pursuit
heading, line-of-sight guidance, CLOS, beam rider, midcourse waypoint,
impact point prediction, Dubins path. The word proportional navigation may
appear only inside the compound augmented-proportional-navigation or as the
baseline being augmented; corpus queries MUST carry the augmented or target
acceleration tokens above.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute augmented proportional
navigation guidance commands for a planar intercept of a maneuvering target:"
and include the outputs listed in the Claim. First tag:
augmented-proportional-navigation. Additional tags only:
maneuvering-target-intercept, target-lateral-acceleration, apn-command,
guidance-law-augmentation. NEVER single generic words (guidance, navigation,
intercept, missile, target, acceleration). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.
