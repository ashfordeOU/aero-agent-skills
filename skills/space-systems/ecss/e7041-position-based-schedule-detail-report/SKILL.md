---
name: e7041-position-based-schedule-detail-report
description: "Build the detail report of a position-based schedule under ECSS-E-ST-70-41C clause 6.22.9.2: size each entry from the request content it carries, select the reported subset by identification, by scheduling group or by an orbit position window that may wrap, order the entries by increasing position, and pack them into as few report packets as the telemetry limit allows without ever splitting one activity across packets. Use when the content, packetisation or subset selection of a position-based schedule detail report is being designed or reviewed. Refuses an activity whose detail cannot fit a packet alone. Trigger: ecss, e-st-70-41c, pus-service-22, position-based-schedule-detail-report, detail-entry-sizing, schedule-report-packetisation, oversized-schedule-entry, orbit-position-window."
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
  tags: [ecss, e-st-70-41c-scope, e7041-position-based-schedule-detail-report, pus-service-22, position-based-schedule-detail, schedule-report-packetisation, detail-entry-sizing, orbit-position-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PUS Position-Based Scheduling — Detail Report (space-systems/ecss/e7041-position-based-schedule-detail-report)

Use when the task is the detail report of the position-based schedule of
ECSS-E-ST-70-41C clause 6.22.9.2 — deciding what a detail entry holds,
which activities the report covers, and how the report is split across
telemetry packets once the request content is carried.

## Domain quick reference

- A detail entry holds everything the summary entry holds — the request
  identification, the orbit position and the scheduling group — plus the
  content of the scheduled request. Carrying the request is what makes
  the report useful for verifying what is actually loaded and what makes
  it too large to assume one packet.
- One activity's detail is never split across two report packets. That
  single rule is what turns report generation into a packing problem
  rather than a stream chop: a packet is closed as soon as the next
  entry no longer fits, and the leftover room is accepted.
- An activity whose own detail exceeds the packet payload therefore has
  no valid report at all. It is refused rather than fragmented, because
  fragmenting it would produce a report the receiving end cannot
  reassemble against the no-split rule.
- The packet payload is the telemetry packet limit less the report
  header, and each entry costs its request content plus a fixed entry
  overhead. Both deductions are needed; sizing on the request content
  alone understates the packet count.
- The achieved packet count is compared against the lower bound the
  total payload implies. The gap between them is the price of the
  no-split rule and is a reportable number, not a defect.
- Subset selection is by identification, by scheduling group or by an
  orbit position window, and the three combine as an intersection. A
  window whose start is above its end wraps through the origin of the
  revolution and selects the arcs either side of it.

## Workflow

1. Validate every activity: identification fields against their packet
   field widths, orbit position against the revolution, scheduling group
   as a positive identifier, and a request length that is strictly
   positive.
2. Refuse a schedule carrying one identification twice before any
   selection runs; the report would otherwise address one activity for
   two.
3. Apply the requested selection as an intersection of the identification
   set, the group set and the position window, evaluating the window with
   a wrap-aware containment test and a named edge tolerance.
4. Order the selected entries by increasing orbit position, breaking ties
   on the identification.
5. Size each entry as the fixed entry overhead plus its request content,
   and the packet payload as the packet limit less the report header.
6. Pack in order: add entries to the open packet while they fit, close it
   and open the next when one does not, and refuse outright an entry
   larger than a whole payload.
7. Report the packet count, the payload lower bound, the per-packet fill,
   the largest entry and any finding: an empty selection, a packet count
   above the bound, a single-entry packet, or a wrapping window.

## Pitfalls

- Chopping the report as a byte stream. It gives the minimum packet count
  and an unreassemblable report; the no-split rule is the constraint the
  packing exists to honour.
- Sizing entries on the request content alone. The per-entry overhead is
  paid once per activity, so a report of many small requests is dominated
  by it and the packet count comes out low.
- Forgetting the report header when computing the payload. Every packet
  pays it, so the error grows with the packet count rather than being a
  one-off.
- Treating a packet count above the lower bound as a defect. The bound
  ignores the no-split rule; the gap is information about how close the
  entries sit to the payload, and chasing the bound means splitting.
- Packing before ordering. Packing the insertion order gives a different
  packet boundary on every run for one schedule, so two reports of one
  unchanged schedule no longer compare.
- Reading a group filtered report as the whole schedule. The selected
  count and the schedule size are separate numbers and both are reported.

## Behavior contract (gate 3)

The activity validation, entry sizing, packet payload derivation,
wrap-aware selection, positional ordering, no-split packing, oversized
entry refusal and lower-bound comparison are exercised by the gate 3
contract test:
scripts/test_e7041_position_based_schedule_detail_report.py against
scripts/e7041_position_based_schedule_detail_report_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_position_based_schedule_detail_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
