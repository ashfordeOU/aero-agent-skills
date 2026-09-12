---
name: pfci-screening
description: "Use when identify the Potentially Fracture Critical Items (PFCIs) within a structural assembly or ground support equipment (GSE) set under ECSS-E-ST-32C clause 6.1: screen each item through the Figure 6-1 decision tree by checking structural role, worst-case failure effect, tensile-load presence, material fracture susceptibility, and minimum dimension threshold; determine whether each item is a PFCI requiring fracture control or a non-PFCI; and record the first gate where non-PFCI items are screened out. GSE items engaged in critical operations are included in the screening scope. Trigger: ecss, e-st-32-structures-scope, pfci, fracture-control, structural-screening, gse, fracture-critical, pfci-list."
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
  tags: [ecss, e-st-32-structures-scope, pfci, fracture-control, structural-screening, gse, fracture-critical, figure-6-1]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural — PFCI Screening (space-systems/ecss/pfci-screening)

Use when the task is to identify which structural items and GSE must be
treated as Potentially Fracture Critical Items (PFCIs) under ECSS-E-ST-32C
clause 6.1, using the Figure 6-1 decision-tree to determine the PFCI or
non-PFCI status of each item before fracture control analysis begins.

## Domain quick reference

- An item becomes a PFCI when all five conditions are satisfied: it
  performs a structural function, its failure would be catastrophic or
  critical, it carries tensile loads, it is made of a material susceptible
  to fracture, and its minimum cross-section meets the dimension threshold.
  The first condition that fails screens the item out as non-PFCI; that
  gate is recorded as the disqualifying gate.
- GSE is in scope provided the GSE item is engaged in a critical
  operation — one whose failure could cause loss of flight hardware or a
  crew safety hazard. GSE not engaged during a critical operation is
  excluded from fracture control scope before the five-gate check is
  applied. The GSE pre-check is auditable and distinct from Gate 1.
- The minimum dimension threshold (programme default: 1.27 cm²) is the
  cross-sectional area below which an item is too small to sustain a
  fatigue-initiating flaw of consequence. Programmes may apply a tighter
  threshold; the default applies when no programme-level override is
  specified.
- Material susceptibility covers all metallic alloys, composites,
  ceramics, and glass. A highly ductile material may be declared
  non-susceptible only when supported by approved fracture-toughness data
  and authorised by the fracture control authority.

## Workflow

1. Collect the item inventory: assemble the full list of candidate
   structural items and GSE, each identified by a unique item ID, name,
   structural role flag, worst-case failure-effect category (catastrophic,
   critical, marginal, negligible), tensile-load flag, material
   susceptibility flag, minimum cross-section area (cm²), and — for GSE
   — whether it is engaged in a critical operation.
2. Apply the GSE pre-check: for each GSE item, confirm it supports a
   critical operation. Exclude it as non-PFCI (gate: GSE-CRITICAL-OPERATION)
   if it does not; carry it forward otherwise.
3. Apply Gate 1 — Structural role: exclude items that perform no
   load-bearing structural function (gate: GATE-1-STRUCTURAL).
4. Apply Gate 2 — Failure effect: exclude items whose worst-case failure
   effect is marginal or negligible (gate: GATE-2-FAILURE-EFFECT).
5. Apply Gate 3 — Tensile-load presence: exclude compression-only or
   unloaded items that carry no tensile stress component capable of driving
   crack growth (gate: GATE-3-TENSILE-LOAD).
6. Apply Gate 4 — Material susceptibility: exclude items whose material
   holds an approved non-susceptibility declaration (gate: GATE-4-MATERIAL).
7. Apply Gate 5 — Minimum dimension: exclude items whose minimum
   cross-section is below the threshold (gate: GATE-5-DIMENSION).
8. Items that survive all five gates are PFCI. Compile the PFCI list and
   the per-item gate trail for handover to fracture control analysis.

## Pitfalls

- Omitting GSE from the screening inventory: GSE items that interface
  with flight hardware during critical operations (lifting, transport,
  mechanical test fixtures) must enter the screening process; their
  absence silently understates the fracture control programme scope.
- Recording a non-PFCI outcome without a disqualifying gate: the gate
  trail is auditable evidence; an item screened out without a recorded
  gate cannot be verified during fracture control reviews.
- Applying the minimum-dimension gate before the failure-effect or
  tensile-load gates: the five-gate order is not arbitrary — applying
  Gate 5 first can incorrectly exclude an item that would have been
  screened in at Gate 2 by a programme-level override.
- Conflating "no catastrophic failure mode" with "no fracture concern at
  all": an item with a critical (non-catastrophic) failure mode still
  satisfies Gate 2 and must proceed through the remaining gates.
- Allowing a GSE item to inherit its critical-operation status from its
  parent assembly: each GSE item is assessed individually on whether its
  own failure during the operation could cause the critical outcome.

## Behavior contract (gate 3)

The GSE pre-check, all five screening gates, batch-screening aggregation,
and input-validation error paths are exercised by the gate 3 contract
test: scripts/test_pfci_screening.py against scripts/pfci_screening_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_pfci_screening.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
