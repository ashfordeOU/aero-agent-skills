---
name: e4008-epoch-time
description: "Convert an epoch-scale schedule entry onto simulation time under ECSS-E-ST-40-08C clause 5.4.1, the single normative item that clause places on an entry written at an absolute instant. Use when a schedule mixes epoch instants with simulation-time offsets and the simulator has to decide when each entry actually fires: subtracting the declared epoch at simulation time zero, refusing a float nanosecond count and an undeclared epoch reference, keeping the conversion exactly reversible, reporting an instant the run has already passed instead of dropping it, and stepping a repeating entry to its first occurrence at or after the resolution instant. Trigger: ecss, e-st-40-08-simulation-modelling-scope, e4008-epoch-time, schedule-epoch-time-entry, epoch-to-simulation-time-conversion, epoch-reference-declaration, epoch-entry-already-past, epoch-entry-repeat-period."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-epoch-time, schedule-epoch-time-entry, epoch-to-simulation-time-conversion, epoch-reference-declaration, epoch-entry-already-past, epoch-entry-repeat-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling — Epoch Time (space-systems/ecss/e4008-epoch-time)

Use when the task is the epoch time scale of ECSS-E-ST-40-08C clause
5.4.1 -- a schedule entry that names the absolute instant it is due
at, rather than an offset from the start of the run, and the one
normative item that fixes how the simulator resolves it.

## Domain quick reference

- Simulation time counts from the start of the run. Epoch time names
  an instant on an absolute scale. An entry on the epoch scale is
  resolved by subtracting the epoch value that corresponds to
  simulation time zero, and nothing else about it changes.
- The arithmetic is trivial and the failures are not. Every way this
  goes wrong is a declaration or a representation problem, which is
  why the clause exists at all.
- Both scales are integer nanoseconds. A double holds every integer
  only up to about nine quadrillion, which a mission-length interval
  in nanoseconds passes, so a float instant is refused rather than
  rounded into something that looks fine.
- The epoch at simulation time zero has to be declared. Treating an
  absent reference as zero does not fail; it silently shifts every
  entry in the schedule by the whole mission epoch, and the run looks
  plausible throughout.
- The conversion is exact and reversible. A resolved entry can always
  be restated on the scale it was written on, which is what lets an
  operator check a schedule against the mission timeline it came
  from.
- An instant already in the past is a finding, not a nuisance. It is
  the usual symptom of a schedule written against the wrong epoch,
  and silently discarding it removes the only evidence.
- A repeating entry is different from a single-shot one here. The
  single shot is gone once its instant has passed; the repeater steps
  forward whole periods to the first occurrence at or after the
  instant the schedule is being resolved for.

## Workflow

1. Validate both instants as exact integer nanosecond counts inside
   the 64-bit range, refusing a float and refusing a boolean, which
   Python would otherwise widen into a zero or a one.
2. Refuse the conversion outright when the epoch at simulation time
   zero has not been declared, rather than defaulting it.
3. Subtract to get the base simulation time, guarding the result
   against overflow of the nanosecond range.
4. Record the declared disposition of that base time against the
   clock now -- in the future, exactly now, or already past -- and
   raise a finding for the past case before any repeat handling.
5. Resolve the occurrence that will actually run: the base time for a
   single shot that has not passed, or the base stepped forward by
   whole periods for a repeater, using integer arithmetic so the
   result is exact on every platform.
6. Order a set of entries by occurrence, break ties by declared
   order, name the entries with no occurrence left rather than
   dropping them silently, and close with the findings.

## Pitfalls

- Holding either scale in a float. Nanoseconds over a mission exceed
  what a double represents exactly, so the entry drifts by a margin
  that grows with the mission and no test at small numbers sees it.
- Defaulting an undeclared epoch reference to zero. Every entry moves
  by the mission epoch at once, so the schedule stays internally
  consistent and looks correct until it is compared with an external
  timeline.
- Discarding an entry whose instant has already passed. The schedule
  then resolves clean against the wrong epoch, and the missing entry
  is only noticed when the event it was supposed to trigger does not
  happen.
- Treating a repeating entry like a single shot. It is not gone once
  its base instant passes; it has a next occurrence, and dropping it
  removes a periodic activity from the whole run.
- Computing the step count for a repeater in floating point. The
  division lands a hair either side of a whole number on different
  platforms, so the occurrence jumps a full period depending on where
  it ran.
- Ordering tied entries by name. Two entries due at the same instant
  keep their declared order; sorting them by name changes the
  execution order of a schedule that was never edited.

## Behavior contract (gate 3)

The nanosecond validation, epoch-to-simulation conversion and its
exact inverse, the overflow guard, the already-past disposition, the
integer repeat-period stepping and the tie-stable occurrence ordering
are exercised by the gate 3 contract test:
scripts/test_e4008_epoch_time.py against
scripts/e4008_epoch_time_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_epoch_time.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
