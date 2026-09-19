---
name: e7041-periodic-file-copy-status-reporting
description: "Derive the cadence and the content of the periodic file copy status report under ECSS-E-ST-70-41C clause 6.23.5.5. Use when the task is turning that reporting function on for a pass, changing its interval, or working out why the ground saw fewer reports than it expected: taking a strictly positive whole interval, restarting the schedule from each enable so the first report falls one whole interval later, generating the ticks with integer arithmetic, and listing every copy operation with its octets moved and outstanding, an empty list included. Trigger: ecss, e-st-70-41c, pus-file-management, periodic-copy-status-reporting, copy-report-generation-interval, copy-status-report-content, copy-reporting-enable-disable, copy-octets-outstanding."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-periodic-file-copy-status-reporting, periodic-copy-status-reporting, copy-report-generation-interval, copy-status-report-content, copy-reporting-enable-disable, copy-octets-outstanding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Periodic File Copy Status Reporting (space-systems/ecss/e7041-periodic-file-copy-status-reporting)

Use when the task is the periodic file copy status reporting of
ECSS-E-ST-70-41C clause 6.23.5.5 -- the function that generates a
report of every copy operation the on-board service is holding, once
per generation interval, for as long as it is enabled.

## Domain quick reference

- The function has exactly three pieces of state: enabled or not, the
  generation interval, and the tick the current enable started at.
  Without the third one the schedule cannot be reproduced, and a
  report that arrives at an unexpected tick looks like a fault.
- The interval is a whole number of on-board time units and at least
  one. Zero is not the fastest cadence, it is a request for continuous
  reporting, which is a different thing the function does not offer.
- Enabling an already-enabled function is not an error. It replaces the
  interval and restarts the schedule from that tick, so the new cadence
  is phased on the new enable rather than on the old one.
- The enable tick is not itself a report tick. The first report falls
  one whole interval later, which is what makes a change of interval
  observable in the timing rather than only in the content.
- Generate the tick list with integer arithmetic. Accumulating a
  floating interval drifts, and a report expected exactly at the end of
  a window lands a fraction outside it on one platform and inside it on
  another.
- An empty copy operation list still produces a report. A report of
  zero entries says the spacecraft has nothing copying; silence says
  nothing at all, and the ground cannot tell it from a lost downlink.
- The useful figure per operation is the octets outstanding, not the
  octets moved. Outstanding is what decides whether the transfer
  finishes before the next pass.

## Workflow

1. Start from the disabled power-on state: not enabled, no interval, no
   enable tick.
2. On enable, validate a strictly positive whole interval and a
   non-negative whole tick, then record all three and categorize the
   result as a first enable, a restart at the same interval, or a
   change of interval.
3. On disable, clear the interval and the enable tick; a disable of an
   already-disabled function is redundant, reported and harmless.
4. Generate the report ticks from the enable tick: the first at one
   interval after it, then each further interval, up to and including
   the window end. A window ending before the enable is an input error.
5. Build each report from the copy operation list as it stands at that
   tick: source, target, octets total, octets moved, octets
   outstanding and state per entry.
6. Validate each entry into the report; a state that is neither running
   nor suspended, or octets moved beyond the total, is an input error
   rather than a row to print.
7. Total the outstanding octets across the report, and keep the entry
   count even when it is zero.
8. Report the window: the ticks, the report content at each, the count,
   and findings for a disabled function, an interval that fits no tick
   inside the window, a run of wholly empty reports, and octets still
   outstanding at the last report.

## Pitfalls

- Treating the enable tick as the first report. Every report then
  arrives one interval early against the ground's model, and a change
  of interval is invisible in the timing.
- Accumulating the interval as a float. The last tick of a long window
  lands just outside the boundary on one machine and just inside it on
  another, which is a schedule that cannot be regression-tested.
- Suppressing the report when nothing is copying. The absence is
  indistinguishable from a reporting function that stopped.
- Keeping the old phase when the interval changes. The cadence then
  depends on when the function was first enabled, hours earlier, and
  nobody can predict the next tick.
- Reporting octets moved alone. It grows toward a total the operator
  must remember; the outstanding figure is the one that answers the
  question being asked.
- Rejecting a redundant disable. It is the safe idempotent command an
  operator sends when the state is uncertain, and refusing it invites
  a riskier one.

## Behavior contract (gate 3)

The interval validation, enable, re-interval and disable outcomes, the
integer tick schedule with the enable tick excluded, the per-entry
report rows with octets outstanding, the report of an empty list, the
window generation and the cadence findings are exercised by the gate 3
contract test:
scripts/test_e7041_periodic_file_copy_status_reporting.py against
scripts/e7041_periodic_file_copy_status_reporting_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_periodic_file_copy_status_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
