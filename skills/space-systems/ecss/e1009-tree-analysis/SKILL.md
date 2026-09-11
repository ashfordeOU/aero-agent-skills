---
name: e1009-tree-analysis
description: "Use when map product-tree frame relationships and derive transformation chains per ECSS-E-ST-10C Annex B: register each assembly element as a body-frame node in a directed tree, verify the tree has a single root and no cycles, find the transformation chain between any two frames through the lowest common ancestor, compose the chain of 4x4 homogeneous matrices into one frame-to-frame transform, and export the Franck diagram edge list showing every parent-to-child frame link. Trigger: ecss, e-st-10-system-scope, transformation-tree, Franck-diagram, frame-relationships, product-tree, coordinate-chain, homogeneous-transform."
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
  tags: [ecss, e-st-10-system-scope, transformation-tree, Franck-diagram, frame-relationships, product-tree, coordinate-chain, homogeneous-transform]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — Transformation Tree and Franck Diagram Analysis (space-systems/ecss/e1009-tree-analysis)

Use when the task is to map product-tree frame relationships and derive
transformation chains per ECSS-E-ST-10C Annex B — registering every
assembly element's body frame as a node in a directed tree, resolving
multi-hop chains through the lowest common ancestor, composing the
homogeneous transforms along that chain, and exporting the Franck
diagram edge list that depicts every parent-to-child frame link.

## Domain quick reference

- ECSS-E-ST-10C Annex B defines the **transformation tree** as a
  directed, acyclic graph in which each node represents the body frame
  attached to one product-tree element (spacecraft, subsystem, unit,
  part) and each directed edge carries the 4x4 homogeneous transform
  that expresses the child frame relative to its parent frame.  The
  tree has exactly one root node (usually the spacecraft reference
  frame) and zero or more children at every other level.
- A **Franck diagram** is a schematic rendition of that tree: boxes
  represent frames, arrows represent the parent-to-child transforms.
  It makes the chain of coordinate-system dependencies visible in one
  view so that reviewers can verify that no element's frame is left
  dangling (without a parent link) and that no circular dependency
  has been introduced.
- A **transformation chain** is the ordered sequence of nodes from a
  source frame to a target frame via the tree.  The chain passes
  upward through the lowest common ancestor (LCA) of the two nodes
  and then descends to the target.  Each ascending step uses the
  child's `transform_to_parent` directly; each descending step uses
  the mathematical inverse of the child's `transform_to_parent`.
- Transforms are 4x4 homogeneous matrices stored in row-major order.
  Composition is left-to-right matrix multiplication along the chain.
  For pure rotation-and-translation transforms the inverse is
  [R^T | -R^T t ; 0 | 1], computed without numerical inversion.

## Workflow

1. **Inventory frames**: for every element in the product tree, record
   its body frame name and its parent frame name.  The root element
   has no parent (set to `None`).  Reject any frame whose parent is
   not already registered — children must be added after their parent.

2. **Validate the tree**: confirm exactly one root exists, run a
   depth-first cycle check across all nodes, then verify every node
   is reachable from the root.  Collect all errors before reporting;
   do not proceed to chain resolution while the tree has structural
   defects.

3. **Resolve the chain**: given a source frame and a target frame,
   collect the ancestor lists of both up to the root, identify the
   LCA as the first common ancestor, then concatenate the upward path
   from source to LCA with the downward path from LCA to target.

4. **Compose the transform**: traverse the chain edge-by-edge.  For
   each ascending edge (node to its parent) multiply by the node's
   `transform_to_parent`; for each descending edge (parent to child)
   multiply by the inverse of the child's `transform_to_parent`.
   Accumulate with left-to-right matrix multiplication starting from
   identity.

5. **Export the Franck diagram**: collect all directed edges
   (parent, child) from the registered nodes.  This edge list is the
   machine-readable Franck diagram; pass it to a renderer or store it
   alongside the transformation tree for review.

6. **Flag defects**: any structural error from step 2 is a hard
   finding — the chain and the Franck diagram cannot be trusted until
   the tree is corrected.  Report each error with the offending node
   name so the engineer can locate and fix the broken link.

## Pitfalls

- Adding a child node before its parent is registered causes a
  validation error.  Always populate the tree in top-down order
  (root first, leaves last).

- Treating an ascending edge and a descending edge identically — both
  as `transform_to_parent` — doubles the transform in one direction
  and cancels it in the other.  Descending edges require the inverse.

- Omitting the homogeneous scale row (bottom row = [0, 0, 0, 1])
  when constructing a transform breaks matrix multiplication silently;
  always set element [3][3] = 1.

- Assuming a connected graph when the tree has multiple roots.
  Multiple roots mean at least one element has been orphaned from the
  main hierarchy; the Franck diagram will show a forest, not a tree.

- Using numerical matrix inversion for the inverse transform
  introduces floating-point error; for rotation-translation matrices
  the closed-form R^T / -R^T t inverse is exact.

## Behavior contract (gate 3)

The frame-node management, tree validation, chain resolution,
transform composition, and Franck-diagram export logic are exercised
by the gate-3 contract test:
scripts/test_e1009_tree_analysis.py against
scripts/e1009_tree_analysis_logic.py (stdlib unittest, offline).  Run:
  python3 scripts/test_e1009_tree_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
