---
name: q6005-data-package-general-provisions
description: "Evaluate the baseline format, retention and completeness provisions a hybrid microcircuit delivery data package has to obey, under ECSS-Q-ST-60-05 clause 13.2.1. Use when the accompanying record set is being specified or received: grade the delivery medium of each document against the grade its category demands, measure the declared retention period against the period demanded, reconcile the pages a document promises with the pages that arrived and the pages that arrived unreadable, test the identification each document carries, and return the provision-compliance index with one verdict. Trigger: ecss, q-st-60-05, data-package-general-provisions, hybrid-data-package-medium-grade, hybrid-data-package-retention-shortfall, hybrid-data-package-page-reconciliation, hybrid-document-identification-fields, hybrid-data-package-provision-index."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-data-package-general-provisions, hybrid-data-package-medium-grade, hybrid-data-package-retention-shortfall, hybrid-data-package-page-reconciliation, hybrid-document-identification-fields, hybrid-data-package-provision-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Data Package General Provisions (space-systems/ecss/q6005-data-package-general-provisions)

Use when the task is clause 13.2.1 of ECSS-Q-ST-60-05: the baseline
expectations on how the accompanying record set is supplied, kept and
completed — the rules the package obeys, not the manufacturing history it is
supposed to contain.

## Domain quick reference

- The medium is graded against what the document has to survive being. A
  conformity declaration has to stay authentic for the life of the record; a
  supporting note does not, and holding both to one medium demand is as wrong
  as holding neither to any.
- An editable file is not a record. It carries no evidence that what is read
  today is what was signed, so it is refused for anything that has to be
  relied on rather than merely consulted — and a photocopy of a signature is
  a reference copy, not an original.
- Retention is measured, not asserted. The declared period is subtracted from
  the period the category demands, and the answer is a number of years the
  package is short by, per document, rather than a yes or a no.
- Completeness is a reconciliation of three counts. The pages a document says
  it has, the pages that arrived, and the pages that arrived unreadable are
  different numbers; a document is complete only when the first two agree and
  the third is zero.
- More pages than declared is a finding too. It means the document was
  assembled after its own front sheet was written, and nobody can now say
  which version the issue status belongs to.
- Identification is what lets a loose page be put back. Without a lot
  reference, a document number, an issue status and page totals, completeness
  cannot be checked by anyone who did not assemble the package.
- The history the records are supposed to evidence, the cover sheets, the
  certificate of conformity and the packing are graded against their own
  clauses; this leaf grades the provisions the package is held to.

## Workflow

1. Name the package and collect its documents: category, medium, declared
   retention, the three page counts, and the identification each one carries.
2. Grade each document's medium against the grade its category demands and
   refuse anything below it outright.
3. Subtract the declared retention from the demanded retention per category
   and record the shortfall in years, keeping the worst across the package.
4. Reconcile the pages: declared against supplied, then supplied against
   unreadable, and derive the usable page ratio from both.
5. Check the four identification fields on every document and raise one
   finding per field that is absent.
6. Grade the package-level provisions against the full published set, so a
   provision nobody declared is graded as not declared, and mark the
   mandatory ones.
7. Take weighted credit over total weight as the provision-compliance index.
8. Name the verdict — incomplete while a mandatory provision is undeclared,
   not met on any non-conforming document, a deficient mandatory provision or
   a low index, met with open actions while findings remain, met only when
   none do.

## Pitfalls

- Applying one medium rule to the whole package. The demand follows the
  document category, and a package that upgrades supporting notes to signed
  originals while accepting a scan of the conformity declaration has spent
  effort in exactly the wrong place.
- Reading the retention period as a tick box. The useful answer is the
  shortfall in years, because that is what the recovery action has to close
  and what the next reviewer will be told.
- Reconciling pages against the supplied count alone. A document can arrive
  whole and unusable; the unreadable count is a third number and it is the
  one nobody records.
- Treating a surplus page as harmless. It says the document grew after its
  front sheet was frozen, which puts the issue status in doubt for every page.
- Assuming an index of contents implies identification. The index lives at
  the front of the package; the identification has to live on each document,
  or a page separated from the binder is anonymous.
- Grading this clause on content. Whether the records evidence the
  manufacture and test history is the parent clause's question; a package can
  be flawlessly formatted and evidence nothing.

## Behavior contract (gate 3)

The medium grading, the retention shortfall, the three-count page
reconciliation, the identification checks, the per-document verdicts, the
provision grading, the provision-compliance index and the package verdict are
exercised by the gate 3 contract test:
scripts/test_q6005_data_package_general_provisions.py against
scripts/q6005_data_package_general_provisions_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q6005_data_package_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
