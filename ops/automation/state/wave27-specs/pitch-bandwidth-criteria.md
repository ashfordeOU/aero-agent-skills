# Wave-27 leaf spec: pitch-bandwidth-criteria (flight-mechanics, handling-qualities pack)

- Path: skills/flight-mechanics/handling-qualities/pitch-bandwidth-criteria/
- Pack: handling-qualities (existing siblings: mil-std-1797a,
  pilot-induced-oscillation, cooper-harper-rating)
- Standards ids: mil-std-1797a  (Ledger Standard: mil-std-1797a)
- Family: flight-mechanics

## Claim

Assess pitch-axis flying qualities with the MIL-STD-1797A bandwidth and
phase-delay criterion for the pitch attitude response: model the
aircraft pitch attitude transfer function as a short-period mode plus a
control anticipation numerator time constant and an actuator lag,
evaluate the open-loop frequency response, find the bandwidth frequency
omega_BW (the lower of the 45-degree phase-margin frequency and the
6 dB gain-margin frequency) and the -180-degree frequency omega_180,
compute the phase delay tau_p from the phase at twice omega_180, and
grade the result against the representative Category A Level 1/2/3
bandwidth and phase-delay boundaries. Produces omega_BW, omega_180,
tau_p, the Level 1/2/3 verdict, and the limiting criterion.

Does NOT do: grade each dynamic mode from the MIL-STD-1797A modal level
tables (short period damping, Dutch roll, spiral, roll) or return a
Cooper-Harper band (handling-qualities mil-std-1797a); predict PIO
category or phase lag at crossover for pilot-induced oscillation
(handling-qualities pilot-induced-oscillation); or design a feedback
control loop with gain and phase margins (gnc-autonomy
frequency-response-design and python-control-design). This leaf applies
the frequency-domain bandwidth / phase-delay criterion to an airframe
pitch response, a different assessment method from the modal tables.

## Model (implement exactly)

Transfer function (documented approximation; K normalized to 1.0 since
the criterion uses phase and gain-ratio only):
  G(s) = (1 + T_th2 * s) / (s * (s^2 + 2*zeta*wn*s + wn^2) *
  (1 + s / w_act))
with s = j*w, wn the short-period natural frequency (rad/s), zeta the
short-period damping, T_th2 the numerator (control anticipation) time
constant (s), w_act the actuator/airframe lag frequency (rad/s).

Inputs:
- wn (float, rad/s), zeta (float), T_th2 (float, s, > 0),
- w_act (float, rad/s, > wn).

Functions (stdlib only; bisection helper for root finding):
- transfer(wn, zeta, T_th2, w_act, w) -> complex G(jw).
- phase_deg(wn, zeta, T_th2, w_act, w) -> unwrapped phase in degrees
  (start at -90 near 0 and unwrap continuously downward; implement by
  sampling from 0.01 rad/s in fine steps, or by analytic quadrant
  logic: atan2 + branch corrections so phase is monotone decreasing).
  Implementation note: numeric unwrap with step 0.01 rad/s up to
  max(4*w_act, 200) rad/s, interpolating between samples for roots.
- mag_db(wn, zeta, T_th2, w_act, w) -> 20*log10(|G|).
- find_root_phase(wn, zeta, T_th2, w_act, target_deg) -> float:
  bisection on phase_deg - target over a dense unwrapped table
  (sub-bisection between bracketing samples); returns None if the
  target is never reached in the scanned band.
- bandwidth(wn, zeta, T_th2, w_act) -> dict:
  w_135 = find_root_phase(..., -135) (45 deg phase margin),
  w_gm6 = frequency where mag_db crosses -6 dB going downward
  (None if never reached; scan from 0.01 upward),
  omega_BW = min of the two that exist (if only one exists, that one),
  w_180 = find_root_phase(..., -180),
  tau_p = -(phase_deg(2*w_180) + 180) / (2*w_180) * (pi/180) when
  w_180 exists, else None.
- level_verdict(omega_BW, tau_p) -> dict {level (str 'Level 1'/'Level
  2'/'Level 3'), limiting (str 'bandwidth' or 'phase delay' or 'both')}.
  Module constants (representative Category A pitch boundaries,
  documented as representative per MIL-STD-1797A 4.5.1, class-dependent
  in the standard; SKILL body says verify against the current
  revision):
  L1_OMEGA = 3.5 rad/s, L2_OMEGA = 2.5 rad/s,
  L1_TAU = 0.2 s, L2_TAU = 0.2 s.
  omega >= L1_OMEGA and tau <= L1_TAU -> Level 1;
  elif omega >= L2_OMEGA and tau <= L2_TAU -> Level 2; else Level 3.
  If omega_BW or tau_p is None the leaf still returns a verdict from
  the available metric and reports the missing one.

ValueError on: wn <= 0, zeta <= 0 or >= 1, T_th2 <= 0, w_act <= wn.

## Worked example

Case A: wn = 4.0, zeta = 0.7, T_th2 = 0.5, w_act = 25.0.
- w_135 = 4.58 rad/s (assert module value within 0.01),
- w_180 = 10.13 rad/s (within 0.02),
- tau_p = 0.0247 s (within 0.001),
- omega_BW = w_135 (the 6 dB gain-margin crossing is not reached in
  this band; assert w_gm6 is None and omega_BW equals w_135),
- Level 1, limiting 'bandwidth' (omega 4.58 >= 3.5; tau 0.0247 <=
  0.2). Assert verdict.

Case B: wn = 3.0, zeta = 0.6, T_th2 = 0.7, w_act = 20.0.
- w_135 = 3.43 rad/s (within 0.01), w_180 = 7.23 rad/s (within 0.02),
- tau_p = 0.0325 s (within 0.001),
- Level 2 (omega 3.43 < 3.5 but >= 2.5; tau fine). Assert.

Additional tests: zeta = 0.35 case (lightly damped: phase drops faster;
assert w_135 < the zeta 0.7 case at the same wn), low wn = 1.5 case
(Level 3 bandwidth), ValueErrors (wn 0, zeta 1.0, w_act = wn).
Keep at least 16 test methods.

## Corpus tasks (ids w27-pitch-bandwidth-criteria-1/2)

Distinctive tokens: pitch bandwidth criterion, phase delay tau,
bandwidth frequency, phase margin 45 degrees, MIL-STD-1797A bandwidth,
short period transfer function, actuator lag, flying qualities level.
Avoid: cooper-harper band, short period damping table grading by class
(mil-std-1797a), PIO category, crossover phase lag
(pilot-induced-oscillation), gain margin / bode control design
(frequency-response-design).

1. "apply the MIL-STD-1797A pitch bandwidth and phase delay criterion:
   find the bandwidth frequency from the 45 degree phase margin and the
   phase delay from the -180 degree frequency of the short period pitch
   attitude transfer function with actuator lag"
2. "grade the pitch tracking flying qualities with the bandwidth
   criterion for the transport: short period 3 rad/s at 0.6 damping
   with a 0.7 second numerator time constant and 20 rad/s actuator
   lag, report the level and the limiting criterion"

## SKILL body notes

Pair with mil-std-1797a (the modal-table companion criterion; this leaf
implements the frequency-domain bandwidth method, not the tables),
pilot-induced-oscillation (phase-related neighbor), and
short-period-mode-analysis (source of wn/zeta inputs). The level
boundaries are representative Category A values from MIL-STD-1797A
4.5.1 and are class-dependent; the SKILL body must say to verify
against the current revision. Standard referenced, not reproduced.
