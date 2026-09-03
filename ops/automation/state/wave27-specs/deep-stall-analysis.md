# Wave-27 leaf spec: deep-stall-analysis (flight-mechanics, stability-control pack)

- Path: skills/flight-mechanics/stability-control/deep-stall-analysis/
- Pack: stability-control (existing siblings: longitudinal-stability,
  lateral-directional-stability, dynamic-stability, trim-analysis,
  control-surface-effectiveness, aileron-reversal, spin-recovery,
  stability-derivatives-avl, short-period-mode-analysis,
  phugoid-mode-analysis)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-mechanics

## Claim

Assess whether a T-tail or aft-fuselage-mounted-tail airplane can enter
a deep stall (a self-sustaining high-angle-of-attack trim beyond the
stall, sometimes called alpha lock) and whether the elevator retains
enough pitch-down authority to recover. The analysis models the loss of
horizontal-tail effectiveness when the tail enters the wing or fuselage
wake at high angle of attack, adds a separated-flow wing-body pitch-up
that rises after the stall and fades at very high angle of attack,
solves for any secondary trim point in the post-stall range, and
compares the elevator pitch-down moment available at that trim with the
pitch-up moment hump the elevator must overcome to pitch back below the
stall. Produces the stall angle, the blanking factor at the post-stall
trim, the deep-stall trim angle and lock depth (or none), the recovery
margin, and the deep-stall / alpha-lock verdicts.

Does NOT do: analyze developed spins, autorotation bands, spin modes,
or spin recovery control inputs (spin-recovery owns the spinning
flight regime); plan stall-characteristics or post-stall flight tests
(flight-test-operations stall-characteristics-testing and
high-angle-of-attack-testing own the flight test programs); size the
horizontal tail for pitch stability (longitudinal-stability and
vehicle-design tail-sizing); or predict stall buffet onset. Deep stall
here means the static pitch trim at high alpha with wake-blanked tail,
not a spin entry.

## Model (implement exactly)

Module constants (documented typicals, SKILL body labels them typicals):
- VISC_STALL_SHIFT_DEG = 2.0 (viscous stall-angle shift above the
  linear clmax/a slope),
- BLANK_DELTA_DEG = 10.0 (angle range over which tail blanking ramps
  from full to the blanked efficiency),
- SEP_RISE_RAD = 0.6 (angle beyond stall over which the separated-flow
  pitch-up rises linearly to its peak),
- SEP_FADE_RAD = 0.4 (angle range over which it fades back to zero),
- R2D = 57.29578, D2R = 0.0174533.

Inputs (dict or keyword args):
- clmax (float, wing maximum lift coefficient),
- a_w (float, wing lift-curve slope 1/rad),
- cm0_wb (float, wing-body zero-alpha pitching moment coefficient),
- cm_alpha_wb (float, wing-body pitch stiffness 1/rad, low-alpha value,
  normally negative),
- v_h (float, horizontal tail volume coefficient V_H = S_t l_t / (S c)),
- a_t (float, tail lift-curve slope 1/rad, clean),
- eta_t0 (float, tail efficiency factor at low alpha, <= 1.0),
- eta_blank (float, tail efficiency when fully blanked, <= eta_t0),
- alpha_wake_deg (float, angle of attack where blanking begins),
- d_eps_dalpha (float, downwash gradient, 0..1),
- sep_contrib (float, peak separated-flow pitch-up slope 1/rad; the
  worked example uses 3.0),
- cm_delta (float, elevator pitch-moment slope 1/rad, negative),
- delta_e_max_deg (float, maximum down-elevator travel, negative deg).

Functions:
- stall_angle_deg(clmax, a_w) -> float:
  (clmax / a_w) * R2D + VISC_STALL_SHIFT_DEG.
- blanking_factor(alpha_deg, alpha_wake_deg) -> float:
  1.0 for alpha <= wake; ramps linearly from 1.0 to
  (eta_blank / eta_t0) across [wake, wake + BLANK_DELTA_DEG]; constant
  (eta_blank / eta_t0) above. (Returned factor multiplies eta_t0.)
- separation_pitch_up(alpha_r, alpha_stall_r, sep_contrib) -> float:
  x = alpha_r - alpha_stall_r;
  if x <= 0: 0.0;
  elif x <= SEP_RISE_RAD: sep_contrib * x;
  elif x <= SEP_RISE_RAD + SEP_FADE_RAD:
       sep_contrib * SEP_RISE_RAD *
       (1.0 - (x - SEP_RISE_RAD) / SEP_FADE_RAD);
  else: 0.0.
- cm_total(alpha_deg, inputs) -> float:
  alpha_r = alpha_deg * D2R; alpha_stall_r = stall_angle_deg(...) * D2R;
  eta = eta_t0 * blanking_factor(alpha_deg, alpha_wake_deg);
  tail = -v_h * eta * a_t * (1 - d_eps_dalpha) * alpha_r;
  sep = separation_pitch_up(alpha_r, alpha_stall_r, sep_contrib);
  return cm0_wb + cm_alpha_wb * alpha_r + sep + tail.
- find_deep_stall_trim(inputs, lo_deg=None, hi_deg=60.0) -> float or
  None: lo defaults to stall_angle_deg + 5.0. Bisection root of
  cm_total over [lo_deg, hi_deg] to 1e-9 rad; None when cm_total(lo) and
  cm_total(hi) have the same sign (no crossing).
- lock_depth_deg(alpha_lock_deg, alpha_stall_deg) -> float:
  max(0.0, alpha_lock_deg - alpha_stall_deg).
- cm_at_stall(inputs) -> float: cm_total(stall_angle_deg(...), inputs).
- recovery_margin(inputs, alpha_lock_deg) -> float:
  max_down_moment = abs(cm_delta) * abs(delta_e_max_deg * D2R);
  if alpha_lock_deg is None: return inf;
  hump = max(cm_total(a, inputs) for a in
  numpy-free linspace(stall_angle_deg(inputs), alpha_lock_deg, 200));
  required = max(0.0, hump); return max_down_moment - required.
- analyze(inputs) -> dict:
  {alpha_stall_deg, alpha_lock_deg (float or None), lock_depth_deg,
  blanking_at_lock, cm_at_stall, recovery_margin, deep_stall (bool),
  alpha_lock (bool), verdict (str)}.
  deep_stall = alpha_lock_deg is not None and lock_depth_deg >= 3.0.
  alpha_lock = deep_stall and recovery_margin < 0.0.
  verdict: "no deep-stall trim" / "deep-stall trim, elevator recovers"
  / "deep-stall alpha lock, elevator insufficient".
ValueError on: clmax <= 0, a_w <= 0, v_h <= 0, eta_t0 <= 0 or > 1,
eta_blank < 0 or >= eta_t0, alpha_wake_deg <= 0, d_eps_dalpha outside
[0, 1], sep_contrib <= 0, cm_delta >= 0, delta_e_max_deg >= 0,
cm_alpha_wb >= 0.

## Worked example

T-tail transport-like airplane:
clmax 1.5, a_w 5.7, cm0_wb 0.02, cm_alpha_wb -0.6, v_h 0.9, a_t 4.2,
eta_t0 0.9, eta_blank 0.25, alpha_wake_deg 20.0, d_eps_dalpha 0.35,
sep_contrib 3.0, cm_delta -1.1, delta_e_max_deg -25.0.

- stall_angle_deg = 1.5/5.7 * 57.29578 + 2.0 = 17.08 deg (assert the
  module value within 1e-6).
- blanking_factor(20.0) = 1.0; blanking_factor(25.0) = 1 - 0.5*(1 -
  0.25/0.9) = 0.63889; blanking_factor(35.0) = 0.27778. Assert.
- separation_pitch_up at alpha 45 deg (0.7854 rad): x = 0.7854 -
  0.29813 = 0.48727 < 0.6 -> sep = 3.0 * 0.48727 = 1.4618. Assert.
- cm_total at 45 deg: wb = -0.6*0.7854 = -0.4712; tail with full
  blanking eta = 0.25: -0.9*0.25*4.2*0.65*0.7854 = -0.4824; cm0 0.02;
  sep 1.4618 -> Cm = +0.528. Positive (pitch-up) in the deep-stall
  band. Assert sign and magnitude within 1e-3.
- Run your module: find_deep_stall_trim must return a root in [55.0,
  60.0] deg (where the fading separation lets Cm cross back to
  negative, the stable high-alpha trim). Record the exact value in your
  test header and assert the module returns it deterministically (two
  calls identical to 1e-9).
- Assert: deep_stall True, alpha_lock True (recovery_margin < 0: the
  pitch-up hump between the stall and the locked trim exceeds the
  elevator pitch-down authority), cm_at_stall < 0, lock_depth_deg in
  [35.0, 45.0].
- Sanity case: same airplane with eta_blank 0.9 (tail never blanked) ->
  the tail keeps authority, Cm stays negative at high alpha,
  find_deep_stall_trim returns None, deep_stall False, recovery_margin
  inf.
- ValueErrors on clmax 0, v_h 0, eta_blank 0.95 (>= eta_t0 0.9),
  cm_delta +0.5, delta_e_max_deg +10, d_eps_dalpha 1.2, sep_contrib 0.
Keep at least 18 test methods (stall angle, blanking ramp points,
separation bump branches, cm_total sign, bisection root, no-root
branch, margins, verdict strings, ValueErrors).

## Corpus tasks (ids w27-deep-stall-analysis-1/2)

Distinctive tokens: deep stall, T-tail blanking, alpha lock, post-stall
trim, tail blanking factor, separated flow pitch-up, pitch-down
recovery authority. Avoid: spin entry, autorotation, spin recovery,
flat spin (spin-recovery); stall warning, buffet, flight test entry
techniques (flight-test-operations stall-characteristics-testing);
neutral point, static margin (longitudinal-stability).

1. "assess whether the T-tail transport can enter a deep stall: compute
   the tail blanking factor at high angle of attack and solve for any
   post-stall trim above the stall angle with the separated flow pitch
   up"
2. "check the deep stall alpha lock hazard for the aft tail airplane:
   find the post-stall trim angle, the lock depth, and whether the
   elevator pitch down authority can recover from the deep stall"

## SKILL body notes

Pair with spin-recovery (departure and spin neighbor), longitudinal-
stability (tail sizing stability neighbor), and cite
flight-test-operations stall-characteristics-testing and
high-angle-of-attack-testing as the flight-test boundary. All wake and
separation coefficients are documented typical engineering-model
constants, not standard values; the SKILL body must say so. FAR/CS 25
referenced (stall and controllability context), not reproduced.
