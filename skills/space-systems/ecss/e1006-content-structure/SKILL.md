---
name: e1006-content-structure
description: "Use when verify that a Technical Specification (TS) document satisfies ECSS-E-ST-10C §7.2 overall requirements: confirm the document organisation includes all mandatory sections in the required order, assign section-level responsibility owners, anchor each technical reference to its document identifier, confirm configuration-management baseline tagging, validate section-numbering format, mark supplementary information in dedicated annexes, and apply applicable content-distribution restrictions on the title page. Trigger: ecss, e-st-10-system-scope, technical-specification, ts-organisation, ts-responsibility, technical-reference, configuration-management, supplementary-information, content-restrictions."
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
  tags: [ecss, e-st-10-system-scope, technical-specification, ts-organisation, ts-responsibility, technical-reference, configuration-management, supplementary-information, content-restrictions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — TS Content Structure (space-systems/ecss/e1006-content-structure)

Use when the task is to verify that a Technical Specification document
satisfies the §7.2 overall content-structure requirements of
ECSS-E-ST-10C -- confirming mandatory section organisation, responsibility
assignment, technical-reference anchoring, CM tagging, format compliance,
supplementary-information isolation, and restriction declarations.

## Domain quick reference

- §7.2 identifies seven dimensions every TS must satisfy before it is
  considered structurally complete: organisation (mandatory sections in
  required order), responsibility (each section has a named owner),
  technical reference (every applicable document carries a document ID),
  CM tagging (document number, issue, revision on the title page),
  format (hierarchical numeric section numbering), supplementary info
  (non-normative material placed in lettered annexes), and restrictions
  (distribution or export restrictions explicitly declared).
- The five mandatory section keys are: scope, applicable_documents,
  terms_and_definitions, requirements, and verification. These must
  appear in this sequence; additional sections may be interspersed.
- Technical references must carry their ECSS or project document number;
  a title alone is not sufficient to anchor a requirement to a specific
  document version.
- CM tagging requires doc_number, issue, and revision to be present on
  the document title page; absence of any field is flagged as a finding.
- Annexes housing supplementary information must each carry a single
  uppercase-letter identifier (A, B, C, ...); numeric annex identifiers
  do not conform to the §7.2 format rule.

## Workflow

1. Collect the ordered list of section keys from the TS draft and pass
   it to validate_organisation; resolve any missing-section or
   out-of-order violations before proceeding to subsequent checks.
2. For each section record its responsibility owner; pass all section
   records to check_responsibility and assign owners where flagged as
   missing or empty.
3. Extract every entry from the applicable-documents table; pass the
   list to check_technical_references and obtain document IDs for any
   entry returned as a finding.
4. Read the document title-page metadata (doc_number, issue, revision);
   pass it to check_cm_tagging and update the title page to resolve
   any missing-field findings.
5. Collect all body section numbers (not annex letters) and pass them
   to validate_section_numbering; renumber any non-conforming entry to
   hierarchical numeric format (e.g. "3.2.1").
6. Collect all annex descriptors (key, letter) and pass them to
   check_supplementary_info; assign or correct single uppercase-letter
   identifiers for any flagged annex.
7. Examine the document-level metadata for restriction markers; pass it
   to check_restrictions and add a restriction_statement to the title
   page for any document marked restricted without a declaration.
8. Call full_ts_structure_review to aggregate all seven dimensions and
   confirm is_ts_structure_compliant returns True before the TS is
   submitted for review.

## Pitfalls

- Treating the presence of a section heading as equivalent to a section
  key in the mandatory set -- the five mandatory keys must be present
  by their canonical identifiers, not by approximate title matching.
- Assigning a single responsibility owner to the entire document rather
  than per section -- each section must have its own named owner so
  that traceability is maintained when sections are updated independently.
- Listing a technical reference by title only -- without a document
  identifier the reference cannot be resolved or version-controlled and
  is treated as incomplete regardless of how descriptive the title is.
- Using numeric identifiers for annexes (e.g. "Annex 1") rather than
  uppercase letters -- the §7.2 format rule requires lettered annexes;
  numeric ones do not conform and are flagged.
- Marking a document as restricted without writing the restriction
  statement on the title page -- the restriction_statement field must
  be explicitly populated; a restriction marker alone is not sufficient
  for traceability and the check will flag the omission.

## Behavior contract (gate 3)

The organisation-validation, responsibility-check, technical-reference-
check, CM-tagging, section-numbering, supplementary-info, and restriction
logic is exercised by the gate 3 contract test:
scripts/test_e1006_content_structure.py against
scripts/e1006_content_structure_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_content_structure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
