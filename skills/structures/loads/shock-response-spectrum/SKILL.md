---
name: shock-response-spectrum
description: "Use when you must compute the shock response spectrum (SRS) of a transient base acceleration pulse for shock qualification of equipment: single-degree-of-freedom oscillator peak response over a frequency grid at fixed damping, RK4 integration of the oscillator equation x_ddot + 2*zeta*wn*x_dot + wn^2*x = -a_base(t), half-sine pulse A*sin(pi*t/T) and decaying-sine pulse A*sin(2*pi*fd*t)*exp(-t/tau) support, peak pseudo acceleration wn^2 times peak relative displacement, the SRS curve as frequency to peak response in m/s2 and in g, and the maximum response with its amplifying frequency. Produces the SRS curve points, the peak response, and the frequency of the maximum that gate shock qualification assessment of equipment. Trigger: shock response spectrum, SRS, transient shock response, half sine pulse, base acceleration, pseudo acceleration, oscillator peak response, shock qualification, amplified frequency."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: loads
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: loads
  tags: [shock-response-spectrum, half-sine-pulse, decaying-sine-transient, base-acceleration, pseudo-acceleration, transient-shock-response, shock-qualification, amplified-frequency]
  version: 0.1.0
  author: Aero Agent Skills
---

# Shock Response Spectrum (structures/loads/shock-response-spectrum)

Use when the task is computing the shock response spectrum (SRS) of a
transient base acceleration pulse for equipment shock qualification:
each SDOF oscillator on the frequency grid responds to the pulse at a
fixed damping, the peak pseudo acceleration of every oscillator forms
the spectrum, and the frequency of the maximum response shows which
structural or equipment mode the shock amplifies most. This leaf
implements the standard SRS model in pure Python, stdlib only, with
RK4 time integration of the oscillator equation. It pairs with
structures/loads/random-vibration-analysis, the steady-state counterpart
that covers the random PSD regime of the same SDOF equipment model, and
sits alongside structures/loads/gust-maneuver-loads in the loads pack.
The transient shock regime is this leaf's claim; the DO-160 test
condition planner for equipment lives in avionics/do160/
environmental-qualification and consumes these response levels.

## Domain quick reference

- Quality factor and damping: zeta = 1/(2Q), Q_DEFAULT = 10.0.
- Base-excited SDOF oscillator (relative displacement x, natural
  frequency wn = 2*pi*fn in rad/s):
  x_ddot + 2*zeta*wn*x_dot + wn^2*x = -a_base(t).
- Peak pseudo acceleration: wn^2 * max|x(t)|, the SRS ordinate. For a
  lightly damped oscillator this equals the peak absolute acceleration
  of the oscillator mass within the Q-squared correction.
- Half-sine pulse: a(t) = A*sin(pi*t/T) for 0 <= t < T, else 0.
- Decaying-sine pulse: a(t) = A*sin(2*pi*fd*t)*exp(-t/tau) for t >= 0
  with fd = 1/T and tau default 3*T.
- Integration: fixed-step RK4 from rest with dt = min(1/(fn*50),
  T/200) per oscillator. Each oscillator is integrated over its
  excitation support: the pulse end T for the half-sine, and the time
  the envelope A*exp(-t/tau) first falls below 1% of A (ENVELOPE_FLOOR)
  for the decaying sine. The SRS ordinate is the peak of the forced
  response over that support. The ideal half-sine leaves a residual
  base velocity; the low-frequency free ring after the pulse is an
  artifact of that idealization and is excluded, which keeps the
  classical half-sine SRS shape (see the worked example anchors).
- Output: one dict per grid frequency {freq_hz, peak_ms2, peak_g}; the
  curve maximum carries the amplifying frequency.
- Units: amplitude m/s2 (G = 9.80665), durations s, frequencies Hz,
  ordinates m/s2 and g. SI throughout.
- FAR 25 frames the equipment and structure dynamic loads context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. State the shock input: pulse type (half-sine or decaying-sine),
   amplitude A in m/s2 (or g times 9.80665), pulse duration T in s,
   and the quality factor Q (default 10). For the decaying sine set
   the decay time tau (default 3*T).
2. Choose the SRS frequency grid: the natural frequencies of the
   equipment modes under evaluation, typically a log-spaced band
   around the pulse content, for example [5..1000] Hz for a 10 ms
   pulse.
3. Call srs_curve with the pulse and grid. The module computes
   zeta = 1/(2Q), integrates each oscillator with RK4 at
   dt = min(1/(fn*50), T/200) over the excitation support, and returns
   the curve list of {freq_hz, peak_ms2, peak_g}.
4. Call max_response on the curve for the peak pseudo acceleration and
   its amplifying frequency, the shock qualification driver.
5. Read individual ordinates off the curve: the low-frequency branch
   (oscillators slow relative to the pulse) rises from near zero, the
   amplification peak sits where the pulse spectrum meets the
   resonance, and the high-frequency branch approaches the input
   amplitude as the oscillator follows the base.
6. Confirm the deterministic checks with the contract test
   scripts/test_shock_response_spectrum.py.

## Worked example

Half-sine pulse, amplitude 10 g (98.0665 m/s2), duration 10 ms, Q 10,
grid [5, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 500, 1000] Hz:

- At 5 Hz the oscillator is slow relative to the pulse: 0.309 g,
  consistent with the anchor 0.31 g.
- The curve maximum sits at 80 Hz with 16.462 g, consistent with the
  anchor 16.5 g near 80 Hz.
- At 1000 Hz the oscillator follows the base: 10.111 g, consistent
  with the anchor 10.1 g high-frequency asymptote.
- Shape: 20 Hz gives 4.367 g and 500 Hz gives 10.427 g, both below the
  80 Hz peak, so the amplification band is monotone up to and down
  from the maximum.

Intermediate half-sine ordinates (g): 10 Hz 1.202, 30 Hz 8.459, 40 Hz
12.222, 50 Hz 14.557, 60 Hz 15.678, 100 Hz 16.201, 150 Hz 14.192,
200 Hz 12.110, 300 Hz 11.009.

Decaying-sine case, amplitude 10 g, T 10 ms, tau 30 ms, Q 10: the
pulse content sits at fd = 1/T = 100 Hz and the curve maximum is
35.780 g at exactly 100 Hz, the resonance of the decaying transient.

## Verification

- Confirm the half-sine worked example values above: 0.309 g at 5 Hz
  (within 10% and within 0.05 g of the 0.31 g anchor), maximum at
  80 Hz at 16.462 g (frequency in [60, 100] Hz, peak within 10% of the
  16.5 g anchor), 10.111 g at 1000 Hz (within 10% of the 10.1 g
  anchor), and the monotonic checks peak(20 Hz) < peak(80 Hz) and
  peak(500 Hz) < peak(80 Hz).
- Confirm the decaying-sine maximum is finite and sits at 100 Hz,
  inside [70, 130] Hz.
- Confirm srs_curve output is deterministic: repeated calls return
  identical curves (no RNG anywhere).
- Confirm ValueError rejection: amplitude <= 0, pulse duration <= 0,
  quality factor q <= 0.5, empty frequency grid, any natural frequency
  <= 0, unknown pulse type, non-positive decay tau for the decaying
  sine, and non-positive wn, out-of-range zeta, non-positive total
  time or time step in sdof_peak.
- Run the contract test offline: python3
  scripts/test_shock_response_spectrum.py (32 tests, deterministic).

## Related leaves

- structures/loads/random-vibration-analysis: the steady-state
  counterpart for the random regime of the same SDOF equipment
  response model; together the two leaves cover the shock and
  vibration qualification regimes.
- structures/loads/gust-maneuver-loads: the loads pack context for
  airframe limit loads from discrete gust and maneuver conditions.
- avionics/do160/environmental-qualification: test condition planning
  for equipment environmental qualification, the consumer of these
  response levels.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_shock_response_spectrum.py

The test covers the analytic base acceleration histories (half-sine
support and decaying-sine envelope), the half-sine worked example
anchors (5 Hz 0.31 g, maximum near 80 Hz at 16.5 g, 1000 Hz 10.1 g,
monotonic shape), the exact deterministic module values, the decaying-
sine maximum near 1/T with its finite resonant peak, determinism of
repeated runs, the g to m/s2 unit consistency of the curve dicts, the
direct sdof_peak round trip, the effect of damping on the resonant
peak, and ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25 frames the dynamic
  loads and equipment context; the SDOF response relations above are
  standard engineering methodology, summary-only per standards-map.yaml
  (far-25 reference-only).
- compliance: STANDARDS-REF, gated: false.
