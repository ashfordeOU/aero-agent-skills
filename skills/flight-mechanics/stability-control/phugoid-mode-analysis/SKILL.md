---
name: phugoid-mode-analysis
description: "Use when you must analyze the phugoid, the long-period longitudinal mode of an aircraft, with the Lanchester approximation from the cruise speed and the lift-to-drag ratio alone: compute the phugoid natural frequency omega_p = g0 * sqrt(2) / V and period, the drag-damping ratio zeta_p = 1 / (sqrt(2) * (L/D)), the damped frequency, the time to half amplitude, and the cycles to half amplitude of the airspeed oscillation, and check the small-damping validity floor of L/D 8. Produces the phugoid mode metrics and the height-velocity energy-exchange verdict. Trigger: phugoid, long-period mode, Lanchester, airspeed oscillation, time to half amplitude, height-velocity exchange, phugoid period, phugoid damping."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: stability-control
  tags: [phugoid-mode-analysis, lanchester-approximation, long-period-mode, airspeed-oscillation, time-to-half-amplitude, height-velocity-exchange, phugoid-damping, drag-damping]
  version: 0.1.0
  author: Aero Agent Skills
---

# Phugoid Mode Analysis (flight-mechanics/stability-control/phugoid-mode-analysis)

Use when the task is the phugoid, the long-period longitudinal mode
that shows up after a speed or thrust disturbance at cruise: the
aircraft slowly oscillates in airspeed and height while the angle of
attack stays nearly constant. This leaf implements the Lanchester
approximation, which needs only the cruise speed V and the
lift-to-drag ratio L/D, and derives the phugoid natural frequency,
period, drag-damping ratio, damped frequency, and the time to half
amplitude in seconds and in cycles. It complements the fast-mode
treatment of
flight-mechanics/stability-control/short-period-mode-analysis, the
derivative-based full evaluation of
flight-mechanics/stability-control/dynamic-stability, and the static
pitch stability background of
flight-mechanics/stability-control/longitudinal-stability.

## Domain quick reference

Physics: the phugoid trades kinetic and potential energy along the
flight path at roughly constant angle of attack. After a speed
disturbance the airplane climbs as it slows, then dives and
accelerates back, so the disturbance shows up as a slow airspeed and
height-velocity exchange (height up when speed down) rather than as a
pitch oscillation. Lanchester modeled this exchange for small
perturbations at constant cruise speed V and constant lift
coefficient; drag does work each cycle and provides the damping. With
g0 = 9.80665 m/s^2:

- Natural frequency: omega_p = g0 * sqrt(2) / V, in rad/s.
- Period: T_p = 2 * pi / omega_p = 2 * pi * V / (g0 * sqrt(2)), in s.
- Damping ratio (drag-damping approximation): zeta_p =
  1 / (sqrt(2) * (L/D)), dimensionless. Valid for large L/D; the
  model assumes zeta_p is small (zeta_p at L/D 8 is about 0.088).
- Damped frequency: omega_d = omega_p * sqrt(1 - zeta_p^2), in rad/s.
  For cruise L/D the damping is light, so omega_d is practically
  equal to omega_p.
- Time to half amplitude: t_half = ln(2) / (zeta_p * omega_p), in s.
  The decay-rate identity zeta_p * omega_p = g0 / (V * (L/D)) gives
  the closed form t_half = ln(2) * V * (L/D) / g0.
- Cycles to half amplitude: N_half = t_half / T_p =
  ln(2) * sqrt(2) * (L/D) / (2 * pi), about 0.156 * (L/D).
  Independent of speed: only the lift-to-drag ratio sets how many
  cycles the oscillation survives.
- Validity: L/D must be at least 8 for the small-damping
  approximation to be credible; omega_p is assumed to sit well below
  the short period frequency (the standard two-timescale longitudinal
  split, stated as an assumption because this leaf does not compute
  the short period mode).

## Workflow

1. Collect the cruise speed V in m/s and the cruise lift-to-drag
   ratio L/D at the trim condition (from
   flight-mechanics/stability-control/trim-analysis or cruise
   performance data).
2. Compute the natural frequency with phugoid_frequency and the
   period with phugoid_period.
3. Compute the drag-damping ratio with phugoid_damping_ratio and the
   damped frequency with damped_frequency.
4. Get the decay metrics: time_to_half_amplitude and
   cycles_to_half_amplitude.
5. Check validity with ld_valid_for_small_damping (L/D 8 floor) and
   record the separation assumption that omega_p is well below the
   short period frequency.
6. Get the complete summary with phugoid_characteristics, which
   returns omega_p, period, zeta_p, omega_d, t_half, cycles_half,
   small_damping_valid, and the separation_assumption string.
7. Confirm the deterministic checks with the contract test
   scripts/test_phugoid_mode_analysis.py.

## Worked example

A transport cruise configuration: V = 250 m/s, L/D = 18.

- omega_p = 9.80665 * 1.41421356237 / 250 = 0.05547 rad/s.
- T_p = 2 * pi / 0.05547 = 113.3 s.
- zeta_p = 1 / (1.41421356237 * 18) = 0.03928.
- Decay rate: zeta_p * omega_p = 0.03928 * 0.05547 = 0.002179 /s,
  equal to g0 / (250 * 18) = 0.002179 /s.
- t_half = ln(2) / 0.002179 = 318.1 s.
- Cycles to half amplitude: N_half = 318.1 / 113.3 = 2.81.
- Validity: L/D = 18 is well above 8, and omega_p = 0.0555 rad/s is
  about two orders below a typical short period frequency of several
  rad/s, so the Lanchester model and the mode separation hold.

The interpretation: after a speed disturbance the airspeed oscillation
decays to half amplitude in about 5.3 minutes (2.81 cycles of a
roughly 1.9 minute period). Damping is light because the L/D of 18
means drag does little work per cycle.

## Verification

- Confirm phugoid_frequency(250.0) returns 0.0554748 rad/s and
  phugoid_period(250.0) returns 113.2620 s, both within 1% of the
  worked example values.
- Confirm phugoid_damping_ratio(18.0) returns 0.0392837, t_half via
  time_to_half_amplitude(250.0, 18.0) returns 318.0660 s (within 1%
  of 318.1 s), and cycles_to_half_amplitude(18.0) returns 2.8082
  (within 1% of 2.81).
- Confirm the identities: phugoid_frequency * phugoid_period equals
  2 * pi; zeta_p * omega_p equals g0 / (V * (L/D)); the closed form
  ln(2) * V * (L/D) / g0 equals the log form ln(2) / (zeta_p *
  omega_p); cycles_half equals t_half / T_p; and omega_d is at or
  below omega_p.
- Confirm ld_valid_for_small_damping returns True at and above L/D 8
  and False below.
- Confirm ValueError on V <= 0, L/D < 1 (below the oscillatory
  floor), non-numeric inputs, and non-positive gravity, across the
  frequency, damping, time, and summary functions.
- Run the contract test offline: python3
  scripts/test_phugoid_mode_analysis.py (34 tests, deterministic).

## Related leaves

- flight-mechanics/stability-control/longitudinal-stability: the
  static pitch stability context (C_m_alpha, neutral point) in which
  the phugoid operates.
- flight-mechanics/stability-control/short-period-mode-analysis: the
  fast pitch mode of the same longitudinal split; its separation
  check uses the Lanchester frequency from this leaf's model.
- flight-mechanics/stability-control/dynamic-stability: the full
  longitudinal mode evaluation from stability derivatives, where the
  phugoid frequency and damping are assessed against the
  non-divergent criterion.
- flight-mechanics/stability-control/trim-analysis: the trimmed
  cruise condition that fixes the speed and lift-to-drag inputs.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_phugoid_mode_analysis.py

The test covers the worked-example anchors (natural frequency 0.05547
rad/s, period 113.3 s, damping 0.03928, time to half 318.1 s, cycles
to half 2.81, all within 1%), the frequency and period round trip,
the speed scaling of frequency and period, the L/D 1 oscillatory
boundary, the decay-rate identity zeta_p * omega_p = g0 / (V * (L/D)),
the closed-form time to half, the cycles-to-period ratio, the L/D 8
validity floor, the summary dict consistency, and ValueError rejection
of non-positive and non-numeric inputs.

## Compliance

- Standards referenced, not reproduced: FAR-25.181 and CS-25.181
  require longitudinal dynamic stability characteristics for
  transport aeroplanes, with the phugoid to be non-divergent and not
  to increase pilot workload; the Lanchester model above is classical
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
