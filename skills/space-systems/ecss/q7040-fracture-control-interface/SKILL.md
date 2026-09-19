---
name: q7040-fracture-control-interface
description: "Coordinate a brazed item between the brazing controls and the fracture-control programme. Use when a brazement sits inside a part whose failure matters and the two disciplines have to agree what the braze file owes: place the item against the fracture categories on consequence, containment and load-path redundancy rather than on how important it feels, work the critical crack size from joint toughness, geometry factor and peak stress, compare it with the flaw an inspection can actually find through a braze layer, and route a shortfall to a proof test or a redesign instead of to another inspection. Trigger: ecss, q-st-70-40-brazing, e-st-32-01c-fracture-control, brazed-fracture-critical-item, braze-detectable-flaw-size, braze-damage-tolerance-factor, braze-repair-fracture-concurrence."
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
  tags: [ecss, q-st-70-40-brazing, e-st-32-01c-fracture-control, q7040-fracture-control-interface, brazed-fracture-critical-item, braze-detectable-flaw-size, braze-damage-tolerance-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Fracture Control Interface (space-systems/ecss/q7040-fracture-control-interface)

Use when the task is the interface between the ECSS-Q-ST-70-40 brazing
controls and the fracture-control requirements of ECSS-E-ST-32-01C: what
a brazed fracture-critical item adds to the braze file, and whether the
inspection behind it can carry the damage-tolerance argument at all.

## Domain quick reference

- The two disciplines meet at one question: can the flaw that survives
  inspection be shown not to grow to failure inside the service life?
- For a brazement that question is harder than for a parent-metal part.
  The flaw of interest lies in a thin filler layer between two
  materials, and the inspection has to find it through one of them.
- Categorisation comes from consequence, containment and redundancy, not
  from cost or visibility. A contained failure is not fracture critical
  however expensive the part is; a catastrophic failure with no
  redundant path is one however cheap it is.
- A fail-safe load path drops the item to the low-risk route. The part
  still gets listed and still owes traceability; it does not owe the
  full damage-tolerance argument.
- A brazement inside a fracture-critical item drags the braze process
  into the fracture-control programme with it. That is what makes the
  repair concurrence a real constraint: a re-braze is a new thermal
  history on a part whose fracture argument was written against the old
  one.
- The critical crack size follows from joint toughness, geometry factor
  and peak stress. Joint toughness is a property of the brazed joint,
  not of either parent alloy, and using a parent-metal value inflates
  the critical size.
- The detectable flaw size is not the instrument's catalogue figure. A
  braze layer costs the method capability, so the declared size is the
  solid-section figure with that penalty applied.
- A penetrant check reaches only a surface-breaking flaw, so it cannot
  size a buried braze-layer flaw at all. A proof test screens flaws by
  loading and has no detectable size of its own; it is a route, not a
  measurement.
- When the required factor is not met, re-inspecting to the same
  capability changes nothing. The routes are a proof test, a redesign
  into a fail-safe or contained path, or a joint made another way.

## Workflow

1. Categorise the item from the three consequence questions and stop
   there when it is outside the programme.
2. For a fracture-critical item, work the critical crack size from the
   brazed-joint toughness, the geometry factor and the peak stress the
   joint sees.
3. Take the inspection method and refuse the ones that cannot size a
   buried flaw. Apply the braze-layer penalty to the solid-section
   capability to get the flaw that actually survives inspection.
4. Compare the two as a factor against the required one, absorbing
   representation error at the boundary with a named tolerance so an
   argument that lands exactly on the factor is not failed by
   arithmetic.
5. Route a shortfall to a proof test where one is feasible and to a
   redesign where it is not. Do not route it to more inspection.
6. List what the braze file owes the fracture programme for the
   category, report the deliverables that are not in it, and carry the
   repair concurrence forward so a later re-braze cannot be worked as a
   routine repair.

## Pitfalls

- Categorising on importance. The question is what the failure does and
  whether anything else carries the load, and an expensive contained
  part answers both the same way a cheap one does.
- Using a parent-metal fracture toughness for the joint. The braze layer
  is the weaker, more brittle path and the parent value inflates the
  critical crack size that the whole argument rests on.
- Quoting the instrument's catalogue detectable size. It was measured on
  a solid section; the braze layer costs capability and the declared
  size has to carry that penalty.
- Answering a damage-tolerance shortfall with tighter inspection. The
  capability is what it is, and re-inspecting to the same capability
  finds the same flaws.
- Treating a penetrant result as coverage of the braze layer. It sees
  the surface; the flaw that matters is buried.
- Repairing a fracture-critical brazement to the ordinary repair route.
  The fracture argument was written against one thermal history, and a
  re-braze replaces it.

## Behavior contract (gate 3)

The three-question categorisation, the critical crack size against
independently worked values, the method refusals and braze-layer
penalty, the damage-tolerance factor with its boundary tolerance, the
deliverable set per category and the inspection, proof-test and redesign
routes are exercised by the gate 3 contract test:
scripts/test_q7040_fracture_control_interface.py against
scripts/q7040_fracture_control_interface_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7040_fracture_control_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
