---
name: e7041-tracing
description: "Evaluate the trace an OBCP engine keeps of a procedure's execution, under ECSS-E-ST-70-41C clause 6.18.4.8. Use when a retrieved trace cannot account for what a procedure did, or when a long run comes back with only its last few records: applying the configured granularity as the filter that fixes which execution events are recordable at all, fitting the records into a bounded buffer under a drop-oldest or stop-at-the-brim policy, separating a trace switched on mid-run from one that covers the whole run, computing coverage against the events offered, and deciding whether what survived can be read as a contiguous sequence. Trigger: ecss, e-st-70-41c, obcp-execution-tracing, obcp-trace-granularity-filter, obcp-trace-buffer-overflow-policy, obcp-mid-run-trace-enable, obcp-trace-reconstructability, obcp-trace-coverage."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-tracing, obcp-execution-tracing, obcp-trace-granularity-filter, obcp-trace-buffer-overflow-policy, obcp-mid-run-trace-enable, obcp-trace-reconstructability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Tracing an OBCP Execution (space-systems/ecss/e7041-tracing)

Use when the task is the execution tracing of ECSS-E-ST-70-41C clause
6.18.4.8 -- the nine requirements that say what the engine records
about a running on-board control procedure, how that recording is
switched and bounded, and therefore what the ground can prove
afterwards about the run.

## Domain quick reference

- Tracing is per procedure and switchable, not a property of the
  engine. Two procedures running side by side can have different trace
  settings, and a trace is evidence only about the procedure whose
  setting was on.
- Switching tracing on while a procedure is already running gives a
  trace that begins in the middle of the run. Nothing about the
  records themselves says so; the first record simply looks like a
  first step. The switch-on point is part of the trace, not metadata
  to be dropped on retrieval.
- Granularity is a filter, not a volume control. Execution events
  carry a level -- the procedure entering and leaving, a block being
  entered, a single step running -- and a coarse setting omits the
  finer events entirely. The question a trace can answer is fixed when
  it is configured, not when it is read.
- The buffer is finite and a long run meets it in one of two ways.
  Dropping the oldest records keeps the end of the run and loses the
  beginning; stopping at the brim keeps the beginning and loses the
  end. Both lose events; they lose opposite ones, and only stopping
  leaves the retained portion contiguous with the run's start.
- Coverage and reconstructability are different questions. A trace can
  hold most of the run and still be unreadable as a sequence if the
  hole is in the middle; a trace can hold a small contiguous prefix
  and answer a question about the start exactly.
- Record times come from the on-board clock and are expected to be
  non-decreasing. A record whose time sits before the one ahead of it
  is a clock correction during the run, and every duration computed
  across that point is wrong.
- A trace configured for a procedure that is not loaded records
  nothing and reports nothing. The configuration looks healthy in the
  management telemetry, which is what makes it worth checking.

## Workflow

1. Normalise the configuration: a procedure identifier, the on or off
   switch, a granularity from the permitted levels, a buffer capacity
   of at least one record, and an overflow policy.
2. Return the tracing-off result immediately when the switch is off --
   an empty trace with the reason stated, never an empty trace whose
   reason has to be inferred.
3. Filter the run's events by granularity, and count what the
   granularity omitted so the omission is reported rather than
   invisible.
4. Drop the events ahead of the switch-on index, and report a
   mid-run start as a finding on the trace.
5. Walk the admitted events and raise a finding on any record time
   that sits before its predecessor.
6. Fit the records into the buffer under the configured policy,
   recording how many were lost and which end of the run went.
7. Number the surviving records in order, keeping each event's index
   in the original run so a hole can be detected later.
8. Report coverage against the events offered, and decide
   reconstructability separately: the trace starts at the run's first
   event, ends at its last, and has no gap between them.
9. Check the configured procedure against the loaded set, so a trace
   configured for something that is not there is named.

## Pitfalls

- Reading a mid-run trace as a whole run. The first record becomes the
  first step, and every conclusion about what the procedure did before
  it is wrong by omission.
- Treating coverage as reconstructability. Seventy per cent of the
  records with a hole in the middle cannot be read as a sequence; a
  contiguous thirty per cent can.
- Raising the granularity to fix a trace that is losing records. A
  finer setting offers more events to the same buffer and loses more
  of them.
- Assuming drop-oldest and stop-at-the-brim differ only in which
  records survive. They differ in which question survives: one keeps
  the anomaly at the end, the other keeps the set-up at the start.
- Ignoring a backwards record time because the records are still in
  order. The order is the arrival order; the times are what durations
  are computed from.
- Confirming tracing from the configuration alone. A configuration for
  an unloaded procedure looks identical to a working one.

## Behavior contract (gate 3)

The configuration normalisation, capacity and policy validation,
granularity filtering with an omission count, mid-run switch-on
reporting, backwards-time finding, drop-oldest and stop-at-the-brim
buffer fitting, loss counting, coverage computation,
reconstructability decision and the unloaded-procedure check are
exercised by the gate 3 contract test: scripts/test_e7041_tracing.py
against scripts/e7041_tracing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_tracing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
