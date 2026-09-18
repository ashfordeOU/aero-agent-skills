---
name: q6005-identification-form-for-approved-lines
description: "Determine how a hybrid technology identification form is completed when the supplier already holds approved production line status, under ECSS-Q-ST-60-05C clause 6.2.2. Use when an approved line is offered against a hybrid order and the buyer needs to know whether the approval really covers the technologies requested, which entries may be answered by reference to it, and which must still be written out in full. Matches every requested technology against the approval scope, places the order date inside the approval window, grants the reduced entry set only on a clean match, and otherwise falls back to the full form. Trigger: ecss, q-st-60-05, identification-form-for-approved-lines, approved-production-line-status, hybrid-approval-scope-match, reduced-form-entry-set, hybrid-approval-validity-window, hybrid-full-form-fallback."
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
  tags: [ecss, q-st-60-hybrid-procurement-scope, q6005-identification-form-for-approved-lines, approved-production-line-status, hybrid-approval-scope-match, reduced-form-entry-set, hybrid-approval-validity-window, hybrid-full-form-fallback]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Identification Form for Approved Lines (space-systems/ecss/q6005-identification-form-for-approved-lines)

Use when the task is the approved-line case of ECSS-Q-ST-60-05C clause
6.2.2 — the supplier already holds production line approval, and the
question is how much of the technology identification form that approval
actually lets them answer by reference instead of writing out.

## Domain quick reference

- Approval status is a state, not a flag. Pending, suspended and
  withdrawn all look like "has an approval" in a supplier database and
  none of them can carry a reduced form; only a live approval can.
- An approval has a window, and the order has to sit inside it. Two
  different defects hide behind one lapsed answer: an order raised after
  the approval expired, and an order raised before it came into force.
  They lead to different conversations with the supplier, so they are
  reported separately.
- The reduction is granted on a clean match, not on a good one. Every
  technology the order requests has to be inside the approval scope. A
  partial match is the dangerous case, because the entries that would be
  answered by reference are exactly the ones covering the technology the
  approval never looked at.
- A scope wider than the order is not a finding. The approval covering
  technologies this hybrid does not use says nothing about this order;
  only the requested-but-uncovered direction matters.
- Reduction moves entries, it does not delete them. Process flow,
  materials, package and sealing, site and process control are answered
  by reference to the approval; identification, type designation, the
  technology list, the internal component list and the screening and
  qualification reference are still written out, because they are
  specific to this hybrid and not to the line.
- A reduced form owes more than a full one in one respect: it has to
  name the approval and its expiry, so a reader a year later can tell
  what the references point at and whether it was still live when the
  form was completed.
- The fallback is the full form, not a refusal. An approval that cannot
  carry the reduction simply leaves the supplier writing every entry
  out, which is the ordinary route and not a nonconformance in itself.

## Workflow

1. Normalise the line approval state against the closed state
   vocabulary; only the live state can carry anything.
2. Validate the approval window and refuse an expiry that precedes the
   issue date, which is a record defect rather than a lapsed approval.
3. Place the order date in the window and keep the signed remaining-days
   count, so an order that misses is reported as either late or early.
4. Normalise the requested technologies and the approval scope, then
   list the requested technologies the scope does not cover and compute
   the covered percentage.
5. Grant the reduction only when the approval is live, the order is
   inside the window and nothing is uncovered; otherwise take the
   full-form fallback.
6. Derive the entries that may be answered by reference and the entries
   still written out in full for the route actually taken, adding the
   approval reference and expiry entries on the reduced route.
7. Report the demanded entries the submitted form does not carry,
   together with the route, the coverage and an ordered findings list.

## Pitfalls

- Reading any approval record as an approval. A suspended line still has
  an approval number and an expiry date; treating the presence of the
  record as the state is how a suspended line gets a reduced form.
- Granting a proportional reduction on a partial scope match. The
  entries a reduction would cover are precisely the ones describing the
  technology outside the scope, so a partial match has to give nothing.
- Counting a wider scope as a mismatch. The comparison runs from the
  order to the approval, not both ways; flagging unused approved
  technologies buries the real gaps.
- Collapsing early and late orders into one lapsed answer. One means the
  approval has run out and needs renewing; the other means the order
  predates it and the paperwork sequence is wrong.
- Dropping the hybrid-specific entries because the line is approved. The
  approval describes the line, not this hybrid; the type designation,
  technology list and screening reference are not line properties and
  never reduce.
- Omitting the approval reference and expiry from a reduced form. Every
  reduced entry then points at nothing a reviewer can follow, and the
  form cannot be re-checked once the approval moves on.

## Behavior contract (gate 3)

The approval-state normalisation, window validation and placement, scope
matching and coverage, the clean-match reduction decision, the route
selection, the per-route entry sets and the absent-entry report are
exercised by the gate 3 contract test:
scripts/test_q6005_identification_form_for_approved_lines.py against
scripts/q6005_identification_form_for_approved_lines_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_identification_form_for_approved_lines.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
