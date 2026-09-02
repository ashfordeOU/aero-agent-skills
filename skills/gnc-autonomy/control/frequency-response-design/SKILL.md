---
name: frequency-response-design
description: "Compute the Bode frequency response of an open loop transfer function for flight control design: evaluate the magnitude and phase at a frequency from the numerator and denominator coefficients at s = j*w, find the gain crossover and phase crossover frequencies, derive the gain margin in dB and the phase margin in degrees, and judge closed loop stability from the margins for the canonical type-1 plant K/(s(s+1)(s+2)). Produces the margins and the stability verdict that gate control law iteration. Use when the task is bode analysis, frequency response, gain crossover, phase crossover, gain margin, phase margin, or stability from the margins. Trigger: bode plot, frequency response, gain margin, phase margin, gain crossover, phase crossover."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [frequency-response, bode-analysis, gain-margin, phase-margin, gain-crossover-frequency, phase-crossover-frequency, crossover-frequency, stability-margins]
  version: 0.1.0
  author: Aero Agent Skills
---

# Frequency Response Design (gnc-autonomy/control/frequency-response-design)

Use when the task is Bode frequency response analysis of an open
loop transfer function for flight control design: magnitude and
phase at a frequency, gain crossover and phase crossover
frequencies, gain margin and phase margin, and the closed loop
stability verdict from the margins.

## Domain quick reference

For the canonical type-1 plant G(s) = K/(s(s+1)(s+2)), represented
as numerator num = [K] and denominator den = [1, 3, 2, 0] in
descending powers of s, evaluated on the imaginary axis s = j*w:

- Magnitude: |G(j*w)| = K / (w * sqrt(w^2 + 1) * sqrt(w^2 + 4)).
- Unwrapped phase: arg G(j*w) = -90 deg - atan(w) - atan(w/2).
- Worked anchor, K = 2 at w = 1 rad/s: |G| = 2/sqrt(10) ~= 0.6325
  (-3.98 dB) and phase = -161.57 deg.
- Phase crossover w_pc: unwrapped phase reaches -180 deg, so
  atan(w) + atan(w/2) = 90 deg, giving w^2/2 = 1 and
  w_pc = sqrt(2) ~= 1.4142 rad/s. At that frequency |G| = K/6.
- Gain margin = 1/|G(j*w_pc)| = 6/K. Worked anchors: K = 2 gives
  3.0 (9.54 dB); K = 6 gives 1.0 (0 dB); K = 8 gives 0.75
  (-2.50 dB).
- Gain crossover w_gc: |G(j*w_gc)| = 1, so w^2(w^2+1)(w^2+4) = K^2.
  Worked anchor K = 2: w_gc ~= 0.7493 rad/s.
- Phase margin = 180 deg + phase(w_gc). Worked anchors: K = 2 gives
  ~32.61 deg; K = 6 gives 0 deg; K = 8 gives ~-7.5 deg.
- Stability verdict: stable iff gain margin > 0 dB AND phase margin
  > 0 deg. K = 2 stable, K = 6 marginal (0 dB, 0 deg), K = 8
  unstable (negative gain margin).
- Units: omega in rad/s, magnitude linear or dB (20*log10), phase
  and phase margin in degrees, gain margin linear or dB.

## Workflow

1. Write the open loop transfer function as numerator and
   denominator coefficient lists in descending powers of s, e.g.
   G(s) = K/(s(s+1)(s+2)) as num = [K], den = [1, 3, 2, 0].
2. Evaluate magnitude and phase at the frequency of interest with
   frequency_response(num, den, omega), or magnitude_db and
   phase_deg directly.
3. Find the 0 dB crossing with gain_crossover_frequency(num, den).
4. Find the -180 deg crossing with phase_crossover_frequency(num,
   den); with no crossing the result is infinite.
5. Compute margins(num, den) to get the gain margin in dB and the
   phase margin in degrees plus their pass flags.
6. Read stability_verdict(num, den) and iterate on K until the
   verdict is stable with both margins above zero.

## Pitfalls

- Confusing this leaf with root-locus-design: root locus traces
  closed loop pole motion as gain varies; Bode analysis works on
  the open loop frequency response s = j*w and judges stability
  from the margins, never from pole coordinates.
- Confusing this leaf with lead-lag-compensation: the compensator
  leaf sizes lead/lag networks to boost a deficient phase margin;
  this leaf only measures the margins of the given open loop
  transfer function and does not synthesize compensators.
- Confusing this leaf with pid-control-design: PID tuning picks
  gains (Ziegler-Nichols, pole placement, anti-windup); this leaf
  reads the margins of whatever open loop transfer function is
  supplied, with no tuning law of its own.
- Confusing this leaf with state-space-analysis: state space works
  with A/B/C matrices, controllability, and eigenvalues; this leaf
  works with polynomial transfer function coefficients and
  frequency response only.
- Reading the gain margin at the gain crossover: GM is
  1/|G(j*w_pc)| evaluated at the phase crossover, while the phase
  margin uses the gain crossover. Swapping the two frequencies
  produces wrong margins.
- Forgetting that atan2 wraps phase into (-180, 180]: the phase
  crossover search needs the unwrapped continuous phase, otherwise
  the -180 deg crossing is invisible on the wrapped plot.
- Applying the margin verdict to non-minimum-phase plants: the
  verdict assumes a minimum-phase open loop with monotonically
  falling phase; otherwise the Nyquist criterion is required.
- Mixing units: omega in rad/s, magnitude in dB with the 20*log10
  convention, and margins in dB and degrees; a linear magnitude
  used inside the dB gain margin formula gives wrong results.

## Behavior contract (gate 3)

The magnitude, phase, crossover, margin, and stability logic is
exercised by the gate 3 contract test:
scripts/test_frequency_response_design.py against
scripts/frequency_response_design_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_frequency_response_design.py

## Compliance

- FAR-25 (14 CFR Part 25) is US government public domain and CS-25
  (EASA) is a free download; both are referenced for the
  airworthiness context of stability margins, name and paraphrase
  only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
