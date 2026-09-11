---
name: e10-config-content
description: "Use when define or check the configuration content of a space product under ECSS-E-ST-10C clause 5.4.2.1 and Annex H: confirm the product tree resolves as a hierarchy with no dangling parent and no cycle, allocate every function of the function tree to a real product-tree node, confirm each leaf node performs at least one function and carries a design definition, and confirm the assembly constraints reference only real nodes in an acyclic precedence order. Trigger: ecss, e-st-10-system-scope, configuration-content, product-tree, function-tree, annex-h, design-definition, assembly-constraints, precedence."
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
  tags: [ecss, e-st-10-system-scope, configuration-content, product-tree, function-tree, design-definition, assembly-constraints]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Configuration Content (space-systems/ecss/e10-config-content)

Use when the task is to define or check the configuration content of
ECSS-E-ST-10C clause 5.4.2.1 -- the four linked elements a product's
configuration definition must carry (product tree, function tree per
Annex H, design definition per node, assembly constraints) and the
structural consistency between them.

## Domain quick reference

- The product tree is a parent-pointer decomposition into
  configuration items. Two structural defects are distinct and must
  not be conflated: a *dangling* parent names a node that does not
  exist, while a *cycle* is a chain of real nodes that closes on
  itself. A node whose chain runs into a dangling parent is reported
  as dangling, not as a cycle -- reporting it twice would mask which
  edit fixes it.
- A leaf node is one no other node claims as parent. Leaves are
  derived from the tree, never declared, so adding a child silently
  demotes a former leaf and changes what the function-coverage check
  demands.
- The Annex H function tree allocates each function to the
  product-tree node that performs it. Two allocation defects are
  separate: a function allocated to nothing at all, and a function
  allocated to a node outside the product tree. Only an allocation
  landing on a real node counts as coverage.
- Every leaf node must perform at least one function -- a leaf that
  performs nothing is a configuration item with no reason to exist.
  Intermediate nodes are not held to that rule; their functions are
  discharged by their children.
- Every product-tree node needs a design definition on file. An
  absent entry and an entry that is not affirmative are the same
  finding: the node is undefined.
- Assembly constraints are a precedence graph over the same nodes. A
  key or prerequisite outside the product tree is a reference defect;
  a closed loop of prerequisites is an unbuildable order. A
  prerequisite that is not itself a key has simply no prerequisites of
  its own and must not be treated as missing.
- The configuration content is complete only when every one of those
  checks is clean. The elements are linked, so a gap in one is not
  offset by completeness in another.

## Workflow

1. Validate the product tree on its own: report dangling parents,
   then report cycles among the nodes that remain resolvable.
2. Derive the leaf set from the parent pointers rather than from any
   declared leaf flag.
3. Check the function tree against the product tree: report functions
   allocated to nothing, then functions allocated to a node outside
   the tree.
4. Report each leaf node with no function landing on it.
5. Report each product-tree node with no design definition on file.
6. Check the assembly precedence: report entries referencing nodes
   outside the tree, then report one circular dependency if the graph
   is cyclic.
7. Aggregate the findings; the configuration content is complete only
   when every list is empty.

## Pitfalls

- Reporting a node with a dangling parent as a cycle as well. The
  chain never closes -- it runs off the tree -- and double-reporting
  it points the fix at the wrong edit.
- Treating a declared leaf flag as authoritative. Leaves follow from
  the parent pointers, so a stale flag lets a node with children
  escape the function-coverage rule, or holds an intermediate node to
  a rule that does not apply to it.
- Accepting a function allocated to a node identifier that does not
  exist as covered. A misspelled allocation looks allocated and is
  exactly the defect the cross-check exists to find.
- Demanding a function on every node rather than on every leaf.
  Intermediate nodes discharge their functions through their children,
  so that reading produces findings against nodes that are correct.
- Treating a prerequisite that never appears as a key of the
  precedence mapping as a missing entry. It is a node with no
  prerequisites; a genuinely unknown node is caught by the
  reference check instead.
- Declaring configuration content complete because the product tree is
  clean while the design definitions or assembly constraints are not
  -- the four elements are checked independently and all must pass.

## Behavior contract (gate 3)

The product-tree structure, leaf derivation, function allocation, leaf
function coverage, design-definition presence, precedence reference and
precedence-cycle logic is exercised by the gate 3 contract test:
scripts/test_e10_config_content.py against
scripts/e10_config_content_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_config_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
