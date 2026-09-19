---
name: e7041-report-event-action-definitions
description: "Produce and grade the report of the event-action definitions an application process holds under ECSS-E-ST-70-41C clause 6.19.8.6. Use when the question is what each definition would do rather than whether it is armed: resolving a requested identifier list against the store, treating an empty list as the whole store, refusing a request whose identifiers are all unknown, reporting the known ones and raising one failure notification per unknown identifier, collapsing a repeated identifier to a single entry, carrying the action each definition holds alongside its enable state in request order, and carrying totals a receiver can check a truncated transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, event-action-definition-report, event-action-definition-request-resolution, unknown-event-definition-identifier, event-action-report-completeness."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-event-action-definitions, event-action-definition-report, event-action-definition-request-resolution, unknown-event-definition-identifier, event-action-report-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report Event-Action Definitions (space-systems/ecss/e7041-report-event-action-definitions)

Use when the task is the definition-reporting request of
ECSS-E-ST-70-41C clause 6.19.8.6 -- reporting, for the event-action
definitions an on-board application process holds, the action each one
carries and whether it is enabled, with the nine normative items that
clause places on the request and its report.

## Domain quick reference

- This request and the status request answer different questions.
  The status request says only whether a definition is armed. This one
  says what it WOULD DO -- the telecommand it releases when its event
  is raised.
- The request carries a list of event definition identifiers, so
  unlike the status sweep it can legitimately be narrowed. An empty
  list is the whole store, not an empty report.
- A definition is keyed by the pair of application process identifier
  and event definition identifier. A request scoped to one application
  process resolves identifiers only inside that process.
- An unknown identifier does not sink the request. The known ones are
  reported and each unknown one produces its own failure notification,
  so an operator learns every bad identifier in one round trip rather
  than one per retry.
- A request whose identifiers are ALL unknown is different. There is
  nothing to report, so the request fails at start and no report is
  generated at all.
- A repeated identifier collapses to one entry. Reporting it twice
  inflates the count the receiver checks the transfer against.
- Entries follow request order for a narrowed request and store order
  for a whole-store one, so a requester can pair entries with what
  they asked for positionally.
- The action is read from the store when the report is assembled.
  Caching it means reporting what the definition used to do.

## Workflow

1. Normalize the store first and reject it on a duplicate
   process-and-event pair, a missing enable flag, or an action with no
   telecommand identifier. An invalid store produces no report.
2. Normalize the request: reject a non-list, reject a non-string
   identifier, and record which identifiers repeat rather than
   silently dropping them.
3. Resolve each requested identifier against the store for the scoped
   application process, splitting them into resolved and unknown while
   keeping request order.
4. Fail the request at start when every requested identifier is
   unknown, and generate no report in that case.
5. Assemble one entry per resolved identifier, each carrying both
   identifiers, the enable state and the action read from the store at
   assembly time.
6. Raise one failure notification per unknown identifier and one
   finding per repeated identifier.
7. Compute the reported and unknown totals from the assembled entries,
   verify the report against its own totals, and close with the
   verdict.

## Pitfalls

- Treating an empty identifier list as an empty report. The requester
  asked for everything and received nothing, and the count agreed with
  itself so nothing looked wrong.
- Sinking the whole request on one unknown identifier. The operator
  then learns about their bad identifiers one per round trip.
- Reporting an empty report for an all-unknown request instead of
  failing at start. An empty report reads as an empty store.
- Reporting a repeated identifier twice. The count inflates and the
  receiver's truncation check starts passing on a report that is
  wrong in the other direction.
- Caching the action rather than reading it at assembly time. The
  report then describes what the definition used to do.
- Resolving an identifier across application processes. A definition
  belonging to another process is reported as though it belonged to
  the requested one.
- Computing the totals from the request rather than from the assembled
  entries. They then count what was asked for instead of what was
  sent, and a truncation passes the check added to catch it.

## Behavior contract (gate 3)

The store normalization, request normalization, whole-store and
narrowed resolution, unknown-identifier notifications, all-unknown
failed start, repeated-identifier collapse, request-order assembly,
action freshness, totals and self-consistency check are exercised by
the gate 3 contract test:
scripts/test_e7041_report_event_action_definitions.py against
scripts/e7041_report_event_action_definitions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_report_event_action_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
