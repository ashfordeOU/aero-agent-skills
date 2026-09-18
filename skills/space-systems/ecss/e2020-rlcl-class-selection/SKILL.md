---
name: e2020-rlcl-class-selection
description: "Evaluate which retriggerable current limiter class a protected load belongs on. Use when an ECSS-E-ST-20-20C clause 5.2.2.1.1 power design has to take an RLCL class from the project class table and show its performance figures hold under repeated retriggering: derate the continuous rating, form the worst-case retrigger duty from the longest trip-off delay against the shortest hold-off, compare the resulting mean fault current with the harness thermal rating and the per-attempt fault energy with its allowance, count the retrigger attempts a capacitive load needs to finish charging against the class attempt allowance, then take the smallest passing class. Refuses a non-ascending table, an inverted hold-off window and a lower limiting current that leaves nothing to charge the load. Trigger: ecss, e-st-20-20c, rlcl-class-selection, retriggerable-current-limiter, rlcl-retrigger-duty-cycle, rlcl-hold-off-time, rlcl-attempt-allowance, rlcl-fault-energy-per-attempt, harness-thermal-mean-rating."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-rlcl-class-selection, retriggerable-current-limiter, rlcl-retrigger-duty-cycle, rlcl-hold-off-time, rlcl-attempt-allowance, rlcl-fault-energy-per-attempt, harness-thermal-mean-rating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — RLCL Class Selection (space-systems/ecss/e2020-rlcl-class-selection)

Use when the task is the retriggerable-limiter class choice of
ECSS-E-ST-20-20C clause 5.2.2.1.1 — taking one class out of the
standard's class table for a protected load and demonstrating that the
performance figures attached to that class still hold once the limiter
is allowed to close again by itself.

## Domain quick reference

- An RLCL behaves like a latching limiter up to the moment it trips.
  Where a latching unit stays open until it is commanded on, a
  retriggerable unit waits a hold-off period and closes again on its
  own, repeating up to a bounded number of attempts before it gives up.
  Its class row therefore carries two figures a latching class does not:
  the hold-off window and the attempt allowance.
- Automatic retriggering makes a sustained fault repetitive rather than
  singular. The harness no longer sees one pulse, it sees a train, so
  the quantity that matters thermally is the MEAN current set by the
  retrigger duty cycle. The binding duty is the LONGEST trip-off delay
  against the SHORTEST hold-off, which is the most conduction per cycle
  a compliant unit may present.
- Each attempt also dumps an energy pulse into the fault. Bus voltage
  times upper limiting current times the longest trip-off delay is the
  per-attempt energy, and it is bounded separately from the mean
  current: a low duty cycle does not make a large individual pulse
  acceptable.
- Retriggering is also a start-up mechanism, and this is what separates
  the RLCL selection from the LCL one. A capacitive load that cannot
  finish charging inside one trip-off delay can still come up across
  several attempts. The charging current is the LOWER limiting current
  minus the load's own steady draw, delivered for the SHORTEST trip-off
  delay, and only the fraction of charge the load keeps across the
  hold-off carries into the next attempt. If the lower limiting current
  does not exceed the steady draw there is no charging current at all
  and no number of attempts will start the load.
- The attempt count the start-up needs is a selection output in its own
  right, compared against the class allowance. Consuming most of the
  allowance just to come up leaves nothing for a genuine transient, so
  it is worth an advisory even when it passes.
- The smallest adequate class wins: a larger class holds a higher fault
  current for longer at a comparable duty, so every retrigger train puts
  more into the same harness for no benefit.

## Workflow

1. Validate the class table: ascending continuous ratings, unique
   names, a limiting band above the class's own continuous rating, and
   trip-off and hold-off windows that are the right way up. Require an
   integer attempt allowance of at least one — an unbounded retrigger
   into a hard short is a bus hazard, not a class.
2. Validate the load: steady current, capacitance, bus voltage, the
   peak and thermal ratings of the harness, and the per-attempt fault
   energy allowance. Refuse a thermal rating that exceeds the peak one.
3. Derate each class continuous rating and keep the classes that carry
   the steady load.
4. Form the worst-case retrigger duty from the longest trip-off delay
   and the shortest hold-off, take the mean fault current from it, and
   compare against the harness thermal rating.
5. Compare the upper limiting current against the harness peak rating,
   and the per-attempt fault energy against its allowance. These are
   three separate gates and a class may pass any two of them.
6. Count the attempts the load needs to finish charging: accumulate the
   charge delivered each attempt at the lower limiting current net of
   the steady draw, apply the declared retention across each hold-off,
   and stop when the class allowance runs out.
7. Take the smallest class that passes every gate; report its duty, mean
   current, per-attempt energy, attempt count and both harness slacks,
   and raise an advisory when start-up consumes most of the allowance.

## Pitfalls

- Selecting an RLCL the way an LCL is selected. The continuous rating,
  limiting band and trip-off window are common to both, but ignoring the
  duty cycle, the per-attempt energy and the attempt allowance drops
  exactly the three checks that automatic retriggering introduces.
- Forming the duty cycle from the nominal trip-off delay and the
  nominal hold-off. A compliant unit may sit at the long end of the
  trip-off window and the short end of the hold-off at the same time, so
  the worst-case duty is that pairing and nothing gentler.
- Treating the mean current as a substitute for the energy check. The
  mean says what the harness heats to; the per-attempt energy says what
  a single pulse does to the fault site and to the switch. A class can
  pass one and fail the other.
- Charging the load capacitance at the lower limiting current without
  subtracting the load's own steady draw. The load keeps consuming
  during the attempt, and when the draw reaches the lower limiting
  current there is no charging current left at all.
- Assuming charge is kept perfectly across the hold-off. A partially
  charged load bleeds down while the limiter is open, and a retention
  fraction below one can turn a two-attempt start-up into one that
  never converges inside the allowance.
- Comparing a mean current or an energy by bare arithmetic. A case
  meant to sit exactly on the thermal rating or exactly on the energy
  allowance can land a few units in the last place above it; the
  comparison absorbs that representation error while the ratings stay as
  specified.

## Behavior contract (gate 3)

The class-table validation, load validation, worst-case duty cycle,
mean fault current, per-attempt fault energy, retrigger start-up attempt
count and smallest-adequate selection are exercised by the gate 3
contract test: scripts/test_e2020_rlcl_class_selection.py against
scripts/e2020_rlcl_class_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2020_rlcl_class_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
