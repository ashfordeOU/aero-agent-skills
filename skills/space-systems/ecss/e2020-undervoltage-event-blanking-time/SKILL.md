---
name: e2020-undervoltage-event-blanking-time
description: "Evaluate the blanking time that lets an undervoltage protection ignore a short dip below its trip threshold, against clause 5.4.3.3.1 of ECSS-E-ST-20-20C. Use when a unit declares a time below the threshold that has to elapse before a trip is issued and that figure has to be shown to sit in a real window. Build the lower bound from the longest transient the bus is allowed to impose, build the upper bound from the hold-up the load can ride out less the detection and switching latency, and report the margin on each side. Then walk the declared dip events, decide which are absorbed and which trip, and name every transient that trips and every genuine undervoltage the blanking swallows. Trigger: ecss, e-st-20-20c-clause-5-4-3-3-1, undervoltage-event-blanking-time, undervoltage-trip-blanking-window, bus-transient-ride-through-blanking, undervoltage-detection-latency-budget, blanked-undervoltage-event-walk, undervoltage-blanking-hold-up-bound."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e-st-20-20c-clause-5-4-3-3-1, e2020-undervoltage-event-blanking-time, undervoltage-trip-blanking-window, bus-transient-ride-through-blanking, undervoltage-detection-latency-budget, blanked-undervoltage-event-walk, undervoltage-blanking-hold-up-bound]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Undervoltage Event Blanking Time (space-systems/ecss/e2020-undervoltage-event-blanking-time)

Use when the task is clause 5.4.3.3.1 of ECSS-E-ST-20-20C: a dip below the
undervoltage threshold shorter than a defined time has to produce no trip.
This leaf takes one timing budget and, when they are declared, a set of dip
events, and decides whether the blanking time fits between the transients it
has to survive and the fault it still has to catch.

## Domain quick reference

- The blanking time is squeezed, not chosen. Its floor comes from the bus —
  the longest disturbance the system is allowed to impose and the load is
  expected to ride out. Its ceiling comes from the load — how long the
  equipment can sit under its threshold before the undervoltage does harm.
  Neither number belongs to the protection designer.
- The detection chain spends part of the ceiling before the blanking timer
  ever gets to. Sensing filter delay, comparator response and the switching
  element's own turn-off all sit inside the hold-up, so the time available to
  blanking is the hold-up less those latencies, not the hold-up.
- The two bounds can cross, and when they do the answer is not a number. A bus
  whose permitted transients outlast the load's hold-up has no blanking time
  that both rides them out and still protects; the finding is that the
  transient envelope and the hold-up are incompatible.
- A dip arms the timer only while the bus is actually under the threshold. A
  long shallow sag that never reaches the trip point is not a blanked event —
  it is an event the protection never saw, and reading it as evidence that
  the blanking works is reading the wrong thing.
- The two wrong answers are not symmetric in consequence but they are
  symmetric in the walk. A transient that trips costs availability; a real
  undervoltage that is absorbed costs the protection its purpose. Both have to
  be named per event rather than summarised as a count.
- Margin is held back from each bound because both are estimates. The longest
  permitted transient is a specification figure that units drift past, and the
  hold-up is a capacitance figure that ages, so sizing the blanking onto
  either edge exactly is sizing it onto a moving wall.

## Workflow

1. Validate the timing budget: a positive blanking time, a positive longest
   transient, a positive hold-up, non-negative detection and switching
   latencies, a positive trip threshold, and a margin fraction below one.
2. Build the lower bound as the longest permitted transient inflated by the
   margin.
3. Build the upper bound as the hold-up reduced by the margin and then reduced
   again by the detection and switching latencies.
4. Report whether the window is feasible at all; when the bounds cross, stop
   grading the declared time and report the incompatibility.
5. Place the declared blanking time in the window and report the margin on
   each side.
6. Validate the declared dip events; reject an event declared an undervoltage
   whose minimum voltage never reaches the trip threshold, because that is a
   contradiction in the input rather than a design finding.
7. Walk each event: an event that never reaches the threshold never arms the
   timer, and an event that does arm it trips only when it outlasts the
   blanking time.
8. Return the verdict with both bounds, both margins, the per-event responses
   and a finding for every event the protection handles the wrong way.

## Pitfalls

- Sizing the blanking time against the hold-up and forgetting the latencies
  already spent inside it. The chain's own delay is part of the same budget,
  and a blanking time equal to the whole hold-up leaves nothing for the trip
  to actually happen in.
- Treating the lower bound as advisory. A blanking time under the longest
  permitted transient turns a normal load step into a trip, and the resulting
  outage looks like a protection fault rather than a sizing error.
- Reading a long sag that stayed above the threshold as a successfully blanked
  event. It never armed the timer, so it says nothing about the blanking at
  all, and a test campaign built only from those events proves nothing.
- Reporting only a count of events handled wrongly. A transient that trips and
  an undervoltage that is absorbed are opposite failures, and averaging them
  into one number hides which way the time has to move.
- Sizing onto a bound exactly. Both bounds are estimates carrying their own
  spread, and a blanking time placed on either edge has no room for the drift
  the figures behind it already have.
- Assuming a feasible window exists. When the permitted transient envelope
  outlasts the hold-up, no blanking time works, and quietly picking one
  anyway ships a protection that cannot do both jobs.

## Behavior contract (gate 3)

The timing validation, lower and upper bound construction, feasibility test,
in-window placement with margins, event validation including the contradictory
undervoltage input, timer arming, per-event response walk and the verdict are
exercised by the gate 3 contract test:
scripts/test_e2020_undervoltage_event_blanking_time.py against
scripts/e2020_undervoltage_event_blanking_time_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_undervoltage_event_blanking_time.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
