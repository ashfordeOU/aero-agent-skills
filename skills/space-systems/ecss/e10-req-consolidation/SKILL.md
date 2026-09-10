---
name: e10-req-consolidation
description: "Use when a requirement subject is common to several next-lower-level products in an ECSS-E-ST-10C specification tree and must be consolidated into a support specification instead of repeated per product, or when the same requirement flows down to two or more products with conflicting values and the conflict must be resolved before the requirement baseline is set. ECSS-E-ST-10C clause 5.2.3.2 governs requirement consolidation and flow-down conflict resolution. Trigger: ecss, e-st-10c, requirement consolidation, support specification, flow-down conflict, common requirements, specification tree, 5.2.3.2."
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
  tags: [ecss, e-st-10c, requirement-consolidation, support-specification, flow-down, conflict-resolution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Consolidation (space-systems/ecss/e10-req-consolidation)

Use when the task is consolidating requirements common to several
products into a support specification, or resolving a conflict that
appears when the same requirement subject flows down to more than
one product, under ECSS-E-ST-10C clause 5.2.3.2.

## Domain quick reference

- ECSS-E-ST-10C clause 5.2.3.2 directs that requirements common to
  several next-lower-level products be consolidated into a support
  specification (a specification-tree node not tied to a single
  deliverable product — see the sibling e10-spec-tree leaf) rather
  than repeated, independently, in each product's technical
  requirements specification (see the sibling e10-trs-flowdown leaf).
- A requirement subject is a consolidation candidate only when it is
  shared by two or more products AND every product carries the same
  agreed value; a shared subject with disagreeing values is a
  flow-down conflict, not a consolidation candidate.
- A flow-down conflict must be resolved to one agreed value, with a
  rationale, before consolidation or baselining (see the sibling
  e10-req-baseline leaf).
- Consolidating a subject supersedes the original per-product
  requirement entries; the support specification becomes their
  single source, traced back to each superseded id.

## Workflow

1. Group flow-down requirements by subject and identify subjects
   shared by two or more products.
2. For each shared subject, compare values across products; a
   disagreement is a flow-down conflict.
3. Resolve any conflict to one agreed value with a documented
   rationale before proceeding.
4. Consolidate each conflict-free, multi-product subject into the
   applicable support specification; record the superseded
   per-product requirement ids.
5. Confirm the support specification and remaining product specs
   stay consistent with the resolved values (see the sibling
   e10-req-consistency leaf).

## Pitfalls

- Consolidating a subject before its value conflict is resolved
  (masks a disagreement instead of resolving it).
- Treating a subject used by only one product as a consolidation
  candidate (nothing to consolidate).
- Resolving a conflict without recording a rationale (untraceable
  decision).
- Leaving superseded per-product requirements in place after
  consolidation (duplicate, divergence-prone source of truth).

## Behavior contract (gate 3)

The grouping, conflict-detection, consolidation, and conflict-
resolution logic is exercised by the gate 3 contract test:
scripts/test_e10_req_consolidation.py against
scripts/e10_req_consolidation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_consolidation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
