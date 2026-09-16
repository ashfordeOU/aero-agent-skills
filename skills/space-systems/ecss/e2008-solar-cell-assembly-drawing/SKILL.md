---
name: e2008-solar-cell-assembly-drawing
description: "Use when an assembly drawing package is offered for release and the joints between its layers have to be controlled, not merely drawn. Assess the source control drawing covering a solar cell assembly against the content Annex B of ECSS-E-ST-20-08C calls for: read the stack outer face inward, derive the bonded joint between each adjacent pair, and require exactly one bond control per joint naming agent, thickness and area coverage; identify each terminal polarity once and marked; and resolve every cited constituent drawing at the issue cited. Trigger: ecss, e-st-20-08c, solar-cell-assembly-drawing-content-audit, solar-cell-assembly-layer-stack-continuity, solar-cell-assembly-bonded-interface-control, solar-cell-assembly-terminal-polarity-identification, solar-cell-assembly-cited-drawing-standing."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-solar-cell-assembly-drawing, solar-cell-assembly-drawing-content-audit, solar-cell-assembly-layer-stack-continuity, solar-cell-assembly-bonded-interface-control, solar-cell-assembly-terminal-polarity-identification, solar-cell-assembly-cited-drawing-standing, solar-cell-assembly-drawing-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Solar Cell Assembly Source Control Drawing (space-systems/ecss/e2008-solar-cell-assembly-drawing)

Use when the task is the content rule of ECSS-E-ST-20-08C Annex B -- what the
source control drawing covering a solar cell assembly has to carry, and
whether the joints between the layers it stacks are controlled or only drawn.

## Domain quick reference

- A solar cell assembly is a bonded stack, so the drawing controls two kinds
  of thing: the items in the stack and the joints between them. Every item can
  be fully specified on its own drawing while the assembly stays uncontrolled,
  because nothing said how thick the bond was or how much area it covered.
- The stack is ordered, outer face inward. The order is not presentation. A
  stack listing the cell outside the coverglass is a different assembly, not a
  mis-typed drawing, and reading it as a typo repairs the paperwork while
  leaving the product wrong.
- Each adjacent pair of layers implies exactly one bonded joint, and each
  joint needs exactly one control record naming the bonding agent, its
  thickness and the share of the joint area it covers. Zero records leaves
  the joint to the supplier; two records leave the supplier to choose, which
  is the same freedom spelled differently.
- Bond coverage is a control, not a target. Below roughly nine tenths of the
  joint area the bond is no longer the thing carrying the layers, whatever
  the record says the agent is.
- A bond control naming a joint the stack does not have is evidence the
  drawing and the stack disagree, and the disagreement is not resolved by
  ignoring the extra record.
- The assembly has a polarity. Each polarity is identified exactly once, and
  identified on the drawing itself: a terminal listed beside the drawing but
  not marked on it is an open item, while a missing or doubled polarity is a
  connection nobody can make correctly.
- An assembly drawing reaches its constituents only through the issues it
  cites. A draft or cancelled citation controls nothing; a superseded one, or
  one at an issue other than the released one, points at something real that
  is no longer current.

## Workflow

1. Take the package as its drawing number, the ordered stack, the bond
   controls, the terminals and the constituent drawings it cites.
2. Resolve the stack: reject a repeated layer role outright, name the required
   roles it lacks, and check it runs outer face inward.
3. Derive the bonded joints from adjacent pairs, and grade each against the
   bond controls: none, one, or more than one, then the coverage of the one.
4. Name every bond control that points at a joint this stack does not have.
5. Check each polarity is identified exactly once and marked on the drawing.
6. Resolve each citation into governing, off issue, or void.
7. Compute the controlled joint share and compare it with the threshold the
   package is being released against.
8. Disposition the drawing: a missing role, an out-of-order stack, an
   uncontrolled, doubly controlled or under-covered joint, a stray bond
   control, an unidentified polarity or a void citation stops the release; an
   unmarked terminal or an off-issue citation releases it against open items.

## Pitfalls

- Auditing the layers and calling the assembly controlled. The joints are
  where an assembly drawing earns its name.
- Reading an out-of-order stack as a transcription slip. Reordering it to
  match expectation quietly invents the assembly the reader wanted.
- Letting two bond controls stand on one joint because both are acceptable.
  Two acceptable answers is a supplier choice, not a control.
- Treating bond coverage as workmanship rather than as a limit. A bond over
  half the joint is not a bond with a cosmetic shortfall.
- Ignoring a bond control that names a joint the stack lacks. It is the
  cheapest available evidence that the drawing and the stack disagree.
- Accepting a terminal list as terminal marking. The operator reads the mark
  on the hardware, not the table beside the drawing.
- Counting two positive terminals as redundancy. It leaves which one the
  harness meets entirely open.
- Citing a constituent drawing with no issue, or at a superseded one. The
  citation looks complete and reaches the wrong document.
- Comparing a controlled joint share with its threshold by bare arithmetic.
  Both are quotients of counts and a package exactly on the threshold can
  evaluate a few units in the last place under it; the comparison absorbs
  that while the threshold stays as written.

## Behavior contract (gate 3)

The stack resolution and ordering check, bonded joint derivation, per-joint
bond control grading, coverage floor, stray bond control detection, terminal
polarity identification, cited drawing standing, controlled joint share and
the release disposition are exercised by the gate 3 contract test:
scripts/test_e2008_solar_cell_assembly_drawing.py against
scripts/e2008_solar_cell_assembly_drawing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_solar_cell_assembly_drawing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
