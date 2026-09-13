---
name: e2001-multipactor-deliverables-per-review
description: "Use when determine which multipactor data-items a project owes at each design-review-gate under ECSS-E-ST-20-01C Annex A: build the deliverable-by-gate schedule for the verification-routes actually in use (multipactor-test, susceptibility-analysis, similarity-justification), audit one gate's submitted set for missing, immature and unplanned entries, enforce the document-maturity each item owes at that gate (draft, issued, approved), score gate-readiness, and roll the whole review-sequence up to the first blocking-gate. Trigger: ecss, e-st-20-electrical-scope, e2001-multipactor-deliverables-per-review, multipactor-deliverables-per-review, design-review-gate-schedule, multipactor-data-item-maturity, multipactor-free-declaration, multipactor-critical-item-list, similarity-justification-dossier, review-sequence-rollup."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-deliverables-per-review, multipactor-deliverables-per-review, design-review-gate-schedule, multipactor-data-item-maturity, multipactor-free-declaration, multipactor-critical-item-list, similarity-justification-dossier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multipactor Deliverables Per Review (space-systems/ecss/e2001-multipactor-deliverables-per-review)

Use when the task is the delivery *schedule* of the multipactor data-items
under ECSS-E-ST-20-01C Annex A -- which multipactor document is owed at
which design-review gate, at what document-maturity, and whether a given
gate's submitted set is complete. What goes *inside* each data-item is a
separate leaf; this one answers when it is due and whether it arrived.

## Domain quick reference

- Annex A binds every multipactor data-item to a point in the review
  sequence. The gates handled here, in order, are the
  system-requirements-review (SRR), the preliminary-design-review (PDR),
  the critical-design-review (CDR), the qualification-review (QR) and the
  acceptance-review (AR). A gate outside that sequence is rejected: the
  schedule cannot place an item against a milestone it does not know.
- The owed set is not fixed -- it follows the verification-routes the
  project actually declared for its multipactor-critical items. Two
  data-items are owed on every route: the multipactor-critical-item-list
  and the multipactor-verification-plan, plus the
  multipactor-free-declaration that closes the verification out. The
  multipactor-test route adds the test-procedure and the test-report; the
  susceptibility-analysis route adds the susceptibility-analysis-report
  and the secondary-emission-yield-data-package; the
  similarity-justification route adds the similarity-justification-dossier.
  An item belonging to a route the project did not declare is not owed,
  and submitting it is an unplanned delivery, not a credit.
- Each data-item carries a delivery window: a first gate at which it is
  first issued and a final gate by which it is approved. Inside that
  window the required document-maturity climbs -- draft at the first
  gate, issued at any intermediate gate, approved at and after the final
  gate. Maturity is ranked (draft < issued < approved), so an item that
  arrives more mature than owed is acceptable, while one that arrives
  less mature is an immature delivery even though it was delivered.
- Gate-readiness is the fraction of the owed set that arrived at or above
  its required maturity. A gate with nothing owed is vacuously ready. The
  readiness comparison against a threshold absorbs floating-point
  representation error, so a set that is exactly complete never fails on
  the last bit of a division.

## Workflow

1. Normalise the declared verification-routes and reject an unrecognised
   route before any schedule is built -- an unknown route would silently
   drop the data-items it owes.
2. Build the deliverable-by-gate schedule: for each gate in the sequence,
   list every owed data-item together with the document-maturity required
   at that gate, skipping items whose first gate has not been reached.
3. Normalise the submitted set for the gate under audit: each entry names
   a data-item from the catalogue and the maturity at which it was
   delivered. Reject an unrecognised data-item id, a missing maturity and
   a duplicate submission of the same item.
4. Compare submitted against owed and split the findings three ways:
   missing (owed, absent), immature (present but below the required
   maturity rank) and unplanned (present but not owed at this gate --
   either not yet due, or belonging to a route the project did not
   declare).
5. Score the gate: readiness is the count of items delivered at or above
   the required maturity over the count owed. The gate is compliant only
   when missing and immature are both empty.
6. Roll the sequence up: evaluate every gate in order, report the first
   gate that is not compliant as the blocking gate, and treat unplanned
   deliveries as observations that do not by themselves block a gate.

## Pitfalls

- Treating the deliverable list as fixed for every project -- the owed
  set is route-dependent, and auditing a similarity-justification case
  against the multipactor-test route's items manufactures false findings
  on the test-procedure and the test-report.
- Counting a delivered item as satisfied without checking its maturity --
  a draft multipactor-free-declaration at the acceptance-review is a
  delivery, not a closure, and the maturity rank is what separates them.
- Reading "no missing items" as gate-compliant while the immature list is
  non-empty -- both lists must be empty, and only one of them is about
  presence.
- Escalating an unplanned early delivery to a finding that blocks the
  gate -- an item delivered ahead of its first gate is recorded as
  unplanned for schedule hygiene, but it is not a shortfall against the
  gate under audit.
- Comparing a readiness fraction to its threshold with a bare inequality
  -- a fully complete gate can compute a fraction a few units in the last
  place below one, so the comparison carries a tolerance rather than the
  engineering criterion being relaxed.

## Behavior contract (gate 3)

The gate normalisation, route-dependent owed-set construction, maturity
ranking, gate audit and review-sequence rollup are exercised by the gate 3
contract test: scripts/test_e2001_multipactor_deliverables_per_review.py
against scripts/e2001_multipactor_deliverables_per_review_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_multipactor_deliverables_per_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
