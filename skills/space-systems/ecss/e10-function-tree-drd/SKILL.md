---
name: e10-function-tree-drd
description: "Use when generate or validate a system function tree against the ECSS-E-ST-10C Annex H Document Requirements Definition: confirm the functional breakdown resolves as a single-rooted, fully connected hierarchy with unique identifiers and resolvable parent links, confirm each function is named with a bare action verb plus an object, reject a level that splits into a single pass-through child, and confirm every elementary function traces to a requirement and is allocated to exactly one system element. Trigger: ecss, e-st-10-system-scope, function-tree, annex-h-drd, functional-breakdown, elementary-function, function-allocation, requirement-trace."
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
  tags: [ecss, e-st-10-system-scope, function-tree, annex-h-drd, functional-breakdown, function-allocation, requirement-trace]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Function Tree DRD (space-systems/ecss/e10-function-tree-drd)

Use when the task is to produce or check a system function tree
against the Document Requirements Definition of ECSS-E-ST-10C Annex H
-- the single-rooted functional breakdown from one top function down
to elementary functions, its naming convention, and the trace and
allocation each elementary function must carry.

## Domain quick reference

- The tree has exactly one top function: the single node with no
  parent. Zero roots and several roots are both structural defects,
  and both are rejected before any content check runs -- a malformed
  tree makes every downstream finding unreliable.
- Structure is validated in a fixed order: unique identifiers, one
  root, resolvable parent links, then full connectivity from the root
  by following child links. The connectivity pass is what catches a
  cyclic branch and a branch detached from the tree, which a
  parent-link check alone cannot see.
- Functions are named with a bare action verb plus an object -- the
  imperative form, never a gerund. The convention is what keeps a
  function distinguishable from the component that performs it.
- A level that splits a function into exactly one child adds no
  information: it is a pass-through, and the DRD treats it as a
  finding rather than a harmless intermediate.
- Every elementary (leaf) function must trace to at least one
  requirement and be allocated to exactly one system element. Zero
  allocations leaves the function unowned; more than one leaves
  ownership ambiguous, and both are findings.
- Duplicate function names are compared without regard to case. Two
  identically named functions are a signal that one breakdown branch
  was copied and not re-worked.
- Structural defects raise; content gaps are collected as findings.
  The distinction matters: a defective tree cannot be assessed at all,
  while an incomplete one can be reported on and finished.

## Workflow

1. Validate identifier uniqueness across the node list.
2. Find the single top function; reject a tree with none or several.
3. Confirm each non-root node's parent link resolves to an existing
   node, then build the child index.
4. Confirm every function is reachable from the top function, which
   rejects both cycles and detached branches.
5. Check each function name against the bare-verb-plus-object
   convention.
6. Record a finding for each single-child (pass-through) level and for
   each duplicate name.
7. For each elementary function, record a finding for a missing
   requirement trace and for an allocation that is absent or not
   exactly one system element.
8. The tree is Annex H compliant only when the finding list is empty.

## Pitfalls

- Naming functions as gerunds or as nouns ("power distribution"),
  which turns the functional breakdown into a second product tree and
  loses the distinction Annex H exists to draw.
- Validating parent links and stopping there. A branch whose parents
  all resolve can still form a cycle or hang detached from the root;
  only the reachability pass finds it.
- Accepting a one-child level as a harmless grouping node. It splits
  nothing, so it carries no functional content and inflates the tree.
- Allocating an elementary function to several system elements to
  reflect shared implementation. Annex H wants one owner; shared
  implementation is expressed by decomposing the function further.
- Treating a structural defect as a finding to be listed alongside the
  others. Identifier collisions and missing roots make the rest of the
  assessment meaningless and must stop it.
- Comparing function names case-sensitively, which lets a copied
  branch pass by differing only in capitalization.

## Behavior contract (gate 3)

The naming, identifier-uniqueness, root-finding, parent-link,
connectivity, duplicate-name, pass-through, requirement-trace and
allocation logic is exercised by the gate 3 contract test:
scripts/test_e10_function_tree_drd.py against
scripts/e10_function_tree_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_function_tree_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
