---
name: e7041-managing-the-application-process-forward-control
description: "Manage the application-process forward-control configuration of the real-time forwarding control service under ECSS-E-ST-70-41C clause 6.14.3.4. Use when the task is deciding which telemetry reports a spacecraft passes to the ground in real time: adding and deleting application-process, report-type and message-subtype selections, resolving a wildcard against the specific entries it subsumes, refusing a partial deletion inside a wildcard, holding requests to the controlled application-process list, and returning a per-item disposition so one rejected item never abandons the rest of the request. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, real-time-forwarding-control, application-process-forward-control, forward-selection-wildcard, message-subtype-selection, controlled-application-process-list, per-item-request-disposition."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-application-process-forward-control, real-time-forwarding-control, application-process-forward-control, forward-selection-wildcard, message-subtype-selection, controlled-application-process-list]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Application-Process Forward Control (space-systems/ecss/e7041-managing-the-application-process-forward-control)

Use when the task is the application-process forward-control
configuration of ECSS-E-ST-70-41C clause 6.14.3.4 -- the selection tree
that decides which telemetry reports the real-time forwarding control
service passes on, and how an add or delete request changes it.

## Domain quick reference

- The configuration is a three-level tree: application process, then
  report type, then message subtype. A report is forwarded only when
  the tree selects it, so an empty configuration forwards nothing. That
  is a legitimate operational state -- a quiet downlink -- not a fault
  to be repaired by defaulting to forward-everything.
- Each level carries an implicit wildcard. An application process entry
  with no report types under it means every report type of that
  application process; a report type entry with no subtypes means every
  subtype of that report type. The wildcard is not a shorthand that
  expands into the list: it is a distinct state, and it keeps meaning
  the right thing when a new subtype is defined on board later.
- A wildcard and the specific entries under it cannot coexist. If both
  were held, a later delete of the specific entry would be ambiguous --
  it would leave the report forwarded through the wildcard while the
  ground believes it was removed. Adding a wildcard therefore clears
  the entries it subsumes, and adding a specific entry beneath an
  existing wildcard is rejected rather than silently absorbed.
- A wildcard cannot be partially deleted. Removing one subtype from an
  all-subtypes entry would require the service to invent the complement
  set; the operator deletes the wildcard and adds back the subtypes
  they want, which is explicit and reviewable.
- Only the application processes the service is configured to control
  may appear. A request naming any other application process is
  rejected at that item -- the service does not gain control of an
  application process by being asked about it.
- Requests carry many items and execute per item. An item that fails
  its own checks is reported as rejected and the items after it are
  still processed, so the response is a disposition list, not a single
  verdict.

## Workflow

1. Validate each request item: an application process identifier in
   range, a report type when a message subtype is named, and values
   inside their own ranges. A subtype named without a report type is a
   malformed item, not a wildcard.
2. Check the application process against the controlled list and reject
   the item if it is not there, before touching the configuration.
3. For an add, walk down to the level the item names, creating the
   intermediate entries. Set a wildcard by clearing what it subsumes;
   reject an entry that a wider wildcard already covers, and reject one
   already present.
4. Apply the sizing limits of the on-board store as per-item
   rejections, so a request that overruns capacity still reports which
   of its items landed.
5. For a delete, remove the named entry and everything below it. Reject
   an absent entry, and reject any attempt to delete inside a wildcard.
6. Answer a forwarding question by testing the application process
   wildcard first, then the report type wildcard, then the subtype set.
7. Report the configuration sorted at every level so two reports of the
   same state compare equal.

## Pitfalls

- Expanding a wildcard into the subtype list at the moment it is set.
  The expansion is a snapshot; a subtype defined afterwards would not
  be forwarded, which is exactly the behaviour the wildcard exists to
  avoid.
- Letting a wildcard and its specific entries coexist. The
  configuration then reports one thing and forwards another as soon as
  a delete arrives.
- Aborting the whole request at the first rejected item. The remaining
  items are independent, and an operator who is told only about the
  first failure has to re-send a request whose later half may already
  have been valid.
- Treating an uncontrolled application process as a new entry to
  create. The controlled list is the service's own configuration, and
  extending it from a telecommand is a change of scope, not an add.
- Reading an empty configuration as uninitialised and forwarding
  everything. A configuration that selects nothing is the state a
  deliberate delete leaves behind.

## Behavior contract (gate 3)

The item validation, controlled-list check, wildcard subsumption,
partial-delete refusal, capacity rejection, forwarding decision and
sorted report are exercised by the gate 3 contract test:
scripts/test_e7041_managing_the_application_process_forward_control.py
against
scripts/e7041_managing_the_application_process_forward_control_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_application_process_forward_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
