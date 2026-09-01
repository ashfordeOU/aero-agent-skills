---
name: pilot-induced-oscillation
description: "Use when you must assess pilot-induced oscillation (PIO) susceptibility and pilot-in-the-loop coupling for a piloted aircraft: categorize the oscillation into Category I (linear aircraft response), Category II (quasi-linear response with rate-limited actuators), or Category III (nonlinear response with mode transitions or control logic changes), identify the typical causes: excessive phase lag, high control sensitivity, actuator rate limiting, structural notch filters, run a phase-lag-at-crossover risk check that returns a low, medium, or high band with the equivalent time delay and phase margin, and select suppression measures such as phase compensation, gain reduction, notch filter retuning, and control logic changes. Supports flight test detection of divergent oscillation. Framed by FAR-25 and CS-25 flight characteristics requirements. Trigger: pilot-induced-oscillation, pio, phase lag, crossover frequency, equivalent time delay, actuator rate limiting, pilot-in-the-loop coupling, pio suppression."
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
  subdomain: handling-qualities
  tags: [pilot-induced-oscillation, pio, pio-categories, phase-lag, crossover-frequency, equivalent-time-delay, actuator-rate-limiting, bandwidth, notch-filter, pilot-in-the-loop-coupling, suppression-measures, flight-test-detection]
  version: 0.1.0
  author: AeroSkills
---

# Pilot-Induced Oscillation (flight-mechanics/handling-qualities/pilot-induced-oscillation)

Use when the task is pilot-induced oscillation (PIO) analysis: the
category of the oscillation, the phase-lag-at-crossover risk band, the
suppression measures, and the flight test detection of the closed-loop
phenomenon.

## Domain quick reference

- A pilot-induced oscillation is an unintentional, sustained
  oscillation of the aircraft that develops from the close coupling
  between the pilot's control inputs and the aircraft response: the
  pilot's corrective inputs add energy to the oscillation instead of
  damping it. It is a pilot-vehicle system phenomenon, not an aircraft
  instability alone.
- Category I (linear aircraft response): the aircraft responds
  essentially linearly; the oscillation develops because the
  pilot-vehicle loop (pilot gain and lag plus aircraft and actuation
  lags) is unstable. Classic triggers: a high gain task with excessive
  phase lag.
- Category II (quasi-linear response, rate-limited actuators): the
  actuator or control surface rate limit saturates during the
  oscillation, so the rate-limited element reduces effective gain and
  adds phase lag. Describing-function methods are needed and the
  oscillation often appears at a frequency different from the linear
  prediction.
- Category III (nonlinear response): the response is dominated by
  transitions, such as control law mode switching, surface saturation,
  or reversion to alternate modes during the task.
- Typical causes: excessive phase lag (equivalent time delay) in the
  pilot-vehicle loop, including pilot reaction delay, digital flight
  control transport delay, actuator lag, and sensor and filter lag;
  high control sensitivity that keeps the loop gain high and shrinks
  the phase margin; actuator rate limiting under large rapid commands;
  and structural notch filters that add phase lag in the piloted
  frequency band.
- Phase-lag-at-crossover risk check: the crossover frequency is the
  frequency where the open-loop pilot-vehicle gain passes through
  unity. The phase lag there gives the phase margin,
  margin = 180 + phase_lag for the negative lag, and the equivalent
  time delay tau_e = |phase_lag| / (360 * f_crossover). Bandwidth-style
  bands: tau_e below 0.10 s is low risk, 0.10-0.20 s is medium, above
  0.20 s is high. Worked: phase_lag_risk(-30.0, 2.0) returns the low
  band with a 150 degree margin and a 0.0417 s delay; (-100.0, 1.0)
  returns high with a 0.2778 s delay.
- Suppression measures: reduce the loop gain and add phase lead
  compensation to recover phase margin; reduce the equivalent time
  delay (faster actuators, less transport delay); increase the actuator
  rate limit or add command-rate shaping; retune or relocate the
  structural notch filter; and add control logic that prevents mode
  switching or reversion during the critical task.
- Flight test detection: closed-loop test techniques track a defined
  task (for example a discrete attitude capture) and watch for an
  oscillatory response that grows after the input stops, with the
  oscillation frequency well below the short period; open-loop
  frequency sweeps measure the phase lag at crossover directly; pilot
  comments such as "the aircraft got ahead of me" are a classic
  symptom.

## Workflow

1. Collect the loop data: the crossover frequency and the phase lag at
   crossover of the open-loop pilot-vehicle response, from a frequency
   sweep or from the equivalent time delay estimate.
2. Categorize the oscillation with categorize_pio(rate_limiting,
   nonlinear): both false gives Category I, rate limiting alone gives
   Category II, and any nonlinear response gives Category III.
3. Run the risk check with phase_lag_risk(phase_lag_deg,
   crossover_freq_hz), which returns the band, the phase margin, and
   the equivalent time delay; confirm the margin with phase_margin and
   the delay with equivalent_time_delay.
4. Interpret the band: low needs no action, medium warrants mitigation
   before further flight test, high demands suppression before the task
   is cleared.
5. Select the suppression measures with suppression_measures(...)
   against the causes present (rate limiting, high sensitivity,
   structural filters, nonlinear response) and the risk band.
6. Plan the flight test detection: a closed-loop task with defined
   tolerances, monitoring for divergent oscillation after the input
   stops, plus an open-loop sweep to confirm the phase lag at
   crossover.

## Pitfalls

- Routing mode analysis here: short period damping, natural frequency,
  and eigenvalue classification belong to dynamic-stability; the PIO
  analysis works on the pilot-vehicle loop, not on the bare aircraft
  modes.
- Routing control power here: actuator sizing, authority margins, and
  hinge moments belong to control-surface-effectiveness; rate limiting
  matters here only as a PIO cause, not as an actuator sizing number.
- Routing pilot ratings here: assigning a Cooper-Harper rating to the
  task belongs to cooper-harper-rating; a low rating may accompany a
  PIO but the rating is not the oscillation analysis.
- Routing flight control system analysis here: gain and phase margin of
  the autopilot or flight control loop without the pilot belong to the
  gnc-autonomy control leaves; the pilot must be in the loop for a
  pilot-induced oscillation.
- Treating a divergent aircraft mode as a PIO: flutter or a divergent
  eigenmode grows without pilot input; a PIO requires the pilot's
  corrective inputs in the loop.
- Confusing the categories: Category II is specifically the
  quasi-linear case where rate limiting is the dominant nonlinearity
  and describing-function methods apply; a linear response is Category
  I even when the pilot oscillates.
- Sign errors in the risk check: the phase lag is negative degrees, the
  margin is 180 plus the lag, and the equivalent time delay uses the
  magnitude of the lag; a flipped sign turns a high risk band into a
  low one.
- Using the wrong crossover: the risk check needs the pilot-vehicle
  loop crossover frequency, not the flight control system crossover or
  a structural mode frequency.
- Confusing equivalent time delay with measured transport delay: tau_e
  is derived from the phase lag at one frequency and lumps all lag
  sources; the measured transport delay is one contributor, not the
  whole result.

## Behavior contract (gate 3)

The PIO categorization, phase-lag risk check, and suppression measure
selection are exercised by the gate 3 contract test:
scripts/test_pilot_induced_oscillation.py against
scripts/pilot_induced_oscillation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_pilot_induced_oscillation.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 flight
  characteristics requirements frame the handling qualities assessment
  for transport aeroplanes; the three-category PIO categorization, the
  equivalent time delay measure, and the suppression measures are
  common flying qualities methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
