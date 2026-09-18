---
name: e7041-report-functional-monitoring-definitions
description: "Build and grade a functional monitoring definition report under ECSS-E-ST-70-41C clause 6.12.4.8. Use when the task is answering a request for the definitions an on-board application is holding: splitting the requested identifiers into those the store holds and those it does not, failing the request wholly or in part rather than dropping an unresolvable identifier, treating an empty request as every definition held, emitting one entry per accepted identifier in the requested order with its complete constituent list and failing threshold, and carrying definition and constituent totals a receiver can check a transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, functional-monitoring-definition-report, on-board-monitoring-service, functional-monitoring-constituent-list, unknown-functional-monitoring-identifier, functional-monitoring-failing-threshold."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-functional-monitoring-definitions, functional-monitoring-definition-report, on-board-monitoring-service, functional-monitoring-constituent-list, unknown-functional-monitoring-identifier, functional-monitoring-failing-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report Functional Monitoring Definitions (space-systems/ecss/e7041-report-functional-monitoring-definitions)

Use when the task is the definition-reporting request of
ECSS-E-ST-70-41C clause 6.12.4.8 -- answering a ground request for the
functional monitoring definitions an on-board application is actually
holding, with the nine normative items that clause places on the
request handling and on the report it produces.

## Domain quick reference

- A functional monitoring definition is a group, not a check. It names
  a set of parameter monitoring definitions and a failing threshold:
  the number of its constituents that have to be failing before the
  group itself counts as failed and its event definition fires.
- The ground segment cannot reconstruct the on-board store from the
  commands it sent. Definitions are created, deleted and modified over
  a long mission by more than one operator, so the store is asked
  directly rather than modelled from history.
- An identifier the store does not hold is reported, never quietly
  skipped. The distinction between a request that was partly refused
  and a report that happens to be short is the whole value of the
  exchange.
- An empty request is a request for everything. That is a deliberate
  convenience and it is why the report says whether it was answering
  the whole store or a named subset.
- Order is part of the contract. A named request comes back in the
  order it asked for, and an empty request comes back in the order the
  store holds, so a receiver can pair entries positionally.
- An entry carries the constituent list itself, not a count standing
  in for it. A count tells a receiver how much it is missing; the list
  tells it what.
- The failing threshold has a valid range fixed by the group: at least
  one, and never more than the number of constituents. A store entry
  outside that range is not a definition that reports oddly, it is an
  invalid entry.
- Totals in the report are a transfer check. A definition count and a
  constituent count let a receiver detect a truncated report without
  knowing what it should have contained.

## Workflow

1. Normalize the on-board store first and reject it outright on a
   duplicate identifier, an empty constituent list, a repeated
   constituent or a threshold outside one to the constituent count.
   An invalid store produces no report.
2. Normalize the request: accept a bare identifier list or a request
   object, preserve order, and reject a repeated identifier as
   malformed rather than de-duplicating it silently.
3. Resolve the request against the store and split the identifiers
   into those held and those not held. An empty request resolves to
   the whole store in store order.
4. Set the acceptance verdict from the split: accepted when every
   identifier resolved, partially accepted when some did, rejected
   when none did, and raise one finding per unresolved identifier.
5. Assemble one entry per resolved identifier, each carrying the
   enable state, the failing threshold, the event definition and the
   complete constituent list with each constituent's checking status.
6. Compute the definition and constituent totals, then verify the
   assembled report against its own totals before returning it, so a
   report that disagrees with itself never leaves.

## Pitfalls

- Answering a partly unresolvable request with a short report and no
  complaint. The receiver then models the missing definitions as
  deleted, which is the opposite of what happened.
- Sorting the entries. A named request expects its own order, and
  re-sorting breaks positional pairing on the receiving side for no
  gain.
- Returning a constituent count instead of the constituent list. It
  satisfies the totals check and defeats the purpose of the request.
- Reading an empty request as an empty report. It is the request for
  everything, and the two differ by the entire store.
- Accepting a failing threshold larger than the group. Such a group
  can never be declared failed, so the surveillance it appears to
  provide does not exist.
- Reporting totals computed from the request rather than from the
  assembled entries. The totals then agree with the intent instead of
  with the content, and a truncation passes the check it was added to
  catch.

## Behavior contract (gate 3)

The store normalization, request normalization, identifier resolution,
acceptance verdict, entry assembly with the full constituent list,
total computation and self-consistency check are exercised by the gate
3 contract test:
scripts/test_e7041_report_functional_monitoring_definitions.py against
scripts/e7041_report_functional_monitoring_definitions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_report_functional_monitoring_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
