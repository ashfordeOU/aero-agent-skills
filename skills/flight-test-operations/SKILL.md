---
name: flight-test-operations
description: "Use when a task concerns flight test operations: route to the flight-test-operations pack: envelope-expansion corner speed, load-factor-envelope load factor, v-speeds cert speeds, stall-speed-determination stall speed, stall-characteristics-testing stall behavior, accelerate-stop-distance rejected takeoff, takeoff-distance-determination takeoff distance, landing-distance-determination landing distance, glide-flight-test glide, flight-loads-survey strain calibration, flutter-testing flutter margin, ground-vibration-testing GVT, limit-cycle-oscillation LCO, dynamic-stability-flight-test mode damping, engine-flight-test performance, flight-test-planning planning, flight-test-instrumentation sensors, flight-test-data-reduction reduction, flight-test-safety risk and go no-go, telemetry-data-acquisition telemetry, test-point-matrix-design matrix. Trigger: flight test, envelope expansion, stall speed, V1, landing distance, flutter, GVT, instrumentation, test point, telemetry, dynamic stability, engine flight test."
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
  author: Aero Agent Skills
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
| flight-test-operations/envelope/stall-characteristics-testing | Stall characteristics testing | 1-g stalls, accelerated stalls, stall warning margins, stall behavior |
| flight-test-operations/envelope/flight-loads-survey | Flight loads survey | strain gauge calibration, maneuver points, load factor versus speed survey, loads envelope |
| flight-test-operations/performance/stall-speed-determination | Stall speed determination | Vs1g from wing loading, weight-corrected stall speed, stall margin |
| flight-test-operations/performance/accelerate-stop-distance | Accelerate-stop distance | rejected takeoff, decision speed V1, braking deceleration, runway fits |
| flight-test-operations/performance/takeoff-distance-determination | Takeoff distance | ground roll, rotation, 35-ft obstacle, takeoff field length, runway fits |
| flight-test-operations/performance/landing-distance-determination | Landing distance | Vref approach speed, flare segment, braking ground roll, 1.67 field length factor, runway fits |
| flight-test-operations/performance/glide-flight-test | Glide flight test | glide ratio, sink rate, best glide speed, glide endurance |
| flight-test-operations/performance/engine-flight-test | Engine flight test | thrust determination, fuel flow, EGT margins, engine performance verification |
| flight-test-operations/flutter/flutter-testing | Flutter testing | flutter margin, 1.2 design dive speed, damping trend extrapolation, frequency separation |
| flight-test-operations/flutter/ground-vibration-testing | Ground vibration testing | GVT modal survey, excitation, FRF peak picking, half-power damping, frequency resolution, mode shapes |
| flight-test-operations/flutter/limit-cycle-oscillation | Limit cycle oscillation | LCO, sustained oscillation, log decrement damping, amplitude growth, freeplay, nonlinear stiffness |
| flight-test-operations/stability/dynamic-stability-flight-test | Dynamic stability flight test | short period, phugoid, Dutch roll, log decrement, damping ratio, handling qualities |
| flight-test-operations/planning/flight-test-planning | Flight test planning | test point build-up ordering, instrumentation coverage, campaign plan, prerequisites |
| flight-test-operations/planning/flight-test-instrumentation | Flight test instrumentation | sensor selection, sample rate, Nyquist, anti-aliasing, quantization, calibration |
| flight-test-operations/planning/flight-test-data-reduction | Flight test data reduction | calibration correction, time alignment, moving average, corrected airspeed, measurement uncertainty, data quality |
| flight-test-operations/planning/flight-test-safety | Flight test safety | risk assessment, go/no-go criteria, emergency procedures, safety pilot duties |
| flight-test-operations/planning/telemetry-data-acquisition | Telemetry data acquisition | sample rates, anti-aliasing, PCM/IRIG formats, telemetry link, ground station, data quality |
| flight-test-operations/planning/test-point-matrix-design | Test point matrix design | test conditions, altitude/speed/weight sweeps, configurations, repeat points, sequencing |
| flight-test-operations/envelope/structural-coupling-test | Structural coupling test | gain margin, phase margin, frequency response, excitation sweep, flight control coupling |
| flight-test-operations/performance/climb-performance-flight-test | Climb performance flight test | rate of climb, climb gradient, pressure altitude change, temperature correction, weight correction |
| flight-test-operations/stability/static-stability-flight-test | Static stability flight test | trim curve slope, elevator angle versus speed, stick fixed neutral point, static margin, elevator angle per g |
| flight-test-operations/envelope/high-angle-of-attack-testing | High angle of attack testing | high angle of attack, post stall, deep stall, AoA calibration, position error correction, stall margin, departure resistance, spin entry, stall warning, flight test envelope |
| flight-test-operations/envelope/spin-testing | Spin testing | spin testing, spin entry, spin recovery, recovery parachute, spin test point, spin resistance, FAR 25.201 |
| flight-test-operations/uas/part107-sora | Part107 Sora | part 107 applicability, part107 sora, sora operational category, ground risk class, air risk class, arc, grc, robustness level, containment, bvlos waiver, drone risk assessment, uas risk, remote pilot certificate, 400 ft agl, visual line of sight. |
| flight-test-operations/performance/level-acceleration-test | Level acceleration test | level acceleration, accelerated level flight, specific excess power, total energy method, excess thrust |
| flight-test-operations/planning/position-error-calibration | Position error calibration | position error calibration, PEC, airspeed calibration, calibrated airspeed, tower fly-by, trailing cone, GPS ground speed doublet, position error correction curve |
| flight-test-operations/envelope/icing-flight-test | Icing flight test | icing flight test, natural icing, artificial ice shape, appendix C envelope, liquid water content, median volumetric diameter, icing encounter severity, ice protection effectiveness test |
| flight-test-operations/planning/noise-certification-test | Noise certification test | noise certification flight test, EPNL, effective perceived noise level, PNLT, tone corrected, 10 dB down, flyover noise, sideline noise, approach noise, cumulative margin |
| flight-test-operations/envelope/vmc-determination | Vmc determination | minimum control speed, Vmc, critical engine, asymmetric yawing moment, rudder pedal force, engine inoperative demonstration |
| flight-test-operations/envelope/buffet-boundary-testing | Buffet boundary testing | buffet boundary, buffet onset, accelerometer RMS rise, high speed buffet, maneuver buffet, buffet margin |
| flight-test-operations/performance/cruise-performance-flight-test | Cruise performance flight test | cruise performance flight test, fuel flow versus Mach, stabilized fuel flow runs, weight corrected fuel flow, maximum range cruise speed, long range cruise speed |
| flight-test-operations/performance/rotorcraft-performance-flight-test | Rotorcraft performance flight test | rotorcraft flight test, measured figure of merit, torque to power, hover ceiling determination, weight density correction |

| flight-test-operations/performance/rotorcraft-forward-flight-performance-test | Rotorcraft forward flight performance test | rotorcraft forward flight flight test, level-flight speed sweep, torque to shaft power, power required polar, vh determination, max continuous power |
| flight-test-operations/stability/lateral-directional-stability-flight-test | Lateral-directional stability flight test | steady heading sideslip sweep, rudder-fixed stability, rudder-free stability, weathercock stability, dihedral effect, pedal force gradient |
| flight-test-operations/flutter/flight-vibration-survey | Flight vibration survey | track and balance, order analysis, per rev amplitude, synchronous DFT, vibration limit, rotor balance survey |
| flight-test-operations/performance/engine-failure-takeoff-flight-test | Engine failure takeoff flight test | balanced field V1, engine out takeoff, VEF recognition, decision speed, continued takeoff, field length verdict |
| flight-test-operations/stability/control-force-flight-test | Control force flight test | control force flight test, stick force gradient, stick force per g, breakout force, control centering check, force transducer calibration, stick force stability |

| flight-test-operations/planning/pcm-telemetry-decommutation | PCM telemetry decommutation | PCM frame sync lock, decommutation, supercommutated channel, subcommutated channel, subframe ID demultiplexing, telemetry time series recovery |


## Routing guidance

- Envelope expansion and corner speed questions route to the
  envelope-expansion sub-skill; certification speed questions route
  to the v-speeds sub-skill; V-n diagram and load factor questions
  route to load-f- Part 107 applicability questions route to the uas part107-sora sub-skill.
actor-envelope.
- Stall behavior questions (1-g stalls, accelerated stalls, warning
  margins) route to stall-characteristics-testing; reference stall
  speed questions route to stall-speed-determination; loads survey
  and strain calibration questions route to flight-loads-survey.
- Rejected-takeoff distance questions (V1, accelerate-stop) route to
  the accelerate-stop-distance sub-skill; takeoff field length
  questions route to takeoff-distance-determination.
- Landing distance questions (Vref, flare, ground roll, field length
  factor, runway fits) route to the landing-distance-determination
  sub-skill; glide questions route to glide-flight-test.
- Engine performance verification questions (thrust, fuel flow, EGT)
  route to engine-flight-test.
- Flutter clearance questions (flutter margin, damping trend,
  frequency separation, design dive speed) route to the
  flutter-testing sub-skill; ground vibration test questions (modal
  survey, excitation, FRF, half-power damping, mode shapes) route to
  ground-vibration-testing; LCO questions route to
  limit-cycle-oscillation.
- Dynamic stability questions (short period, phugoid, Dutch roll,
  log decrement, damping ratio) route to
  dynamic-stability-flight-test.
- Test point build-up and campaign planning questions route to the
  flight-test-planning sub-skill; sensor, sample rate, and
  anti-aliasing questions route to flight-test-instrumentation;
  telemetry link and data acquisition questions route to
  telemetry-data-acquisition; test point matrix and condition
  sweeps route to test-point-matrix-design; risk, go/no-go, and
  emergency procedure questions route to flight-test-safety.
- Post-flight data reduction questions (calibration correction, time
  alignment, filtering, corrected airspeed, measurement uncertainty)
  route to the flight-test-data-reduction sub-skill.
- Aircraft performance, structures, and certification questions
  route to their domain packs (flight-mechanics, structures,
  avionics).
- Structural coupling gain and phase margins, frequency response excitation sweeps, and flight control coupling questions route to the envelope structural-coupling-test sub-skill.
- Rotorcraft performance flight test questions (measured figure of merit, torque to power, hover ceiling determination, weight density correction) route to the performance rotorcraft-performance-flight-test sub-skill.
- Climb performance flight test, measured rate of climb, pressure altitude change, and climb gradient correction questions route to the performance climb-performance-flight-test sub-skill.
- Trim curve slope, elevator angle versus speed, stick-fixed neutral point, static margin, and elevator angle per g questions route to the stability static-stability-flight-test sub-skill.
- High angle of attack flight test planning, AoA position error calibration, stall warning margin, and departure resistance assessment route to the envelope high-angle-of-attack-testing sub-skill.
- Spin flight testing, spin entry and recovery procedure, recovery parachute requirements, spin test point matrix, and spin-resistance criteria route to the envelope spin-testing sub-skill.
- Airspeed position error calibration, tower fly-by and trailing cone runs, GPS ground speed doublet, PEC curve, and calibrated airspeed questions route to the planning position-error-calibration sub-skill.
- Vmc determination questions (minimum control speed, vmc, critical engine, asymmetric yawing moment, rudder pedal force, engine inoperative demonstration) route to the vmc-determination sub-skill.
- Buffet boundary testing questions (buffet boundary, buffet onset, accelerometer rms rise, high speed buffet, maneuver buffet, buffet margin) route to the buffet-boundary-testing sub-skill.
- Cruise performance flight test questions (cruise performance flight test, fuel flow versus mach, stabilized fuel flow runs, weight corrected fuel flow, maximum range cruise speed, long range cruise speed) route to the cruise-performance-flight-test sub-skill.
- Rotorcraft level-flight performance test questions (level-flight speed sweep, torque to shaft power, power-required polar, vh determination) route to the performance rotorcraft-forward-flight-performance-test sub-skill.
- Static lateral-directional stability flight test questions (steady-heading sideslip sweep, rudder-fixed and rudder-free stability, weathercock and dihedral effect, pedal force gradient) route to the stability lateral-directional-stability-flight-test sub-skill.

- In-flight vibration survey questions (track and balance, per-rev order analysis, vibration limit, rotor balance survey) route to the flutter flight-vibration-survey sub-skill.
- Engine-out takeoff questions (balanced-field V1, VEF recognition, decision speed, continued takeoff) route to the performance engine-failure-takeoff-flight-test sub-skill.

- Longitudinal control-force flight test reduction questions (force transducer calibration, stick force gradient, stick force per g, breakout force, centering check) route to the stability control-force-flight-test sub-skill.
- PCM telemetry decode questions (frame sync lock, decommutation of supercommutated and subcommutated channels, subframe ID demultiplexing) route to the planning pcm-telemetry-decommutation sub-skill.


## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
- Level-acceleration and specific-excess-power flight test questions route to the performance level-acceleration-test sub-skill.
- Icing certification flight test questions (natural icing encounters, artificial ice shapes, Appendix C envelope classification, ice protection effectiveness test points) route to the envelope icing-flight-test sub-skill.
- Noise certification questions (EPNL from a PNLT time history, flyover sideline and approach conditions, cumulative margin) route to the planning noise-certification-test sub-skill.
