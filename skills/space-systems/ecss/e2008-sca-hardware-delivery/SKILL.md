---
name: e2008-sca-hardware-delivery
description: "Evaluate whether a shipment of ordered solar cell assemblies may be released under ECSS-E-ST-20-08C clause 6.7, where the hardware and the clause 6.6 documentation package have to close together. Use when a delivery is presented for dispatch: confirm the package is released and hold any unit drawn from a lot it does not cover, disposition each assembly as shippable, shippable on an accepted concession or held, reconcile each order line short and over against its ordered count, apply the declared partial-delivery floor, and report what holds the shipment. Trigger: ecss, e-st-20-08c, clause-6-7, sca-hardware-delivery-release, cell-assembly-lot-documentation-coverage, sca-order-line-quantity-reconciliation, sca-partial-delivery-floor, cell-assembly-concession-shipment."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-hardware-delivery, e-st-20-08c, clause-6-7, sca-hardware-delivery-release, cell-assembly-lot-documentation-coverage, sca-order-line-quantity-reconciliation, sca-partial-delivery-floor, cell-assembly-concession-shipment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Hardware Delivery (space-systems/ecss/e2008-sca-hardware-delivery)

Use when the task is the clause 6.7 delivery of ECSS-E-ST-20-08C: the ordered
cell assemblies are ready to leave, and whether they may go has to be settled
against both the order they answer and the documentation package the preceding
clause asks for.

## Domain quick reference

- Two arms have to close, not one. A shipment is not releasable because the
  count came out right, and it is not releasable because a package exists. A
  count check alone ships undocumented hardware; a package check alone ships
  the wrong quantity with immaculate paperwork.
- The join between the arms is narrower than either. A released package covers
  the lots it was written for, and a unit drawn from a lot outside that list
  travels with paperwork that does not describe it. Nothing is wrong with the
  package and nothing is wrong with the unit -- the pairing is wrong, and only
  a per-unit lot check sees it.
- Lot coverage is read before conformance. A unit nobody documented does not
  become a conformance question, so the coverage finding is the one reported
  rather than a second-order judgement about the hardware itself.
- Conformance has three states, not two. Conforming ships, nonconforming is
  held, and nonconforming under an accepted concession ships but is counted
  apart, so a release is never silently made of concessions.
- Reconciliation runs in both directions. A line short of its ordered count is
  the familiar case; a line with more shippable units than were ordered is a
  reconciliation defect, not generosity, and sending the surplus disposes of
  hardware the order never bought.
- A short line is a policy question. A project that permits partial delivery
  still sets a floor under it, and a line below that floor is held rather than
  sent with a backorder note. An unstated policy is not a permissive one.
- The floor is inclusive. A line landing exactly on it releases, so the
  comparison absorbs representation error instead of the floor being nudged to
  make the arithmetic tidy.

## Workflow

1. Resolve the release policy, requiring both the partial-delivery permission
   and the floor to be stated rather than defaulted from an absent key.
2. Grade the documentation package handed over from clause 6.6: released rather
   than draft, and covering at least one lot.
3. Disposition each offered assembly: hold it first if its lot is outside the
   package's coverage, then read its conformance as shippable, shippable on an
   accepted concession, or held.
4. Check every unit cites an order line the order actually contains, and refuse
   a unit offered twice.
5. Reconcile each order line: the shippable count against the ordered count,
   naming shortfall and overage separately.
6. Apply the partial-delivery policy to a short line -- refused outright when
   the order forbids partials, released as a partial when the share reaches the
   floor, held below it.
7. Release the shipment only when the package is usable, no unit sits outside
   its coverage and every line is releasable, and report the paperwork and
   count arms together.

## Pitfalls

- Checking the package and stopping. A released package proves paperwork
  exists, not that it describes the units in the crate; the lot of every unit
  has to fall inside its coverage.
- Treating an over shipment as a courtesy. A line shipping more than it sold is
  as much a reconciliation defect as a short one, and the surplus units leave
  the configuration they were built under.
- Folding concessions into the conforming count. A release made mostly of
  concessions reads identically to a clean one unless they are counted apart.
- Defaulting an unstated partial-delivery rule. Assuming partials are permitted
  turns a held short shipment into a dispatched one on silence alone.
- Grading a unit's conformance before its lot coverage. It answers a question
  about hardware nobody documented and buries the finding that matters.
- Nudging the release floor so a line exactly on it counts. The floor is
  already inclusive; the tolerance belongs inside the comparison.
- Reporting a bare hold. The findings from both arms name the package, the
  uncovered units and the line that fell short, which is what makes the hold
  actionable instead of a second round trip.

## Behavior contract (gate 3)

The release policy validation and its refusal to default an unstated rule, the
documentation package handoff, the per-unit disposition with lot coverage read
ahead of conformance, the three conformance states, the order line
reconciliation short and over, the inclusive partial-release floor with its
outright refusal, and the roll-up into one release verdict are exercised by the
gate 3 contract test: scripts/test_e2008_sca_hardware_delivery.py against
scripts/e2008_sca_hardware_delivery_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_sca_hardware_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
