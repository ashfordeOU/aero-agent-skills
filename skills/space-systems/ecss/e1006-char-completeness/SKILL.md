---
name: e1006-char-completeness
description: "Use when assess requirement-set completeness against a mission or function decomposition tree per ECSS-E-ST-10C §8.2.8: verify every leaf node in the tree has at least one covering requirement, every requirement traces to a known tree node, and no invalid trace references exist. Flag uncovered leaf nodes as completeness gaps. Flag requirements with no valid tree trace as uncategorized. Flag trace references to nonexistent nodes as data-entry errors, distinct from structural gaps. Returns a structured result: uncovered leaves, orphan requirements, and invalid trace pairs; is_complete is True only when all three lists are empty. Trigger: ecss, e-st-10-system-scope, e-st-10c, requirement-completeness, function-tree, mission-tree, traceability, gap-analysis, requirement-coverage."
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
  tags: [ecss, e-st-10-system-scope, e-st-10c, requirement-completeness, function-tree, mission-tree, traceability, gap-analysis, requirement-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Scope — Requirement-Set Completeness (space-systems/ecss/e1006-char-completeness)

Use when the task is the requirement-set completeness assessment of
ECSS-E-ST-10C §8.2.8 -- verifying that every leaf node in the mission
or function decomposition tree is covered by at least one requirement,
and that every requirement traces back to a known node in that tree.

## Domain quick reference

- §8.2.8 treats completeness as a two-sided check: the tree side (every
  leaf must be covered) and the requirement side (every requirement must
  be anchored to the tree). A gap on either side is a finding.
- The function or mission decomposition tree is hierarchical: an
  internal node represents a decomposed function or mission element;
  a leaf node is the bottom-level element that has not been further
  decomposed. Coverage is assessed at the leaf level -- a requirement
  that traces only to a parent node does not automatically cover the
  parent's children.
- An uncovered leaf is a completeness gap: the leaf represents a piece
  of the mission or function scope for which no requirement has been
  written.
- A requirement with no valid trace to any tree node is uncategorized
  against the tree -- it may be a hanging requirement, a duplicate with
  a wrong reference, or a data-entry error.
- An invalid trace reference (a requirement pointing to a node ID that
  does not exist in the tree) is recorded as a data-entry error and is
  reported separately from uncovered-leaf gaps, because the underlying
  requirement may actually be correct once the reference is fixed.

## Workflow

1. Build the function or mission decomposition tree from the system
   engineering baseline: load each node with its unique identifier and
   its parent identifier (or no parent for the root). Reject a node
   with a missing or duplicate identifier before proceeding.
2. Identify all leaf nodes -- nodes that have no children in the
   loaded tree. These are the coverage targets.
3. Load the requirement set. For each requirement, record the list of
   tree node identifiers it is stated to cover (its trace links).
4. Walk each requirement's trace links. For each link that resolves to
   a known tree node, mark that node as covered; if the node is a leaf,
   mark it in the covered-leaf set. For each link that does not resolve,
   record it as an invalid trace reference (req ID, unknown node ID).
   A requirement whose trace list is empty, or whose entire trace list
   is invalid, is flagged as uncategorized.
5. Compute the uncovered-leaf list: all leaf nodes not in the
   covered-leaf set.
6. Aggregate: uncovered leaves, uncategorized requirements, and
   invalid trace references. The assessment is complete (no gap) only
   when all three lists are empty.

## Pitfalls

- Checking coverage at the parent level and concluding that children
  are covered by inheritance. The procedure requires a direct trace
  link to a leaf node; a parent-level trace does not satisfy the
  leaf-level coverage check.
- Treating an invalid trace reference as a covered leaf. An unknown
  node ID may be a typo or a deleted node; it is a data-entry finding,
  not evidence of coverage.
- Ignoring uncategorized requirements as harmless. A requirement that
  traces to nothing may represent scope outside the tree, a missing
  tree node, or a stale reference; all three warrant investigation.
- Reporting is_complete = True when only the uncovered-leaf list is
  empty. Completeness requires all three finding lists to be empty:
  uncovered leaves, uncategorized requirements, and invalid traces.

## Behavior contract (gate 3)

The tree-building, leaf-detection, coverage-check, orphan-detection,
and invalid-trace logic is exercised by the gate 3 contract test:
scripts/test_e1006_char_completeness.py against
scripts/e1006_char_completeness_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e1006_char_completeness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
