---
name: e1006-purpose
description: "Use when assess the purpose, chain position, and content model of an ECSS Technical Specification (TS) per ECSS-E-ST-10C §4: determine whether each TS section belongs to the general part (scope, applicability, normative references, terms and definitions, product definition) or the requirements part (technical requirements, verification requirements, interface requirements, design requirements), identify the TS issuer and recipient roles in the customer–supplier chain, and verify that all mandatory sections are present before placing the TS under configuration control. Trigger: ecss, e-st-10-system-scope, technical-specification, ts-purpose, ts-content-model, customer-supplier-chain, general-part, requirements-part, ts-completeness."
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
  tags: [ecss, e-st-10-system-scope, technical-specification, ts-purpose, ts-content-model, customer-supplier-chain, general-part, requirements-part]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Technical Specification Purpose and Content Model (space-systems/ecss/e1006-purpose)

Use when the task is to assess the purpose, chain position, or content
model of an ECSS Technical Specification (TS) per ECSS-E-ST-10C §4 --
determining which part of the TS a given section belongs to, identifying
the issuing and receiving roles in the customer-supplier chain, and
verifying that all mandatory sections are present.

## Domain quick reference

- ECSS-E-ST-10C §4 establishes that a TS is the supplier-issued document
  capturing the agreed technical baseline at a customer-supplier interface.
  It is the contractual anchor for the technical content of the product
  being delivered; the supplier creates and maintains it under
  configuration control, and the customer reviews and formally accepts
  it at the agreed milestone.
- The TS content model has two parts. The general part (scope,
  applicability, normative references, terms and definitions, and
  optionally product definition, document structure, abbreviations)
  frames the document and establishes its context without containing
  binding requirements. The requirements part (technical requirements,
  verification requirements, and optionally interface requirements,
  design requirements, performance requirements, functional requirements)
  carries all binding technical content. Every section of a TS belongs
  to exactly one part; a section outside both recognized sets is not
  a valid TS section under §4.
- In a multi-level customer-supplier chain, the same organization can
  sit in a dual position: it issues a TS to its own customer and
  simultaneously receives a TS from each of its sub-suppliers. Each TS
  is independent and maintained separately at its respective interface.
  An organization acting solely as a customer does not issue a TS at
  that interface; it receives and reviews one.

## Workflow

1. For each section in the TS under review, determine which part it
   belongs to: general part if it frames context (scope, applicability,
   normative references, terms and definitions, product definition,
   document structure, abbreviations); requirements part if it carries
   binding technical content (technical requirements, verification
   requirements, interface requirements, design requirements, performance
   requirements, functional requirements). Reject any section type
   outside both recognized sets before it is included in the assessment.
2. Check that all mandatory sections are present: the general part
   requires scope, applicability, normative references, and
   terms_definitions; the requirements part requires technical_requirements
   and verification_requirements. Record every absent mandatory section
   as a structural finding; do not mark the TS structurally complete
   until the finding list is empty.
3. Identify the organization's position in the customer-supplier chain at
   this interface: supplier (issues the TS, maintains it under config
   control), customer (receives and reviews the TS, formally accepts at
   the milestone), or both (dual position at an intermediate level of a
   decomposed chain -- issues one TS upstream and receives at least one
   downstream). Record the chain position alongside the TS assessment.
4. Aggregate the structural findings per TS document. A TS is structurally
   complete only when the missing-sections list and the findings list are
   both empty and a valid chain position has been recorded.

## Pitfalls

- Treating the general part as normatively void -- the general part
  provides the scope of applicability that governs which requirements in
  the requirements part apply to a given product variant; an incomplete
  or ambiguous general part can silently exclude a requirement.
- Omitting the verification_requirements section on the grounds that
  it will be added later -- §4 requires it as a mandatory section; an
  absent verification_requirements section is a structural finding
  against the TS, not a deferrable action.
- Assuming that an intermediate-level organization in the chain only
  issues or only receives a TS -- at an intermediate level it does both,
  and the upstream and downstream TSs are independent artifacts with
  separate configuration control records.
- Placing a section of unrecognized type into the TS -- any section
  outside the recognized general-part and requirements-part sets must
  be rejected at the structure review; including it masks the fact that
  no §4-defined home exists for its content.

## Behavior contract (gate 3)

The section-categorization, chain-position, missing-section, and
full-structure-assessment logic is exercised by the gate 3 contract
test: scripts/test_e1006_purpose.py against
scripts/e1006_purpose_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
