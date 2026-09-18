---
name: e2020-status-integrity-during-bus-startup
description: "Verify that a current limiter's actual state and its reported status both track the intended state through main bus start up and through recovery from zero volts, under ECSS-E-ST-20C clause 5.2.7.4.1. Use when a power distribution unit is assessed against a recorded start up profile: establish the window in which the limiter control logic has a guaranteed supply, hold samples below that floor as indeterminate rather than as agreement, find every zero volt excursion and require the declared default state once the supply returns, then weigh intended state, actual state and reported status at each valid sample. Trigger: ecss, e-st-20c-clause-5-2-7-4-1, limiter-state-integrity, main-bus-start-up-profile, zero-volt-recovery-default-state, limiter-status-telemetry-agreement, control-logic-supply-window."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-status-integrity-during-bus-startup, e-st-20c-clause-5-2-7-4-1, limiter-state-integrity, main-bus-start-up-profile, zero-volt-recovery-default-state, limiter-status-telemetry-agreement, control-logic-supply-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limiter State Integrity Through Bus Start Up (space-systems/ecss/e2020-status-integrity-during-bus-startup)

Use when the task is the clause 5.2.7.4.1 question of ECSS-E-ST-20C: over
the whole of main bus start up, and over the recovery that follows a fall
to zero volts, was the current limiter in the state it was intended to be
in, and did the status it reported describe that state.

## Domain quick reference

- Two separate claims live in the same clause. State integrity is whether
  the limiter output was in the intended state. Status integrity is
  whether the status the unit sent back described the state it was
  actually in. A unit can hold the right state and report the wrong one,
  and that is a fault in its own right, because everything downstream of
  the telemetry then acts on a state that does not exist.
- A limiter's control and status logic has no defined state until the bus
  has risen past the supply floor the unit declares. Below that floor the
  output can sit anywhere and the status line can read anything, so those
  samples are indeterminate evidence. They are neither a failure to be
  raised nor agreement to be credited.
- Crediting a below-floor sample as agreement is the more damaging of the
  two errors. It lets a profile that never woke the unit up report a
  clean pass, which is why a profile that never reached the floor is a
  coverage finding rather than a result.
- A fall to zero volts is not a pause in the same start up. It ends the
  previous one, and what follows is a cold start that has to come back in
  the default state the design declares, usually off, so that nothing
  downstream is re-energised by the bus coming back rather than by a
  command.
- The state after a dropout is read once the supply is valid again and
  the declared settling time has elapsed. Reading it earlier samples the
  transient rather than the state the unit settled into.
- The supply floor, the zero volt threshold, the default state and the
  settling time are declared unit and project data, not physical
  constants, so they are stated with the result.
- Both the floor and the zero volt threshold are compared against a
  measured voltage. A sample cut exactly to either one can evaluate a
  unit in the last place across it, so the comparison carries a named
  tolerance instead of the limit being moved.

## Workflow

1. Take the recorded profile: one sample per instant carrying the bus
   voltage, the intended state, the state the limiter output was in, and
   the status the unit reported. Refuse a profile whose timestamps do not
   strictly increase, because the order is what every later step reads.
2. Refuse a zero volt threshold that is not below the logic supply floor;
   the two would otherwise describe the same boundary and the recovery
   check would have nothing to observe.
3. Mark each sample as inside or outside the supply window, comparing the
   bus voltage with the floor through the named tolerance.
4. Find the zero volt excursions as contiguous runs at or under the
   threshold, collapsing a multi-sample dropout into one event and
   keeping a run that is still open at the end of the record.
5. Inside the window, take the two readings per sample: intended against
   actual, and reported against actual. Record an absent status as
   unreported rather than as agreement.
6. For each excursion, find the first sample that is both past the
   settling time and inside the supply window, and require the default
   state there. Report an excursion with no such sample as not observed.
7. Roll up: the mismatches, the status disagreements, the unreported
   samples, the recovery verdicts, and the coverage finding for a profile
   that never woke the unit.

## Pitfalls

- Reading the status line as the state. The whole point of the clause is
  that the two can differ, so a check that compares intended against
  reported and never against actual cannot see the failure it exists to
  find.
- Counting a below-floor sample as agreement. An unpowered unit agrees
  with everything, and a profile made mostly of dead bus then reports a
  high agreement rate that means nothing.
- Treating a dropout as a gap in one start up. The recovery afterwards is
  a cold start, and the default state is what it has to come back in, not
  whatever state it held before the bus fell.
- Sampling the recovered state immediately after the bus returns. The
  output is still moving, so the reading describes the transient rather
  than the state the unit settled into, and a settling time is what
  separates them.
- Reporting a clean profile that never reached the supply floor as a
  pass. Nothing was exercised, and an empty result is indistinguishable
  from a good one once it is in the file.
- Comparing the bus voltage with the supply floor or the zero volt
  threshold by bare arithmetic. Both limits sit on measured quantities,
  so a sample cut exactly to one can be grouped inside the window on one
  platform and outside it on another.

## Behavior contract (gate 3)

The profile validation with its strict time ordering, the state alias
folding, the supply window with its named voltage tolerance, the zero
volt excursion runs including one left open at the end of the record, the
per-sample state and status verdicts with indeterminate and unreported as
distinct outcomes, the settling-time recovery observation and its
not-observed route, the threshold-below-floor refusal and the never-woke
coverage finding are exercised by the gate 3 contract test:
scripts/test_e2020_status_integrity_during_bus_startup.py against
scripts/e2020_status_integrity_during_bus_startup_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_status_integrity_during_bus_startup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
