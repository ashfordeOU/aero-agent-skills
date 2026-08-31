---
name: engineering-report
description: "Use when you must draft or review an engineering report and verify its structure: the required sections (abstract, introduction, method, results, discussion, conclusion, references), abstract length against the recommended 150 to 300 word range, completeness of the deliverable, units and uncertainty statements for every reported value, traceability of results to requirements, review gates, and version control. Produces missing-section lists, abstract-length pass or fail, units-statement pass or fail, uncertainty-statement pass or fail, completeness ratios, and requirement traceability closure lists. Trigger: engineering report, report structure, abstract length, required sections, completeness, units statement, uncertainty statement, traceability, review gate, version control."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: documentation
  tags: [engineering-report, report-structure, abstract-length, required-sections, completeness, units-statement, uncertainty-statement, traceability, review-gate, version-control, documentation]
  version: 0.1.0
  author: AeroSkills
---

# Engineering Report (cross-cutting/documentation/engineering-report)

Use when the task is writing or reviewing an engineering report and
validating its deliverable structure: report anatomy, abstract length,
completeness, units and uncertainty reporting, margin statements,
traceability to requirements, review gates, and version control. This
is the cross-cutting documentation-pack discipline for the report as
a deliverable; margin computation and the margin sentence live in the
engineering-margins leaf, and requirement lifecycle processes live in
the systems-engineering-safety pack.

## Domain quick reference

- Report anatomy, canonical order: abstract, introduction, method,
  results, discussion, conclusion, references. A report is
  structurally complete when all seven are present; extras
  (appendix, nomenclature, acknowledgements) do not count toward the
  anatomy but are allowed.
- Audience and purpose: state the intended reader (review board,
  certification authority, customer, internal team) and the decision
  the report supports. The abstract summarizes purpose, method, key
  results, and conclusion in one paragraph.
- Abstract length: 150 to 300 words is the recommended range. Shorter
  abstracts omit the method or the results; longer ones stop being a
  summary.
- Completeness ratio: required sections present divided by required
  sections, a decimal in [0.0, 1.0]. 1.0 is complete, 0.0 means no
  required section is present.
- Units: every measured or computed value carries its unit (N, Pa,
  kg, m, s, K and derived forms). A value without a unit is not
  reportable. One unit convention per table and per equation.
- Uncertainty: every measured value carries its uncertainty, stated
  as +/- with the same unit, or as a percent, or as a tolerance. A
  bare number without stated variation is not reportable.
- Margin statements: name the margin value, the basis (limit or
  ultimate), and the pass or fail verdict. Example: "Margin of safety
  0.25 (ultimate basis): pass".
- Traceability: each reported result traces to the requirement or
  input it answers. A traceability closure list names the missing
  requirement ids; an empty list means closed.
- Review gates: the report passes a review gate (draft review,
  internal review, release) only when anatomy is complete, values
  carry units and uncertainty, margins are stated with basis and
  verdict, and traceability is closed.
- Version control: the report header carries a revision identifier
  (Rev A, v1.2), the date, and the author. Change history records
  what changed per revision and why.

## Workflow

1. Identify the audience and the decision the report supports; state
   both in the introduction.
2. Lay out the report anatomy with required_sections_verdict: pass
   the section headings present, get the missing list in canonical
   order.
3. Check the abstract with abstract_length_ok against the 150 to 300
   word range.
4. Score the deliverable with report_completeness_score: pass the
   present sections and the required set, get the ratio.
5. Audit every reported value: units_statement_ok for the unit,
   uncertainty_statement_ok for the uncertainty, margin_statement_ok
   for margin statements (value plus basis).
6. Close traceability with traceability_verdict: pass the traced
   requirement ids and the required ids, get the missing list.
7. Write the version control header and the change history, then
   route the report through its review gates.

## Pitfalls

- Counting an appendix or a nomenclature toward the anatomy: only the
  seven canonical sections count for completeness.
- Writing the abstract outside 150 to 300 words: gate it with
  abstract_length_ok, which is inclusive on both bounds.
- Reporting a value without its unit: "The load is 125000" fails
  units_statement_ok. One unit convention per table, never a mix.
- Reporting a measured value without uncertainty: a bare number with
  no +/- , tolerance, or uncertainty statement fails
  uncertainty_statement_ok.
- Writing a margin statement without the basis: "Margin of safety
  0.25" carries no limit or ultimate basis and fails
  margin_statement_ok. The verdict pass or fail follows the sign of
  the margin.
- Confusing the completeness ratio with the anatomy verdict: the
  ratio is a decimal score, the verdict is the missing-section list.
- Shipping without traceability closure: an empty missing list from
  traceability_verdict is the release precondition.
- Skipping the version control header: a revision identifier, date,
  and author must appear in the report header.
- Mixing this leaf with the engineering-margins leaf: margin
  computation and the margin sentence belong to
  engineering-margins; this leaf audits the report structure that
  carries them.

## Behavior contract (gate 3)

The report structure logic is exercised by the gate 3 contract test:
scripts/test_engineering_report.py against
scripts/engineering_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_engineering_report.py

## Compliance

- Standards referenced, not reproduced: SEP-2640 is referenced for
  the delivery context of engineering documentation artifacts
  (skill packages and report deliverables served over MCP); the
  report-writing practice itself is common engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
