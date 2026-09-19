---
name: e4008-mission-start
description: "Derive the mission time scale from a declared mission start under ECSS-E-ST-40-08C clause 5.4.2, the single normative item that clause places on the instant mission time is measured from. Use when a schedule is written on the operational timeline rather than on run time: mapping mission time onto simulation time through mission start and the epoch at simulation zero, keeping a negative mission time legal so pre-separation activities survive, holding both scales in exact integer nanoseconds, and deciding whether a second declaration is unchanged, a restatement whose shift moves every entry, or refused because the simulator is already executing. Trigger: ecss, e-st-40-08-simulation-modelling-scope, e4008-mission-start, mission-time-scale, mission-start-declaration, negative-mission-time, mission-start-restatement-shift."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-mission-start, mission-time-scale, mission-start-declaration, negative-mission-time, mission-start-restatement-shift]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling — Mission Start (space-systems/ecss/e4008-mission-start)

Use when the task is mission start under ECSS-E-ST-40-08C clause
5.4.2 -- the single instant that creates the mission time scale, and
the one normative item fixing how a schedule entry written on that
scale becomes a simulation time.

## Domain quick reference

- Three scales are in play and only one of them counts from the start
  of the run. Simulation time counts from run start, epoch time is
  absolute, and mission time counts from mission start. The whole
  clause is the one line that joins them: simulation time equals
  mission time plus mission start minus the epoch at simulation zero.
- Mission time is the scale an operational timeline is written on,
  which is why it exists at all. A flight procedure says two minutes
  after separation, not eleven minutes into the simulation run.
- Negative mission time is legal and load-bearing. Everything before
  separation -- arming, pre-heating, final checks -- sits on the
  negative side, and a check that refuses a negative value deletes
  exactly the entries an operator most wants rehearsed.
- Both scales stay in integer nanoseconds. A double stops holding
  every integer well inside a mission expressed in nanoseconds, so a
  float value is refused rather than quietly rounded.
- Mission start is declared once. A second declaration is not
  automatically wrong, but it is never silent: repeating the same
  instant is a no-op worth naming, and a different instant shifts
  every mission-time entry in the schedule by the same amount.
- A move while the simulator is executing is refused. Entries already
  dispatched cannot be recalled, so the shift would apply to only
  part of the schedule and leave the timeline internally
  inconsistent.
- The interesting consequence of a shift is not the new times but
  which entries crossed the clock. An entry that was due and is now
  in the past will never run, and that list is the reason to report a
  restatement rather than apply it.

## Workflow

1. Validate mission start and the epoch at simulation zero as exact
   integer nanosecond counts, refusing a float and refusing a boolean.
2. Compute mission start on the simulation scale once; every entry
   mapping is that offset plus the entry's mission time.
3. Map each entry, keeping negative mission times and marking them as
   pre-mission-start rather than filtering them out.
4. Order the resolved entries by simulation time and break ties by
   declared order, so a schedule that was not edited does not change
   execution order.
5. On a second declaration, decide before applying: unchanged,
   restated with a reported shift, or refused because the simulator
   is executing.
6. Where a restatement is taken, resolve the schedule on both the old
   and the new mission start and report which entries crossed the
   current simulation time, because those are the ones that will
   silently never run.

## Pitfalls

- Refusing or clamping a negative mission time. Pre-separation
  activities are exactly the entries that live there, and clamping
  them to zero stacks them all onto mission start.
- Holding mission time in a float. The error is invisible in a unit
  test written in seconds and grows to whole nanoseconds and beyond
  over a real mission length.
- Applying a mission start change silently. Every mission-time entry
  moves at once, the schedule stays internally consistent, and the
  only symptom is that the run no longer matches the timeline it was
  written against.
- Allowing a mission start change while the simulator is executing.
  Entries already dispatched cannot be moved, so half the schedule
  shifts and half does not.
- Reporting a restatement by its new times alone. The operationally
  important output is the list of entries that crossed the clock,
  since those disappear from the run without any error.
- Ordering tied entries by name. Two entries at the same mission time
  keep their declared order; a name sort reorders a schedule nobody
  touched.

## Behavior contract (gate 3)

The nanosecond validation, mission-start offset, mission-to-simulation
and mission-to-epoch mappings with their exact inverse, the
negative-mission-time handling, the declaration decision across
simulator states and the restatement shift with its crossed-the-clock
list are exercised by the gate 3 contract test:
scripts/test_e4008_mission_start.py against
scripts/e4008_mission_start_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_mission_start.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
