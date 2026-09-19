---
name: q6005-rejected-lot-disposition
description: "Evaluate what may be done with a hybrid microcircuit batch that has been refused under ECSS-Q-ST-60-05C clause 10.4.3: test each disposition route — rework and resubmission, screening to a lower grade, return to the manufacturer, use as is under a customer waiver, and scrapping — against the rejection context, report the conditions keeping each closed, keep scrapping as the always-open fallback, treat customer notification as unconditional and prior, and recommend the first open route with the approvals and records it drags with it. Use when a rejected lot needs a decision. Trigger: ecss, q-st-60-05c, rejected-hybrid-lot-disposition, rework-and-resubmit-route, screen-to-lower-grade-route, scrap-and-deface-record, customer-notification-of-rejection."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-rejected-lot-disposition, rejected-hybrid-lot-disposition, rework-and-resubmit-route, screen-to-lower-grade-route, scrap-and-deface-record, customer-notification-of-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Disposition of a Refused Lot (space-systems/ecss/q6005-rejected-lot-disposition)

Use when the task is deciding what happens to a hybrid microcircuit batch
that has already been declared unacceptable under ECSS-Q-ST-60-05C clause
10.4.3 — which recovery routes are open, what closes them, and what each one
obliges before it can be taken.

## Domain quick reference

- Rejection and disposition are two decisions, taken in that order. The first
  says the batch is unacceptable; the second says where the material goes.
  Merging them is how a lot gets quietly reworked before anyone has recorded
  that it failed.
- The routes are ordered by how much of the material they recover: rework and
  resubmit, screen to a lower grade, return to the manufacturer, use as is
  under a waiver, scrap. Preference is not permission — a preferred route that
  fails its conditions is closed, and the order only decides between routes
  that are genuinely open.
- Rework is bounded by three independent things: the failure mode has to be
  the kind that rework addresses, the assembly stage reached has to still
  permit the work, and the units have to have repair allowance left. A
  lot-wide materials or design defect fails all of these at once, because
  there is nothing local to repair.
- Downgrading is not a relabelling exercise. A lower grade has to exist in the
  procurement specification, the customer has to have agreed to it, and the
  units have to meet that grade individually — and a defect that fails the
  part at every grade is not downgradable at all.
- A waiver covers a concession, not a failure. Documentation and cosmetic
  exceedances can be waived by the customer whose requirement it is; a
  functional or hermeticity failure cannot, because the waiver would be
  against physics rather than against a requirement.
- Scrapping is always open, and that is what makes the assessment total. Its
  conditions are about what happens next — a scrapping record and physical
  defacement — so that parts declared unacceptable cannot reappear in someone
  else's supply chain.
- Notification is prior and unconditional. Whatever route is chosen, choosing
  it before telling the customer removes options that were theirs, so a
  disposition taken first is recorded as inadmissible rather than merely
  impolite.

## Workflow

1. Validate the rejection context: every route condition is a boolean, and
   the remaining repair allowance is a non-negative integer. An absent flag
   defaults to false, so a route is closed until something says it is open.
2. Test each route independently and collect its blockers by name rather than
   returning the first failure — a reviewer needs to know what would have to
   change for a better route to open.
3. Keep scrapping eligible unconditionally so the assessment always yields a
   decision.
4. Resolve the notification obligation, which no route can remove, and record
   whether it has been discharged.
5. Recommend the first open route in preference order and attach its
   obligations — the authorization, approval, re-marking, segregation,
   handover or defacement records that route requires.
6. Return the recommendation, the open routes, the blocked routes with their
   reasons, the notification state and whether the disposition is admissible.

## Pitfalls

- Reworking before the rejection is recorded. The rework destroys the evidence
  the rejection rests on, and the lot history then shows a batch that was
  never refused and units that were nonetheless repaired.
- Treating the preference order as authority. Rework sits first because it
  recovers the most material, not because it is easier to justify; a route
  with an open condition is closed regardless of where it sits.
- Downgrading a lot on the lot's behaviour. The lower grade is met unit by
  unit, and a lot that averages into the lower grade still contains units that
  do not meet it.
- Waiving a hermeticity or functional failure. A waiver concedes a
  requirement; it cannot concede a leaking seal, and a waiver written against
  one is a finding in its own right.
- Scrapping without defacement. Parts marked for scrap and left intact are the
  classic route by which rejected material re-enters supply, often through a
  broker, years later.
- Notifying the customer after the decision. The notification exists so the
  customer can choose among the routes; sent afterwards it is a report, and
  the choice it was meant to inform has already been made.

## Behavior contract (gate 3)

The context validation, the per-route blocking conditions, the always-open
scrapping fallback, the unconditional notification obligation and the
preference-ordered recommendation are exercised by the gate 3 contract test:
scripts/test_q6005_rejected_lot_disposition.py against
scripts/q6005_rejected_lot_disposition_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_rejected_lot_disposition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
