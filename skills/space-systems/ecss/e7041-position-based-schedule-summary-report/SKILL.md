---
name: e7041-position-based-schedule-summary-report
description: "Generate the summary report of a position-based schedule under ECSS-E-ST-70-41C clause 6.22.9.1: carry one entry per scheduled activity holding its request identification, its orbit position and its scheduling group while leaving the request content out, select the reported subset by group or by an orbit position window that may wrap through the origin, and order the entries by increasing position with the identification as the tie break. Use when the content, ordering or subset selection of a position-based schedule summary report is being designed or reviewed. Refuses a duplicate identification and a position off the revolution. Trigger: ecss, e-st-70-41c, pus-service-22, position-based-schedule-summary-report, scheduled-request-identification, orbit-position-window, summary-entry-ordering, scheduling-group-selection."
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
  tags: [ecss, e-st-70-41c-scope, e7041-position-based-schedule-summary-report, pus-service-22, position-based-schedule-summary, orbit-position-window, summary-entry-ordering, scheduled-request-identification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PUS Position-Based Scheduling — Summary Report (space-systems/ecss/e7041-position-based-schedule-summary-report)

Use when the task is the summary report of the position-based schedule of
ECSS-E-ST-70-41C clause 6.22.9.1 — deciding what one entry of the report
holds, which scheduled activities the report covers, and in what order
they come out.

## Domain quick reference

- A summary entry identifies a scheduled request and says where on the
  orbit it sits. It carries the request identification, the orbit
  position and the scheduling group, and it does not carry the request
  itself. Leaving the request out is the whole difference between this
  report and the detail report of the neighbouring clause, and it is
  what keeps a summary of a full schedule small enough to downlink in
  one go.
- The request identification is the packet identification of the
  scheduled request: the source, the application process and the
  sequence count. It is the handle every later command uses, so the same
  identification must not sit on two activities of one schedule.
- The orbit position axis is a closed revolution, held here as the
  half-open span from the origin up to but not including a full turn. A
  position window whose start is above its end therefore wraps through
  the origin and selects the two arcs either side of it, not the empty
  set and not the complement.
- The report order is positional, not insertion order: entries come out
  by increasing orbit position, with the identification breaking a tie
  so two activities at one position always report in the same order.
- Selecting a subset is a filter on the report, not on the schedule. The
  entry count of the report and the size of the schedule it was drawn
  from are separate numbers and both belong in the answer.

## Workflow

1. Validate every activity: the identification fields against their
   packet field widths, the orbit position against the revolution, and
   the scheduling group as a positive identifier.
2. Reduce each activity to its summary entry, dropping the request
   content rather than copying it, so an entry cannot leak the request
   by accident.
3. Refuse a schedule that carries one identification twice; the later
   command surface has no way to address the second one.
4. Apply the requested selection: a set of scheduling groups, an orbit
   position window, or both. Evaluate the window with a wrap-aware
   containment test and absorb the edge with a named tolerance rather
   than by widening the bounds.
5. Order the surviving entries by increasing orbit position, breaking
   ties on the identification.
6. Size the report from the entry count when the layout is known, and
   report the entry count, the schedule size, the first and last
   positions, and any finding: an empty selection, a wrapping window, or
   selected activities with no group.

## Pitfalls

- Copying the request into a summary entry. It makes the report grow
  with the request content, defeats the point of having two report
  clauses, and is the defect that turns a one-packet summary into a
  packetisation problem.
- Treating a wrapping window as invalid or as empty. A window from just
  before the origin to just after it is the normal way to ask about the
  arc that spans it, and dropping it silently reports an empty schedule
  for a populated one.
- Excluding a position that lands exactly on a window bound. The bound
  is inclusive and the comparison absorbs representation error with a
  tolerance; tightening the bound instead loses a genuine entry.
- Reporting in insertion order. Two ground runs then produce two orders
  for one schedule, and a diff of the two reports shows changes that
  are not there.
- Reporting the selected count as the schedule size. A group filtered
  summary covers part of the schedule; conflating the two understates
  what is actually loaded on board.

## Behavior contract (gate 3)

The position and identification validation, summary entry reduction,
wrap-aware window containment, group selection, positional ordering and
report sizing are exercised by the gate 3 contract test:
scripts/test_e7041_position_based_schedule_summary_report.py against
scripts/e7041_position_based_schedule_summary_report_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_position_based_schedule_summary_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
