---
name: e7041-report-parameter-values
description: "Generate and grade the parameter value report of ECSS-E-ST-70-41C clause 6.20.4.1. Use when a ground request asks what a named list of on-board parameters currently reads: resolving each requested identifier against the application process that holds it, collapsing a repeated identifier to one entry, reporting the parameters that resolved while raising one failure notification per identifier that did not, failing the request at start only when nothing resolved, keeping entries in request order so a requester can pair them positionally, refusing to report a stored value that no longer fits its own definition, and carrying totals a receiver can check a truncated transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, on-board-parameter-value-report, parameter-report-request-resolution, unknown-parameter-identifier, parameter-value-report-completeness."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-parameter-values, on-board-parameter-value-report, parameter-report-request-resolution, unknown-parameter-identifier, parameter-value-report-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report Parameter Values (space-systems/ecss/e7041-report-parameter-values)

Use when the task is the value-reporting request of ECSS-E-ST-70-41C
clause 6.20.4.1 -- reporting the current values of the on-board
parameters a request names, with the eight normative items that clause
places on the request and its report.

## Domain quick reference

- This is a named request, not a sweep. It carries a list of
  parameter identifiers, so unlike a whole-store status report it can
  and should be narrowed.
- An identifier resolves inside one application process. Uniqueness
  is scoped to the process, so a request must say which process it is
  asking, and an identifier held by another process does not resolve.
- An identifier that resolves to nothing does not sink the request.
  The rest are reported and each bad identifier gets its own failure
  notification, so an operator learns all of them in one round trip.
- A request where nothing resolves is different. There is no report
  to send, so the request fails at start rather than sending an empty
  one that reads as an empty store.
- A repeated identifier collapses to one entry. Reporting it twice
  inflates the count a receiver checks the transfer against.
- Entries follow request order so a requester can pair the nth entry
  with the nth identifier without matching on names.
- A value is read from the store when the report is assembled and
  checked against the parameter's own definition on the way out. A
  stored value that no longer fits its definition is a store defect,
  and reporting it passes that defect off as the state of the
  spacecraft.
- The reported and unknown counts exist so a receiver can detect a
  truncated transfer without knowing what the report should have
  held.

## Workflow

1. Normalize the store first: each parameter carries an application
   process, an identifier, a representation, an optional bounded
   domain and a current value. Reject a repeated identifier inside one
   process. An invalid store produces no report.
2. Normalize the request: reject a non-list, reject a non-string
   identifier, and record which identifiers repeat rather than
   silently dropping them.
3. Resolve each requested identifier against the store scoped to the
   named application process, keeping request order and splitting the
   unresolved ones out.
4. Fail the request at start when nothing resolved, and generate no
   report in that case.
5. Read each resolved parameter's current value and check it against
   its own definition; a value that does not fit is withheld and
   raised rather than reported.
6. Assemble one entry per reported parameter carrying the identifier,
   the representation and the value, in request order.
7. Raise one failure notification per unresolved identifier and one
   finding per repeated identifier.
8. Compute the reported, withheld and unknown totals from the
   assembled entries, verify the report against its own totals, and
   close with the verdict.

## Pitfalls

- Sinking the whole request on one unknown identifier. The operator
  then learns about their bad identifiers one per round trip.
- Sending an empty report when nothing resolved instead of failing at
  start. An empty report reads as a spacecraft holding no parameters.
- Reporting a repeated identifier twice. The count inflates and the
  receiver's truncation check starts passing on a report that is
  wrong in the other direction.
- Reordering entries by identifier or by store order. A requester
  pairing positionally then reads the wrong value against the wrong
  name and nothing in the report says so.
- Reporting a stored value without checking it against its
  definition. The defect leaves the spacecraft looking like telemetry.
- Withholding a bad value silently. The entry disappears, the counts
  still agree, and the gap looks like a truncation nobody can locate.
- Resolving an identifier across application processes. Another
  process's parameter is reported under the requested process's name.
- Computing the totals from the request rather than from the
  assembled entries. They then count what was asked for instead of
  what was sent.

## Behavior contract (gate 3)

The store normalization, request normalization, scoped resolution,
unknown-identifier notifications, nothing-resolved failed start,
repeated-identifier collapse, request-order assembly, value-against-
definition check, withheld-value findings, totals and self-consistency
check are exercised by the gate 3 contract test:
scripts/test_e7041_report_parameter_values.py against
scripts/e7041_report_parameter_values_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_report_parameter_values.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
