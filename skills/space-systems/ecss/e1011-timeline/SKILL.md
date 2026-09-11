---
name: e1011-timeline
description: "Use when build the operations timeline for a human-rated space system per ECSS-E-ST-10-11C §4.9.3: sequence each crew task in a phased timeline, compute the time-averaged workload index for each hourly assessment window, verify no window exceeds the maximum allowable workload level, confirm mandatory rest gaps are preserved between consecutive high-demand activity clusters, and check that concurrent task counts remain within the cognitive limit specified by the HFE requirement. Trigger: ecss, e-st-10-system-scope, operations-timeline, crew-workload, workload-index, human-factors, task-sequencing, rest-period, concurrent-tasks."
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
  tags: [ecss, e-st-10-system-scope, operations-timeline, crew-workload, workload-index, human-factors, task-sequencing, rest-period, concurrent-tasks]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Operations Timeline (space-systems/ecss/e1011-timeline)

Use when build the operations timeline for a human-rated space system per
ECSS-E-ST-10-11C §4.9.3 -- sequencing crew tasks in a phased timeline,
computing the hourly workload index for each assessment window, checking
every window against the maximum allowable workload level, verifying
mandatory rest gaps between high-demand clusters, and confirming concurrent
task counts remain within the HFE cognitive limit.

## Domain quick reference

- Each crew activity in the mission phase is assigned a task ID, start
  time (minutes from the phase epoch), duration, and one of three workload
  levels: low (routine monitoring), medium (active procedure execution), or
  high (emergency response or complex multi-step operations). Workload level
  maps to a numeric value (low = 1, medium = 2, high = 3) used in index
  computation. An unrecognized level is a structural error that must be
  resolved before workload analysis proceeds.
- The time-averaged workload index for an assessment window is the sum of
  (workload_value × fraction_of_window_occupied) for all tasks active within
  that window. A window is typically one crew-hour. The index must not exceed
  the maximum allowable value (equivalent to one sustained high-level task)
  in any window; two concurrent high-level tasks push the index to 6, which
  always violates the limit.
- The concurrent task count at any instant must not exceed the cognitive
  limit drawn from the HFE requirement (typically three simultaneous tasks
  per crew member). The check fires at every task start and end event, not
  just at window boundaries; off-boundary violations are a common miss.
- After any cluster of consecutive high-demand assessment windows (index
  exceeding the high-demand threshold), a minimum rest gap must separate
  that cluster from the next. The gap is measured from the end of the last
  high-demand window in the first cluster to the start of the first
  high-demand window in the next cluster. A crew changeover or short
  procedure break shorter than the minimum does not satisfy the rest
  requirement.

## Workflow

1. Collect all crew tasks for the mission phase. For each task record: a
   unique task ID, a short description, start time in minutes from the phase
   epoch (non-negative integer), duration in minutes (positive integer),
   workload level (low / medium / high), and required crew count (≥ 1).
   Reject any task entry that fails these structural checks before proceeding
   to workload analysis.
2. Slide a one-hour assessment window across the full timeline span in
   60-minute steps. For each window compute the time-averaged workload index
   (sum of workload_value × overlap_minutes for all tasks in the window,
   divided by window duration in minutes). Flag any window where the index
   exceeds the maximum allowable workload level.
3. Perform an event-sweep at every task start and end instant. Maintain an
   active-task count: increment on task start, decrement on task end. When
   a task starts, if the resulting count exceeds the cognitive limit, record
   a concurrent-task violation. Tasks ending and tasks starting at the same
   minute are ordered so ends are processed before starts, preventing a
   spurious violation when one task replaces another exactly.
4. Identify all high-demand windows (index exceeds the high-demand
   threshold) and group consecutive windows into clusters. For each pair of
   adjacent clusters measure the inter-cluster gap in minutes. Flag any gap
   shorter than the minimum required rest duration.
5. Aggregate all findings from steps 1 through 4. The timeline is
   workload-compliant only when all three finding lists are empty:
   structural errors, workload exceedances, concurrent-task violations, and
   rest-gap shortfalls.

## Pitfalls

- Applying task workload values as peak loads rather than time-weighted
  contributions — a high-level task occupying only half a window contributes
  index 1.5, not 3.0; sum the weighted products, do not take the window
  maximum.
- Treating a gap between tasks as a rest period without verifying its
  duration meets the minimum — procedure transitions and tool changeovers
  are not rest periods and must not be counted toward the rest requirement.
- Omitting low-workload tasks from the timeline on the assumption they have
  no effect — even low-level tasks accumulate when many are concurrent; a
  cluster of three simultaneous low-level tasks produces an index of 3,
  equal to one sustained high-level task, and all three count against the
  concurrent-task limit.
- Checking concurrent-task count only at window boundaries and missing
  intra-window spikes — the event-sweep must fire at each exact task
  start/end minute to catch violations that open and close within a window.

## Behavior contract (gate 3)

The task-entry validation, workload-index computation, concurrent-task
event-sweep, and rest-gap cluster check are exercised by the gate 3
contract test: scripts/test_e1011_timeline.py against
scripts/e1011_timeline_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_timeline.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
