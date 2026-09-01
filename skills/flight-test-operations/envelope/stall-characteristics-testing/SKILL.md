---
name: stall-characteristics-testing
description: "Use when you must plan and gate the stall characteristics flight test: build the stall test matrix across configurations and power settings, pick the entry technique (gradual deceleration at one knot per second, power-on, turning, accelerated), compare the natural stall with the accelerated stall at the entry load factor, verify the stall warning onset (buffet or stick shaker) against the required margin, and judge the recovery characteristics (altitude loss, pitch-up, roll-off, departure resistance) against the certification requirements. Produces the test matrix, the warning onset verdict, and the recovery verdict that gate the stall test program. Trigger: stall characteristics, buffet, stick shaker, accelerated stall, stall warning, natural stall, recovery."
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
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [stall-testing, stall-characteristics, buffet, stick-shaker, departure-resistance]
  version: 0.1.0
  author: AeroSkills
---

# Stall Characteristics Testing (flight-test-operations/envelope/stall-characteristics-testing)

Use when the task is the stall characteristics flight test: stall test
matrix, entry techniques, stall warning onset, natural versus
accelerated stall, and recovery characteristics.

## Domain quick reference

- Stall test matrix: repeat each stall point in the clean, takeoff,
  and landing configurations, at idle and at maximum continuous power,
  and at the aft and forward c.g. limits; the aft c.g. condition is
  the critical one for stall characteristics.
- Entry techniques: the natural stall is entered wings level with a
  gradual deceleration of about one knot per second (0.5144 m/s^2)
  holding the trim attitude; the power-on stall adds climb power and a
  nose-up attitude; the turning stall is entered in a coordinated bank
  so the stall occurs at a higher speed; the accelerated stall is
  entered at an elevated load factor n, so the wing stalls at
  V = Vs * sqrt(n) where Vs is the 1g stall speed.
- Stall warning (FAR 25.207 / CS-25.207 context, paraphrased): the
  warning must be clear and distinct, either natural aerodynamic
  warning or an artificial device (stick shaker, horn), and must begin
  at a speed at least five percent above the stalling speed, or three
  knots, whichever is greater, in every configuration.
- Natural stall versus accelerated stall: the natural stall develops
  at 1g during a slow deceleration, with buffet, pitch break, and
  possible wing drop as first evidence; the accelerated stall is
  reached at the same CL_max but at a higher dynamic pressure and
  speed, and it probes high-AOA behavior, roll-off, and departure
  resistance before the normal stall regime.
- Recovery characteristics (FAR 25.203 / CS-25.203 context,
  paraphrased): at stall the aeroplane must show no excessive
  pitch-up, no uncontrollable rolling or yawing, and no tendency to
  spin or depart; recovery must be prompt with normal use of the
  flight controls (power reduction, pitch down, wings level) and with
  a limited altitude loss.

## Workflow

1. Build the stall test matrix: configurations, power settings, and
   c.g. conditions per test point.
2. Compute the entry load factor for a turning stall with
   level_turn_load_factor(bank_deg) and the corresponding stall speed
   with accelerated_stall_speed(vs1g, load_factor).
3. Derive the required warning speed with
   stall_warning_speed(vs1g, margin) and check the observed warning
   onset with stall_warning_on_time(warning_speed, vs1g, margin).
4. Size the entry deceleration with
   entry_deceleration_time(entry_speed, stall_speed, decel_rate).
5. Judge the observed recovery with stall_recovery_verdict(altitude
   loss, pitch-up, roll-off) and gate the stall test program on the
   verdict.

## Pitfalls

- Calling the turning stall speed the 1g stall speed: in a banked
  turn the wing stalls at V = Vs * sqrt(n) with n = 1/cos(bank); a 60
  degree bank doubles the load factor and raises the stall speed by
  about 41 percent.
- Entering the accelerated stall with a rapid pull instead of a
  stabilized entry: the load factor must be held and the deceleration
  controlled, otherwise the observed speed and angle of attack do not
  represent the steady accelerated stall.
- Treating stick shaker onset as the stall itself: the shaker is a
  warning device that must fire ahead of the stall with margin; the
  stall evidence is buffet, pitch break, or roll-off.
- Checking the warning margin in only one configuration: the warning
  onset requirement applies in every configuration and power setting
  in the matrix.
- Ignoring the aft c.g. condition: stall and recovery behavior
  degrade toward the aft c.g. limit, so a clean test at the forward
  c.g. hides the critical case.
- Reporting altitude loss without the recovery procedure used: the
  recovery altitude loss only means something when power reduction
  and pitch-down are applied promptly and consistently.
- Passing zero or negative inputs to the logic functions; the module
  raises ValueError instead of returning a meaningless speed, time, or
  verdict.

## Behavior contract (gate 3)

The accelerated stall speed, level turn load factor, warning onset,
entry deceleration, and recovery verdict logic is exercised by the
gate 3 contract test: scripts/test_stall_characteristics_testing.py
against scripts/stall_characteristics_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_stall_characteristics_testing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the stall entry
  techniques, warning margin, and recovery requirements are common
  flight test methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
