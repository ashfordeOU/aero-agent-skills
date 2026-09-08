# Wave-46 leaf spec: impact-time-control-guidance (gnc-autonomy, guidance pack)

- Path: skills/gnc-autonomy/guidance/impact-time-control-guidance/
- Pack: guidance (present siblings include proportional-navigation-guidance,
  augmented-proportional-navigation, midcourse-guidance, impact-point-
  prediction, pursuit-guidance and the other intercept-law leaves; the
  wave-46 whole-family probe task-7 GO-2 at HEAD 45931c16).
- Claim fences (quoted from the sibling frontmatter/body at prep; none
  claims the impact-time-constrained terminal law):
  - impact-point-prediction (this pack): "Use when the task is predicting
    where an unguided ballistic projectile lands from its launch state:
    range, time of flight, impact..." - open-loop, unguided, no guidance
    command.
  - midcourse-guidance (this pack, body lines 34-35): steering to "a
    waypoint, a constraint corridor, a handover geometry" rather than "to
    the target directly; a terminal law (proportional navigation, pursuit,
    ...)" - owns the handover trigger and ZEM/trajectory-shaping, no
    commanded-impact-time law.
  - augmented-proportional-navigation (this pack): adds "the target lateral
    acceleration perpendicular to the line of sight scaled by half the
    effective navigation ratio" - maneuvering-target augmentation, not
    time-of-arrival control.
  - proportional-navigation (this pack): the unaugmented planar law; its
    augmented sibling's Related-leaves fence routes the two PN forms to
    their own leaves.
  Whole-tree greps at prep (receipt gate (a), re-verified at spec prep):
  impact-time | salvo | impact-angle -> 0 hits under skills/ and 0 of 1266
  corpus tasks; no wave40-46 recon or leaf plan names the seam. GENUINE
  gap: no guidance leaf produces a time-to-go-error-feedback command for a
  commanded impact time (simultaneous-arrival / salvo).
- Standards id: arp4754a (grep-verified at spec prep: standards-map.yaml
  line 38; reference-only, the guidance-pack convention of the sibling
  intercept-law leaves). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Compute the deterministic impact-time-control guidance (ITCG) command for a
planar salvo/simultaneous-impact engagement against a stationary target:
the proportional-navigation (PN) baseline acceleration from the closing
speed and line-of-sight rate, the leading-order PNG time-to-go estimate on
the collision course, the impact-time error between the commanded remaining
time-to-go and the PNG estimate, and the impact-time-error feedback bias
acceleration that lengthens or shortens the intercept path so the group
arrives at the commanded impact time. Produces the total lateral
acceleration command, the PN baseline, the bias term, the time-to-go
estimate and the impact-time error for the given engagement state.

Does NOT do: trajectory propagation or numeric integration (the command is
evaluated at the given engagement state; a fixed-step Euler check of the
bias sign appears only in the contract test as a deterministic identity
probe, not as a leaf feature); maneuvering-target augmentation (belongs to
augmented-proportional-navigation); impact-angle constraints (no leaf in
the family claims them; out of scope here); waypoint/corridor steering or
handover (midcourse-guidance); unguided ballistic prediction
(impact-point-prediction); guidance gain scheduling or autopilot design.
The model is the canonical biased-PN impact-time-control structure of the
Jeon-Lee-Tahk family (Jeon, Lee and Tahk, "Impact-time-control guidance law
for anti-ship missiles," IEEE Transactions on Aerospace and Electronic
Systems 42(2):629-641, 2006, summarized by name and paraphrase only, never
reproduced): proportional-navigation baseline plus an impact-time-error
feedback term driven by time-to-go, with the feedback gain scheduled on the
engagement state (here the navigation constant, the family's standard
scheduling choice).

## Model (implement exactly)

Module constants (documented in the logic file):
- K_IT_DEFAULT = 4.0 (default impact-time feedback gain, scheduled on the
  engagement state as the navigation constant)

Functions (pure stdlib math, deterministic, no RNG):

1. png_baseline(nav_constant, closing_speed, los_rate) -> float
   a_png = nav_constant * closing_speed * los_rate  (m/s^2)
   ValueError: nav_constant <= 1.0 (navigation constant must exceed 1 for
   a converging intercept law), closing_speed < 0.0.

2. tgo_estimate_png(closing_speed, range_to_target) -> float
   t_go = range_to_target / closing_speed  (s), the leading-order PNG
   time-to-go on the collision course (exact when the interceptor flies
   the collision triangle).
   ValueError: closing_speed <= 0.0, range_to_target < 0.0.

3. impact_time_bias(gain, closing_speed, tgo_desired, tgo_actual) -> float
   e_t = tgo_desired - tgo_actual
   a_b = gain * closing_speed * e_t / tgo_actual^2  (m/s^2)
   Positive bias (e_t > 0, interceptor must arrive later than the natural
   PNG time) pulls the trajectory onto a longer course; negative bias
   (e_t < 0) shortens it.
   ValueError: gain <= 0.0, closing_speed <= 0.0, tgo_actual <= 0.0,
   tgo_desired <= 0.0.

4. itcg_command(nav_constant, closing_speed, los_rate, range_to_target,
   tgo_desired, gain=None) -> tuple (a_cmd, a_png, a_b, tgo_png, e_t)
   a_png = png_baseline(...); tgo_png = tgo_estimate_png(...);
   a_b = impact_time_bias(gain or K_IT_DEFAULT, closing_speed,
   tgo_desired, tgo_png); a_cmd = a_png + a_b.
   Returns (total lateral acceleration command m/s^2, PN baseline m/s^2,
   bias term m/s^2, PNG time-to-go estimate s, impact-time error s).

5. time_to_impact_seconds(range_to_target, closing_speed) -> float
   Natural (uncontrolled) time to impact on the collision course, s
   (= tgo_estimate_png).

No imports beyond math. All computations float; all asserts in the
contract test use math.isclose / assertAlmostEqual tolerances (no exact
float equality on computed sums).

## Identities to test

1. Zero impact-time error: when tgo_desired equals the PNG time-to-go
   estimate, the bias is exactly 0 and the total command equals the pure
   PN baseline (a_cmd == a_png within 1e-12 relative).
2. Time-to-go estimate: tgo_estimate_png(Vc, R) = R / Vc exactly
   (a ratio of two given floats; assert with math.isclose rel 1e-15).
3. Impact-time error arithmetic: e_t = tgo_desired - tgo_png for the
   worked example below (rel 1e-15).
4. Bias sign physics: for e_t > 0 (later arrival commanded) the bias is
   positive; for e_t < 0 the bias is negative (sign check on two crafted
   inputs).
5. Bias dimension/scheduling: at fixed gain, doubling closing speed at
   constant e_t/tgo_actual^2 doubles the bias magnitude (linearity in
   closing_speed).
6. Determinism: calling itcg_command twice with identical inputs returns
   bit-identical results.
7. Natural time identity: time_to_impact_seconds(R, Vc) equals the PNG
   time-to-go estimate (same closed form).
8. Fixed-step Euler sign probe (test-side, deterministic): with the
   worked-example engagement state and a positive commanded delay, a
   simple constant-speed lateral-autopilot integration reaches the target
   later than the same integration with the bias forced to zero
   (illustrative physics check, tolerance 0.5 s; integration runs in the
   test with fixed dt = 0.01, no RNG, < 20 s wall).

## Worked example

All values below are REAL outputs of the prep anchor
/tmp/w46spec/anchor_impact_time_guidance.py (pure stdlib, exit 0).

Engagement: stationary target, R = 8000.0 m, V_c = 300.0 m/s,
lambda_dot = 0.004 rad/s, N = 4.0, commanded remaining time-to-go
t_go_des = 30.0 s. Natural PNG time to impact = 8000/300 = 26.666666666667 s.

- a_png = 4.800000000000 m/s^2
- tgo_png = 26.666666666667 s
- e_t = 3.333333333333 s (tgo_des - tgo_png, positive: arrive later)
- a_bias = 5.625000000000 m/s^2  (= 4.0 * 300.0 * 3.333333333333 /
  26.666666666667^2)
- a_cmd = 10.425000000000 m/s^2

Zero-error identity at tgo_des = tgo_png: a_cmd = 4.800000000000 m/s^2,
a_bias = 0.000000000000 m/s^2, e_t = 0.0.

Euler sign probe (same anchor, V = 340 m/s, 5 deg initial lead):
natural PNG impact at t = 23.5500 s; biased ITCG impact at t = 27.6500 s
(commanded 30 s); the bias lengthens the flight time by 4.1000 s.

## Validation list (deterministic checks the contract test must run)

1. Worked-example asserts: a_png within 1e-9 relative of 4.8, tgo_png
   within 1e-9 relative of 26.666666666667, e_t within 1e-9 relative of
   3.333333333333, a_bias within 1e-9 relative of 5.625, a_cmd within
   1e-9 relative of 10.425.
2. Zero-error identity: tgo_des = tgo_png -> a_bias == 0 within 1e-12,
   a_cmd == a_png within 1e-12 (both absolute and relative).
3. ValueErrors: nav_constant <= 1.0 (test 1.0 and 0.5); closing_speed < 0
   in png_baseline; closing_speed <= 0 in tgo_estimate_png;
   range_to_target < 0; gain <= 0 in impact_time_bias; tgo_actual <= 0;
   tgo_desired <= 0.
4. Boundary: closing_speed = 0 raises; range = 0 gives tgo = 0 (valid,
   no raise when closing_speed > 0).
5. Sign checks: crafted e_t > 0 case gives positive a_bias; e_t < 0 case
   gives negative a_bias.
6. Linearity: doubling closing_speed doubles the bias at constant
   e_t / tgo_actual^2 (rel 1e-12).
7. Determinism: two identical itcg_command calls return identical tuples.
8. Natural-time identity: time_to_impact_seconds equals tgo_estimate_png.
9. Euler sign probe: biased integration impact time exceeds the unbiased
   one by > 3.0 s at the worked-example command (tolerance band around the
   anchor's 4.1 s; assert the difference is between 3.0 and 5.5 s).
10. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for eval/hit1-wave46-impact-time-
control-guidance.yaml)

Copy EXACTLY (receipt gate (e), sim-verified Hit@1):

tasks:
  - id: w46-impact-time-control-guidance-1
    query: "compute the impact-time-control-guidance command for the salvo
      attack: form the proportional navigation baseline from the line of
      sight rate and closing velocity, estimate time to go, and add the
      impact-time-error feedback term scaled by the navigation constant"
    intent: "gnc-autonomy; salvo impact-time-control guidance command from
      PN baseline and time-to-go-error feedback"
    expected_skill: "gnc-autonomy/guidance/impact-time-control-guidance"
  - id: w46-impact-time-control-guidance-2
    query: "run the impact-time-control-guidance law so the interceptor
      group arrives at the commanded-impact-time: evaluate the
      time-to-go-error-feedback term and report the simultaneous-impact
      guidance command"
    intent: "gnc-autonomy; commanded-impact-time arrival via
      time-to-go-error-feedback"
    expected_skill: "gnc-autonomy/guidance/impact-time-control-guidance"

## Description/tag guidance for the builder

Draft description (action verb, <= 1000 chars, <= 148 words):

"Use when you must compute the impact-time-control-guidance command for a
salvo or simultaneous-impact engagement: the proportional-navigation
baseline acceleration from the closing speed and the line of sight rate,
the PNG time-to-go estimate on the collision course, the impact-time error
between the commanded remaining time to go and the natural PNG time, and
the time-to-go-error-feedback bias that lengthens or shortens the intercept
path so the group arrives at the commanded impact time. Produces the total
lateral acceleration command with its PN baseline, bias term, time-to-go
estimate and impact-time error."

Metadata tags EXACTLY (receipt gate (f), hyphenated only):
impact-time-control-guidance (first tag), salvo-attack-guidance,
commanded-impact-time, time-to-go-error-feedback,
simultaneous-impact-guidance.

FORBIDDEN tokens (sibling claims): proportional-navigation as a tag or
headline claim (the PN law itself belongs to proportional-navigation-
guidance), zero-effort-miss, waypoint-steering, trajectory-shaping (midcourse-
guidance), impact-point-prediction tokens (ballistic open-loop), and any
single-word generic tags (guidance, control, navigation, intercept).

Build-time notes: add one fence line to the guidance-pack proportional-
navigation or augmented-proportional-navigation leaf pointing
impact-time / salvo / commanded-impact-time content to this leaf, one
router row in skills/gnc-autonomy/SKILL.md, and 2 corpus tasks at merge
(the receipt gate (e) sim shows both queries Hit@1 with margins 32.0 vs
21.5 and 20.0 vs 7.0, zero theft).
