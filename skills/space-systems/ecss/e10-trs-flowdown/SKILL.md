---
name: e10-trs-flowdown
description: "Use when flowing customer technical requirements down to next-lower-level technical requirements specifications (TRS) per ECSS-E-ST-10C clause 5.2.3.1: check every customer TS requirement reaches at least one child TRS, that no child TRS value contradicts the parent TS or a sibling TRS, and that each TRS carries the document structure expected by E-ST-10-06. Trigger: ecss, e-st-10c, trs flowdown, technical requirements specification, requirement flow-down, customer TS, next-lower-level requirements, e-st-10-06."
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
  tags: [ecss, e-st-10c, trs, flowdown, requirements, e-st-10-06]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS TRS Flow-Down (space-systems/ecss/e10-trs-flowdown)

Use when the task is establishing next-lower-level technical
requirements specifications (TRS) from a customer technical
specification (TS) under ECSS-E-ST-10C clause 5.2.3.1: one TRS per
product/configuration item, kept consistent with the customer TS and
with each other, and structured per E-ST-10-06.

## Domain quick reference

- Flow-down takes the customer TS for a product and produces one TRS
  per next-lower-level product (configuration item); each TRS must
  stay consistent with the parent TS and with sibling TRS documents
  at the same level.
- A requirement "flows down" when at least one child TRS explicitly
  carries it (by shared requirement identifier); a TS requirement
  with no child carrying it has not been flowed down.
- Consistency has two directions: parent-child (a TRS value must not
  contradict the TS value for the same requirement id) and sibling
  (two TRS documents must not assign different values to a
  requirement id they both carry).
- E-ST-10-06 governs TRS document structure; at minimum a conformant
  TRS states its scope, the applicable/reference documents it
  depends on, its requirement set, and how each requirement will be
  verified.
- This leaf checks flow-down completeness and consistency and DRD
  section presence; it does not allocate requirements to functions
  (see e10-req-allocation), build the specification tree
  (e10-spec-tree), or resolve general internal inconsistencies
  (e10-req-consistency).

## Workflow

1. Collect the customer TS requirement set (requirement id -> value)
   for the product being decomposed.
2. Collect each next-lower-level TRS as: the DRD sections present,
   and its requirement set (requirement id -> value), for every
   product/configuration item at that level.
3. Check DRD section presence for each TRS against the minimum
   section set; list any missing sections.
4. Check flow-down coverage: every TS requirement id must appear in
   at least one TRS's requirement set; list any that do not.
5. Check parent-child consistency: for a requirement id carried by
   both the TS and a TRS, the values must match; list mismatches.
6. Check sibling consistency: for a requirement id carried by more
   than one TRS, the values must match across TRS documents; list
   mismatches.
7. Flow-down is ready only when there are no missing sections, no
   coverage gaps, and no parent-child or sibling conflicts; otherwise
   report the specific issues found for correction before proceeding
   to consolidation (e10-req-consolidation) and sign-off
   (e10-req-agreement).

## Pitfalls

- Marking flow-down complete while a TS requirement has not been
  picked up by any child TRS (silent coverage gap).
- Letting a TRS restate a parent requirement with a changed value
  without recording it as a deliberate, agreed deviation.
- Two sibling TRS documents assigning different values to a shared
  requirement (e.g. a common interface constraint) without
  reconciliation.
- Treating a TRS as flow-down-complete when it is missing the
  scope, applicable-documents, requirements, or verification
  sections expected of a technical requirements specification.

## Behavior contract (gate 3)

The section-check, coverage, and consistency logic is exercised by
the gate 3 contract test: scripts/test_e10_trs_flowdown.py against
scripts/e10_trs_flowdown_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_trs_flowdown.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
