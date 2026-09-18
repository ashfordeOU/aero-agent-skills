---
name: q7029-test-report
description: "Document an offgassing test under ECSS-Q-ST-70-29 by assembling the report and checking it holds together: the article and run identification, the product inventory, the concentration table, the toxicity and odour assessments and the stated conclusion, with every product cross-checked across the three tables and every stated total recomputed from the rows it claims to summarise. Use when a completed offgassing campaign must become a traceable report and a conclusion that contradicts its own tables has to be caught before issue. Trigger: ecss, q-st-70-29, offgassing-test-report, offgassing-report-traceability, offgassing-table-cross-check, offgassing-total-recomputation, offgassing-conclusion-consistency, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-test-report, offgassing-test-report, offgassing-report-traceability, offgassing-table-cross-check, offgassing-total-recomputation, offgassing-conclusion-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Test Report (space-systems/ecss/q7029-test-report)

Use when the task is the reporting step of ECSS-Q-ST-70-29: assembling the
identification, quantification and assessment outputs of an offgassing test
into one issued report, and proving that what the report concludes is what its
own tables support.

## Domain quick reference

- A report is evidence, and evidence is traceable. The identification block
  has to carry the article, the batch, the tested mass, the vessel volume, the
  conditioning temperature and duration, and the analytical method, because
  without them the numbers cannot be reproduced or re-graded later.
- The report holds three views of the same set of products: what was
  identified, what each was measured at, and how each was assessed. A compound
  present in one view and absent from another is a defect in the report, and
  it is a defect in both directions — an assessed compound that was never
  quantified is as wrong as a quantified one that was never assessed.
- Every stated total is a derived value. It is recomputed from the rows it
  claims to summarise rather than trusted, and the comparison carries a named
  tolerance for accumulation error, not a tolerance wide enough to hide a
  missing row.
- The conclusion is derived too. It follows from the assessment verdicts, so a
  report stating acceptance while carrying a breached criterion or an open
  item is inconsistent and does not issue.
- An open item is reported as an open item. A product with no limit, a panel
  that was not graded or a peak left unidentified stays visible in the issued
  report rather than being resolved by omission.

## Workflow

1. Validate the identification block: every traceability field present and of
   the right kind, with positive mass, volume, temperature and duration.
2. Validate each of the three tables and refuse a table with duplicate
   compound rows.
3. Cross-check the compound sets in both directions and record every product
   missing from a table it should appear in.
4. Recompute the stated total released mass from the concentration rows and
   compare it with the reported figure under a named tolerance.
5. Recompute the stated governing toxicity total from the assessment rows and
   compare it the same way.
6. Derive the conclusion from the assessment verdicts and the open items, then
   compare it with the conclusion the report states.
7. Return the assembled report, its section inventory, and every finding:
   missing field, orphan row, total mismatch, conclusion mismatch, open item.

## Pitfalls

- Trusting a stated total because it was produced by the same tool that
  produced the rows. A total that is not recomputed is not checked; the whole
  point of the recomputation is that the two paths are independent.
- Cross-checking in one direction only. Walking the identification list and
  looking for concentrations finds the missing measurement but not the
  measured compound that was never identified.
- Widening the total-comparison tolerance until a mismatch passes. The
  tolerance covers accumulation error in a sum of a few dozen rows; a
  discrepancy larger than that is a missing or duplicated row.
- Issuing a conclusion that was written before the assessment finished. The
  stated conclusion has to be compared against the derived one, not adopted
  as the derived one.
- Dropping open items from the issued report because they are not failures.
  An open item is the reader's cue that the assessment is incomplete, and
  removing it converts incompleteness into apparent acceptance.

## Behavior contract (gate 3)

The traceability-field validation, table validation, two-way cross-check,
total recomputation, conclusion derivation and finding assembly are exercised
by the gate 3 contract test: scripts/test_q7029_test_report.py against
scripts/q7029_test_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7029_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
