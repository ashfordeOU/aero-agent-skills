---
name: q6005-detail-specification-format-deliverable
description: "Verify that a hybrid detailed product specification, delivered as a document, follows the clause skeleton and carries the entries Annex B of ECSS-Q-ST-60-05C prescribes. Use when a draft specification is tabled for acceptance: parse every heading number, refuse a malformed or duplicated one, rebuild the clause tree and report a heading whose parent clause is absent, flag sibling numbering that skips or repeats, hold a heading nested deeper than the layout allows, check each mandated entry appears under the clause that owns it, separate a misfiled entry from a missing one, and return a layout conformance ratio with a verdict. Trigger: ecss, q-st-60-05c-annex-b, hybrid-specification-layout-format, specification-clause-number-tree, specification-sibling-numbering-break, specification-mandated-entry-placement, specification-layout-conformance-ratio."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuit-scope, q6005-detail-specification-format-deliverable, hybrid-specification-layout-format, specification-clause-number-tree, specification-sibling-numbering-break, specification-mandated-entry-placement, specification-layout-conformance-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Detail Specification Layout (space-systems/ecss/q6005-detail-specification-format-deliverable)

Use when the task is the layout step of ECSS-Q-ST-60-05C Annex B —
grading the delivered detailed product specification as a document: is
the numbered clause skeleton well formed, is every template clause
there, and does each mandated entry sit under the clause that owns it,
so the document can be accepted, remarked on, or held.

## Domain quick reference

- The specification's layout is a numbered clause tree two levels
  deep: a top clause and its subclauses. Depth is part of the layout,
  not a drafting preference, so a third level is a finding even when
  the content underneath it is correct.
- Heading numbers are structural data, not labels. A number carries a
  parent path, so 3.2 asserts that clause 3 exists and that 3.1 comes
  before it. Parsing the number into a path is what makes an orphan
  subclause and a skipped sibling detectable at all.
- The template clauses run scope, applicable documents, requirements
  with its general, design-and-construction, electrical,
  mechanical-and-environmental and marking subclauses, quality
  assurance with its screening, lot-acceptance and qualification
  subclauses, and delivery with its packaging and documentation
  subclauses.
- Each template clause owns a named set of entries: the circuit
  designation and intended application under scope, the substrate,
  interconnection and sealing under design and construction, the limit
  table and test conditions under electrical, the screening sequence
  under screening, and so on. Ownership is what makes a misfiled entry
  a distinct finding from a missing one — the content exists, it is
  just not where a reader or an assessor will look for it.
- Three surplus and shortfall groups are kept apart because they route
  differently: a heading belonging to no template clause, an entry
  belonging to no clause at all, and an entry filed under the wrong
  clause. Only the last is a move; the first two are a rewrite or a
  remark.
- Conformance is measured, not asserted. Every template clause and
  every owned entry is one obligation, tree faults are subtracted, and
  the resulting ratio is what the acceptance conversation runs on.

## Workflow

1. Parse each delivered heading number into a clause path, refusing a
   non-numeric, padded or zero component and a number written twice.
2. Rebuild the tree from those paths: report a subclause whose parent
   path was never written, a sibling sequence that does not run from
   one without a gap, and any heading deeper than the layout allows.
3. Map the delivered headings onto the template clauses; report the
   template clauses absent from the draft and the headings that map to
   nothing.
4. Walk the ownership map: an owned entry never written anywhere is
   missing, an owned entry written under another clause is misfiled and
   the finding names the clause it belongs to, and an entry owned by no
   clause is unknown.
5. Refuse an entry filed under two clauses at once — that is an input
   defect, not a layout finding, and silently keeping one copy would
   hide it.
6. Score the conformance ratio over the clause and entry obligations,
   subtracting tree faults, and floor it at zero so a draft bearing no
   relation to the template does not score negative.
7. Return accept when the findings list is empty, accept-with-remarks
   when only unknown entries remain, and hold otherwise.

## Pitfalls

- Comparing heading strings instead of parsing them. "3.10" sorts
  before "3.2" as text, so a string comparison invents a sibling break
  that is not there and misses the one that is.
- Reporting a misfiled entry as missing. The content is written and
  the supplier is owed a move, not a rewrite; merging the two inflates
  the effort estimate and sends the draft back for the wrong reason.
- Accepting an entry filed under two clauses by taking the first. A
  duplicated entry is ambiguous about which clause governs it, and
  resolving that silently is the defect, not the duplication.
- Treating an extra heading as harmless. A clause outside the template
  breaks the numbering a downstream assessor cites against, so it is
  reported even when its content is sound.
- Comparing the conformance ratio with 1.0 by strict equality. It is a
  quotient of counts and can land a few units in the last place away
  from unity; the named tolerance absorbs that.

## Behavior contract (gate 3)

The clause number parsing, tree reconstruction, sibling and depth
checks, template coverage, entry ownership and misfiling split,
conformance ratio and the accept / accept-with-remarks / hold verdict
are exercised by the gate 3 contract test:
scripts/test_q6005_detail_specification_format_deliverable.py against
scripts/q6005_detail_specification_format_deliverable_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6005_detail_specification_format_deliverable.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
