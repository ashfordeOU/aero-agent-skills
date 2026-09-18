---
name: e7041-managing-the-housekeeping-parameter-report-forward
description: "Maintain the housekeeping parameter report forward-control configuration of the real-time forwarding control service under ECSS-E-ST-70-41C clause 6.14.3.5. Use when the task is choosing which housekeeping parameter reports reach the ground in real time, one report structure at a time: adding and deleting structure identifiers per application process, refusing an identifier the housekeeping service never defined under that application process, holding an all-structures wildcard against the specific entries it subsumes, and finding selections left stale by a structure definition that has since been deleted. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, housekeeping-forward-control, housekeeping-report-structure-selection, all-structures-forward-wildcard, stale-structure-selection, per-item-request-disposition."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-housekeeping-parameter-report-forward, housekeeping-forward-control, housekeeping-report-structure-selection, all-structures-forward-wildcard, stale-structure-selection, real-time-forwarding-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Housekeeping Parameter Report Forward Control (space-systems/ecss/e7041-managing-the-housekeeping-parameter-report-forward)

Use when the task is the housekeeping parameter report forward-control
configuration of ECSS-E-ST-70-41C clause 6.14.3.5 -- the per-structure
selection that decides which housekeeping parameter reports the
real-time forwarding control service passes on.

## Domain quick reference

- Housekeeping parameter reports cannot be separated by report type and
  message subtype, because every housekeeping report an application
  process produces carries the same pair. What distinguishes them is
  the report structure they were generated from, so this configuration
  works one structure identifier at a time and sits alongside the
  coarser application-process selection rather than replacing it.
- A structure identifier is only meaningful inside the application
  process that defines it. The same number under two application
  processes names two unrelated structures, so the definition
  catalogue is consulted per application process and never globally.
- An identifier the housekeeping service has not defined cannot be
  selected. Accepting it would let a later definition of that number
  start forwarding traffic nobody asked for, at a moment nobody chose.
- The all-structures wildcard means "every housekeeping report of this
  application process", and it keeps meaning that as structures are
  defined afterwards. It is a state, not an expansion, so it cannot be
  held together with specific identifiers and cannot be partially
  deleted.
- A definition can be deleted while a selection still names it. The
  selection is then stale: it forwards nothing, it is invisible in the
  downlink, and it will start forwarding again the moment the
  identifier is reused. It is a finding, not a failure, and the
  configuration report has to surface it.
- Requests carry many identifiers and execute per identifier, so the
  response is a disposition list and a rejected item never abandons the
  ones behind it.

## Workflow

1. Validate the definition catalogue and each request item: an
   application process identifier in range, and a structure identifier
   in range when one is named. An absent identifier is the wildcard.
2. Reject an item naming an application process the service does not
   control, before any catalogue lookup.
3. Reject an identifier the catalogue does not define under that
   application process, and check that lookup against the application
   process of the item, not against the union of all of them.
4. Apply an add: set the wildcard by clearing what it subsumes, reject
   an identifier already selected, reject one a live wildcard already
   covers, and turn the sizing limits of the store into per-item
   rejections.
5. Apply a delete: removing the application process entry removes every
   identifier under it; an absent identifier and a partial delete
   inside a wildcard are each rejected.
6. Answer a forwarding question from the wildcard first, then the
   identifier set.
7. Expand the wildcard against the live catalogue when reporting what
   is actually forwarded, and list every stale selection separately.

## Pitfalls

- Selecting housekeeping reports by report type and message subtype.
  That selects all of them or none of them, which is the reason this
  finer configuration exists.
- Treating a structure identifier as global. A selection copied from
  one application process to another will either be refused or, worse,
  accepted against an unrelated structure that happens to share the
  number.
- Expanding the all-structures wildcard into the identifier list when
  it is set. Structures defined later would then not be forwarded,
  which is precisely what the wildcard was chosen to avoid.
- Dropping a stale selection silently when its definition is deleted.
  It reappears as live forwarding if the identifier is ever reused, and
  nobody reviewing the configuration would have seen it coming.
- Reporting only the count of accepted identifiers. The operator needs
  which ones were rejected and why, or the next request repeats the
  same mistake.

## Behavior contract (gate 3)

The catalogue validation, controlled-list check, undefined-structure
refusal, wildcard subsumption, partial-delete refusal, live-catalogue
expansion and stale-selection detection are exercised by the gate 3
contract test:
scripts/test_e7041_managing_the_housekeeping_parameter_report_forward.py
against
scripts/e7041_managing_the_housekeeping_parameter_report_forward_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_housekeeping_parameter_report_forward.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
