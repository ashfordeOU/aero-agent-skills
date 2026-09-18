---
name: q7004-test-item-categories
description: "Map every item entering an ECSS thermal test campaign onto its test item category: material, process, mechanical part or assembly. Use when the ECSS-Q-ST-70-04C test item clauses have to be applied to a mixed list before specimens are cut: derive each category from declared attributes rather than a label, let a joined unit outrank the operation that built it and an operation outrank a bare mechanical function, reject loose pieces that are not one item, then read the specimen form, the property measured afterwards, the specimen demand and the reach limits off the category. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-item-categorization, material-versus-process-coupon, assembly-test-item-reach-limit, process-representative-coupon, thermal-test-specimen-demand."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-test-item-categories, thermal-test-item-categorization, material-versus-process-coupon, assembly-test-item-reach-limit, process-representative-coupon, thermal-test-specimen-demand]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Test Item Categories (space-systems/ecss/q7004-test-item-categories)

Use when the task is the test item categorization of ECSS-Q-ST-70-04C —
sorting what is about to be thermally tested into materials, processes,
mechanical parts and assemblies, because the specimen, the specimen count,
the property measured afterwards and the reach of the result all follow from
which kind of item is in front of you.

## Domain quick reference

- Four kinds of test item. A material is a substance evaluated in its own
  right on coupons cut from the delivered stock. A process is an operation
  applied to material, evaluated through a coupon that carries the operation
  and was made to the production procedure. A mechanical part is one
  manufactured piece with a mechanical function. An assembly is two or more
  pieces joined into one functional unit with its interfaces present.
- The category is derived, not declared. Attributes settle it: how many
  distinct pieces, whether they are joined into one unit, which operations
  were applied, and whether the piece carries a mechanical function.
- Precedence runs from the most composite kind down. A joined unit of several
  pieces is an assembly whatever operation built it. A single piece that only
  exists because an operation was applied is a process item, even when the
  piece also has a mechanical function. Anything left that carries a function
  is a mechanical part, and anything left is the material itself.
- Several pieces that are not joined are not one test item. A set of loose
  parts is a set of separate items and has to be declared that way, otherwise
  the specimen count and the measured property are both wrong.
- Reach is asymmetric and never upward or downward by default. An assembly
  result covers the unit as assembled and not the constituent materials or
  operations outside it. A material result covers the lot and form tested and
  not an operation applied to it. A process result follows the procedure and
  facility used, so a changed procedure is outside it.
- Specimen demand is per item, not per campaign. Each item in a category
  carries that category's minimum specimen count plus its reference
  specimens, and the campaign total is the sum across the grouped items.

## Workflow

1. Declare every item with an identifier and its four attributes. Reject a
   repeated identifier, because the grouped result is keyed on it.
2. Derive each category by precedence and stop at the first kind that fits.
   Reject a multi-piece item that is not joined rather than guessing which
   piece is the test item.
3. Group the campaign by category, keeping the identifiers so the report can
   be read back to the items that produced it.
4. Read the specimen form and the measured property off each present
   category, and take the specimen demand as the per-item count times the
   number of items in that category.
5. Attach the reach limits to each present category, in the form of what the
   result covers and what it explicitly does not, so a later claim can be
   checked against them.
6. Close with the duties the mix creates: record the procedure behind any
   process coupon, keep an uncycled reference per material, and report each
   category separately.

## Pitfalls

- Categorizing from the item's name. A part number on a bonded coupon does
  not make it a mechanical part; the operation is what the campaign is
  evaluating, and the specimen has to be made to the production procedure.
- Treating an assembly test as covering its materials. The materials saw the
  environment only in that configuration, with that load path and those
  interfaces, so the result supports nothing about them used elsewhere.
- Testing a process coupon made in the laboratory rather than to the
  production procedure. The result then follows the laboratory operation, and
  the operation actually shipped is still unevaluated.
- Declaring several loose pieces as one item to save chamber time. The
  measured property becomes undefined, because there is no single unit whose
  performance is being read.
- Sizing the campaign on the number of categories rather than the number of
  items. Two material lots are two items and carry the per-item count twice.
- Merging the pass rate across categories. A campaign that failed only its
  process coupons and passed everything else reads as a broad partial pass
  once the categories are summed together.

## Behavior contract (gate 3)

The attribute validation, precedence-based categorization, grouping,
specimen-demand arithmetic, specimen definitions and reach limits are
exercised by the gate 3 contract test:
scripts/test_q7004_test_item_categories.py against
scripts/q7004_test_item_categories_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7004_test_item_categories.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
