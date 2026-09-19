---
name: e4008-activity
description: "Audit the activities inside an SMP schedule task against ECSS-E-ST-40-08C clause 5.4.5 and the fourteen normative items that clause places on them. Use when a schedule has to be resolved against the assembled model rather than read on its own: giving each activity one declared kind carrying only its own payload and a name unique in its task, resolving the instance path, checking an entry point exists and takes no arguments, checking a field exists, is writable and receives a value of the declared type inside its range, checking an emitted event exists, and reporting activities that advance simulated time or write one field twice. Trigger: ecss, e-st-40-08-simulation-modelling-scope, e4008-activity, schedule-activity-kinds, activity-entry-point-invocation, activity-field-assignment, activity-event-emission, activity-write-order-hazard."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-activity, schedule-activity-kinds, activity-entry-point-invocation, activity-field-assignment, activity-event-emission, activity-write-order-hazard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling — Schedule Activity (space-systems/ecss/e4008-activity)

Use when the task is the schedule activity of ECSS-E-ST-40-08C clause
5.4.5 -- the smallest thing a schedule does, reaching into the
assembled model to call an entry point, write a field or emit an
event, and the fourteen normative items that fix what one may be.

## Domain quick reference

- An activity is the only place the schedule touches the model.
  Everything above it -- entries, tasks, time scales -- decides when;
  the activity decides what, and it is the only part that can name
  something the model does not have.
- It is therefore resolved against two artefacts at once. Read on its
  own an activity is almost always well formed; read against the
  assembly and its catalogue, most defects become visible.
- An activity carries exactly one kind. The kind decides which
  payload it is allowed to hold, so a field name sitting on an
  entry-point activity is not extra information, it is a symptom of
  an activity edited from one kind into another.
- An entry point is a no-argument call by construction. An activity
  that supplies arguments has been written against an operation, not
  an entry point, and truncating the arguments silently would run
  something different from what was asked.
- A field assignment has to clear four separate gates in order: the
  field is declared, it is writable, the value is of the declared
  type, and the value is inside the admissible range. Each failure
  points at a different edit, so they are reported separately.
- Range is not only the explicit bounds. The declared integer type
  has a width, and a value that overflows it is out of range even
  where no minimum or maximum was written down.
- Activities take no simulated time. One that declares a duration or
  blocks breaks the atomicity of the task it sits in, which is
  visible only as another task running at a time the schedule never
  declared.
- Order matters where two activities touch the same field. The later
  write wins, so the sequence is doing something the reader has to
  intend rather than discover.

## Workflow

1. Validate the assembled model first -- every instance names a
   declared type, every field a known type, every declared range
   the right way round. A malformed model raises rather than
   producing findings against the schedule.
2. Check the activity's own shape: a name, exactly one declared
   kind, the payload that kind requires, and no payload belonging to
   another kind.
3. Check atomicity before resolving anything, since a duration or a
   blocking flag is a finding regardless of what the activity points
   at.
4. Resolve the instance path. Everything after this depends on it,
   so an unresolved path closes the activity out with that one
   finding rather than cascading.
5. Apply the kind-specific checks: entry point declared and given no
   arguments; field declared, writable, typed and in range, in that
   order; event declared on the type.
6. Over a whole sequence, add the two checks no single activity can
   make: a name repeated inside one task, and the same field written
   more than once, reporting the positions so the reader can see
   which write survives.

## Pitfalls

- Grading an activity against the schedule alone. Every
  instance-path, entry-point, field and event finding needs the
  model, and a schedule-only check passes artefacts that cannot be
  loaded.
- Accepting an entry-point activity that carries arguments. It was
  written against an operation, and dropping the arguments runs a
  call the author did not write.
- Collapsing the four field gates into one finding. Declared,
  writable, typed and in range are four different edits, and a
  single not-settable message sends the reader to the wrong one.
- Checking only the explicit minimum and maximum. The declared
  integer type carries its own width, so a value that overflows it
  passes a bounds-only check and wraps at load.
- Comparing a float value with its declared bound by bare strict
  inequality. A value meant to sit exactly on the bound can land a
  few units in the last place outside it, and the schedule is
  rejected for a value that was correct.
- Treating two writes to one field as redundancy. The later write
  wins, so the pair is either a deliberate sequence or a merge
  accident, and only the positions in the report tell them apart.
- Letting an unresolved instance path cascade into a field or entry
  point finding. There is no type to check against, and the extra
  findings hide the single edit that fixes all of them.

## Behavior contract (gate 3)

The model validation, kind and payload exclusivity, name uniqueness
within a task, instance-path resolution, entry-point existence and
no-argument rule, the ordered field gates with type-width and declared
range, event existence, the atomicity checks and the repeated-write
order hazard are exercised by the gate 3 contract test:
scripts/test_e4008_activity.py against
scripts/e4008_activity_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_activity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
