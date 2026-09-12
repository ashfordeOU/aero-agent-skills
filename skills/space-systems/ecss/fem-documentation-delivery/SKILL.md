---
name: fem-documentation-delivery
description: "Use when verify the FEM documentation and delivery package for a structural model under ECSS-E-ST-32C model documentation and delivery requirements: determine which document types the delivery set must contain (model description, element quality report, material property record, coordinate system description, load case list, mass properties check), confirm each document carries mandatory metadata fields and a model revision consistent across the package, identify any missing document type, absent metadata field, revision mismatch, or missing required file, and assess whether the package is delivery-compliant. Trigger: ecss, e-st-32-structures-scope, fem, finite-element-model, fem-documentation, model-delivery, mmdd, structural-analysis, model-description."
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
  tags: [ecss, e-st-32-structures-scope, fem, finite-element-model, fem-documentation, model-delivery, mmdd, structural-analysis, model-description]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — FEM Documentation and Delivery (space-systems/ecss/fem-documentation-delivery)

Use when the task is to verify that a finite element model delivery
package satisfies the ECSS-E-ST-32C model documentation and delivery
(MMDD) requirements — confirming that all required document types are
present, that each document carries its mandatory metadata fields with a
consistent model revision across the package, and that all required FEM
files are included.

## Domain quick reference

- The MMDD requirements define two categories of deliverable: a set of
  required document types (model description, element quality report,
  material property record, coordinate system description, load case
  list, mass properties check) that must all be present in every FEM
  delivery, and a set of optional document types (modal analysis
  summary, boundary condition description, model correlation report,
  sensitivity analysis report) that may appear but are not mandatory.
  A document type outside both known sets is not a recognized MMDD
  deliverable and must be flagged before the package is accepted.
- Each document in the delivery set must carry a fixed group of
  metadata fields: a unique document identifier, a document revision
  mark, the FEM model identifier the document describes, the model
  revision the document corresponds to, the responsible author, and the
  issue date. A document missing any of these fields is incomplete and
  non-compliant, regardless of its content.
- All documents in a delivery package must carry the same model
  revision mark. A revision mismatch across documents signals that at
  least one document was produced against a different model revision and
  the package is internally inconsistent; the finding captures all
  revision marks seen and the document-to-revision mapping so the
  inconsistent document can be identified and updated.
- The file delivery check confirms that at minimum an FEM input file
  and a documentation package bundle are present in the set of delivered
  files. File format or internal correctness is outside this check; the
  MMDD delivery check only verifies presence by file type.

## Workflow

1. Inventory every document in the delivery package. For each document,
   resolve its document type against the recognized type set (required
   or optional); reject the package immediately if any document carries
   an unrecognized type — such a document cannot be assessed against
   MMDD criteria.
2. Compare the set of document types present against the required type
   set; produce one finding for each required type that is absent from
   the package. Optional types that are absent are not findings.
3. For each document, check that all mandatory metadata fields are
   populated (document identifier, revision, model identifier, model
   revision, author, date); produce one finding per absent field, keyed
   to the document.
4. Collect the model revision mark from every document and check
   uniformity. If any document is missing its model revision field,
   raise an error — the consistency check cannot proceed without it.
   If more than one distinct revision mark appears, produce a revision
   mismatch finding that lists all revision marks found and maps each
   document to its revision.
5. Check that all required file types are present in the delivered file
   set (FEM input file, documentation package bundle); produce one
   finding for each missing file type.
6. Aggregate the findings from all four checks (completeness, metadata,
   consistency, file delivery). The package is MMDD-delivery-compliant
   only when every finding list is empty.

## Pitfalls

- Accepting a package as complete because optional documents are
  present while a required type is absent — the MMDD completeness gate
  covers required types only; optional types do not substitute for
  required ones.
- Reading a document with partial metadata as satisfactory because the
  most visible fields (document identifier, revision) are populated —
  the compliance check requires every mandatory field, including model
  identifier, model revision, author, and date; a single absent field
  is a finding.
- Running the revision consistency check and reporting "consistent"
  when only a subset of documents carry a model revision field — a
  document without the model revision field is an error that must be
  raised before the consistency result is reported; dropping the
  document from the comparison instead masks the problem.
- Treating the file delivery check as a content or format check — the
  MMDD file delivery step checks only that a file of each required type
  was submitted; internal correctness of the FEM input deck or the
  documentation bundle is out of scope for this check and is handled
  by the content quality and element quality checks in adjacent ECSS
  leaves.

## Behavior contract (gate 3)

The document-type validation, metadata field check, document
completeness assessment, revision consistency verification, file
delivery confirmation, and package compliance aggregation logic are
exercised by the gate 3 contract test:
scripts/test_fem_documentation_delivery.py against
scripts/fem_documentation_delivery_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_fem_documentation_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
