---
name: e10-req-allocation
description: "Use when allocating requirements to functions and to product-tree elements (configuration items) under ECSS-E-ST-10C: run functional analysis to establish the function tree, allocate each requirement to the function(s) it drives, allocate each requirement to the configuration item(s) that implement it, and check allocation completeness (no unallocated requirement, no orphan function or element) before the requirement baseline is frozen. ECSS-E-ST-10C clause 5.2.3.5 governs requirement allocation as part of system engineering requirement flow-down. Trigger: ecss, e-st-10c, requirement allocation, functional analysis, product tree, configuration item, function tree, 5.2.3.5, space systems engineering."
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
  tags: [ecss, e-st-10c, requirement-allocation, functional-analysis, product-tree, configuration-item, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Allocation (space-systems/ecss/e10-req-allocation)

Use when the task is allocating system or product requirements to
functions and to product-tree elements under ECSS-E-ST-10C clause
5.2.3.5, continuing the requirement flow-down started in the sibling
e10-req-analysis and e10-trs-flowdown leaves.

## When to use

- A requirement set exists (from e10-req-analysis / e10-trs-flowdown)
  and needs allocating to the functions that realize it and the
  configuration items (CIs) that implement it.
- Checking allocation completeness before freezing a requirement
  baseline (see e10-req-baseline) or a configuration baseline (see
  e10-config-baselines).
- Tracing which product-tree elements implement a given function, or
  which requirements land on a given CI.

## Domain quick reference

- Functional analysis decomposes the system into functions (the
  function tree; see e10-config-content / Annex H); the product tree
  decomposes it into configuration items (CIs).
- Clause 5.2.3.5 requires every requirement to be allocated both to the
  function(s) it drives and to the product-tree element(s) that
  implement it -- a two-sided allocation, not just one.
- Allocation is many-to-many: a requirement can drive several
  functions and land on several CIs; a function or CI can carry
  several requirements.
- Allocation is distinct from verification-method assignment (see
  e10-req-verif-methods) and from traceability record-keeping (see
  e10-req-traceability), though all three ride on the same requirement
  set.

## Procedure

1. Fix the reference function tree and product tree for the level
   being allocated (from functional analysis and the specification
   tree; see e10-spec-tree).
2. For each requirement, identify the function(s) it drives and record
   the functional allocation.
3. For each requirement, identify the product-tree element(s) (CIs)
   that implement it and record the product-tree allocation.
4. Reject an allocation that names a function or CI outside the
   reference trees (a naming or scope error).
5. Reject a requirement recorded with only a functional allocation or
   only a product-tree allocation -- clause 5.2.3.5 requires both
   sides before the allocation counts as complete.
6. Run the coverage check: list requirements still unallocated, and
   list functions or CIs carrying zero requirements (orphans worth a
   second look -- an unused function/CI, or a missed allocation).
7. Feed the completed allocation into the requirement baseline
   (e10-req-baseline) and the configuration baseline
   (e10-config-baselines); do not freeze either baseline while
   requirements remain unallocated.

## Pitfalls

- Allocating a requirement to a function only (or a CI only) and
  treating that as complete -- clause 5.2.3.5 needs both sides.
- Allocating to a function or CI name that was never defined in the
  function/product tree (typo or scope drift).
- Leaving an orphan CI or function unnoticed, which usually means a
  requirement was missed or the tree includes an element nothing
  actually needs.
- Confusing allocation (this leaf) with verification-method assignment
  (e10-req-verif-methods) -- allocation says where a requirement
  lives, not how it is proven.

## Verification

The allocation and coverage logic is exercised by the gate 3 contract
test: scripts/test_e10_req_allocation.py against
scripts/e10_req_allocation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_allocation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
