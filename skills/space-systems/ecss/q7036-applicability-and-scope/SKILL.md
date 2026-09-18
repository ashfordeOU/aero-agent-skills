---
name: q7036-applicability-and-scope
description: "Scope the stress-corrosion-cracking discipline over a metallic parts list under ECSS-Q-ST-70-36C. Use when a hardware list mixes aluminium, titanium, carbon and low-alloy steel, stainless steel, nickel, copper, magnesium and refractory metals with non-metallic items and the SCC control boundary has to be drawn before any alloy is chosen: normalize each declared material onto a known family, let a coating take the scope of its substrate rather than its own composition, separate the families carrying a published SCC resistance rating from those owing test or literature evidence, and report the rated coverage of the in-scope hardware with a finding per uncovered part. Trigger: ecss, q-st-70-36c, scc-scope-boundary, scc-metallic-family-normalization, scc-resistance-rating-coverage, coating-substrate-scope, scc-evidence-owed-part."
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
  tags: [ecss, q-st-70-materials-scope, q-st-70-36c, q7036-applicability-and-scope, scc-scope-boundary, scc-metallic-family-normalization, scc-resistance-rating-coverage, coating-substrate-scope, scc-evidence-owed-part]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Materials — SCC Applicability and Scope (space-systems/ecss/q7036-applicability-and-scope)

Use when the task is the framework step of ECSS-Q-ST-70-36C that decides
which hardware the stress-corrosion-cracking discipline covers at all --
drawing the boundary across a mixed parts list before anybody argues
about a specific alloy, a temper or a stress level.

## Domain quick reference

- Scope follows the material family, not the part name or its function.
  The metallic families the discipline recognises are aluminium,
  titanium, carbon and low-alloy steel, stainless steel, nickel alloys,
  copper alloys, magnesium, and the refractory metals; polymers,
  ceramics, glasses, elastomers and polymer-matrix composites sit
  outside it because no SCC resistance rating is defined for them.
- Being in scope and being dispositionable are two different things. The
  common structural families carry published resistance ratings that a
  selection can be defended against directly. The sparse families --
  refractory metals, beryllium -- are in scope but carry no such rating,
  so a part made of one owes test or literature evidence before its
  choice can be closed.
- A surface layer has no scope of its own. A coating, plating or
  conversion layer inherits the scope of the substrate it sits on,
  because it is the substrate that carries the sustained stress the
  cracking mechanism needs. A coating declared without its substrate is
  therefore an incomplete input, not a defaultable one.
- Product form matters for the later steps, not for the boundary: a
  weldment, a casting, an extrusion and a fastener of the same family
  are all equally in scope, and they part company only when the
  resistance rating of their specific state is read.
- Coverage is reported over the in-scope parts only. A list that is
  mostly composite is not "well covered" because the metal in it happens
  to be rated; the ratio has to have the non-metallic items out of its
  denominator or it flatters the hardware.

## Workflow

1. Normalize every declared material onto a canonical family, accepting
   the usual shorthand and spelling variants; refuse a name that maps to
   no known family rather than guessing the nearest one.
2. Normalize the product form, and for a coating resolve the governing
   family through the declared substrate; a coating with no substrate
   declared is an input error.
3. Decide scope from the governing family: metallic is in, non-metallic
   is out, and record which of the two the decision rested on.
4. For each in-scope part, record whether its family carries a published
   SCC resistance rating or owes evidence.
5. Aggregate: count in-scope and out-of-scope parts, compute the rated
   coverage over the in-scope set alone, and absorb the division's
   representation error at the reporting boundary.
6. Raise one finding per in-scope part with no published rating, naming
   the governing family so the evidence request is actionable, and
   refuse a parts list carrying a duplicate identifier.

## Pitfalls

- Reading a coating as its own material. A nickel plating on magnesium
  is a magnesium scope decision; dispositioning it as nickel moves the
  part from the most susceptible family in the list to one of the least.
- Treating an unrated family as out of scope. Refractory metals and
  beryllium are inside the discipline; the missing rating is a gap in
  the evidence, not an exemption from the control.
- Computing coverage over every part on the list. Including the
  composite and polymer items in the denominator raises the ratio for
  hardware that was never at risk and hides the metal that is.
- Guessing at an unrecognised material name. A near-miss spelling that
  silently resolves to a neighbouring family carries a wrong resistance
  rating into every downstream step; the correct response is to refuse.
- Letting the product form decide the boundary. A casting and a wrought
  bar of the same family are both in scope; their forms separate them
  when the state-specific rating is read, not before.

## Behavior contract (gate 3)

The family and form normalization, the coating-to-substrate resolution,
the scope predicates, the per-part disposition and the coverage
aggregation are exercised by the gate 3 contract test:
scripts/test_q7036_applicability_and_scope.py against
scripts/q7036_applicability_and_scope_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7036_applicability_and_scope.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
