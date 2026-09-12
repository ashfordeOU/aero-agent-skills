---
name: e1024-eicd-element
description: "Use when produce EICDs for space segment elements under ECSS-E-ST-10-24C
  §5.8.3: categorize each interface by type (element-to-element or element-to-launcher),
  verify that all required identification fields are populated, confirm characteristic
  coverage across the applicable physical media families (mechanical, electrical,
  thermal, data, RF), and cross-check that every interface characteristic entry
  carries at least one linked verification provision. Flag EICDs with missing fields,
  unrecognized interface types, uncovered characteristic families, or characteristics
  lacking verification linkage. Use across all space segment element boundary interfaces
  throughout the EICD preparation and review lifecycle. Trigger: ecss,
  e-st-10-system-scope, eicd, element-interface, element-to-launcher,
  interface-control-document, interface-identification, verification-linkage."
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
  tags: [ecss, e-st-10-system-scope, eicd, element-interface, element-to-launcher, interface-control-document, interface-identification, verification-linkage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Control — EICD at Space Segment Element Level (space-systems/ecss/e1024-eicd-element)

Use when the task is producing or reviewing External Interface Control Documents
(EICDs) at the space segment element level per ECSS-E-ST-10-24C §5.8.3 —
covering element-to-element interfaces and element-to-launcher interfaces.

## Domain quick reference

- §5.8.3 requires an EICD for every physical boundary between two space segment
  elements and for every boundary between a space segment element and the launch
  vehicle. Each EICD is an interface-type record with a unique identifier, both
  sides named (provider and consumer), a set of interface characteristics grouped
  by physical medium family, a list of applicable requirement references, and a
  verification provision entry for every declared characteristic.
- Interface types are categorized into two groups: `element_to_element` (two
  space segment elements sharing a boundary) and `element_to_launcher` (a space
  segment element at the launch vehicle interface). Any interface record whose
  type falls outside these two groups is uncategorized and must be resolved
  before the EICD is accepted.
- Physical medium families for characteristic coverage include mechanical (loads,
  envelope, mass, centre of gravity), electrical (power bus, grounding, EMC),
  thermal (heat flux, temperature range, conductance path), data (protocol, rate,
  format, timing), and RF (frequency band, EIRP, polarisation). A required family
  with no characteristic entry is a coverage gap that must be closed.
- Every characteristic carries a unique identifier. Each such identifier must
  appear in at least one verification provision record (analysis, test, inspection,
  or review of design). A characteristic with no linked provision is a traceability
  gap that blocks EICD acceptance.

## Workflow

1. Identify every interface boundary within the space segment and between the
   space segment and the launch vehicle. Assign each boundary an interface record
   with a unique `interface_id`, the `interface_type`, and the identifiers of
   both the provider element and the consumer element (or the launcher).
2. For each interface record, categorize its `interface_type` as
   `element_to_element` or `element_to_launcher`; reject and escalate any record
   whose type is outside these two groups before proceeding.
3. Check the completeness of every required EICD field:
   `interface_id`, `interface_type`, `provider_element_id`,
   `consumer_element_id`, `characteristics`, `requirement_refs`, and
   `verification_provisions`. Record every missing or empty field as a finding.
4. For each interface record, determine which physical medium families are
   applicable (mechanical, electrical, thermal, data, RF) and verify that at
   least one characteristic entry exists for each required family. A family with
   no entry is flagged as an uncovered family.
5. For every characteristic entry (identified by `char_id`), verify that at
   least one verification provision record references that `char_id`. Collect
   all `char_id` values with no matching provision as unlinked characteristics.
6. Aggregate findings per EICD record. An EICD is compliant under §5.8.3 when
   missing fields, uncategorized type, uncovered families, and unlinked
   characteristics are all empty.

## Pitfalls

- Treating an unknown interface type as defaulting to `element_to_element` —
  an ambiguous boundary categorization propagates errors into the requirement
  and verification trees; it must be resolved explicitly, not defaulted.
- Omitting the launcher interface EICD because the launch vehicle is provided
  by a separate authority — §5.8.3 requires the space segment element side of
  the interface to be documented regardless of who owns the launcher interface
  document on the other side.
- Leaving `requirement_refs` empty because the interface seems self-evident —
  an EICD with no requirement references has no auditable basis and will fail
  a compliance review even if its characteristics are fully described.
- Counting a characteristic as verified simply because a test exists at system
  level — the verification provision must be traceable to the specific
  `char_id` in this EICD; a general test with no linkage does not satisfy the
  check.

## Behavior contract (gate 3)

The interface categorization, EICD completeness, characteristic family coverage,
and verification linkage logic is exercised by the gate 3 contract test:
scripts/test_e1024_eicd_element.py against
scripts/e1024_eicd_element_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_eicd_element.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
