---
name: e7041-controlling-the-position-based-schedule-execution
description: "Evaluate the execution function of a position-based schedule under ECSS-E-ST-70-41C clause 6.22.6.3: run enable, disable and reset control commands against the subservice state, advance the reported orbit position, and decide which held activities the function releases and which it flies past. Use when enabling or disabling position-based schedule execution, resetting the schedule, reporting the execution status, or the disposition of activities that came due while the function was disabled is being specified or reviewed. Refuses an unknown command and a backwards position advance. Trigger: ecss, e-st-70-41c, pus-service-22, position-based-schedule-execution-function, schedule-execution-enable, schedule-execution-disable, position-based-schedule-reset, missed-activity-disposition."
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
  tags: [ecss, e-st-70-41c, pus-service-22, e7041-controlling-the-position-based-schedule-execution, position-based-schedule-execution-function, schedule-execution-enable, schedule-execution-disable, position-based-schedule-reset, missed-activity-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Position-Based Scheduling — Controlling the Execution Function (space-systems/ecss/e7041-controlling-the-position-based-schedule-execution)

Use when the task is the execution control of ECSS-E-ST-70-41C clause
6.22.6.3 — enabling, disabling and resetting the function that releases
position-based activities, and working out what the schedule actually does
as the spacecraft flies past the positions it holds.

## Domain quick reference

- Enabling is separate from holding. The schedule keeps its entries whether
  the function is enabled or not, so disabling stops releases without
  emptying the store and a design that conflates the two loses the schedule
  every time the function is turned off.
- Reset empties the store and leaves the enable state alone. An enabled
  function after a reset is an armed function with nothing to release, which
  is a legitimate state and worth reporting as one.
- Release is decided at an orbit position, not at a time. An activity is due
  once the reported position reaches or passes the position it was pinned
  to, and the comparison has to weigh the orbit number and the angle
  together.
- The reported position only moves forward. An advance that goes backwards
  is a position report error or an orbit counter change, and it belongs to a
  different command than this one.
- Activities that came due while the function was disabled are the whole
  design question. They were not released and they are now behind the
  spacecraft, so either they are dropped or they fire late and out of
  position, and both answers have consequences the ground has to know.
- A release consumes the entry. An activity released once is out of the
  store, so a second advance past the same position releases nothing, and a
  function that re-releases is scheduling the same activity twice.

## Workflow

1. Validate the state: a boolean enable flag, activities with unique
   identifiers pinned to whole orbit numbers and angles inside one
   revolution, and a starting orbit position.
2. Order the held activities by orbit position so the release decision reads
   them front to back.
3. Apply each control command in turn against the state the previous command
   left: enable, disable, reset, or advance the reported position.
4. On an advance, collect the held activities at or behind the new position.
   If the function is enabled, release them and remove them from the store.
5. If the function is disabled, record them as missed and apply the declared
   disposition: discard them, or keep them for a late release that will fire
   out of position.
6. Report the final enable state, the reported position, the pending
   activities, the releases, the missed set and the findings the run earned.

## Pitfalls

- Emptying the schedule on disable. The operator expected a pause and gets a
  wipe, and every activity uplinked for the rest of the orbit is gone.
- Deciding release on the angle alone. An activity pinned to the next orbit
  releases on this one, a whole revolution early.
- Leaving a released activity in the store. The next advance finds it due
  again and releases it a second time, which for a thruster or a deployment
  is not a reporting defect.
- Silently discarding the activities a disabled function flew past. The
  ground sees a clean status and never learns that the pass it planned did
  not happen.
- Choosing late release without saying what it costs. The activity fires at
  a position it was never designed for, and a pointing or illumination
  assumption behind it no longer holds.
- Treating reset as a disable. The enable state survives a reset, so a
  function reset while enabled starts releasing the moment anything is
  inserted.

## Behavior contract (gate 3)

The state validation, position folding, due-activity selection, the enable,
disable, reset and advance commands, the missed-activity dispositions and
the assembled control run report are exercised by the gate 3 contract test:
scripts/test_e7041_controlling_the_position_based_schedule_execution.py
against
scripts/e7041_controlling_the_position_based_schedule_execution_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_controlling_the_position_based_schedule_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
