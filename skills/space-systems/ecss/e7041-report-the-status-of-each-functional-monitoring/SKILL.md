---
name: e7041-report-the-status-of-each-functional-monitoring
description: "Produce and grade the status report covering every on-board functional monitoring definition under ECSS-E-ST-70-41C clause 6.12.4.9. Use when the task is answering what the definitions are currently doing rather than what they are: emitting one entry per definition held with no identifier list accepted, carrying each enable state, deriving each functional status from the constituent checking states against the failing threshold, keeping a disabled group unchecked while still surfacing constituents outside their limits, refusing an invalid parameter the power to reach the threshold, and carrying totals a receiver can check a transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, functional-monitoring-status-report, functional-monitoring-enable-status, disabled-functional-monitoring-unchecked, invalid-parameter-monitoring-constituent, monitoring-status-report-completeness."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-the-status-of-each-functional-monitoring, functional-monitoring-status-report, functional-monitoring-enable-status, disabled-functional-monitoring-unchecked, invalid-parameter-monitoring-constituent, monitoring-status-report-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report Functional Monitoring Status (space-systems/ecss/e7041-report-the-status-of-each-functional-monitoring)

Use when the task is the status-reporting request of ECSS-E-ST-70-41C
clause 6.12.4.9 -- reporting, for every functional monitoring
definition the on-board application holds, whether it is enabled and
what its current status works out to, with the five normative items
that clause places on the report.

## Domain quick reference

- This request and the definition-reporting request answer different
  questions about the same objects. One says what the definitions ARE
  -- their constituents and thresholds. This one says what they are
  DOING right now.
- It covers the whole store by construction. There is no identifier
  list to narrow it, because an operator asking what is currently
  failing cannot be expected to name the definitions they have not
  thought of.
- Status is derived, not stored. It is a function of the constituent
  checking states and the failing threshold, so reporting a stored
  status field invites the two to drift apart and reports the drift as
  fact.
- The derivation has three outcomes for an enabled group: unchecked
  when nothing inside it is checking, failed when the number of
  constituents outside their limits has reached the threshold, and
  running otherwise.
- A disabled group reports unchecked whatever its constituents say.
  That is correct and it is also a blind spot, so constituents outside
  their limits underneath a disabled group are surfaced as a finding
  rather than left silent.
- A constituent on an invalid parameter is not checking. It must not
  manufacture a group failure, and it must not quietly make one
  unreachable either, so it is counted and reported on its own.
- The totals -- definition count and enabled count -- exist so a
  receiver can detect a truncated transfer without knowing what the
  report should have contained.

## Workflow

1. Normalize the store first and reject it outright on a duplicate
   identifier, an empty constituent list, a repeated constituent, a
   missing enable flag or a threshold outside one to the constituent
   count. An invalid store produces no report.
2. Tally each definition's constituents by contribution: within
   limits, outside limits, invalid and unchecked, plus the count that
   is actually checking.
3. Derive each functional status from that tally and the failing
   threshold, taking the disabled case first so a disabled group
   cannot be reported as running or failed.
4. Assemble one entry per definition in store order, each carrying the
   identifier, the enable state, the derived status, the failing count
   against its threshold and the invalid-constituent count.
5. Reconcile any declared status against the derived one, and raise a
   finding for a disabled group covering out-of-limit constituents and
   for an enabled group carrying invalid ones.
6. Compute the definition and enabled totals, verify the assembled
   report against its own totals, and close with the verdict plus the
   definitions that were inconsistent.

## Pitfalls

- Reporting a stored status field. It was written by whatever last
  updated it, and the receiver takes it as the current state of the
  spacecraft.
- Letting a disabled group report running because its constituents
  are healthy. Disabled means nothing is being surveyed, and running
  tells an operator the opposite.
- Letting a disabled group report failed because its constituents are
  not healthy. The correct answer is unchecked plus a finding, so the
  status stays honest and the blind spot still gets seen.
- Counting an invalid parameter as a failure. An invalid parameter is
  an absence of information, and turning it into a group failure
  produces alarms that no real excursion caused.
- Counting an invalid parameter as within limits. That is the same
  mistake with the sign reversed: a group one failure short of its
  threshold stays quiet while a constituent nobody can read might be
  the one that crossed.
- Accepting an identifier list for this report. Narrowing it to what
  the requester already suspects defeats the only reason a whole-store
  status sweep exists.
- Computing the totals from the store rather than from the assembled
  entries. They then agree with the intent instead of the content, and
  a truncation passes the check that was added to catch it.

## Behavior contract (gate 3)

The store normalization, constituent tally, status derivation for
enabled and disabled groups, invalid-constituent handling, declared
versus derived reconciliation, whole-store assembly, totals and
self-consistency check are exercised by the gate 3 contract test:
scripts/test_e7041_report_the_status_of_each_functional_monitoring.py
against
scripts/e7041_report_the_status_of_each_functional_monitoring_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_report_the_status_of_each_functional_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
