---
name: e2006-thermal-blanket-grounding
description: "Use when verify that every metallic layer of a multi-layer-insulation blanket reaches structure through its own direct grounding-straps instead of a chained layer-to-layer route, per ECSS-E-ST-20-06C clause 6.3.3.3: resolve each layer ground-path, reject looped and daisy-chained topologies, combine the straps in parallel and add the lateral-resistance of the layer to grade the ground-path-resistance against the bonding limit, size the required strap-count from the blanket-area and the redundancy minimum, and report every ungrounded-metallic-layer per blanket. Trigger: ecss, e-st-20-06c, thermal-blanket-grounding, multi-layer-insulation, blanket-metallic-layer, grounding-strap-redundancy, daisy-chained-ground-path, bonding-resistance-limit, blanket-strap-count."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-thermal-blanket-grounding, e-st-20-06c, multi-layer-insulation, blanket-metallic-layer, grounding-strap-redundancy, daisy-chained-ground-path, bonding-resistance-limit, blanket-strap-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Thermal-Blanket Layer Grounding (space-systems/ecss/e2006-thermal-blanket-grounding)

Use when the task is the blanket-grounding provision of ECSS-E-ST-20-06C
clause 6.3.3.3: the metallized layers of a multi-layer-insulation
blanket each carry their own charge, and each one has to reach
structure on its own straps rather than by borrowing the bond of the
layer above or below it.

## Domain quick reference

- A blanket is a stack, not a single surface. Every metallized layer is
  an isolated conductor that collects charge, so the grounding
  requirement is per layer. A blanket whose outer layer is bonded and
  whose inner layers are not has the same number of ungrounded
  conductors as a blanket with no bond at all.
- Direct means direct. A layer whose declared ground target is another
  layer is chained, and the chain has three defects: it adds every
  intermediate layer's resistance in series, it makes one broken
  interlayer joint orphan every layer downstream of it, and it
  routes discharge current through the thin metallization of a layer
  that was never sized to carry it. The topology check is therefore a
  hop count to structure, not a yes/no on "is it grounded".
- A ground path that revisits a layer, or that names a node that does
  not exist, is not a finding but an input error: the topology is
  undefined and nothing downstream of it can be computed. A layer that
  simply declares no target is a different thing — that is an
  ungrounded layer, and it is a finding.
- Straps on one layer act in parallel: the conductance adds, so the
  combined resistance is below the best single strap. The lateral
  resistance of the metallization itself, from the furthest point of
  the layer to its attachment, sits in series ahead of that
  combination and is often the term that decides the verdict on a
  large blanket.
- A layer that declares a bond but carries no strap has no bond point,
  so its path resistance is infinite rather than zero. Treating a
  missing strap as a zero-resistance connection is the failure mode
  that lets a paper design pass.
- Strap count has two drivers: a redundancy minimum, so that no single
  strap failure floats the layer, and blanket area, so that no part of
  a large layer is far from an attachment. The requirement is the
  larger of the two.

## Workflow

1. Normalize the blanket: identifier, area, and the layer stack. For
   each layer record the metallization flag, the declared ground
   target, the straps with their resistances and the lateral
   resistance of the layer. Reject duplicate layer or strap
   identifiers, a non-positive strap resistance, a negative lateral
   resistance and a layer identifier that shadows the structure node.
2. Skip non-metallized layers — they hold no charge to drain and carry
   no requirement — but keep them visible in the result so the stack
   stays auditable.
3. Resolve each metallic layer's ground path by following its declared
   target until it reaches structure. Raise on a loop, a self
   reference or an unknown node; return a dead end as an ungrounded
   layer.
4. Flag a resolved path longer than one hop as chained, and compute
   the total path resistance as the sum of each traversed layer's own
   parallel-strap-plus-lateral resistance.
5. Compare the path resistance with the bonding limit, absorbing the
   representation error of a path that sits exactly on the limit
   instead of relaxing the limit itself.
6. Size the required strap count from the blanket area and the
   redundancy minimum, and flag a layer that carries fewer.
7. Check the blanket as a whole: count the straps that land directly
   on structure, and flag a blanket that depends on a single one.
8. Aggregate. The blanket is not compliant until the per-layer list
   and the blanket-level list are both empty.

## Pitfalls

- Reporting a blanket as grounded because a continuity reading at one
  attachment point passed. The reading proves one layer is bonded; the
  inner layers are what the requirement is about.
- Accepting a chain because it does reach structure in the end. The
  series resistance, the shared single point of failure and the
  current routed through a neighbouring metallization are all present
  even when the end-to-end reading looks acceptable.
- Treating a missing strap as a perfect connection. A declared bond
  with no hardware behind it is an infinite path resistance, and the
  computation has to say so.
- Sizing straps on area alone and dropping below the redundancy
  minimum on a small blanket. One strap is one failure away from an
  ungrounded layer whatever the area is.
- Ignoring the lateral resistance of the metallization. On a large
  layer that term dominates the parallel strap resistance, and leaving
  it out passes a design whose far corner never drains.
- Widening the bonding limit so a design that lands a few units in the
  last place above it passes. The rescue belongs in the comparison, as
  a tolerance on the representation, never in the limit.

## Behavior contract (gate 3)

The layer and blanket validation, ground-path resolution, loop
rejection, parallel-strap and lateral resistance, strap-count sizing,
blanket redundancy check and set aggregation are exercised by the
gate 3 contract test: scripts/test_e2006_thermal_blanket_grounding.py
against scripts/e2006_thermal_blanket_grounding_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_thermal_blanket_grounding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
