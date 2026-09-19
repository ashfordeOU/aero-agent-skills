---
name: e7041-report-the-status-of-each-event-action-definition
description: "Produce and grade the status report covering every event-action definition an application process holds under ECSS-E-ST-70-41C clause 6.19.8.5. Use when the question is which definitions are currently armed rather than what they would do: emitting one entry per definition held with no identifier list accepted, carrying the application process and event definition identifiers alongside that definition's own enable state, keeping the definition flag distinct from the event-action function's enable state instead of folding one into the other, surfacing definitions left enabled underneath a disabled function, and carrying totals a receiver can check a truncated transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, event-action-status-report, event-action-definition-enable-status, event-action-function-enable-state, event-action-status-report-completeness."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-the-status-of-each-event-action-definition, event-action-status-report, event-action-definition-enable-status, event-action-function-enable-state, event-action-status-report-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report Event-Action Definition Status (space-systems/ecss/e7041-report-the-status-of-each-event-action-definition)

Use when the task is the status-reporting request of ECSS-E-ST-70-41C
clause 6.19.8.5 -- reporting, for every event-action definition the
on-board application process holds, whether that definition is
enabled, with the four normative items that clause places on the
report.

## Domain quick reference

- This request and the definition-reporting request answer different
  questions about the same objects. One says what a definition WOULD
  DO when its event is raised -- the action it carries. This one says
  only whether it is currently armed.
- It covers the whole store by construction. There is no identifier
  list to narrow it, because an operator asking what is armed cannot
  be expected to name the definitions they have forgotten about.
- A definition is keyed by the pair of application process identifier
  and event definition identifier, not by the event identifier alone.
  Two application processes may both react to the same event and their
  definitions are separate objects.
- There are two enable flags and they are not the same flag. Each
  definition has its own, and the event-action function of the
  application process has one of its own that gates all of them.
- The status this report carries is the definition's own flag. It is
  not rewritten by the function flag, because an operator restoring
  the function needs to know which definitions will come back armed.
- That honesty creates a blind spot: a definition reading enabled
  underneath a disabled function will not act. It is reported as
  enabled and raised as a finding, so the report stays truthful and
  the gap still gets seen.
- The totals -- definition count and enabled count -- exist so a
  receiver can detect a truncated transfer without knowing what the
  report should have contained.

## Workflow

1. Normalize the store first and reject it outright on a duplicate
   application-process-and-event pair, a missing or non-boolean enable
   flag, or an empty identifier. An invalid store produces no report.
2. Read the event-action function enable state for the application
   process separately, and require it explicitly rather than assuming
   the function is on.
3. Derive each definition's effective state from the two flags:
   disabled when its own flag is clear, inhibited when its flag is set
   under a disabled function, and armed only when both are set.
4. Assemble one entry per definition in store order, each carrying the
   application process identifier, the event definition identifier and
   the definition's own enable state.
5. Reconcile any declared status against the derived effective state,
   and raise a finding for every definition left enabled underneath a
   disabled function.
6. Compute the definition and enabled totals from the assembled
   entries, verify the report against its own totals, and close with
   the verdict plus the definitions that were inconsistent.

## Pitfalls

- Reporting the effective state in the enable field. An operator who
  re-enables the function then has no idea which definitions will
  start acting, which is the one thing this report exists to tell
  them.
- Reporting a stored status field instead of the two flags. It was
  written by whatever last updated it, and the receiver takes it as
  the current state of the spacecraft.
- Letting a disabled function pass silently. Every definition beneath
  it is inert, and a report that says nothing about that reads as an
  armed spacecraft.
- Keying a definition on the event identifier alone. Two application
  processes reacting to the same event then collapse into one entry
  and one of them disappears from the report.
- Accepting an identifier list for this report. Narrowing it to what
  the requester already suspects defeats the only reason a whole-store
  sweep exists.
- Computing the totals from the store rather than from the assembled
  entries. They then agree with the intent instead of the content, and
  a truncation passes the check that was added to catch it.
- Treating an empty store as an error. An application process that
  holds no event-action definitions has a valid, empty report.

## Behavior contract (gate 3)

The store normalization, paired-key duplicate detection, effective
state derivation across both enable flags, inhibited-definition
findings, declared versus derived reconciliation, whole-store
assembly, totals and self-consistency check are exercised by the gate
3 contract test:
scripts/test_e7041_report_the_status_of_each_event_action_definition.py
against
scripts/e7041_report_the_status_of_each_event_action_definition_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_report_the_status_of_each_event_action_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
