---
name: q1009-minor-disposition
description: "Evaluate a proposed disposition for a minor nonconformance under ECSS-Q-ST-10-09 clause 5.2.2.4 before the supplier board signs it off. Use when a minor departure has been categorized and somebody has written rework, repair, use-as-is, return to supplier or scrap against it. Tests three things that fail independently of each other: whether the item can physically carry that disposition at all, whether the supplier board may authorize it or the case rises to the customer board on a permanent departure against a customer-controlled requirement or on customer-furnished property, and whether the documented conditions that disposition owes are all present. Trigger: ecss, q-st-10-09, minor-nonconformance-disposition, nrb-disposition-authority, use-as-is-authorization, repair-limitation-record, scrap-of-customer-furnished-property, disposition-evidence-set."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-minor-disposition, minor-nonconformance-disposition, nrb-disposition-authority, use-as-is-authorization, repair-limitation-record, disposition-evidence-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Minor Disposition (space-systems/ecss/q1009-minor-disposition)

Use when the task is the disposition step of ECSS-Q-ST-10-09 clause
5.2.2.4 — settling what happens to an item carrying a minor departure,
who may say so, and what the decision has to leave behind.

## Domain quick reference

- Five dispositions are on the table and they are not interchangeable.
  Rework restores full conformance and the departure disappears from the
  delivered item. Repair leaves the item serviceable but permanently
  different from its drawing. Use-as-is leaves it untouched and
  permanently different. Return sends it back to whoever supplied it.
  Scrap removes it from the programme.
- Availability comes before authority. Rework needs a departure that can
  actually be reversed; a shortened fastener cannot be lengthened, so
  rework is not a choice there, it is a wish. Repair needs an item that
  can be repaired. Return needs somebody else to have supplied it.
  Checking the authority of a disposition the item cannot carry wastes
  the board's time on the wrong question.
- Minor is the supplier board's to dispose of, but not unconditionally.
  Two cases rise to the customer whatever the category: a repair or
  use-as-is against a requirement the customer controls, because the
  customer is the one being handed a permanently different item; and the
  scrapping of customer-furnished property, because it is not the
  supplier's to destroy.
- Authority is an ordered scale, not a label. The customer board may
  take a case the supplier board could have taken; the supplier board
  may not take one that rose. Testing equality instead of rank rejects
  perfectly valid customer approvals.
- Every disposition owes a different evidence set, and the sets differ
  because the question each one has to answer years later differs. A
  rework has to show conformance was restored. A repair has to show the
  repair design was justified and the limitation recorded against the
  affected units. A use-as-is has to show the justification and the
  effectivity. A return has to show where the item went. A scrap has to
  show it was authorized, physically removed and replaced.
- The effectivity list is what makes a permanent departure findable
  later. A repair recorded without it leaves a fleet in which nobody can
  say which units are different.

## Workflow

1. Validate the case: the severity category, the proposed disposition,
   the five item properties that decide availability, the evidence
   assembled and the authority that approved it. An unanswered property
   is an input error, not a false.
2. Derive the dispositions the item can carry and refuse a proposal
   outside that set, naming what is available instead.
3. Derive the authority the case needs, and name every reason it rose —
   a case can rise on more than one ground, and each is reviewed
   separately.
4. Compare the approving authority against the needed one on rank, so a
   higher board's approval satisfies a lower requirement.
5. Test the evidence against the set the chosen disposition owes; a
   present-but-false evidence flag counts as missing, which is what a
   signed-off checklist with an unticked box actually means.
6. Report authorized only when the disposition is available, the
   authority is satisfied and the evidence is complete, and flag
   separately whether the item leaves with a permanent departure.

## Pitfalls

- Writing rework on an irreversible departure because rework is the
  disposition nobody has to justify. The item ships unchanged and the
  paperwork says it was corrected.
- Disposing of a use-as-is internally because the departure was minor.
  The category decides the severity, not who owns the requirement being
  departed from; a customer-controlled requirement makes it the
  customer's call however small the departure.
- Scrapping customer-furnished property on an internal signature. The
  material was never the supplier's to dispose of, and the finding
  outlives the item.
- Testing the approving authority for equality with the needed one. A
  customer board signature then fails a case it comfortably covers, and
  the board is reconvened for nothing.
- Recording a repair without the effectivity list. The limitation exists
  and nobody can say which serial numbers carry it, so every later query
  about the fleet is answered by inspection.
- Treating an unticked evidence box as an absent question. It is a
  question that was asked and answered no, which is exactly the case the
  completeness check exists to catch.

## Behavior contract (gate 3)

The case validation, the availability derivation, the authority
escalation rules, the ranked authority comparison, the per-disposition
evidence sets and the overall authorization verdict are exercised by the
gate 3 contract test: scripts/test_q1009_minor_disposition.py against
scripts/q1009_minor_disposition_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_minor_disposition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
