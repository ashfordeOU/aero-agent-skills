---
name: q6005-hybrid-materials-and-parts-selection
description: "Evaluate whether each constituent item proposed for a hybrid assembly — substrate, die-attach adhesive, bonding wire, preform, lid — may be selected under ECSS-Q-ST-60-05C clause 9.2: take each candidate's qualification standing, compute the thermomechanical strain an expansion mismatch imposes across the joint over the declared temperature excursion, screen polymeric items for total mass loss and condensable volatiles, take the wire-to-pad couple for an intermetallic-prone or tin-bearing pairing, and return selectable, selectable-with-evaluation or not-selectable per item with every failing condition named. Use when choosing or reviewing the constituent materials of a hybrid. Trigger: ecss, q-st-60-05c, hybrid-constituent-material-selection, die-attach-expansion-mismatch-strain, hybrid-polymer-outgassing-screen, wire-to-pad-bond-couple, hybrid-item-selectability, hybrid-material-qualification-standing."
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
  tags: [ecss, q-st-60-05-hybrid-materials-and-parts, q6005-hybrid-materials-and-parts-selection, hybrid-constituent-material-selection, die-attach-expansion-mismatch-strain, hybrid-polymer-outgassing-screen, wire-to-pad-bond-couple, hybrid-item-selectability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Constituent Material and Part Selection (space-systems/ecss/q6005-hybrid-materials-and-parts-selection)

Use when the task is choosing, or reviewing somebody else's choice of, the
substrates, adhesives, bonding wires, preforms, lids and sealing materials a
hybrid assembly is built from under ECSS-Q-ST-60-05C clause 9.2 — the decision
that fixes what goes inside the package before any of it is bought.

## Domain quick reference

- A hybrid is not a part that was selected; it is a package full of items that
  were each selected separately and then have to live together for the mission
  life inside one sealed cavity. The selection is therefore graded per item and
  again as a set, because an item that is individually blameless can still be
  the wrong neighbour for the one attached to it.
- Qualification standing is the first condition and the cheapest to check. A
  qualified item arrives with its own evidence. Qualified-by-similarity and
  unqualified items owe an evaluation, and the difference between a deferral
  and a refusal is entirely whether a programme is open to run it — an
  evaluation owed with nowhere to run it is a refusal wearing a softer word.
- Expansion mismatch is a joint property, not an item property. The same
  substrate is comfortable under one die and marginal under another, so the
  mismatch strain is the coefficient difference multiplied by the temperature
  excursion the joint actually sees, and an item with no declared neighbour has
  no mismatch condition to grade rather than a passing one.
- The evaluation band below the allowable exists because a joint sitting just
  inside its limit has no room for a process shift. A strain that lands on the
  allowable is met, not exceeded, but it is not comfortable either, and the
  band is what makes that visible without moving the limit.
- Outgassing applies to the polymeric items and to nothing else. Total mass
  loss and collected volatile condensable material are properties of a cured
  formulation, so an adhesive or sealing material declared without them cannot
  be graded at all — that is an input error, not a passing screen.
- The wire-to-pad couple is metallurgy, not assembly. Like metals are proven,
  an unlike couple owes an intermetallic evaluation over the thermal life, and
  a tin-bearing couple is refused outright rather than evaluated, because the
  refusal is a materials prohibition and no amount of test data lifts it.

## Workflow

1. Validate each candidate: a known constituent category, a name, a recognised
   qualification standing, and the properties its category cannot be graded
   without — outgassing figures for a polymer, both metals for a wire.
2. Take the qualification standing. Anything short of qualified opens an
   evaluation against the item.
3. Where the project declares what the item is attached to and the temperature
   excursion the joint sees, compute the mismatch strain and grade it against
   the allowable and the evaluation band beneath it.
4. Screen the polymeric items for mass loss and condensable volatiles, naming
   each figure that exceeds its allowable rather than reporting one verdict.
5. Take the wire-to-pad couple and separate the proven, the evaluable and the
   prohibited.
6. Merge the per-condition outcomes worst-first into one selectability per
   item, then convert an open evaluation into a refusal when no evaluation
   programme is available to close it.
7. Roll the items up: report the refused items, the items still open, the
   settled fraction, and whether the bill of materials is complete as opposed
   to merely free of refusals.

## Pitfalls

- Grading expansion mismatch as a property of the substrate. It is a property
  of the joint; the same substrate passes under one attachment and fails under
  another, and a table of substrate coefficients decides nothing on its own.
- Reading a strain that lands on the allowable as a failure. The allowable is
  met at the allowable. What it is not is comfortable, which is what the
  evaluation band beneath it is for.
- Treating an open evaluation as a soft finding. An evaluation owed with no
  programme, no schedule and no budget to run it is a refusal that has not been
  written down yet, and it will be discovered at the design review.
- Accepting a polymeric item on its datasheet mechanical data alone. Without
  cured-formulation mass loss and condensable figures there is no screen — the
  item has not passed, it has not been graded.
- Reading a tin-bearing couple as an evaluation case. The prohibition is on the
  material, so more test data does not move it; the answer is a different
  finish, not a longer test.
- Rolling the selection up as pass or fail. Complete and buildable are
  different states: a set with one open evaluation can be built to while the
  evaluation runs, and a set with one refusal cannot be built at all.

## Behavior contract (gate 3)

The candidate validation, qualification standing, expansion-mismatch strain
with its evaluation band, vacuum outgassing screen, wire-to-pad couple, the
worst-first merge and the selection roll-up are exercised by the gate 3
contract test: scripts/test_q6005_hybrid_materials_and_parts_selection.py
against scripts/q6005_hybrid_materials_and_parts_selection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_hybrid_materials_and_parts_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
