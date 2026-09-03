---
name: deep-stall-analysis
description: "Assess whether a T-tail or aft-fuselage-mounted-tail airplane can enter a deep stall, a self-sustaining high-angle-of-attack trim beyond the stall sometimes called alpha lock, and whether the elevator retains pitch-down authority to recover. Compute the viscous stall angle from the wing lift slope, model the loss of horizontal-tail effectiveness in the wing or fuselage wake with a tail blanking factor, add the separated-flow wing-body pitch-up that rises after the stall and fades at very high angle of attack, solve for the post-stall trim angle in the deep-stall band, and compare the elevator pitch-down moment with the pitch-up hump it must overcome. Produces the stall angle, blanking factor at the trim, lock depth, recovery margin, and the deep-stall and alpha-lock verdicts. Trigger: deep stall, T-tail blanking, alpha lock, post-stall trim, tail blanking factor, separated flow pitch-up, pitch-down recovery authority."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: stability-control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: stability-control
  tags: [deep-stall-analysis, t-tail-blanking, alpha-lock, post-stall-trim, separated-flow-pitch-up, tail-blanking-factor, pitch-down-recovery-authority, wake-blanked-tail]
  version: 0.1.0
  author: Aero Agent Skills
---

# Deep Stall Analysis (flight-mechanics/stability-control/deep-stall-analysis)

Use when the task is to assess whether a T-tail or aft-fuselage-mounted
tail airplane can enter a deep stall, a self-sustaining high-angle-of-
attack trim beyond the stall sometimes called alpha lock, and whether
the elevator retains enough pitch-down authority to recover from it.
The model captures the loss of horizontal-tail effectiveness when the
tail enters the wing or fuselage wake at high angle of attack through a
tail blanking factor, adds a separated-flow wing-body pitch-up that
rises after the stall and fades at very high angle of attack, solves
for the post-stall trim point in the deep-stall band, and compares the
elevator pitch-down moment available at that trim with the pitch-up
moment hump the elevator must overcome to pitch back below the stall.
It pairs with flight-mechanics/stability-control/spin-recovery as the
departure and spinning neighbor and with
flight-mechanics/stability-control/longitudinal-stability as the tail
sizing and static stability neighbor. Deep stall here means the static
pitch trim at high alpha with a wake-blanked tail, not a spin entry;
developed spins and autorotation bands belong to spin-recovery, and
stall and post-stall flight test programs belong to
flight-test-operations stall-characteristics-testing and
high-angle-of-attack-testing. All wake and separation coefficients in
this model are documented typical engineering-model constants, not
standard values.

## Domain quick reference

- Stall angle: alpha_stall = (clmax / a_w) * R2D +
  VISC_STALL_SHIFT_DEG, with a viscous shift of 2.0 deg above the
  linear clmax/a slope.
- Tail blanking factor: 1.0 below the wake angle, linear ramp to
  eta_blank / eta_t0 across the next BLANK_DELTA_DEG = 10 deg, constant
  at eta_blank / eta_t0 above. The factor multiplies eta_t0, so the
  effective tail efficiency is eta = eta_t0 * factor. Setting
  eta_blank equal to eta_t0 gives factor 1.0 everywhere, a tail that is
  never blanked.
- Tail pitch contribution: Cm_t = -v_h * eta * a_t * (1 -
  d_eps_dalpha) * alpha (radians), from the tail volume coefficient
  v_h, tail lift slope a_t and downwash gradient d_eps_dalpha.
- Separated-flow pitch-up: rises linearly at slope sep_contrib over
  SEP_RISE_RAD = 0.6 rad beyond the stall, fades linearly back to zero
  over SEP_FADE_RAD = 0.4 rad, zero outside that band.
- Total moment: Cm = cm0_wb + cm_alpha_wb * alpha + Cm_sep + Cm_t.
  A positive Cm in the deep-stall band means the airplane pitches up
  into the post-stall region; a downward crossing of Cm through zero at
  high alpha is the stable deep-stall trim (alpha lock point).
- Recovery authority: max_down_moment = |cm_delta| * |delta_e_max|,
  compared with the maximum pitch-up moment hump between the stall and
  the locked trim. Positive recovery margin means full down elevator
  can pitch the nose back below the stall.
- FAR 25 and CS 25 frame the stall and controllability context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Gather the configuration: clmax, a_w, cm0_wb, cm_alpha_wb, v_h,
   a_t, eta_t0, eta_blank, alpha_wake_deg, d_eps_dalpha, sep_contrib,
   cm_delta and delta_e_max_deg into the inputs dict.
2. Compute the stall angle with stall_angle_deg(clmax, a_w) and the
   tail blanking factor across alpha with blanking_factor(alpha_deg,
   alpha_wake_deg, eta_blank / eta_t0).
3. Build the pitch moment curve with cm_total(alpha_deg, inputs) and
   check its sign at the stall with cm_at_stall(inputs). A negative
   Cm at the stall is the trimmed pre-stall state.
4. Solve for the post-stall trim with find_deep_stall_trim(inputs):
   it scans the band from stall + 5 deg up to hi_deg (default 60 deg)
   and returns the highest-angle Cm zero crossing, the stable
   high-alpha trim where the fading separated-flow pitch-up lets Cm
   fall back below zero. None means Cm never crosses in the band, so
   the tail keeps authority and no deep-stall trim exists.
5. Measure the lock with lock_depth_deg(alpha_lock_deg,
   alpha_stall_deg) and the blanking at the trim from
   blanking_factor at the lock angle.
6. Compute recovery_margin(inputs, alpha_lock_deg): the elevator
   pitch-down moment available over the pitch-up hump between the
   stall and the locked trim. Infinite when no lock exists.
7. Run analyze(inputs) for the verdict dict: deep_stall True when a
   post-stall trim sits at least 3 deg above the stall; alpha_lock
   True when the elevator cannot overcome the hump (negative
   recovery margin).
8. Confirm the deterministic checks with the contract test
   scripts/test_deep_stall_analysis.py.

## Worked example

T-tail transport-like airplane: clmax 1.5, a_w 5.7, cm0_wb 0.02,
cm_alpha_wb -0.6, v_h 0.9, a_t 4.2, eta_t0 0.9, eta_blank 0.25,
alpha_wake_deg 20.0, d_eps_dalpha 0.35, sep_contrib 3.0,
cm_delta -1.1, delta_e_max_deg -25.0.

- Stall angle: 1.5 / 5.7 * 57.29578 + 2.0 = 17.08 deg (module value
  17.077837).
- Blanking factor: 1.0 at 20 deg, 0.63889 at 25 deg, 0.27778 at 30 deg
  and above (eta 0.25, tail almost fully in the wake).
- At 45 deg (0.7854 rad): the tail is fully blanked so Cm_t =
  -0.9 * 0.25 * 4.2 * 0.65 * 0.7854 = -0.482; the separated-flow
  pitch-up, x = 0.4873 rad past the stall, adds 3.0 * 0.4873 = 1.462;
  wing-body Cm = 0.02 - 0.471 = -0.451. Total Cm = +0.528, positive,
  the pitch-up deep-stall band.
- find_deep_stall_trim returns 58.77 deg, in the [55, 60] deg band,
  deterministically (two calls agree to 1e-9). Lock depth 58.77 -
  17.08 = 41.69 deg.
- Recovery: max down moment = 1.1 * 25 * 0.0174533 = 0.480. The
  pitch-up hump peak between stall and lock is about 0.729, so the
  recovery margin is 0.480 - 0.729 = -0.249, negative. analyze
  verdict: "deep-stall alpha lock, elevator insufficient", with
  cm_at_stall -0.818 (pre-stall trim is stable) and blanking factor
  0.27778 at the lock.
- With the same airplane at eta_blank 0.9 (tail never blanked, blank
  ratio 1.0) the tail keeps authority, Cm stays negative at high
  alpha, find_deep_stall_trim returns None and the verdict is
  "no deep-stall trim" with recovery margin infinite.
- With cm_delta -1.6 and delta_e_max_deg -30.0 the down moment rises
  to 0.838, the margin turns positive (+0.109) and the verdict becomes
  "deep-stall trim, elevator recovers".

## Verification

- stall_angle_deg(1.5, 5.7) returns 17.077837 deg, within 1e-6 of the
  module contract value.
- blanking_factor(25.0, 20.0, 0.25 / 0.9) returns 0.638889 and
  blanking_factor(35.0, 20.0, 0.25 / 0.9) returns 0.277778.
- separation_pitch_up at 45 deg returns 1.4620 (rise branch);
  peak 1.8 at 0.6 rad past the stall; 0.9 at 0.8 rad; zero at and
  beyond 1.0 rad and below the stall.
- cm_total(45.0, inputs) returns +0.5283, positive in the deep-stall
  band; cm_at_stall(inputs) is -0.818, negative.
- find_deep_stall_trim returns 58.7701 deg deterministically; the
  eta_blank 0.9 sanity case returns None.
- analyze reports deep_stall True, alpha_lock True, lock depth 41.69
  deg and the alpha-lock verdict for the worked example.
- ValueError rejection: clmax <= 0, a_w <= 0, v_h <= 0, eta_t0 <= 0 or
  > 1, eta_blank < 0 or > eta_t0, alpha_wake_deg <= 0, d_eps_dalpha
  outside [0, 1], sep_contrib <= 0, cm_delta >= 0, delta_e_max_deg
  >= 0 and cm_alpha_wb >= 0 all raise ValueError.
- Run the contract test offline: python3
  scripts/test_deep_stall_analysis.py (35 tests, deterministic).

## Related leaves

- flight-mechanics/stability-control/spin-recovery: the departure and
  spinning regime neighbor; developed spin modes and spin recovery
  control inputs are its claim, not this leaf.
- flight-mechanics/stability-control/longitudinal-stability: neutral
  point and static margin for the low-alpha stability context and the
  tail volume basis.
- flight-mechanics/stability-control/dynamic-stability: the short
  period and phugoid modes around the trimmed states.
- flight-test-operations/envelope/stall-characteristics-testing: the
  flight test program for stall characteristics, the testing boundary
  for this analysis.
- flight-test-operations/envelope/high-angle-of-attack-testing: the
  flight test program for the post-stall regime this model assesses.
- vehicle-design/sizing/tail-sizing: sizing the horizontal tail that
  sets v_h and the tail authority used here.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_deep_stall_analysis.py

The test covers the stall angle value and scaling, the blanking factor
ramp points, the separation pitch-up branches (rise, peak, fade,
zero), the positive Cm deep-stall band at 45 deg, the negative Cm at
the stall, the bisection root value in [55, 60] deg with
determinism, the no-root sanity case, lock depth, recovery margins
(negative, infinite, positive), the analyze verdict strings, the full
output dict, and ValueError rejection of every non-physical input in
the validation list.

## Compliance

- Standards referenced, not reproduced: FAR 25 and CS 25 frame the
  stall and controllability context (25.103 stall, 25.143
  controllability and 25.145 longitudinal control context,
  summary-only per standards-map.yaml). The wake blanking and
  separated-flow coefficients in this model are documented typical
  engineering-model constants, not values taken from the standards.
- compliance: STANDARDS-REF, gated: false.
