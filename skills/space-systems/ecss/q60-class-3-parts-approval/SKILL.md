---
name: q60-class-3-parts-approval
description: "Determine which components proposed for a Class 3 application the customer has to review, and what their approval actually says. Use when a proposed Class 3 parts list is submitted or its approval file is reviewed: read each part against the rules that invoke customer review rather than assuming every part needs it, hold an invoked part to its submission dossier item by item, treat customer silence past the response window as pending rather than as consent, honour a restriction attached to an approval until it carries an implementation record, refuse a part the customer declined, and report both the part-level status and whether the list may be used. Trigger: ecss, ecss-q-st-60c-clause-6-2-4, class-3-parts-approval, class-3-customer-review-invocation, class-3-approval-submission-dossier, class-3-customer-response-window, class-3-approval-restriction-closure."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-3-parts-approval, ecss-q-st-60c-clause-6-2-4, class-3-parts-approval, class-3-customer-review-invocation, class-3-approval-submission-dossier, class-3-customer-response-window, class-3-approval-restriction-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 3 EEE Parts — Customer Approval (space-systems/ecss/q60-class-3-parts-approval)

Use when the task is clause 6.2.4 of ECSS-Q-ST-60C — the review and approval
the customer invokes over components proposed for a Class 3 application, and
what a project may do with a part while that review is outstanding.

## Domain quick reference

- Class 3 review is invoked, not universal. The first question is never
  whether a part is approved but whether anything about it put it in front of
  the customer at all. A part that invoked nothing is usable on the project's
  own authority, and the answer says so rather than leaving it unresolved.
- What invokes the review is a property of the part and its use, not of the
  buyer's caution: an unpreferred source, a part type the project has not
  carried before, a plastic-encapsulated part sitting in a critical function,
  a use outside the published derating rules, a sole source with no alternate.
  Every rule a part triggered is reported, because each one is a separate
  thing the customer is being asked about.
- The submission is what the decision is taken against. It owes the circuit
  function, the source and route, the reason this assurance category is
  adequate for that use, and whatever quality and test evidence exists. Each
  absent item is a separate gap with a separate repair.
- An approval granted on an incomplete dossier does not release the part. A
  decision nobody can reconstruct afterwards is not an auditable decision,
  however favourable it was.
- Silence is not consent. A submission carrying no decision is pending, and
  stays pending once the response window has run out. An elapsed window is an
  escalation to raise, not an approval to assume.
- A restriction attached to an approval releases nothing until it carries an
  implementation record. Restricted is a state, not a slower kind of release.
- A refusal binds whatever else the file contains.
- One blocked part blocks the list, so the part-by-part result and the
  list-level result are both reported.

## Workflow

1. Take the proposed parts list and read each entry: part number, declared
   assurance category, and which invocation rules are true of it.
2. Confirm the entry is declared at the category this check releases; a part
   carried at another category is not reviewed here.
3. Collect every invocation rule the part triggered. None triggered means the
   part is usable without a customer review, and that is the verdict.
4. For an invoked part, look for a submission at all. One with none is named
   rather than counted as merely incomplete.
5. Check the submission dossier item by item, collecting every absent item
   instead of stopping at the first.
6. Read the customer decision. A refusal blocks; silence is pending; an
   approval is only an approval on a complete dossier.
7. For silence, compare elapsed time with the response window, absorbing a
   case that lands exactly on the edge with a named tolerance rather than by
   moving the edge.
8. For a restricted approval, walk its restrictions and require an
   implementation record on each one.
9. Return a status per part, the fraction of the list the customer was asked
   about, and a single list-level verdict, with every finding attached to the
   part number it belongs to.

## Pitfalls

- Submitting every Class 3 part for review because Class 1 and Class 2 work
  that way. The clause is an invoked review, and treating it as universal
  buries the parts that genuinely need a customer decision.
- Treating an uninvoked part as unresolved. It is usable, and saying nothing
  about it leaves a buyer waiting for an answer that will never come.
- Reporting the first invocation rule only. Several can be true at once and
  the customer is being asked about each of them.
- Accepting an approval granted against a dossier missing half its items.
  A review that could not be performed is not a review that passed.
- Reading customer silence as consent because the window has run out. An
  elapsed window is a reason to escalate, not a decision.
- Counting a restricted approval as a release with paperwork still to follow.
  Until the implementation records exist the part is not released.
- Letting a complete dossier override a refusal. The decision is the
  customer's, not the file's.
- Reviewing a part carried on the components list at another assurance
  category on the strength of a submission that looked complete.
- Reporting one blocking reason per part. A missing dossier item and an open
  restriction are separate repairs and both have to be named.

## Behavior contract (gate 3)

The invocation rule set, submission completeness, customer decision handling,
response window with its tolerance, restriction closure rule, category check,
invoked fraction and list-level verdict are exercised by the gate 3 contract
test: scripts/test_q60_class_3_parts_approval.py against
scripts/q60_class_3_parts_approval_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_3_parts_approval.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
