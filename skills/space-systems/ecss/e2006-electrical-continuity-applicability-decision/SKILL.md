---
name: e2006-electrical-continuity-applicability-decision
description: "Use when determine whether the surface electrical-continuity rules of ECSS-E-ST-20-06C clause 6.3.3.1 govern a spacecraft outer item: walk the applicability decision-diagram in order — plasma-exposure, deliberately-biased and high-voltage-surface routing, conductive versus dielectric material-family, the small-isolated-conductive-part waiver sized from stored-discharge-energy, and the severity of the mission charging-environment — then record the governing rule, the route taken, and every ungrounded-conductive-surface finding across the outer-surface inventory. Trigger: ecss, e-st-20-06c, electrical-continuity, applicability-decision-diagram, surface-grounding-applicability, isolated-conductive-part-waiver, plasma-exposure-screening, charging-environment-severity, outer-surface-inventory."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-electrical-continuity-applicability-decision, e-st-20-06c, electrical-continuity, applicability-decision-diagram, surface-grounding-applicability, isolated-conductive-part-waiver, plasma-exposure-screening, charging-environment-severity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Electrical-Continuity Applicability Decision (space-systems/ecss/e2006-electrical-continuity-applicability-decision)

Use when the task is the clause 6.3.3.1 entry gate of ECSS-E-ST-20-06C:
deciding, item by item, whether the surface electrical-continuity
requirements apply to an outer spacecraft surface at all, whether the
item belongs to a neighbouring rule instead, or whether it falls inside
the exception for a small isolated conductive part.

## Domain quick reference

- The decision is a diagram, not a single predicate. Its nodes are
  visited in a fixed order, and the first node that resolves ends the
  walk: an item routed out at the exposure node is never assessed for
  a waiver, and an item routed to the biased-surface rule is never
  measured against the high-voltage onset. Recording the route taken
  is part of the output — two items can share a verdict and have
  arrived at it through different nodes, which is what an auditor
  checks.
- Node 1 is plasma exposure. An item fully enclosed inside the
  spacecraft has no view to the ambient plasma, so surface continuity
  does not govern it; the internal-electrostatic-discharge rules do.
  An item behind partial shielding stays in scope and carries a
  justification finding rather than an automatic exemption.
- Nodes 2 and 3 route items whose potential is not free to float. A
  deliberately-biased surface holds a potential imposed by design, and
  a surface operating at or above the high-voltage onset is governed
  by the high-voltage-surface rule. Both leave clause 6.3.3.1 with a
  named destination, not with a pass.
- Node 4 separates the material families. A conductive outer material
  (bulk metal, conductive coating, dissipative coating) is bonded
  directly. A dielectric outer layer cannot be bonded at its surface,
  so the requirement lands on the conductive backing underneath it,
  and the dielectric itself is handled by the surface-material control
  rule.
- Node 5 is the small-part waiver, and it is a two-part test: a small
  exposed area alone does not earn it. The stored electrostatic energy
  of the isolated part, evaluated at the worse of its operating
  potential and the environment floating potential, must also stay
  inside the non-hazardous limit. A physically large capacitance
  defeats the waiver however small the visible area is.
- Node 6 grades the mission charging-environment. A geostationary,
  transfer, medium-altitude, highly-elliptical, high-inclination or
  interplanetary regime is a severe surface-charging environment; a
  low-inclination or equatorial low-altitude orbit is benign and
  permits the relaxed material-control route while still requiring the
  bond itself.

## Workflow

1. Normalize each outer item into a record: identifier, exposure,
   material family, mission orbit regime, exposed area, capacitance to
   structure, operating potential, deliberately-biased flag and
   as-designed bonding state. Reject an unrecognized exposure,
   material family or orbit regime before the walk starts.
2. Resolve the exposure node. An enclosed item exits with
   "not applicable" and is handed to the internal rules; an exposed or
   partially shielded item continues.
3. Resolve the bias node, then the high-voltage node, computing the
   high-voltage condition from the absolute operating potential
   against the named onset rather than trusting a free-text label.
   Either hit exits with the destination rule named.
4. Resolve the material-family node. A dielectric outer layer moves
   the requirement onto its conductive backing; a conductive outer
   material continues to the waiver test.
5. Evaluate the small-isolated-conductive-part waiver for an unbonded
   conductive item: exposed area inside the small-part limit AND
   stored discharge energy inside the non-hazardous limit. Grant the
   waiver only when both hold, and keep the computed energy in the
   record.
6. Grade the charging environment and emit the verdict — continuity
   required, continuity required on the backing, relaxed
   material-control, or waived — attaching an ungrounded-conductive-
   surface finding whenever an in-scope item is not bonded.
7. Aggregate the inventory: verdict counts, in-scope count and the
   open-findings list. The inventory is not clear until that list is
   empty.

## Pitfalls

- Treating the diagram as a set of independent filters and running
  every node on every item. Order carries meaning: a deliberately
  biased surface that also sits above the high-voltage onset belongs
  to the bias rule, and reporting it as a high-voltage item sends the
  design review to the wrong requirement.
- Reading "routed to another rule" as "compliant". An item that leaves
  6.3.3.1 has not been assessed, it has been handed over; the verdict
  must name the receiving rule so the handover is traceable.
- Granting the small-part waiver on exposed area alone. Area and
  stored energy are both necessary, and the energy has to be taken at
  the worse of the operating and floating potential — an unbonded part
  that only sees a few volts in test can sit at kilovolts in a severe
  environment.
- Letting a benign orbit regime cancel the bond. A relaxed verdict
  relaxes the material-control burden on the surface, not the
  continuity of a conductive part to structure.
- Exempting a partially shielded item because it is "not really
  exposed". Partial shielding is a justification to be written down,
  not a node that ends the walk.
- Comparing a computed stored energy against its limit with a bare
  greater-than on raw floats. A part that is exactly at the limit can
  land a few units in the last place above it; the logic absorbs that
  representation error at the comparison instead of moving the limit.

## Behavior contract (gate 3)

The record validation, decision-diagram ordering, high-voltage onset,
small-part waiver and inventory aggregation are exercised by the gate 3
contract test:
scripts/test_e2006_electrical_continuity_applicability_decision.py
against
scripts/e2006_electrical_continuity_applicability_decision_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_electrical_continuity_applicability_decision.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
