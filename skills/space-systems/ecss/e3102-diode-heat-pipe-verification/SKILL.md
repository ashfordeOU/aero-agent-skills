---
name: e3102-diode-heat-pipe-verification
description: "Verify a diode heat pipe against its forward transport, reverse heat-leak and mode-switch requirements under ECSS-E-ST-31-02C clause 5.5.5.2c. Use when the task is reading forward capability off a temperature curve, deriving forward and reverse conductance from measured heat and temperature difference, grading the diodicity ratio the pair produces, bounding the heat a reversed pipe still passes backwards into the cold side, timing how long the pipe takes to settle into reverse mode from a sampled transient, and integrating the energy that leaks through the switch. Trigger: ecss, e-st-31-02c, diode-heat-pipe-forward-transport, reverse-mode-heat-leak, diodicity-ratio, mode-switch-time, mode-switch-energy, reverse-conductance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-31-02-two-phase-scope, e3102-diode-heat-pipe-verification, diode-heat-pipe-forward-transport, reverse-mode-heat-leak, diodicity-ratio, mode-switch-time, mode-switch-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Diode Heat Pipe Verification (space-systems/ecss/e3102-diode-heat-pipe-verification)

Use when the task is the diode heat pipe verification of ECSS-E-ST-31-02C
clause 5.5.5.2c -- the three properties that make a thermal diode a
diode: what it carries forwards, what it refuses to carry backwards, and
what the transition between the two costs in time and in leaked energy.

## Domain quick reference

- A diode heat pipe is a one-way thermal path. Forwards it behaves as an
  ordinary heat pipe; reversed -- when the nominal condenser becomes the
  hotter end -- a liquid trap or a gas blocking arrangement starves the
  evaporator and the conductance collapses. The point of the device is to
  protect a payload from a heat source that sometimes becomes a heat sink,
  or the reverse.
- Forward capability is still a capillary-limit question read off a
  temperature curve, and the same refusal to extrapolate past the measured
  span applies.
- The figure of merit is the diodicity ratio: forward conductance over
  reverse conductance, each derived from a measured heat flow and the
  temperature difference it produced. A high forward conductance does not
  make a good diode on its own -- the ratio is what the requirement is
  written against, and a pipe can pass its forward requirement while
  failing as a diode.
- Reverse heat leak is graded in watts at the service temperature
  difference, not in conductance. The cold side has an absorption budget,
  and what matters is the product of reverse conductance and the
  difference the mission actually imposes, which may be far larger than
  the difference the conductance was measured at.
- The switch is a transient, not an instant. Liquid has to be displaced
  into the trap or gas has to sweep the vapour space, and during that
  time the pipe is still conducting backwards. The switch is complete at
  the moment the reverse power settles at or below the threshold and does
  not rise above it again: an early dip that recovers is not a switch,
  and reading the first crossing gives an optimistic time.
- The energy that leaks during the switch is the integral of the reverse
  power up to that settling instant. Trapezoidal integration of the
  sampled transient is the honest reduction, and integrating the whole
  record instead of stopping at the crossing charges steady-state reverse
  leak to the switch.

## Workflow

1. Validate the forward transport curve and read the capability at the
   operating temperature, refusing a temperature outside the tabulated
   span.
2. Grade that capability against the forward requirement as a ratio,
   treating an exact unity as compliant.
3. Derive the forward conductance from the forward heat and its
   temperature difference, and the reverse conductance from the reverse
   pair, rejecting a zero temperature difference rather than dividing
   through it.
4. Reduce the two to a diodicity ratio and grade it against the required
   ratio, which is never below one.
5. Multiply the reverse conductance by the service reverse temperature
   difference and grade the resulting leak against the allowance.
6. Validate the sampled transient: at least two samples, strictly
   increasing in time, never a negative power.
7. Find the settling index as the first sample after which the reverse
   power never rises above the threshold again, then interpolate the
   crossing between it and the sample before it. Refuse a transient that
   never settles rather than returning the last sample time.
8. Integrate the transient by trapezoids up to that crossing, grade the
   energy against the budget and the time against its allowance, and
   report both alongside the transport and leak verdicts.

## Pitfalls

- Passing the forward requirement and calling the diode qualified. The
  forward direction is the easy one; the diodicity ratio and the reverse
  leak are the requirements the device exists to meet.
- Grading the reverse path on conductance alone. The cold side absorbs
  watts, and the service temperature difference can be several times the
  one the conductance was measured at.
- Taking the first downward crossing of the threshold as the switch time.
  A liquid slug can uncover the wick briefly and let the reverse power
  dip before it recovers; the switch is the last descent, not the first.
- Reading the last sample time when the transient never settles. That
  reports a completed switch from a record that does not show one; the
  correct response is to refuse and ask for a longer record.
- Integrating the whole sampled record for the switch energy. Past the
  crossing the pipe is in steady reverse mode, and charging that residue
  to the switch inflates the number without measuring anything new.
- Deriving a conductance from a near-zero temperature difference. The
  quotient explodes and reports a spectacular diodicity from measurement
  noise.

## Behavior contract (gate 3)

The curve validation and refusal to extrapolate, the forward ratio, the
conductance derivations, the diodicity ratio, the reverse leak at the
service difference, the transient validation, the last-descent settling
time with its interpolated crossing and its refusal of an unsettled
record, and the trapezoidal switch energy truncated at the crossing are
exercised by the gate 3 contract test:
scripts/test_e3102_diode_heat_pipe_verification.py against
scripts/e3102_diode_heat_pipe_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3102_diode_heat_pipe_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
