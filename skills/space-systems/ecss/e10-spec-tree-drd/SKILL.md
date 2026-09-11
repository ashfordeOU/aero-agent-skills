---
name: e10-spec-tree-drd
description: "Use when generate or validate a project specification tree against the ECSS-E-ST-10C Annex J Document Requirements Definition: confirm the tree is singly rooted, fully connected and free of duplicate identifiers, confirm each specification sits exactly one level below its parent, confirm every product-tree node carries exactly one specification, and confirm every non-root specification declares the parent it flows its requirements down from. Trigger: ecss, e-st-10-system-scope, specification-tree, annex-j-drd, requirement-flowdown, product-tree-coverage, specification-levels."
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
  tags: [ecss, e-st-10-system-scope, specification-tree, annex-j-drd, requirement-flowdown, product-tree-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Specification Tree DRD (space-systems/ecss/e10-spec-tree-drd)

Use when the task is to produce or check a project's specification tree
against the Document Requirements Definition of ECSS-E-ST-10C Annex J --
the hierarchy of technical specifications that mirrors the product tree,
and the flow-down link each specification carries to its parent.

## Domain quick reference

- The specification tree is not the product tree; it is the tree of
  documents that specify it. The two are checked against each other,
  and a specification with no product node is as much a defect as a
  product with no specification.
- There is exactly one top-level system specification. Zero roots and
  several roots are both structural defects, rejected before any
  content check runs, because a malformed tree makes every downstream
  finding unreliable.
- Structure is validated in a fixed order: unique identifiers, one
  root, resolvable parent links, then reachability from the root.
  The reachability pass is what catches a cyclic branch and a branch
  detached from the apex, neither of which a parent-link check alone
  can see.
- A specification's kind fixes its level -- system, subsystem,
  equipment, part. A child must sit exactly one level below its
  parent; a skipped level means a decomposition step was never
  specified, so the requirements of that step have nowhere to live.
- Product coverage is exact, not minimal: a node with no
  specification leaves requirements unstated, and a node specified
  twice leaves two documents free to contradict each other. Both are
  findings.
- Every non-root specification declares the parent it flows down
  from, and that declaration must name its actual parent. A
  flow-down link pointing somewhere else is worse than a missing one,
  because the trace looks complete while leading to the wrong
  requirement set.
- Structural defects raise; content gaps are collected as findings. A
  defective tree cannot be assessed at all, while an incomplete one
  can be reported on and finished.

## Workflow

1. Validate identifier uniqueness and the kind of every specification.
2. Find the single top-level specification; reject a tree with none or
   several.
3. Confirm each non-root specification's parent link resolves, then
   build the child index.
4. Confirm every specification is reachable from the root, which
   rejects both cycles and detached branches.
5. Check each specification's level against its parent's, and confirm
   the root sits at system level.
6. Cross-check against the product tree: report nodes with no
   specification and nodes specified more than once.
7. Confirm every non-root specification declares a flow-down link that
   names its actual parent.
8. The tree is Annex J compliant only when the finding list is empty.

## Pitfalls

- Treating the specification tree as a copy of the product tree.
  They are cross-checked precisely because they can disagree, and
  collapsing them hides exactly the gaps Annex J exists to surface.
- Validating parent links and stopping there. A branch whose parents
  all resolve can still close on itself or hang detached from the
  root; only the reachability pass finds it.
- Accepting a level skip as a harmless shortcut when a subsystem
  talks straight to a part. The missing intermediate specification is
  where that decomposition's requirements would have been written.
- Reading product coverage as "at least one specification". Two
  specifications for one product is a live contradiction risk, not
  redundancy.
- Accepting any non-empty flow-down field as a trace. A link that
  names a specification other than the parent passes a presence check
  and still points at the wrong requirement set.
- Listing a duplicate identifier alongside the content findings. It
  makes every trace ambiguous, so the assessment must stop instead.

## Behavior contract (gate 3)

The kind/level, identifier-uniqueness, root-finding, parent-link,
reachability, level-consistency, product-coverage and flow-down logic
is exercised by the gate 3 contract test:
scripts/test_e10_spec_tree_drd.py against
scripts/e10_spec_tree_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_spec_tree_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
