# Wave-27 leaf spec: shock-response-spectrum (structures, loads pack)

- Path: skills/structures/loads/shock-response-spectrum/
- Pack: loads (existing siblings: gust-maneuver-loads,
  random-vibration-analysis)
- Standards ids: far-25  (Ledger Standard: far-25)
- Family: structures

## Claim

Compute the shock response spectrum (SRS) of a transient base
acceleration time history: for a grid of single-degree-of-freedom
oscillator natural frequencies at a given damping, integrate each
oscillator's response to the base acceleration (half-sine and decaying
transient support), take the peak absolute response acceleration of
each oscillator, and return the SRS as a frequency-to-peak-response
table plus the peak and the amplifying frequency. Produces the SRS
curve points, the maximum response, and the frequency of the maximum
that gate shock qualification assessment of equipment.

Does NOT do: compute the steady-state random vibration response to a
power spectral density with the Miles equation (random-vibration-
analysis owns the PSD/Miles regime); size gust or maneuver loads
(gust-maneuver-loads); or plan DO-160 vibration test conditions
(avionics do160 environmental-qualification). This leaf is the
transient shock regime only.

## Model (implement exactly)

Module constants:
- Q_DEFAULT = 10.0 (quality factor; zeta = 1/(2Q)),
- G = 9.80665.

SDOF oscillator equation (relative displacement x of a base-excited
oscillator): x_ddot + 2*zeta*wn*x_dot + wn^2*x = -a_base(t).
Peak pseudo acceleration = wn^2 * max|x(t)|.

Integration: fixed-step RK4 with dt = min(1/(fn*50), pulse_duration/
200) per oscillator, integrated over the pulse plus 5 natural periods
after the pulse ends. Time histories supported:
- half-sine: a(t) = A*sin(pi*t/T) for 0<=t<=T else 0.
- decaying sine: a(t) = A*sin(2*pi*fd*t)*exp(-t/tau) for t>=0.

Inputs:
- base_accel_type (str, "half-sine" or "decaying-sine"),
- amplitude_ms2 (float, A),
- pulse_duration_s (float, T for half-sine; also used as the period
  reference for decaying-sine frequency fd = 1/T),
- decay_tau_s (float, for decaying-sine, default 3*T),
- natural_freqs_hz (list of float, the SRS frequency grid),
- q (float, default Q_DEFAULT).

Functions:
- base_accel(t, type, A, T, fd, tau) -> float.
- sdof_peak(wn, zeta, base_accel_fn, total_time, dt) -> float:
  peak pseudo acceleration (wn^2 * max|x|). RK4 integration.
- srs_curve(...) -> list of dict {freq_hz, peak_ms2, peak_g}.
- max_response(curve) -> dict {freq_hz, peak_ms2, peak_g}.

ValueError on: amplitude < 0, pulse_duration <= 0, q <= 0.5,
empty frequency list, any natural freq <= 0.

## Worked example

Half-sine pulse, amplitude 10 g (98.0665 m/s2), duration 10 ms, Q 10.
SRS grid [5, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 500,
1000] Hz. Expected behavior (from the reference integration):
- At 5 Hz the oscillator is slow relative to the pulse: peak ~0.31 g
  (assert the module value within 0.05 g of the anchor 0.31 g; the
  exact RK4 value depends on dt, so assert the module's own value
  deterministically and within 10% of the anchor).
- The maximum response occurs near 80 Hz and is ~16.5 g (assert the
  max-response frequency is in [60, 100] Hz and the module's peak is
  within 10% of the anchor 16.5 g; record the exact module values in
  the test header).
- At 1000 Hz the oscillator follows the base: peak ~10.1 g (assert
  within 10% of 10.1 g), i.e. the high-frequency asymptote approaches
  the input amplitude.
- Monotonic shape checks: peak at 20 Hz < peak at 80 Hz; peak at 500
  Hz < peak at 80 Hz. Assert.
Decaying-sine case: A 10 g, T 10 ms, tau 30 ms: assert the peak
response is finite and the maximum occurs at a frequency near 1/T =
100 Hz (assert the max-response frequency is within [70, 130] Hz;
record exact values in the test header).
ValueErrors: amplitude 0, pulse 0, q 0.2, empty grid.
Keep at least 16 test methods. All integration is deterministic with
fixed dt (no RNG).

## Corpus tasks (ids w27-shock-response-spectrum-1/2)

Distinctive tokens: shock response spectrum, SRS, transient shock
response, half sine pulse, base acceleration, pseudo acceleration,
oscillator peak response, shock qualification, amplified frequency.
Avoid: PSD, Miles equation, g-rms, random vibration
(random-vibration-analysis); gust load factor (gust-maneuver-loads);
DO-160 vibration test matrix (do160 environmental-qualification).

1. "compute the shock response spectrum of the 10 g 10 ms half sine
   base acceleration pulse at Q 10 and find the frequency of maximum
   response for the equipment qualification"
2. "build the SRS curve for the decaying sine shock transient and
   report the peak pseudo acceleration in g at the 100 Hz oscillator"

## SKILL body notes

Pair with random-vibration-analysis (steady-state counterpart; the two
leaves together cover the shock and vibration regimes) and gust-
maneuver-loads (loads pack context). The RK4 SDOF integration and
half-sine/decaying-sine support are documented; real test specs use
measured time histories and are handled by the same integration path
if extended. FAR/CS 25 referenced (equipment and structure dynamic
loads context) not reproduced.
