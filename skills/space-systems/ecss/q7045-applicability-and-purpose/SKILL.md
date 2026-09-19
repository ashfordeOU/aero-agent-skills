---
name: q7045-applicability-and-purpose
description: "Determine whether a proposed mechanical test campaign on a metallic product falls inside the scope of ECSS-Q-ST-70-45C and what the data it returns may be used for: separate metallic product forms from materials outside the standard, admit only the mechanical properties it covers, read the purpose the data is generated for, and size the test matrix so every declared property, orientation and temperature owns enough valid test pieces for that purpose. Use when scoping a metallic materials test plan, reviewing a supplier test proposal or judging whether an existing dataset supports a design allowable. Trigger: ecss, q-st-70-45c, metallic-mechanical-test-scope, metallic-test-campaign-purpose, metallic-test-matrix-sizing, design-allowable-sample-size, metallic-property-coverage."
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
  tags: [ecss, q-st-70-45c-metallic-mechanical-testing, q-st-70-45c, q7045-applicability-and-purpose, metallic-mechanical-test-scope, metallic-test-campaign-purpose, metallic-test-matrix-sizing, design-allowable-sample-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Applicability and Purpose (space-systems/ecss/q7045-applicability-and-purpose)

Use when the task is the scope clause of ECSS-Q-ST-70-45C: which products and
which properties the mechanical test methods cover, what purpose a campaign is
being run for, and how many valid test pieces each declared condition owes
before the resulting numbers may be quoted.

## Domain quick reference

- The standard covers metallic product forms. A polymer, a ceramic, a
  fibre-reinforced laminate or a bonded assembly is tested under its own
  document, and a metal-matrix composite sits on the boundary and is admitted
  only where the declared product form is genuinely a metallic product.
- Scope is decided by property as well as by material. Tensile, compression,
  shear, bearing, fracture-toughness, fatigue, creep and stress-rupture
  behaviour are mechanical properties of the product. Density, thermal
  expansion, electrical resistivity and corrosion behaviour are not, and
  routing them here produces a plan nobody can execute.
- Purpose sets the sample size, not the other way round. A dataset assembled
  for lot acceptance answers one question about one lot; a design allowable
  has to carry a statistical basis across heats, so the same three test pieces
  that close an acceptance decision are nowhere near a design value.
- A campaign is a matrix, not a count. Each declared property is owed at each
  declared orientation and each declared temperature, so a plan with a healthy
  total can still leave a cell of the matrix empty, and that empty cell is the
  one the design will need.
- Test pieces that were run but declared invalid do not count towards the
  minimum. A piece that broke outside the gauge length, slipped in the grips
  or was taken from an undocumented location has produced a reading, not a
  result.
- The standard generates data; it does not accept the material. Whether the
  numbers that come out clear a specification limit is the acceptance
  decision, made against the procurement document, and it is a separate step
  from asking whether the campaign was in scope and complete.

## Workflow

1. Read the product: material family, product form and the document the
   material is procured against. A non-metallic family leaves the scope of
   this standard immediately, with the reason recorded.
2. Sort the requested properties into the mechanical set the standard covers
   and the rest, and carry the remainder out as an explicit out-of-scope list
   rather than dropping it silently.
3. Read the declared purpose of the campaign — design-allowable generation,
   qualification, lot acceptance or process verification — and take the
   minimum valid test pieces per matrix cell from that purpose.
4. Expand the matrix: every in-scope property against every declared
   orientation against every declared test temperature. That cross product is
   the set of cells the plan owes.
5. Count only the valid test pieces assigned to each cell, and raise a cell
   with none as a gap distinct from a cell that is merely short.
6. Where the purpose is design-allowable generation, check the heat coverage
   as well as the count, because pieces drawn from a single heat cannot carry
   a multi-heat statistical basis however many of them there are.
7. Close with a scope-and-completeness status naming the out-of-scope
   requests, the empty cells, the short cells and any heat-coverage shortfall.

## Pitfalls

- Deciding scope from the material family alone. A metallic product asked for
  a non-mechanical property is still out of scope for this standard, and a
  plan that keeps the request produces a test nobody can book.
- Sizing the campaign from a total piece count. Fifty pieces spread over a
  matrix with an empty cell is a failed plan, and the total hides it.
- Counting invalid pieces towards the minimum. An invalid break has consumed
  material and machine time without adding a result, so the cell is still
  short and needs a replacement piece.
- Promoting an acceptance dataset to a design allowable. The minimum that
  closes a lot decision was never intended to carry a statistical basis, and
  re-labelling the purpose does not add the heats the basis needs.
- Reading a complete matrix as an accepted material. Completeness says the
  data exists and is usable; the comparison against the procurement limits is
  the next decision, not this one.
- Moving a minimum to absorb a cell that lands one piece short. The shortfall
  is a real gap in the evidence; the required counts stay as specified and the
  cell is filled.

## Behavior contract (gate 3)

The material and property scope decisions, the purpose-to-minimum mapping, the
matrix expansion, valid-piece counting, heat-coverage rule for design
allowables and the combined campaign verdict are exercised by the gate 3
contract test: scripts/test_q7045_applicability_and_purpose.py against
scripts/q7045_applicability_and_purpose_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_applicability_and_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
