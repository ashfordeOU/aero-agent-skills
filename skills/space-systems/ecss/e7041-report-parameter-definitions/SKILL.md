---
name: e7041-report-parameter-definitions
description: "Build and grade a report of the object memory parameter definitions an application holds, under ECSS-E-ST-70-41C clause 6.20.5.4. Use when a ground request asks where named parameters actually live on board: resolving each identifier against the definition store, failing the request wholly or in part rather than dropping an unresolvable one, treating an empty request as every definition held, emitting one entry per accepted identifier in the requested order carrying the whole binding rather than a bare identifier, and carrying a definition count and a total reported width a receiver can check a transfer against. Trigger: ecss, e-st-70-41-packet-utilization-scope, object-memory-parameter-definition-report, on-board-parameter-management-service, parameter-binding-descriptor, unknown-parameter-definition-identifier, reported-definition-width-total."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-report-parameter-definitions, object-memory-parameter-definition-report, on-board-parameter-management-service, parameter-binding-descriptor, unknown-parameter-definition-identifier, reported-definition-width-total]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Report Parameter Definitions (space-systems/ecss/e7041-report-parameter-definitions)

Use when the task is the definition-reporting request of
ECSS-E-ST-70-41C clause 6.20.5.4 -- answering a ground request for the
object memory parameter definitions an on-board application is
actually holding, with the seven normative items that clause places on
the request handling and on the report it produces.

## Domain quick reference

- A parameter definition is a binding, not a value. It names the
  object memory, the bit offset, the type that fixes the width and
  the flags that say whether the definition may be changed and
  whether the value may be set.
- The ground cannot reconstruct the store from the changes it sent.
  A patch campaign runs across operators and shifts, so the store is
  asked directly rather than modelled from command history.
- An identifier the store does not hold is reported, never quietly
  skipped. The difference between a partly refused request and a
  report that happens to be short is the whole value of the exchange.
- An empty request is a request for everything. That is a deliberate
  convenience, and it is why the report says whether it answered the
  whole store or a named subset.
- Order is part of the contract. A named request comes back in the
  order it asked for, an empty request comes back in store order, and
  a receiver pairs entries positionally on that promise.
- An entry carries the binding itself. A report of identifiers alone
  confirms a parameter exists and tells the ground nothing it did not
  already know.
- The type is what makes the width, and the width is what makes the
  total. Reporting a type the application does not declare leaves the
  receiver unable to size the entry at all.
- The totals are a transfer check. A definition count and a total
  reported width let a receiver detect a truncated report without
  knowing what it should have contained.

## Workflow

1. Normalize the definition store first and reject a duplicate
   identifier, a negative offset or an undeclared type outright. An
   invalid store produces no report.
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
   memory, offset, type, width and both flags.
6. Compute the definition count and the total reported width from the
   assembled entries, then verify the report against its own totals
   before returning it.

## Pitfalls

- Answering a partly unresolvable request with a short report and no
  complaint. The receiver models the missing parameters as deleted,
  which is the opposite of what happened.
- Sorting the entries. A named request expects its own order and
  re-sorting breaks positional pairing for no gain.
- Reporting identifiers and offsets without the type. The receiver
  then cannot tell where one parameter ends and the next begins.
- Reading an empty request as an empty report. It is the request for
  everything, and the two differ by the entire store.
- Computing the width total from the request rather than from the
  assembled entries. The totals then agree with the intent instead of
  the content, and a truncation passes the check added to catch it.
- Omitting the re-definable and settable flags because they are not
  part of the location. They are what tells the ground which of these
  definitions a later change request could touch at all.

## Behavior contract (gate 3)

The store normalization, request normalization, identifier
resolution, acceptance verdict, entry assembly with the whole
binding, total computation and self-consistency check are exercised
by the gate 3 contract test:
scripts/test_e7041_report_parameter_definitions.py against
scripts/e7041_report_parameter_definitions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_report_parameter_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
