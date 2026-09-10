---
name: e10-spec-tree
description: "Use when establishing or maintaining the specification tree of a space product decomposition per ECSS-E-ST-10C clause 5.2.3.1c and Annex J: mirror the product tree with one technical specification per node (support specifications included), check the tree has no orphan or duplicate specs, and confirm every spec's parent link matches the product tree's parent-child structure. Trigger: specification tree, spec tree, product decomposition, support specification, ECSS-E-ST-10C 5.2.3.1c, Annex J."
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
  tags: [ecss, e-st-10c, specification-tree, annex-j, product-tree, support-specification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Specification Tree (space-systems/ecss/e10-spec-tree)

Use when the task is establishing or maintaining the specification
tree of a product decomposition under ECSS-E-ST-10C clause 5.2.3.1c
and Annex J: one technical specification per product-tree node,
support specifications included, kept consistent with the product
tree's structure.

## Domain quick reference

- The specification tree mirrors the product tree (ECSS-E-ST-10C
  clause 5.2.3.1c): every product-tree node (configuration item) gets
  exactly one technical specification (TS) at that level.
- "Support specifications" cover products that support the mission
  product without flying or being delivered as the end item (e.g.
  ground support equipment, test rigs) -- they belong in the tree
  alongside the flight-product specs, at the node they specify.
- A spec's parent in the specification tree must be the technical
  specification of the product-tree node's parent -- flow-down and
  Annex J structure both depend on this parent link being correct.
- Annex J fixes the specification-tree record's shape: node
  identifier, product-tree parent, spec identifier, spec status.
  This leaf checks that shape, not the requirement content within
  each spec (see the sibling e10-trs-flowdown leaf for TRS content
  and e10-req-traceability for requirement-level trace).

## Workflow

1. List every node of the product tree (configuration items, support
   products included).
2. For each node, record its one technical specification and the
   product-tree parent node.
3. Check for orphan specs: a spec whose product-tree node does not
   exist in the product tree.
4. Check for duplicate specs: more than one spec assigned to the same
   product-tree node.
5. Check for missing specs: a product-tree node with no assigned
   spec.
6. Check parent-link consistency: each spec's declared parent
   product-tree node must equal its product-tree node's actual
   parent (root nodes have no parent).
7. The tree is consistent only when there are no orphans, no
   duplicates, no missing specs, and no parent-link mismatches;
   otherwise list every violation found.

## Pitfalls

- Treating a support specification (GSE, test rig) as out of scope
  and leaving its product-tree node without a spec.
- Assigning two specs to one product-tree node during a re-baseline
  (old and new spec both left active).
- A spec's recorded parent left stale after the product tree is
  re-parented (spec tree and product tree drift apart).
- Confusing this leaf's tree-shape check with TRS content flow-down
  (sibling e10-trs-flowdown leaf) or requirement-level traceability
  (sibling e10-req-traceability leaf).

## Behavior contract (gate 3)

The specification-tree consistency logic is exercised by the gate 3
contract test: scripts/test_e10_spec_tree.py against
scripts/e10_spec_tree_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_spec_tree.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
