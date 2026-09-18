---
name: q6005-passive-chip-procurement
description: "Evaluate the purchase of a bare passive chip element under ECSS-Q-ST-60-05C clause 8.2: resolve the order line to a chip resistor, capacitor or inductor, merge the type-specific ordering data set with the baseline every bare chip carries, name what the line failed to declare, check the termination metallization against the attachment method the assembly will use, form the applied-to-rated stress ratio against the derating limit that type carries, confirm one production lot per delivery, and return release, hold or reject with the governing reason. Use when an order line for bare chip resistors, capacitors or inductors is graded before release. Trigger: ecss, q-st-60-05c, passive-chip-element-procurement, chip-element-ordering-data-items, chip-termination-attach-compatibility, passive-chip-derating-ratio, single-lot-delivery-traceability."
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
  tags: [ecss, q-st-60-05-hybrid-procurement-scope, q6005-passive-chip-procurement, passive-chip-element-procurement, chip-element-ordering-data-items, chip-termination-attach-compatibility, passive-chip-derating-ratio, single-lot-delivery-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Passive Chip Elements (space-systems/ecss/q6005-passive-chip-procurement)

Use when the task is the purchase of ECSS-Q-ST-60-05C clause 8.2 — the
buying rules that attach to resistors, capacitors and inductors supplied as
bare, unencapsulated chips for hybrid assembly, where what the order line
has to say changes with the element type and the chip arrives with no
package to hide behind.

## Domain quick reference

- A bare chip is bought on paper, not on a part number. The package that
  would otherwise carry a marking, a lead finish and a body is absent, so
  every property the assembly depends on has to appear as a declared
  ordering data item or it is simply not known when the chip arrives.
- The data set is two layers. One layer is carried by every bare passive
  chip whatever it does: the manufacturer part identification, the
  procurement specification it is bought against, the lot identification,
  the termination metallization, and the quality level. The second layer is
  the element's own — a resistor owes its resistive film system, tolerance
  and trim method; a capacitor owes its dielectric category, tolerance and
  a destructive physical analysis; an inductor owes its core material,
  tolerance and self-resonant frequency.
- Termination metallization is not a preference, it is half of a
  metallurgical pair. Gold terminations dissolve into tin-bearing solder
  and leave an embrittled joint; a silver-bearing termination is not a
  gold-wire bonding surface; a tin finish is a solder termination and not
  a bonding one. The finish alone is not a finding and neither is the
  attachment method alone — the pair is.
- The derating limit travels with the element type, not with the order.
  Power in a chip resistor, voltage on a chip capacitor and current through
  a chip inductor are each graded as a fraction of the rated quantity, and
  a chip that would be comfortable as one type can be over-stressed as
  another at the same declared numbers.
- One delivery, one production lot. A split delivery is not a paperwork
  irritation: it breaks the link between the lot data supplied and the
  elements in the tray, and nothing downstream of that link can be relied
  on afterwards.
- The disposition is three-valued. Undeclared data is recoverable — the
  supplier can answer — so it holds the line. A metallurgical conflict or
  a broken lot link is not recoverable from the same delivery, so it
  rejects it.

## Workflow

1. Resolve the element type on the order line to a chip resistor, chip
   capacitor or chip inductor, accepting the common short forms; refuse a
   type this clause does not cover rather than grading it on the baseline
   alone.
2. Build the required ordering data set as the union of the baseline items
   and the items the resolved type adds, then name every required item the
   order line did not declare.
3. Take the declared termination metallization together with the
   attachment method the assembly will use and decide whether the pair is
   taken as delivered or needs a barrier or another finish.
4. Form the applied-to-rated stress ratio and compare it with the derating
   limit of the resolved type, absorbing representation error at the limit
   with a named tolerance rather than by loosening the limit.
5. Confirm the delivered quantity carries exactly one distinct lot
   identifier; no identifier and several identifiers are different
   findings and both break traceability.
6. Combine the four checks into a disposition — release, hold or reject —
   and report the finding that governs it, then roll several order lines
   up so the worst line governs the order.

## Pitfalls

- Grading a bare chip on the baseline data set alone. The baseline is what
  every passive chip owes, not what any of them owes in full; a capacitor
  line that never declared its dielectric category is incomplete however
  tidy the baseline looks.
- Reading the termination finish on its own. Gold is an excellent bonding
  surface and a poor soldering one, so a finish is only a finding once the
  attachment method it will meet is known.
- Applying one derating fraction across the order. The fraction belongs to
  the element type, so a single figure applied to resistors, capacitors and
  inductors alike is simultaneously too tight on one and too loose on
  another.
- Accepting a delivery drawn from two lots because the total quantity is
  right. The count is not the point; the lot data no longer describes the
  elements in the tray, and every later lot-based decision inherits that.
- Rejecting an order line for undeclared data. An absent data item is a
  question for the supplier and holds the line; treating it as a rejection
  discards a lot that a reply would have released.
- Widening the derating limit so a chip sitting exactly on it passes. The
  equality is a representation question, handled by the tolerance inside
  the comparison; the limit stays as specified.

## Behavior contract (gate 3)

The element-type resolution, ordering data completeness, termination and
attachment pairing, derating ratio comparison, single-lot check, order line
disposition and order roll-up are exercised by the gate 3 contract test:
scripts/test_q6005_passive_chip_procurement.py against
scripts/q6005_passive_chip_procurement_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_passive_chip_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
