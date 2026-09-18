---
name: q6005-supplier-quality-and-technical-audit
description: "Assess an on-site quality and technical audit of a hybrid supplier's production line and decide whether that line supports a category two validation, under ECSS-Q-ST-60-05 clause 6.3.3. Use when the audit evidence has to be graded rather than summarised: require an audit team carrying both a quality auditor and a technology specialist, treat a desk review of a mandatory area as uncovered, score quality-system maturity and technical capability on separate axes so a strong one cannot mask a weak one, count open findings by severity, and return both indices with one verdict and a validity term. Trigger: ecss, q-st-60-05, supplier-quality-and-technical-audit, production-line-audit, quality-system-maturity, technical-capability-score, audit-nonconformity-severity, audit-team-composition, supplier-audit-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-supplier-quality-and-technical-audit, production-line-audit, quality-system-maturity, technical-capability-score, audit-nonconformity-severity, audit-team-composition, supplier-audit-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Supplier Quality and Technical Audit (space-systems/ecss/q6005-supplier-quality-and-technical-audit)

Use when the task is clause 6.3.3 of ECSS-Q-ST-60-05: the on-site examination
of a supplier's production line inside a category two validation — the element
that looks at how the line is run and what it is capable of, rather than at
what came off it.

## Domain quick reference

- The audit answers two different questions and they are scored on separate
  axes. A quality system can be exemplary on a line that cannot hold a wire
  bond, and a line can be technically excellent while nothing about it is
  under control. One blended score lets either failure hide behind the other,
  so each axis carries its own threshold and both have to be met.
- This is an on-site exercise by definition. An area examined from a desk, or
  taken on the supplier's declaration, was not audited in the sense the route
  needs — it counts as uncovered, not as covered more cheaply, and it earns
  nothing on its axis whatever maturity the paperwork claimed.
- The audit team is part of the evidence. Nobody reads a quality system
  without a quality auditor and nobody reads a hybrid line without a
  technology specialist, so a team short of either leaves the audit incomplete
  before any area is scored. An observer does not stand in for either.
- A finding is graded by severity and by whether it was closed before the
  audit was signed. Closure moves a finding out of the open count but never
  out of the record, and an open critical decides the outcome on its own.
- Validity runs from the audit and is cut for each open major, because an open
  major is a standing reason the line may no longer be the line that was
  audited by the time the result is used.

## Workflow

1. Name the supplier and the specific production line; an audit of the company
   is not an audit of the line the product comes off.
2. Validate the audit team and list any required role nobody carries. A gap
   here is an incompleteness, not a weighting.
3. Validate the area records: an area appears once, an unknown area name,
   examination mode or maturity level is an input error, and an area nobody
   mentioned is graded as not examined rather than quietly dropped.
4. Grade each area against the full published set, giving zero credit to
   anything not examined on site and marking a mandatory area seen only from a
   desk as uncovered.
5. Compute the quality-system index and the technical-capability index
   separately, each as weighted credit over that axis's total weight, and test
   each against its own threshold with a named tolerance at the bound.
6. Count the open findings by severity, keeping the closed ones in the record.
7. Cut the validity term for each open major and name the verdict — incomplete
   while a team role or a mandatory area is short, line not supported on an
   axis below threshold, an open critical or an exhausted term, supported with
   open actions when findings remain, supported only when none do.

## Pitfalls

- Averaging the two axes into one audit score. That is exactly the arithmetic
  that lets a strong quality system carry a line that cannot make the product.
- Accepting a desk review of a mandatory area because the supplier sent good
  documentation. The route needs someone standing in front of the process; the
  documentation is what that person checks against, not a substitute for them.
- Auditing the company rather than the line. Certificates belong to the
  organisation; capability belongs to the specific line and shift the product
  is built on.
- Counting a closed finding as though it never happened. Closure changes the
  open count and the validity term, not the record of what the audit saw.
- Sending a team of quality auditors to a hybrid line. Without a technology
  specialist the technical axis is being scored by people who cannot read it.
- Issuing the full validity term with open majors outstanding. Each one is a
  reason the audited line may have moved before the result is used.
- Re-using an audit across a line move, a shift change or a new process
  baseline. Those are the events the audit and its term exist to catch.

## Behavior contract (gate 3)

The team-composition check, area validation, on-site examination rule,
per-axis indices and thresholds, finding-severity counting, validity term and
audit verdict are exercised by the gate 3 contract test:
scripts/test_q6005_supplier_quality_and_technical_audit.py against
scripts/q6005_supplier_quality_and_technical_audit_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_supplier_quality_and_technical_audit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
