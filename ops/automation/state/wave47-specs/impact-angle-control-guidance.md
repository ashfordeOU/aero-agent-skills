# Wave-47 leaf spec: impact-angle-control-guidance (gnc-autonomy, guidance pack)

- Path: skills/gnc-autonomy/guidance/impact-angle-control-guidance/
- Pack: guidance (present siblings include proportional-navigation,
  augmented-proportional-navigation, midcourse-guidance, impact-time-control-
  guidance, impact-point-prediction, pursuit-guidance, collision-course-
  guidance, command-to-line-of-sight and the other intercept-law leaves; the
  wave-47 whole-family probe task-3 GO-2 at HEAD a4ae6d1e).
- Claim fences (quoted from the sibling frontmatter/body at prep; none
  claims the impact-angle-constrained terminal law):
  - impact-time-control-guidance (this pack, pitfalls lines 137-138,
    verbatim): "Do not add impact-angle constraints: no leaf in the family
    claims them and they are out of scope for the time-only law." - the
    nearest sibling explicitly renounces the impact-angle member.
  - proportional-navigation (this pack, frontmatter description): "compute
    the proportional navigation guidance command for a planar intercept ...
    determine the closing velocity from the relative position and velocity
    vectors, compute the line of sight rate, and calculate the commanded
    acceleration perpendicular to the line of sight from the navigation
    constant" - the LOS-rate nulling baseline only; no terminal-angle
    constraint term.
  - augmented-proportional-navigation (this pack, body): adds "the target
    lateral acceleration perpendicular to the line of sight scaled by half
    the effective navigation ratio", and "with a_T_perp = 0 the augmented
    command degenerates to the pure proportional navigation command" -
    maneuvering-target augmentation of the same baseline, not angle shaping.
  - midcourse-guidance (this pack, body lines 25-33): steers "through the
    midcourse phase between launch and terminal handover: reaching a planned
    waypoint or constraint geometry, shaping the trajectory" - waypoint and
    handover territory, no terminal impact-angle command.
  - impact-point-prediction (this pack): open-loop unguided ballistic impact
    prediction from launch state; no guidance command at all.
  - pursuit-guidance (this pack): "pure pursuit or lead pursuit aim heading,
    the guidance error, the capture condition" - LOS-alignment heading laws.
  Whole-tree greps at prep (receipt gate (a), re-verified at spec prep):
  `rg -i -l 'impact[- ]angle|terminal[- ]angle' skills/ -g 'SKILL.md'` ->
  1 hit: the impact-time-control-guidance sibling's own pitfall line
  137-138 above, an explicit renunciation and not an ownership claim; corpus
  scan `rg -ic 'impact[- ]angle|terminal[- ]angle' eval/hit1-corpus.yaml` ->
  0 of 1286 tasks. GENUINE gap: no guidance leaf computes a terminal-impact-
  angle-constrained guidance command.
- Standards id: arp4754a (grep-verified at spec prep: standards-map.yaml
  line 38; reference-only, the guidance-pack convention of the sibling
  intercept-law leaves, same as the impact-time sibling). Ledger Standard:
  arp4754a.
- Family: gnc-autonomy

## Claim

Compute the deterministic impact-angle-control guidance command for a planar
intercept of a stationary target with a commanded terminal flight path angle:
the collision-course nulling baseline from the crossrange offset, the
crossrange velocity component and the time-to-go estimate, the terminal
crossrange velocity that realizes the commanded impact angle, the impact-
angle error between the commanded terminal flight path angle and the current
flight path angle, and the impact-angle-error feedback bias that reshapes the
intercept path so the interceptor meets the target at the commanded impact
angle. Produces the total lateral acceleration command, the collision-course
nulling baseline, the bias term, the time-to-go estimate and the impact-angle
error for the given engagement state. The model is the energy-optimal
impact-angle-constrained guidance structure of the Ryoo-Cho-Tahk family
(Ryoo, Cho and Tahk, "Optimal Guidance Laws with Terminal Impact Angle
Constraint," Journal of Guidance, Control, and Dynamics 28(4):724-732, 2005,
summarized by name and paraphrase only, never reproduced): a time-to-go
polynomial shaping law specialized to a stationary target, written as the
PN-like collision-course nulling baseline plus the impact-angle-error
feedback bias (v - v_f)/t_go-scaled.

Does NOT do: trajectory propagation or numeric integration as a leaf feature
(the command is evaluated at the given engagement state; the fixed-step Euler
planar engagement check appears only in the contract test as a deterministic
terminal-angle identity probe, not as a leaf capability); maneuvering-target
augmentation (belongs to augmented-proportional-navigation); impact-time or
salvo control (impact-time-control-guidance owns the time-constrained member
of the terminal-law family); waypoint/corridor steering or handover
(midcourse-guidance); unguided ballistic prediction (impact-point-
prediction); the standalone proportional-navigation law, its capture
conditions or its variants (proportional-navigation siblings); 3D engagement
geometry; seeker, sensor, measurement or noise modeling; guidance gain
scheduling or autopilot design.

## Model (implement exactly)

Module constants (documented in the logic file):
- W_Y = 6.0, W_V = 4.0, W_VF = 2.0 (time-to-go polynomial weights on the
  crossrange offset, the crossrange velocity and the terminal crossrange
  velocity of the energy-optimal impact-angle law)

Functions (pure stdlib math, deterministic, no RNG):

1. crossrange_velocity(speed, gamma) -> float
   v = speed * sin(gamma)  (m/s), the crossrange velocity component.
   ValueError: speed <= 0.0.

2. tgo_estimate(closing_speed, range_to_target) -> float
   t_go = range_to_target / closing_speed  (s), the leading-order time-to-go
   on the closing geometry (exact on the collision course).
   ValueError: closing_speed <= 0.0, range_to_target < 0.0.

3. impact_angle_error(commanded_gamma, gamma) -> float
   e_g = commanded_gamma - gamma  (rad), the impact-angle error between the
   commanded terminal flight path angle and the current flight path angle.
   No rejection (planar unwrapped difference; the model stays away from the
   wrap discontinuity by convention of the worked engagement).

4. impact_angle_bias(speed, tgo, gamma, commanded_gamma) -> float
   v = crossrange_velocity(speed, gamma); v_f = crossrange_velocity(speed,
   commanded_gamma); a_bias = 2.0 * (v - v_f) / tgo  (m/s^2), the impact-
   angle-error feedback. Positive when the current crossrange velocity
   exceeds the terminal one (a steeper terminal dive must first be set up),
   negative when the commanded course is shallower.
   ValueError: speed <= 0.0, tgo <= 0.0.

5. collision_nulling_baseline(tgo, crossrange_offset, v_perp) -> float
   a_base = -W_Y * (crossrange_offset + v_perp * tgo) / tgo^2  (m/s^2), the
   PN-like collision-course nulling term: zero when the interceptor is on
   the collision course (crossrange_offset + v_perp * tgo = 0). In the
   linearized model this is the LOS-rate-nulling baseline of the law.
   ValueError: tgo <= 0.0.

6. impact_angle_guidance_command(tgo, crossrange_offset, v_perp, speed,
   gamma, commanded_gamma) -> tuple (a_cmd, a_base, a_bias, t_go, e_g)
   a_bias = impact_angle_bias(speed, tgo, gamma, commanded_gamma);
   a_base = collision_nulling_baseline(tgo, crossrange_offset, v_perp);
   a_cmd = a_base + a_bias.
   Returns (total lateral acceleration command m/s^2, collision-course
   nulling baseline m/s^2, impact-angle-error bias m/s^2, time-to-go
   estimate s, impact-angle error rad).
   ValueError: speed <= 0.0, tgo <= 0.0.

No imports beyond math. All computations float; all asserts in the contract
test use math.isclose / assertAlmostEqual tolerances (no exact float equality
on computed sums).

## Identities to test

1. Zero impact-angle error: when gamma equals commanded_gamma, the bias is
   exactly 0 and the total command equals the collision-course nulling
   baseline alone (a_bias == 0 within 1e-12 absolute).
2. Collision course: when crossrange_offset + v_perp * tgo == 0 the baseline
   is exactly 0 (the miss is already nulled).
3. Terminal straight course (closed-form null command): on the straight line
   that reaches the target at the commanded angle, v = v_f and
   crossrange_offset = -v_f * tgo, so a_base and a_bias both vanish and
   a_cmd == 0 exactly (anchor: 0.000000000000 m/s^2 at tgo = 10 s).
4. Impact-angle error arithmetic: e_g = commanded_gamma - gamma for the
   worked example below (rel 1e-15).
5. Bias sign physics: for a steeper commanded terminal angle (commanded_gamma
   more negative than gamma, so v - v_f > 0) the bias is positive; for a
   shallower command the bias is negative (anchor: -12.462790070115 m/s^2).
6. Bias linearity: at fixed geometry and angles, doubling the speed doubles
   the bias magnitude (anchor: 13.176914536240 = 2 * 6.588457268120).
7. Determinism: calling impact_angle_guidance_command twice with identical
   inputs returns bit-identical results.
8. Linear-model terminal constraint: fixed-step Euler integration (dt =
   0.001) of the linearized kinematics under the closed-form law drives the
   crossrange velocity to v_f and the offset toward 0 as tgo -> 0 (anchor:
   v_end - v_f = -1.539e-02 m/s, y_end = 0.086606202 m).
9. Nonlinear planar engagement (test-side, deterministic): fixed-step Euler
   integration of the point-mass kinematics under the law reaches the
   stationary target with terminal flight path angle within ~0.3 deg of the
   commanded gamma_f across dt = 0.005 down to dt = 0.0002 (anchor sample at
   dt = 0.005: gamma_end = -60.037102 deg vs -60.000000 commanded).

## Worked example

All values below are REAL outputs of the prep anchor
/tmp/w47spec/anchor_impact_angle_control_guidance.py (pure stdlib, exit 0).

Engagement: stationary target at the origin; interceptor starts at
x = -8660.254038 m, y = +5000.000000 m (range exactly 10000.0 m, line of
sight 30 deg below the horizontal), V = 300.0 m/s, gamma_0 = -30 deg
(velocity along the line of sight, i.e. a collision course), commanded
terminal flight path angle gamma_f = -60 deg, y_0 = +5000.0 m crossrange
offset, closing speed V_c = 300.0 m/s on the collision course.

- t_go0 = 33.333333333333 s  (= 10000.0 / 300.0)
- v0 = crossrange_velocity(300.0, -0.523598776) = -150.000000000000 m/s
- v_f = crossrange_velocity(300.0, -1.047197551) = -259.807621135332 m/s
- e_g0 = -0.523598775598 rad = -30.000000000000 deg (gamma_f - gamma_0)
- a_base0 = -0.000000000000 m/s^2 (collision course: y_0 + v0 * t_go0 = 0)
- a_bias0 = 6.588457268120 m/s^2
  (= 2.0 * (-150.0 - (-259.807621135332)) / 33.333333333333)
- a_cmd0 = 6.588457268120 m/s^2
- impact_angle_guidance_command(t_go0, y_0, v0, V, gamma_0, gamma_f) =
  (6.588457268120, -0.000000000000, 6.588457268120, 33.333333333333,
  -0.523598775598)

Identity samples from the same anchor run: zero-error bias (gamma =
gamma_f) = 0.000000000000 m/s^2; terminal straight course at tgo = 10 s
(y = 2598.076211353 m, v = v_f = -259.807621135 m/s) gives a_cmd =
0.000000000000 m/s^2; bias linearity 13.176914536240 = 2 * 6.588457268120;
shallowing-command bias (gamma = -60 deg, commanded -10 deg) =
-12.462790070115 m/s^2; determinism bit-identical: True. Linear-model
closed loop (dt = 0.001): y_end = 0.086606202 m, v_end = -259.823007259
m/s vs v_f = -259.807621135 m/s (difference -1.539e-02 m/s).

Planar engagement identity probe (Euler, dt = 0.005, speed 300 m/s,
stationary target, stop at range <= 0.5 m or at closest approach):
flight time = 33.885000 s, miss range = 0.096219 m, gamma_end =
-60.037102 deg vs commanded -60.000000 deg (terminal-angle error
-0.037102 deg). The max sampled command 1436.184250 m/s^2 (146.450 g)
occurs in the final tgo -> 0 step at range ~1.4 m, the terminal
singularity of the time-to-go polynomial command (commands stay below
~55 m/s^2 while range >= 50 m); the identity asserted by the contract test
is the terminal flight path angle, which lands within ~0.25 deg of the
command for dt from 0.005 down to 0.0002 (anchor sample at dt = 0.005:
gamma_end = -60.037102 deg).

## Validation list (deterministic checks the contract test must run)

1. Worked-example asserts: t_go0 within 1e-9 relative of 33.333333333333,
   v0 within 1e-9 relative of -150.000000000000, v_f within 1e-9 relative
   of -259.807621135332, e_g0 within 1e-9 relative of -0.523598775598 rad
   and of -30.000000000000 deg, |a_base0| < 1e-9 (collision course),
   a_bias0 within 1e-9 relative of 6.588457268120, a_cmd0 within 1e-9
   relative of 6.588457268120, and the full command tuple equals
   (6.588457268120, -0.000000000000, 6.588457268120, 33.333333333333,
   -0.523598775598) elementwise within 1e-9.
2. Zero-error identity: gamma = commanded_gamma -> a_bias == 0 within 1e-12
   absolute, a_cmd == a_base within 1e-12.
3. Terminal straight course: v = v_f and offset = -v_f * tgo -> a_cmd == 0
   within 1e-9 absolute (anchor exactly 0.000000000000).
4. Collision course: offset = -v_perp * tgo -> a_base == 0 within 1e-9.
5. ValueErrors: speed <= 0 in crossrange_velocity, impact_angle_bias and
   impact_angle_guidance_command (test 0.0 and -1.0); closing_speed <= 0
   and range_to_target < 0 in tgo_estimate; tgo <= 0 in impact_angle_bias,
   collision_nulling_baseline and impact_angle_guidance_command (test 0.0
   and -1.0).
6. Boundary: range_to_target = 0 with closing_speed > 0 gives t_go = 0
   (valid, no raise); tgo exactly 0 then raises in the bias functions.
7. Sign checks: crafted steeper command (commanded_gamma < gamma) gives
   positive a_bias; shallower command (commanded_gamma > gamma) gives
   negative a_bias (anchor -12.462790070115 at gamma = -60 deg, commanded
   -10 deg).
8. Linearity: doubling the speed doubles the bias magnitude at fixed
   geometry and angles (rel 1e-12; 13.176914536240 = 2 * 6.588457268120).
9. Determinism: two identical impact_angle_guidance_command calls return
   identical tuples.
10. Linear-model terminal constraint: fixed-step Euler (dt = 0.001) of
    dy/dt = v, dv/dt = a_cmd with tgo reduced by dt each step drives
    |v_end - v_f| < 0.05 m/s and |y_end| < 1.0 m (anchor: 0.0154 m/s,
    0.0866 m).
11. Planar engagement identity probe: fixed-step Euler (dt = 0.005, stop at
    range <= 0.5 m or at closest approach, no RNG, wall < 20 s) from the
    worked-example state reaches the target with flight time between 33.5 s
    and 34.5 s, miss range < 5.0 m, and terminal flight path angle between
    -61.0 deg and -59.0 deg (anchor: 33.885 s, 0.096 m, -60.037 deg);
    the same probe with dt = 0.001 keeps the terminal angle within the
    same band.
12. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for eval/hit1-wave47-impact-angle-
control-guidance.yaml)

Copy EXACTLY (receipt gate (e), sim-verified Hit@1):

tasks:
  - id: w47-impact-angle-control-guidance-1
    query: "compute the impact-angle-control-guidance command so the
      interceptor meets the target at the commanded impact angle: form the
      impact-angle error feedback from the current flight path angle and the
      time to go and shape the guidance command"
    intent: "gnc-autonomy; impact-angle-constrained guidance command from
      impact-angle-error feedback and time to go"
    expected_skill: "gnc-autonomy/guidance/impact-angle-control-guidance"
  - id: w47-impact-angle-control-guidance-2
    query: "run the terminal-impact-angle guidance law: evaluate the
      impact-angle-error-feedback term shaped by time to go and report the
      guidance command that drives the terminal flight path angle to the
      commanded-impact-angle"
    intent: "gnc-autonomy; terminal impact angle arrival via
      impact-angle-error-feedback and time-to-go shaping"
    expected_skill: "gnc-autonomy/guidance/impact-angle-control-guidance"

## Description/tag guidance for the builder

Draft description (action verb, <= 1000 chars, <= 148 words):

"Use when you must compute the impact-angle-control-guidance command for a
planar intercept against a stationary target with a commanded terminal
flight path angle: the collision-course nulling baseline from the crossrange
offset, the crossrange velocity and the time to go, the terminal crossrange
velocity that realizes the commanded impact angle, the impact-angle error
between the commanded terminal flight path angle and the current flight path
angle, and the impact-angle-error-feedback bias that reshapes the intercept
path so the interceptor meets the target at the commanded impact angle.
Produces the total lateral acceleration command with its nulling baseline,
bias term, time-to-go estimate and impact-angle error."

Metadata tags EXACTLY (receipt gate (f), hyphenated only):
impact-angle-control-guidance (first tag), terminal-impact-angle,
commanded-impact-angle, impact-angle-error-feedback,
terminal-flight-path-angle-constraint.

FORBIDDEN tokens (sibling claims): impact-time-control, salvo,
simultaneous-impact, commanded-impact-time, time-to-go-error-feedback
(impact-time-control-guidance owns the time-constrained member of the
terminal-law family); proportional-navigation as a tag or headline claim
(the standalone PN law and its variants belong to the proportional-navigation
siblings; the baseline here is described as the collision-course nulling
term); zero-effort-miss, waypoint-steering, trajectory-shaping, velocity-to-
be-gained, handover-condition (midcourse-guidance); impact-point-prediction
tokens (ballistic open-loop); target-lateral-acceleration, maneuvering-target
(augmented-proportional-navigation); 3D engagement geometry, seeker, sensor
or measurement modeling; and any single-word generic tags (guidance, control,
navigation, intercept, missile).

Build-time notes: add one fence line to the guidance-pack impact-time-control-
guidance leaf (its pitfall at lines 137-138 already renounces impact-angle
constraints; extend with a Related-leaves pointer) or to proportional-
navigation pointing terminal-impact-angle / commanded-impact-angle content to
this leaf, one router row in skills/gnc-autonomy/SKILL.md, and 2 corpus tasks
at merge (the receipt gate (e) sim shows both queries Hit@1 with margins 24.5
vs 17.5 and 21.0 vs 11.0, zero theft).
