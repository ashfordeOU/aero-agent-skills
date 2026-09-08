---
name: impact-time-control-guidance
description: "Use when you must compute the impact-time-control-guidance command for a salvo or simultaneous-impact engagement: the proportional-navigation baseline acceleration from the closing speed and the line of sight rate, the PNG time-to-go estimate on the collision course, the impact-time error between the commanded remaining time to go and the natural PNG time, and the time-to-go-error-feedback bias that lengthens or shortens the intercept path so the group arrives at the commanded impact time. Produces the total lateral acceleration command with its PN baseline, bias term, time-to-go estimate and impact-time error. Trigger: impact time control, salvo attack, simultaneous impact, commanded impact time, time to go error feedback, ITCG."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: guidance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: guidance
  tags: [impact-time-control-guidance, salvo-attack-guidance, commanded-impact-time, time-to-go-error-feedback, simultaneous-impact-guidance]
  version: 0.1.0
  author: Aero Agent Skills
---

# Impact-Time-Control Guidance (gnc-autonomy/guidance/impact-time-control-guidance)

Use when the task is computing the impact-time-control guidance (ITCG)
command for a salvo or simultaneous-impact engagement against a stationary
target: the proportional-navigation (PN) baseline from the closing geometry,
the leading-order PNG time-to-go estimate on the collision course, the
impact-time error between the commanded remaining time-to-go and the natural
PNG estimate, and the time-to-go-error-feedback bias that steers the
interceptor group to arrive at the commanded impact time. This is the
canonical biased-PN impact-time-control structure of the Jeon-Lee-Tahk
family (IEEE Transactions on Aerospace and Electronic Systems 42(2):629-641,
2006, summarized by name and paraphrase only, never reproduced). Pairing
leaves: proportional-navigation-guidance owns the unaugmented planar PN law,
augmented-proportional-navigation the maneuvering-target augmentation;
impact-point-prediction is open-loop ballistic prediction; midcourse-guidance
handles waypoint steering and handover.

## Domain quick reference

- Planar collision-course intercept against a stationary target: closing
  speed V_c (m/s), line of sight rate lambda_dot (rad/s), range to target
  R (m), navigation constant N (dimensionless, > 1), commanded remaining
  time-to-go t_go_des (s).
- PN baseline acceleration: a_png = N * V_c * lambda_dot.
- PNG time-to-go on the collision course: t_go = R / V_c (exact when the
  interceptor flies the collision triangle).
- Impact-time error: e_t = t_go_des - t_go.
- Time-to-go-error-feedback bias: a_b = K_it * V_c * e_t / t_go^2, with the
  feedback gain K_it scheduled on the engagement state (navigation
  constant by default).
- Total command: a_cmd = a_png + a_b.
- A positive error (later arrival commanded than the natural PNG time)
  gives a positive bias that lengthens the intercept path; a negative
  error shortens it.

## Workflow

1. Fix the engagement state: closing speed V_c, line of sight rate
   lambda_dot, range R, navigation constant N and the commanded remaining
   time-to-go t_go_des. Non-physical inputs are rejected with ValueError
   (navigation constant at or below 1, non-positive closing speed or range
   in the estimate, non-positive gain or times in the bias).
2. Compute the PN baseline with png_baseline(nav_constant, closing_speed,
   los_rate): a_png = N * V_c * lambda_dot.
3. Estimate the natural PNG time-to-go with tgo_estimate_png(closing_speed,
   range_to_target): t_go = R / V_c.
4. Form the impact-time error e_t = t_go_des - t_go between the commanded
   remaining time-to-go and the PNG estimate.
5. Compute the time-to-go-error-feedback bias with
   impact_time_bias(gain, closing_speed, tgo_desired, tgo_actual):
   a_b = gain * V_c * e_t / t_go^2. The default gain is the navigation
   constant (K_IT_DEFAULT = 4.0); a custom gain may be passed.
6. Sum the baseline and the bias with itcg_command(nav_constant,
   closing_speed, los_rate, range_to_target, tgo_desired, gain=None),
   which returns (a_cmd, a_png, a_b, tgo_png, e_t): the total lateral
   acceleration command, its PN baseline, the bias term, the time-to-go
   estimate and the impact-time error.
7. Read the natural (uncontrolled) time to impact with
   time_to_impact_seconds(range_to_target, closing_speed), the same closed
   form as the PNG estimate, for the salvo feasibility context.
8. Confirm the deterministic checks with the contract test
   scripts/test_impact_time_control_guidance.py.

## Worked example

All values are REAL outputs of the logic module at the spec anchor state
(R = 8000.0 m, V_c = 300.0 m/s, lambda_dot = 0.004 rad/s, N = 4.0,
t_go_des = 30.0 s):

- png_baseline(4.0, 300.0, 0.004) = 4.800000000000 m/s^2
- tgo_estimate_png(300.0, 8000.0) = 26.666666666667 s
- impact time error e_t = 30.0 - 26.666666666667 = 3.333333333333 s
- impact_time_bias(4.0, 300.0, 30.0, 26.666666666667) = 5.625000000000 m/s^2
- itcg_command(4.0, 300.0, 0.004, 8000.0, 30.0) =
  (10.425000000000, 4.800000000000, 5.625000000000, 26.666666666667,
  3.333333333333)

The natural PNG time to impact is 26.67 s; commanding a 30 s simultaneous
arrival produces a positive bias of 5.625 m/s^2 that lengthens the intercept
path. Zero-error identity: at t_go_des equal to the PNG estimate the bias is
exactly 0 and the command collapses to the pure PN baseline
(4.8 m/s^2). The planar fixed-step Euler probe in the contract test shows
the bias lengthens the flight time by about 4.1 s at this command.

## Verification

- Deterministic stdlib math only; no RNG, no network, no numeric
  integration in the leaf (the Euler probe lives in the contract test as a
  test-side identity check).
- ValueErrors: navigation constant at or below 1.0; negative closing speed
  in the baseline; non-positive closing speed or negative range in the
  time-to-go estimate; non-positive gain, actual time-to-go or desired
  time-to-go in the bias.
- Identities: zero impact-time error gives zero bias and the pure PN
  command; the natural time to impact equals the PNG time-to-go estimate;
  doubling the closing speed at constant e_t / t_go^2 doubles the bias;
  two identical calls return bit-identical results.

## Related leaves

- gnc-autonomy/guidance/proportional-navigation-guidance (the unaugmented
  planar PN law that forms this law's baseline)
- gnc-autonomy/guidance/augmented-proportional-navigation (maneuvering-
  target augmentation of the same baseline)
- gnc-autonomy/guidance/midcourse-guidance (waypoint steering, handover,
  trajectory shaping)
- gnc-autonomy/guidance/impact-point-prediction (open-loop unguided
  ballistic impact prediction)
- gnc-autonomy/control/digital-control-design (sampled-data control of the
  inner loop that would track this command)

## Pitfalls

- Do not claim the proportional-navigation law itself: this leaf forms a PN
  baseline from given engagement geometry but the standalone law, its
  capture conditions and its variants belong to the PN siblings.
- Do not add impact-angle constraints: no leaf in the family claims them and
  they are out of scope for the time-only law.
- The bias formula is deterministic at the given engagement state; this is
  not a trajectory propagator. Do not present the fixed-step Euler check in
  the contract test as a leaf capability.
- The t_go = R / V_c estimate is the leading-order collision-course form;
  for wide heading errors the natural PNG time deviates from it, which is
  exactly the error the feedback term acts on.
- Keep the commanded time-to-go positive and the navigation constant above
  1.0; both are enforced with ValueError.
- Do not use single-word generic tags (guidance, control, navigation,
  intercept): they would steal corpus tasks from the family router rows.

## Behavior contract (gate 3)

The contract test scripts/test_impact_time_control_guidance.py (33 methods,
stdlib unittest, offline, deterministic) verifies: the worked-example
baseline, time-to-go, error, bias and total command within 1e-9 relative;
the zero-error identity (bias zero, command equal to the PN baseline); the
ValueError rejections (navigation constant at or below 1, negative closing
speed, non-positive closing speed or negative range in the estimate,
non-positive gain and non-positive times in the bias); boundary behavior;
the linearity of the bias in closing speed; determinism of repeated calls;
the natural-time identity; and the planar Euler sign probe showing the bias
lengthens the flight time by the anchor margin (between 3.0 and 5.5 s). The
test passes under both /usr/bin/python3 and the pyenv 3.13 interpreter; no
exact-float equality is asserted on computed sums.

## Compliance

STANDARDS-REF, gated false. ARP4754A (reference-only) frames development
assurance for guided systems; the ITCG law itself is paraphrased public
guidance-theory literature (Jeon, Lee and Tahk 2006) and is never
reproduced verbatim.
