---
name: flight-test-operations
description: "Use when a task concerns flight test operations, envelope expansion, performance determination, flutter clearance, ground vibration testing, and campaign planning: guide the router to the flight-test-operations pack, whose envelope-expansion and v-speeds sub-skills cover corner speed and certification speeds, stall-speed-determination and accelerate-stop-distance cover stall and rejected-takeoff distances, landing-distance-determination covers the FAR 25.125 landing distance, flutter-testing and ground-vibration-testing cover flutter margin and GVT modal survey, and flight-test-planning and flight-test-instrumentation cover test point build-up, sensors, and sampling. This pack is the campaign planning and data-reduction layer. Trigger: flight test, envelope expansion, corner speed, V-speeds, Vref, stall speed, Vs1g, accelerate stop distance, rejected takeoff, V1, landing distance, flutter margin, damping trend, ground vibration test, GVT, modal survey, instrumentation, sample rate, anti-aliasing, test point."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; router/entry point for the flight-test-operations domain pack"
metadata:
  domain: flight-test-operations
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Flight test operations domain pack (router)

Route here when the task is flight test planning, envelope
expansion, certification speed determination, performance
distance checks, flutter clearance, ground vibration testing,
or instrumentation.

## Domain

Flight test operations: envelope expansion planning, certification
V-speeds, reference stall speed determination, rejected-takeoff and
landing distance checks, flutter clearance, ground vibration testing,
flight test instrumentation, and campaign planning.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| flight-test-operations/envelope/envelope-expansion | Envelope expansion | corner speed, airspeed classes, expansion steps, load factor limits |
| flight-test-operations/envelope/v-speeds | V-speeds | Vref, V2, Vr from stall speeds, Vno/Vne guard, certification speeds |
| flight-test-operations/envelope/load-factor-envelope | Load factor envelope | V-n diagram, stall speed boundary, corner point, limit load factor, gust line, placard envelope |
| flight-test-operations/performance/stall-speed-determination | Stall speed determination | Vs1g from wing loading, weight-corrected stall speed, stall margin |
| flight-test-operations/performance/accelerate-stop-distance | Accelerate-stop distance | rejected takeoff, decision speed V1, braking deceleration, runway fits |
| flight-test-operations/performance/landing-distance-determination | Landing distance | Vref approach speed, flare segment, braking ground roll, 1.67 field length factor, runway fits |
| flight-test-operations/flutter/flutter-testing | Flutter testing | flutter margin, 1.2 design dive speed, damping trend extrapolation, frequency separation |
| flight-test-operations/flutter/ground-vibration-testing | Ground vibration testing | GVT modal survey, excitation, FRF peak picking, half-power damping, frequency resolution, mode shapes |
| flight-test-operations/flutter/limit-cycle-oscillation | Limit cycle oscillation | LCO, sustained oscillation, log decrement damping, amplitude growth, freeplay, nonlinear stiffness |
| flight-test-operations/planning/flight-test-planning | Flight test planning | test point build-up ordering, instrumentation coverage, campaign plan, prerequisites |
| flight-test-operations/planning/flight-test-instrumentation | Flight test instrumentation | sensor selection, sample rate, Nyquist, anti-aliasing, quantization, calibration |
| flight-test-operations/planning/flight-test-data-reduction | Flight test data reduction | calibration correction, time alignment, moving average, corrected airspeed, measurement uncertainty, data quality |

## Routing guidance

- Envelope expansion and corner speed questions route to the
  envelope-expansion sub-skill; certification speed questions route
  to the v-speeds sub-skill.
- Reference stall speed questions route to the
  stall-speed-determination sub-skill.
- Rejected-takeoff distance questions (V1, accelerate-stop) route to
  the accelerate-stop-distance sub-skill.
- Landing distance questions (Vref, flare, ground roll, field length
  factor, runway fits) route to the landing-distance-determination
  sub-skill.
- Flutter clearance questions (flutter margin, damping trend,
  frequency separation, design dive speed) route to the
  flutter-testing sub-skill.
- Ground vibration test questions (modal survey, excitation, FRF,
  half-power damping, mode shapes) route to the
  ground-vibration-testing sub-skill.
- Test point build-up and campaign planning questions route to the
  flight-test-planning sub-skill; sensor, sample rate, and
  anti-aliasing questions route to the flight-test-instrumentation
  sub-skill.
- Load factor envelope questions (V-n diagram, stall speed boundary,
  corner point, gust line, placard envelope) route to the
  load-factor-envelope sub-skill.
- Limit cycle oscillation questions (LCO, sustained oscillation, log
  decrement damping, freeplay, nonlinear stiffness) route to the
  limit-cycle-oscillation sub-skill.
- Post-flight data reduction questions (calibration correction, time
  alignment, filtering, corrected airspeed, measurement uncertainty)
  route to the flight-test-data-reduction sub-skill.
- Aircraft performance, structures, and certification questions
  route to their domain packs (flight-mechanics, structures,
  avionics).

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
