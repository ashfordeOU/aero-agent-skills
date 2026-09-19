---
name: e7041-execution-status-reporting
description: "Generate the execution status report for the on-board control procedures aboard, under ECSS-E-ST-70-41C clause 6.18.4.5. Use when the task is getting a fleet of procedure statuses onto the downlink intact: declaring whether the report covers everything, a named subset or only what changed, keeping a stable entry order so one report can be diffed against the last, splitting a report too long for one telemetry packet into a counted sequence instead of truncating it, and pricing the reporting cadence against the link budget. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, obcp-execution-status-report, obcp-status-report-packetisation, obcp-changed-since-last-report, obcp-status-report-scope, obcp-status-report-cadence."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-execution-status-reporting, obcp-execution-status-report, obcp-status-report-packetisation, obcp-changed-since-last-report, obcp-status-report-scope, obcp-status-report-cadence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Execution Status Reporting (space-systems/ecss/e7041-execution-status-reporting)

Use when the task is the execution status report of ECSS-E-ST-70-41C
clause 6.18.4.5 -- getting the status of the on-board control
procedures aboard into telemetry packets the ground can read as one
thing.

## Domain quick reference

- Knowing the status of every procedure aboard is one job; getting it
  to the ground inside a packet is another, and this is the second one.
  Three decisions make the report: which procedures it covers, in what
  order, and across how many packets.
- Scope has to be declared, not inferred. All procedures, a named
  subset the ground asked for, or only the ones whose status changed.
  Without the declaration an absent procedure is unreadable -- it might
  be unchanged, it might not have been asked for, it might be gone.
- A changed-since-last-report needs the previous statuses to compare
  against. Nothing can be known to have changed against a baseline
  that was never kept, and defaulting to "report everything" there
  quietly turns a cheap report into the expensive one.
- A procedure missing from the previous report has changed. It is new
  to the ground, and treating an absent baseline entry as agreement
  hides exactly the procedures that just appeared.
- Entry order has to be stable. Diffing one report against the last is
  the main thing anyone does with them, and an order that drifts makes
  every report look like everything moved.
- An entry costs a fixed number of octets and a packet carries a header
  plus whatever fits after it. A report longer than one packet becomes
  a numbered sequence; a report that fills one packet and stops looks
  complete and is not.
- An empty report is still a report. One packet saying nothing changed
  is a positive statement; no packet at all is indistinguishable from a
  reporting chain that died.

## Workflow

1. Validate the population: a non-empty list, a non-empty id and a
   known status on every entry, no duplicate ids.
2. Declare the scope before selecting anything, and carry it in the
   report so the reader knows what an absence means.
3. For a requested subset, refuse an id that is not aboard and refuse a
   repeat, and keep the order the ground asked in.
4. For a changed report, require the previous statuses. Treat a
   procedure missing from that baseline as changed.
5. Validate the packet geometry: a packet has to hold its header plus
   at least one entry, or no report can be built at all.
6. Compute entries per packet from the space left after the header, and
   split the selected entries into that many at a time.
7. Number every packet in the sequence and carry the sequence count in
   each, so a partial arrival is visible as partial.
8. Emit one empty packet when the selection is empty rather than
   nothing at all.
9. Price the cadence: octets per report times reports per hour against
   the downlink budget, treating a demand that lands exactly on the
   budget as affordable, and report the rate the link would actually
   carry.

## Pitfalls

- Truncating at the first packet. The report parses, it has a header
  and entries, and the procedures that fell off the end read exactly
  like procedures that are not aboard.
- Leaving the scope out of the report. The ground then cannot tell an
  unchanged procedure from one that was never asked about.
- Running a changed report with no baseline. Either everything is
  reported as changed, defeating the point, or nothing is, hiding a
  status that moved.
- Sorting the entries differently from one report to the next. Every
  diff then shows churn that did not happen.
- Suppressing an empty report. Silence on the link is the same shape as
  a reporting chain that stopped, and the operator finds out late.
- Sizing a packet without its header. The last entry then does not fit
  and the split is off by one for every report the mission sends.
- Deciding cadence affordability with a strict inequality. The demand
  is an integer octet count times a possibly fractional report rate, so
  a cadence exactly on budget can land either side of it; compare with
  a relative tolerance.

## Behavior contract (gate 3)

The entry and population validation, the three scopes and their
refusals, absent-baseline-counts-as-changed, packet geometry
validation, entries per packet after the header, exact packet sizing,
counted-sequence partitioning with no entry lost, the empty-report
packet, scope carried in the report, grouped and zero-filled status
counts, and the cadence pricing with exact-budget acceptance are
exercised by the gate 3 contract test:
scripts/test_e7041_execution_status_reporting.py against
scripts/e7041_execution_status_reporting_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e7041_execution_status_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
