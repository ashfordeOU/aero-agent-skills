---
name: e3311-s-a-devices-containing-explosives
description: "Assess a safe and arm device that carries its own explosive lead against ECSS-E-ST-33-11C clause 4.11.5. Use when the task is proving the device cannot arm by accident and genuinely interrupts the train when safe: grading the out-of-line rotor offset in charge diameters and the barrier behind it, counting the declared arming events and rejecting any pair driven from one source, weighing the safe-position lock torque against the inertial torque the shock case applies, and reading position indication, monitor-to-firing isolation, arming time against its window and de-arm capability. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, safe-and-arm-device-explosive, explosive-train-out-of-line-interrupt, arming-event-independence, safe-position-lock-retention, safe-arm-position-monitoring, safe-arm-de-arm-capability."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-s-a-devices-containing-explosives, safe-and-arm-device-explosive, explosive-train-out-of-line-interrupt, arming-event-independence, safe-position-lock-retention, safe-arm-position-monitoring, safe-arm-de-arm-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Safe and Arm Devices Containing Explosives (space-systems/ecss/e3311-s-a-devices-containing-explosives)

Use when the task is the safe-and-arm screen of ECSS-E-ST-33-11C
clause 4.11.5 -- a device that carries an explosive lead of its own
and whose whole purpose, most of the time, is to not pass an
initiation through.

## Domain quick reference

- The device is graded on its failure to work. In the safe state the
  rotor lead is out of line, so a donor that fires produces heat,
  noise and nothing downstream; in the armed state the same lead
  closes the train. Both states are requirements.
- The interrupt is a geometric quantity, so it is expressed against
  the charge that has to miss: an offset in millimetres means nothing
  until it is divided by the lead diameter, and a lead offset by less
  than its own diameter is still partly in line.
- The barrier is graded separately from the offset. Offset stops the
  jet from lining up; barrier thickness stops what spreads sideways,
  and a device can pass one and fail the other.
- Arming independence is the gate most designs fail on paper and pass
  in review. Counting the arming events is not the check -- two events
  wired from one sequencer output are one event with two names, so
  the sources are grouped and any shared source is a finding.
- Safe-position retention is a torque comparison, not an assertion.
  The shock environment times the rotor mass times the offset arm
  gives an applied torque, and the detent has to beat it with margin.
- Monitoring has two halves: that both positions are indicated, and
  that the indication circuit is isolated from the firing circuit.
  A monitor sharing a return with the firing line is a path into the
  bridgewire wearing the label of a sensor.
- De-arm is what makes an aborted countdown recoverable. A device
  that cannot return to safe converts every hold after arming into a
  hazardous operation.

## Workflow

1. Normalize the device and reject it on a missing arming-event list,
   duplicate event identifiers, an inverted arming-time window or a
   missing source on any event, because an event with no source cannot
   be tested for independence.
2. Grade the interrupt: divide the safe-state offset by the lead
   diameter, compare against the required ratio, and grade the barrier
   thickness as a separate finding.
3. Group the arming events by source, count the distinct sources
   rather than the events, and report both a shortfall in count and
   any source driving more than one event.
4. Compute the inertial torque from rotor mass, shock acceleration and
   offset arm, and grade the safe lock torque against it with margin.
5. Check safe and armed position indication, then the isolation
   resistance between the monitoring and firing circuits.
6. Grade the arming time inside its declared window and the de-arm
   capability, then close with the failed gates and the verdict.

## Pitfalls

- Reading an offset in millimetres as an interrupt. Out of line is
  relative to the lead diameter, and the same 1.5 mm offset fully
  interrupts a 1 mm lead and barely shades a 3 mm one.
- Counting arming events instead of sources. This is the defect that
  produces a device advertised as dual-interlocked whose two
  interlocks fail together on one relay.
- Grading the detent by its own strength. Retention is a comparison
  with the applied torque, and the applied torque moves with the
  shock environment the device is actually installed in.
- Treating position indication as the monitoring requirement. An
  indicated position on a circuit sharing a path with the firing line
  has added a hazard while closing a paperwork item.
- Accepting an arming time that is only fast enough. The window has a
  lower bound too, and a device that arms sooner than the sequence
  expects has armed during an operation still counted as safe.
- Comparing a ratio or a margin with its requirement by bare
  arithmetic. An offset landing exactly on one charge diameter can sit
  a few units in the last place below it; the comparison absorbs that
  while the requirement stays untouched.

## Behavior contract (gate 3)

The device and arming-event normalization, the out-of-line and
barrier gates, the source-grouped independence check, the inertial
torque and lock-retention margin, the monitoring, arming-time and
de-arm gates, and the per-device and set verdicts are exercised by the
gate 3 contract test:
scripts/test_e3311_s_a_devices_containing_explosives.py against
scripts/e3311_s_a_devices_containing_explosives_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_s_a_devices_containing_explosives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
