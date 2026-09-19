---
name: q6005-data-package-cover-sheets
description: "Verify the summary front pages of a hybrid microcircuit delivery data package against the shipment and the records behind them, under ECSS-Q-ST-60-05 clause 13.2.2. Use when a cover sheet is drafted or received with a batch: test the printed serial range against the units actually delivered, reconcile the enclosure index both ways with what is in the binder, check the declared quantity against the serials and the range span, test the build standard the package points at, grade the front-sheet fields and return the completeness index with one verdict. Trigger: ecss, q-st-60-05, data-package-cover-sheets, hybrid-cover-sheet-fields, hybrid-cover-sheet-serial-range, hybrid-cover-sheet-enclosure-index, hybrid-cover-sheet-quantity-reconciliation, hybrid-cover-sheet-build-standard."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-data-package-cover-sheets, hybrid-cover-sheet-fields, hybrid-cover-sheet-serial-range, hybrid-cover-sheet-enclosure-index, hybrid-cover-sheet-quantity-reconciliation, hybrid-cover-sheet-build-standard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Data Package Cover Sheets (space-systems/ecss/q6005-data-package-cover-sheets)

Use when the task is clause 13.2.2 of ECSS-Q-ST-60-05: the summary pages at
the front of the delivery data package that name the batch, the build standard
it was made to, and everything enclosed behind them.

## Domain quick reference

- A cover sheet is a claim about a package, and a claim can be checked. The
  serial range it prints, the quantity it declares and the enclosures it lists
  are each measurable against the shipment and the binder behind it, so none
  of them is read and accepted.
- The serial range is not decoration. Every delivered unit has to fall inside
  it, and a range that spans numbers no delivered unit carries is a range
  somebody widened instead of counting — it quietly claims units that are not
  in the box.
- The enclosure index is reconciled both ways. A record listed and absent is
  the failure everyone looks for; a record present and unlisted is the one
  that shows the index was written against a different package.
- Quantity is a third statement of the same fact. The declared quantity, the
  serials handed over and the span of the printed range have to agree, and any
  two of them agreeing says nothing about the third.
- The build standard is what makes the package mean anything. Without a
  drawing reference, a drawing issue and a specification reference, the
  enclosed test data belongs to no configuration and evidences nothing.
- An illegible mandatory field is not a missing one. It was produced and
  cannot be used, which is a rejection rather than an assessment that never
  started.
- The format and retention rules the package obeys, the history it carries,
  the certificate of conformity and the packing are graded against their own
  clauses; this leaf grades the front sheet.

## Workflow

1. Name the batch and collect the sheet: printed first and last serial,
   declared quantity, listed enclosures and the build standard it points at.
2. Collect the shipment: the serials actually delivered, and the records
   actually in the binder.
3. Test the range — every delivered serial inside it, and no stretch of
   numbers inside it that no delivered unit uses.
4. Difference the index against the binder both ways and take matched over
   listed as the index agreement ratio.
5. Reconcile the declared quantity against the serial count and against the
   range span, separately.
6. Check the build standard for its drawing reference, drawing issue and
   specification reference.
7. Grade the front-sheet fields against the full published set, so a field
   nobody supplied is graded as absent, and mark the mandatory ones; take
   weighted credit over total weight as the completeness index.
8. Name the verdict — incomplete while a mandatory field is absent, rejected
   on a range mismatch, an unreconciled index, a quantity that does not agree,
   a bare build standard, an illegible mandatory field or a low index,
   acceptable with open actions while findings remain, acceptable when none do.

## Pitfalls

- Checking the index in one direction. Missing enclosures get found because
  somebody goes looking for them; the unlisted extra record sits in the binder
  unnoticed and is the stronger evidence that two lists were kept.
- Reading the serial range as a label. A range printed one wider than the
  batch claims a unit that was never built, and it is the range that later
  reviewers quote.
- Reconciling the quantity against one source. Serial count and range span
  are independent statements, and a cover sheet is wrong if either disagrees.
- Accepting a drawing reference without an issue. A drawing number with no
  issue letter points at every version of the configuration at once.
- Grading the sheet on the fields alone. A cover sheet with every field
  present can still contradict the shipment, and the field grade will not say
  so.
- Treating an illegible field as absent. Absent stops the assessment; an
  illegible mandatory field means the sheet was produced and has to be
  reissued, which is a different action.

## Behavior contract (gate 3)

The serial-range coverage, the two-way enclosure reconciliation, the
three-way quantity check, the build-standard checks, the field grading, the
cover-sheet completeness index and the sheet verdict are exercised by the
gate 3 contract test:
scripts/test_q6005_data_package_cover_sheets.py against
scripts/q6005_data_package_cover_sheets_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_data_package_cover_sheets.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
