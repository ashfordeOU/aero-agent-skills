---
name: q6013-internal-supplier-specification-drd
description: "Assess whether a supplier internal specification controls a commercial part purchase as its data item requires under ECSS-Q-ST-60-13C Annex C. Use when a supplier offers its own document in place of a space procurement specification and the buyer must judge it: refuse a specification with no reference or issue, check it fixes the part identification, the site and process baseline, the screening and lot-acceptance operations, the ratings, the marking and traceability rules and the change-notification duty, name the clauses left to supplier discretion, and test every declared limit against the application. Trigger: ecss, q-st-60-13c-annex-c, supplier-internal-specification-drd, commercial-part-purchase-specification-coverage, supplier-specification-change-notification-lead, supplier-specification-discretionary-clause, supplier-specification-application-limit-coverage."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-internal-supplier-specification-drd, commercial-part-purchase-specification-coverage, supplier-specification-change-notification-lead, supplier-specification-discretionary-clause, supplier-specification-application-limit-coverage, supplier-specification-process-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Supplier Internal Specification DRD (space-systems/ecss/q6013-internal-supplier-specification-drd)

Use when the task is the Annex C data item of ECSS-Q-ST-60-13C: a
supplier has offered its own internal specification as the document a
commercial part is bought against, and the question is whether that
document contains enough to control the purchase.

## Domain quick reference

- Accepting a supplier's own specification is accepting the supplier's
  own definition of the part. The data item therefore fixes what the
  document has to carry: the part identification and type, the
  manufacturing site and process baseline, the screening operations, the
  lot-acceptance operations, the electrical limits and ratings, the
  marking and traceability rules, the change-notification duty and the
  storage and handling conditions.
- A clause stated with no text behind it does not control anything. The
  specification reads complete while each clause points nowhere, so a
  blank text reference is an uncontrolled clause and the covered share
  falls accordingly.
- A clause reserved to the supplier's discretion is worse than a clause
  left out. A missing clause is visible to any reader; a clause saying
  the supplier may move the site, revise the process or change the
  screening flow at will looks like control and grants none, so the
  discretionary clauses are named separately and stop the purchase.
- The change-notification duty is the clause that keeps the other seven
  true over time. A notice period shorter than the buyer needs to
  re-qualify, or a notice clause the supplier may waive, leaves the
  specification describing a part that has already moved.
- The specification has to reach the application, not merely exist. Each
  declared limit runs in a direction — a rating the application must not
  exceed, or a capability the application needs at least — and the
  comparison is made in that direction. A demand landing exactly on its
  limit is covered, the tolerance being there to absorb representation
  error rather than to widen the rating.

## Workflow

1. Validate the data-item policy first: the minimum clause coverage, the
   change-notification lead time the buyer needs, whether supplier
   discretion and a non-binding notice are tolerated, and the marginal
   band inside which a covered limit is still advised on. A coverage
   floor above one, a non-positive lead time or a full-width marginal
   band is refused rather than used.
2. Validate the specification identity: a non-blank reference, a
   non-blank issue label, the supplier name and a non-negative notice
   period. An absent document, or one with a blank reference or issue,
   closes the assessment on specification not provided.
3. Validate every clause record: a recognised clause name, no duplicate
   clause, a boolean stated flag, a text reference that may be blank but
   is then read as absent, and a boolean discretion flag. Take the
   covered share over the required clauses, counting only the clauses
   that are stated, backed by text and not discretionary.
4. Name the absent clauses, the uncontrolled ones and the discretionary
   ones separately; a clause can be two of those at once and is reported
   under each.
5. Decide whether the change notice binds: the clause has to be
   controlled and the declared period has to reach the lead time the
   buyer needs.
6. Validate every declared limit — a named parameter declared once, a
   recognised direction, finite specification and application values —
   then compare each in its own direction, collecting the uncovered
   parameters and, among the covered ones, those met with less room than
   the marginal band allows.
7. Close on one verdict in order: specification not provided, clause
   coverage short, clause left to discretion, change notice not binding,
   application limit not covered, or specification accepted for
   purchase. Report the coverage, the named clauses and the limit
   findings alongside it.

## Pitfalls

- Counting a discretionary clause as covered. It is stated and it has
  text, so a naive coverage count passes it; it binds nobody, which is
  why the coverage excludes it and the finding names it.
- Comparing every limit in the same direction. A maximum rating and a
  minimum capability fail in opposite directions, and a single
  greater-than test silently passes half of them.
- Widening a rating to make an exact-boundary demand pass. A demand
  landing on its limit is covered by the tolerance inside the
  comparison; the declared limit stays as the supplier wrote it.
- Accepting the notice period without the notice clause. A generous
  number in the covering letter and a waivable clause in the document
  is the combination that has surprised the most buyers.
- Reporting a bare verdict. The coverage, the discretionary clauses and
  the marginal limits are what the next issue of the specification is
  compared against, and the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, specification identity validation, clause
validation and coverage, the absent, uncontrolled and discretionary
clause findings, the change-notice binding test, the limit validation,
the directional coverage comparison, the marginal-limit advisory and the
purchase verdict are exercised by the gate 3 contract test:
scripts/test_q6013_internal_supplier_specification_drd.py against
scripts/q6013_internal_supplier_specification_drd_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_internal_supplier_specification_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
