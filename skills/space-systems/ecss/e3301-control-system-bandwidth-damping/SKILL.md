---
name: e3301-control-system-bandwidth-damping
description: "Verify that a mechanism control loop places its bandwidth clear of the driven structure's flexible modes and keeps the damping ECSS-E-ST-33-01C clauses 4.7.8.3 and 4.7.8.4 require. Use when a closed-loop bandwidth, a modal survey and a separation factor exist and the loop must be shown not to excite a boom, panel or gearbox mode: derives the bandwidth ceiling the lowest mode sets, turns each modal damping ratio into the resonant peak the loop sees, compares that peak plus the gain margin with the attenuation the roll-off supplies, and grades closed-loop damping declared or recovered from a measured overshoot. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-control-bandwidth-ceiling, flexible-mode-separation-factor, modal-resonant-peak-attenuation, closed-loop-damping-ratio-floor, control-rolloff-per-octave, overshoot-recovered-damping."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-control-system-bandwidth-damping, mechanism-control-bandwidth-ceiling, flexible-mode-separation-factor, modal-resonant-peak-attenuation, closed-loop-damping-ratio-floor, control-rolloff-per-octave]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Control Bandwidth and Damping (space-systems/ecss/e3301-control-system-bandwidth-damping)

Use when the task is the bandwidth-and-damping part of the mechanism
control-system design of ECSS-E-ST-33-01C clauses 4.7.8.3 and 4.7.8.4 —
deciding how fast the loop is allowed to be given the flexible structure
it drives, and how much damping the closed loop has to retain once it is
that fast.

## Domain quick reference

- The loop bandwidth is bounded from above by the structure, not by the
  actuator. The lowest flexible mode of the driven appendage sets a
  ceiling equal to its frequency divided by the separation factor the
  programme declares; a loop faster than that ceiling closes around a
  mode it was never modelled with.
- A lightly damped mode is an amplifier. Its resonant peak is the
  inverse of twice its damping ratio, so a mode at one percent damping
  presents about 34 dB of gain the loop has to attenuate before the
  required gain margin is even counted. Modal damping and required
  margin therefore add, in decibels, into a single attenuation demand.
- The attenuation actually available is the loop roll-off integrated
  over the octave count between bandwidth and mode. Doubling the
  separation buys one slope's worth of decibels — a 12 dB/octave
  roll-off across three and a third octaves supplies about 40 dB. This
  is why separation and roll-off slope trade against each other and
  cannot be argued separately.
- Closed-loop damping is a requirement on the achieved response, not on
  the compensator. It can be declared from the design poles or
  recovered from a measured step overshoot through the second-order
  relation; both routes have to be graded against the same floor, and
  the settling time follows from the damping and the natural frequency.
- A declared modal damping ratio much above a few percent makes the
  resonant peak look small. For a deployed space structure that is an
  assumption, not a measurement, and it is admissible only when modal
  test evidence sits behind it.

## Workflow

1. Validate the bandwidth, the separation factor and the flexible-mode
   set; a duplicate mode name, a non-positive frequency or a damping
   ratio at or above critical is an input error, not a case to clamp.
2. Sort the modes by frequency and derive the bandwidth ceiling from
   the lowest one and the separation factor; grade the declared
   bandwidth against that ceiling with a named tolerance at the bound.
3. For every mode, form the separation ratio and decide first whether
   the mode sits inside the bandwidth at all — a mode inside the loop
   fails separation and attenuation together and is reported once.
4. Convert each modal damping ratio into a resonant peak in decibels,
   add the required gain margin, and compare the sum with the roll-off
   attenuation supplied at that mode's octave count.
5. Grade closed-loop damping against the required minimum, taking it
   from the declared value or recovering it from measured overshoot,
   and report the settling time the result implies when a natural
   frequency is available.
6. Report every finding separately: bandwidth above the ceiling, a mode
   inside the loop, a separation or attenuation shortfall, an
   uncorroborated modal damping assumption, and a damping shortfall.

## Pitfalls

- Setting the bandwidth from the actuator or from a settling-time wish
  and checking the modes afterwards. The lowest mode sets the ceiling
  first; a bandwidth chosen before the modal survey is a number waiting
  to be withdrawn.
- Counting the separation factor as if it were the whole requirement. A
  mode five times the bandwidth can still be under-attenuated when it
  is lightly damped and the roll-off is shallow; separation and
  attenuation are two findings, not one.
- Reading a modal damping ratio off a handbook and treating it as
  demonstrated. Above a few percent the assumption dominates the
  result, so it needs modal test evidence or it is reported as an
  assumption.
- Grading closed-loop damping only on the compensator design poles when
  a step response has been measured. The measured overshoot is the
  evidence; the second-order relation converts it, and both routes are
  graded against the same floor.
- Widening the required margin or the damping floor so an exact
  equality passes. An equality at the limit is a representation
  question, absorbed by the tolerance inside the comparison, and the
  required value stays as specified.

## Behavior contract (gate 3)

The input validation, mode-set ordering, bandwidth-ceiling derivation,
resonant-peak and roll-off attenuation comparison, overshoot-to-damping
recovery, settling-time estimate and finding assembly are exercised by
the gate 3 contract test:
scripts/test_e3301_control_system_bandwidth_damping.py against
scripts/e3301_control_system_bandwidth_damping_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_control_system_bandwidth_damping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
