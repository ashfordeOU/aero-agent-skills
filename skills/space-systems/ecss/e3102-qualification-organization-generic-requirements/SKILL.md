---
name: e3102-qualification-organization-generic-requirements
description: "Define the customer and supplier duties and the applicability of the embedded generic requirements of ECSS-E-ST-31-02 clauses 4.2 and 4.3 for two-phase heat transport equipment: resolve which embedded duties bite for the product category and procurement route in hand, settle a jointly held duty against that route rather than by preference, grade the owners the parties actually declared, and refuse a duty dropped without a recorded tailoring agreement. Use when a heat pipe or loop heat pipe procurement needs its qualification organization fixed before the technical specification is issued. Trigger: ecss, e-st-31-02-two-phase, two-phase-qualification-organization, customer-supplier-duty-assignment, embedded-generic-requirement-applicability, two-phase-procurement-route, unowned-duty-detection, tailoring-agreement-record."
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
  tags: [ecss, e-st-31-02-two-phase, e3102-qualification-organization-generic-requirements, two-phase-qualification-organization, customer-supplier-duty-assignment, embedded-generic-requirement-applicability, two-phase-procurement-route, unowned-duty-detection, tailoring-agreement-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase — Qualification Organization and Generic Requirements (space-systems/ecss/e3102-qualification-organization-generic-requirements)

Use when the task is the organization step of ECSS-E-ST-31-02 clauses 4.2
and 4.3 -- naming the customer and the supplier for a two-phase heat
transport procurement, and working out which of the generic requirements
the standard embeds actually apply to the product category and
procurement route in hand.

## Domain quick reference

- The standard embeds a set of generic duties that come with the
  equipment rather than with the project. They are not all live on every
  job. Two context facts switch them on or off: what kind of product is
  being bought, and how it is being bought.
- Product category, weakest heritage first: new-development (no
  qualified predecessor), modified-design (a qualified design changed
  for this application), off-the-shelf (a catalogue item already
  qualified elsewhere).
- Procurement route: full-development-contract (the supplier develops
  against a customer technical specification), recurring-build (a repeat
  of an already-qualified item), catalogue-purchase (the item is bought
  as offered).
- A duty the standard leaves jointly held is not a free choice between
  the parties. It follows the route, because the route decides who holds
  the data. On a development contract only the supplier has the design
  in hand, so the supplier carries it; on a catalogue purchase the
  supplier has no development visibility to offer, so the customer
  carries it; on a recurring build both parties hold enough of the
  picture for it to stay joint.
- Some duties can be tailored away and some cannot. A duty that may be
  dropped is still only dropped against a recorded tailoring agreement
  reference; without one, the drop is an unrecorded deviation, not
  tailoring.
- A duty that was dropped but never applied is its own finding. It says
  the two parties are working from different applicability pictures, and
  that disagreement will surface again at the qualification review.

## Workflow

1. Declare the context: customer, supplier, product category and
   procurement route. Reject an uncategorized product or route rather
   than defaulting it, because every duty below is switched by these two
   facts.
2. Resolve the applicable set. Keep a duty only when the context matches
   both its category list and its route list, and reject a context in
   which nothing at all applies -- that means the registry does not
   cover the job.
3. Resolve the owner of each surviving duty, sending a jointly held duty
   to the party the route puts the data with.
4. Grade the owners the parties actually wrote down against that
   resolution. Report a duty with no owner, a duty given to the wrong
   party, and an owner attached to a duty that does not apply.
5. Grade every proposed drop. Refuse a drop of a duty the standard does
   not allow to be tailored, refuse a drop with no tailoring agreement
   on record, and refuse a drop of something that never applied.
6. Close with the active duty set grouped by owner, and an agreement
   verdict that is open while any finding stands.

## Pitfalls

- Treating the embedded generic requirements as boilerplate that applies
  in full to everything. Half of them do not reach a catalogue purchase,
  and carrying them anyway buries the ones that do in a list nobody
  reads.
- Splitting a jointly held duty by negotiation. The route already
  decides it, and a split agreed against the route puts the duty on the
  party that cannot discharge it -- most often verification matrix
  upkeep handed to a vendor who never sees the technical specification.
- Reading heritage duties as applying to a new design. Heritage evidence
  is owed by a reuse claim; asking for it on a clean sheet design
  produces an empty submission that looks like a closed action.
- Dropping a duty in a meeting and recording it in minutes. A drop with
  no tailoring agreement reference is a deviation that will be found at
  the qualification review, when it is far more expensive to close.
- Leaving a duty unowned because both parties assume the other has it.
  Fluid and envelope material compatibility is the classic one, and it
  is the duty most likely to decide whether the equipment degrades in
  orbit.

## Behavior contract (gate 3)

Requirement validation, applicability resolution, route-driven role
resolution, assignment audit, disapplication audit and the agreement
verdict are exercised by the gate 3 contract test:
scripts/test_e3102_qualification_organization_generic_requirements.py
against
scripts/e3102_qualification_organization_generic_requirements_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3102_qualification_organization_generic_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
