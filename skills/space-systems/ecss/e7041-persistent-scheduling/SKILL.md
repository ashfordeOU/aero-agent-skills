---
name: e7041-persistent-scheduling
description: "Determine how a position-based schedule behaves across successive orbits under ECSS-E-ST-70-41C clause 6.22.5: separate the persistent activities that re-arm on a later orbit from the one-shot activities the schedule consumes at release, project every release over an orbit sweep, and report the entries that remain. Use when persistent position-based activities, a re-arming orbit interval, a repeat limit, residual schedule occupancy or an activity that never fires inside the planned orbits is being specified or reviewed. Refuses a zero orbit interval and a one-shot entry declaring repeats. Trigger: ecss, e-st-70-41c, pus-service-22, persistent-position-based-activity, activity-re-arming-orbit-interval, one-shot-schedule-entry, orbit-sweep-release-projection, residual-schedule-occupancy."
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
  tags: [ecss, e-st-70-41c, pus-service-22, e7041-persistent-scheduling, persistent-position-based-activity, activity-re-arming-orbit-interval, one-shot-schedule-entry, orbit-sweep-release-projection, residual-schedule-occupancy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Position-Based Scheduling — Persistent Scheduling (space-systems/ecss/e7041-persistent-scheduling)

Use when the task is the persistent scheduling capability of
ECSS-E-ST-70-41C clause 6.22.5 — deciding which position-based activities
survive their own release, how often they re-arm, and what the schedule still
holds once a planned run of orbits has been flown.

## Domain quick reference

- Persistence is a property of the entry, not of the schedule. The same
  schedule carries entries the release consumes and entries the release
  re-arms, and a design that treats the whole schedule as one or the other
  either loses a repeating activity or never frees a slot.
- A persistent entry needs an orbit interval. Re-arming for the next orbit is
  only the default; an activity wanted every third orbit is a different entry
  from one wanted every orbit, and the interval is what distinguishes them.
- A repeat limit and an unlimited entry behave differently at the end of the
  sweep. A limited entry leaves the schedule once it has fired its last time,
  an unlimited one never does, and the residual occupancy is the difference.
- The sweep is a window, not the mission. An entry whose first orbit is past
  the window never fires inside it and stays in the schedule; an entry whose
  interval is longer than the window fires once and looks one-shot without
  being one.
- Occupancy is the thing that runs out. Slots are finite, so the useful
  answer is not only which activities fire but how many entries the schedule
  is still holding when the window closes.
- A one-shot entry declaring a repeat count is a contradiction in the load,
  not a default to be resolved quietly. The two fields disagree about what
  the entry is, and the load is the place to say so.

## Workflow

1. Validate each activity: a unique request identifier, a whole non-negative
   first orbit, an angle inside one revolution from the ascending node, and a
   boolean persistence flag.
2. Resolve the repeat fields against the persistence flag; a persistent entry
   takes a positive orbit interval and a repeat limit, a one-shot entry takes
   neither and refuses both.
3. Order the loaded schedule by first orbit, then angle, then identifier, so
   the projection is reproducible.
4. Project each entry's releases across the orbit sweep, stopping a limited
   entry once it has fired its declared number of times.
5. Compute the residual schedule: entries not yet consumed, entries whose
   repeat limit the sweep did not exhaust, and every unlimited entry.
6. Report the releases per entry, the total, the residual occupancy and the
   findings: an entry that never fires inside the sweep and an interval
   longer than the sweep itself.

## Pitfalls

- Treating every entry as persistent because the schedule is. Slots then
  never free, the schedule fills, and the next insertion is refused for a
  reason nothing in the design predicts.
- Defaulting a persistent entry to every orbit without saying so. An activity
  meant for one orbit in ten then runs ten times as often, and the first
  symptom is a power or duty-cycle budget overrun, not a scheduling error.
- Counting releases without counting the residual. The sweep can look
  perfectly healthy while the schedule quietly retains every entry it started
  with.
- Reading an entry that fires once inside the window as one-shot. Its
  interval may simply be longer than the window, and deleting it on that
  reading removes an activity that was due on a later orbit.
- Resolving a one-shot entry that declares repeats by ignoring one of the two
  fields. Whichever field is ignored, the schedule executes something other
  than what was uplinked.

## Behavior contract (gate 3)

The activity validation, persistence resolution, schedule ordering, release
projection with interval and repeat limit, residual occupancy and the
assembled orbit-sweep projection are exercised by the gate 3 contract test:
scripts/test_e7041_persistent_scheduling.py against
scripts/e7041_persistent_scheduling_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_persistent_scheduling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
