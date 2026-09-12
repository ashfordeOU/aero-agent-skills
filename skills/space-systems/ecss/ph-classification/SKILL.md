---
name: ph-classification
description: "Use when determine the pressure hardware category of a spacecraft or launch vehicle hardware item per ECSS-E-ST-32 clause 4.1: assign each item as a Pressure Vessel (PV), Pressure System (PS), Pressure Container (PC), or Simple Pressure Equipment (SPE) using the figure 4-1 through 4-3 decision criteria; apply SPE simplicity thresholds for pressure level, internal volume, geometry, material, and heat source; resolve multi-component assemblies as pressure systems with individually categorized sub-items; flag items that carry primary structural loads concurrently with pressure retention. Trigger: ecss, e-st-32-structures-scope, pressure-hardware, pressure-vessel, pressure-system, pressure-container, spe, ph-classification."
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
  tags: [ecss, e-st-32-structures-scope, pressure-hardware, pressure-vessel, pressure-system, pressure-container, spe, ph-classification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Pressure Hardware Category Determination (space-systems/ecss/ph-classification)

Use when the task is the pressure hardware category determination required
by ECSS-E-ST-32 clause 4.1 — applying the figure 4-1 through 4-3 decision
criteria to assign each hardware item to one of the four pressure categories
(PV, PS, PC, SPE) and resolving composite assemblies into their constituent
category structure.

## Domain quick reference

- Clause 4.1 establishes four pressure hardware categories. A **Pressure
  Vessel (PV)** is a single closed item whose sole primary function is
  pressure retention; it does not carry primary structural loads beyond
  those imposed by the pressure itself. A **Pressure System (PS)** is an
  interconnected assembly of pressure-retaining components (vessels,
  pipes, valves, fittings) that work as a functional unit; each
  constituent item within the PS is categorized individually before the
  assembly as a whole is resolved to PS. A **Pressure Container (PC)** is
  a closed item that retains pressure and simultaneously carries primary
  structural loads (e.g., a propellant tank that is also a primary
  structural node of the spacecraft). **Simple Pressure Equipment (SPE)**
  is a pressure-retaining item that meets all simplicity criteria
  simultaneously: simple geometric shape, maximum expected operating
  pressure (MEOP) at or below the threshold, internal volume at or below
  the threshold, standard/recognized material, and no internal heat
  source.

- The figure 4-1 decision tree evaluates items in priority order: assembly
  status first (→ PS), then structural-load concurrency (→ PC), then SPE
  simplicity criteria (→ SPE), with PV as the default for any item that
  fails all three branch conditions. Figure 4-2 codifies the SPE
  simplicity criteria as a five-condition AND gate; failure of any single
  condition routes the item to PV. Figure 4-3 addresses composite
  assemblies by decomposing the PS into its constituent items and
  recursively applying the figure 4-1 logic to each before rolling up to
  the PS label at the assembly level.

- MEOP is the highest pressure a system is expected to experience in
  service, including all operating modes; it is the governing pressure
  parameter for the SPE threshold check, not proof pressure or burst
  pressure.

## Workflow

1. For each hardware item under review, determine whether it is an
   interconnected assembly of pressure-retaining components forming a
   functional unit. If yes, record it as a PS candidate and enumerate its
   constituent sub-items for individual evaluation in the next step.

2. For each item that is not an assembly (including PS sub-items), check
   whether it concurrently carries primary structural loads while retaining
   pressure. If both functions are present, assign PC. Do not apply the
   SPE or PV checks to a PC candidate.

3. For items that are neither assemblies nor PC candidates, evaluate the
   five SPE simplicity criteria simultaneously: (a) geometry is a simple
   shape (sphere, plain cylinder, or flat-ended cylinder), (b) MEOP does
   not exceed the SPE pressure threshold, (c) internal volume does not
   exceed the SPE volume threshold, (d) material is standard and
   recognized for pressure service, (e) there is no internal heat source.
   Only if all five conditions are satisfied, assign SPE.

4. Any item that does not satisfy the assembly, PC, or SPE conditions is
   assigned PV. Record the rationale — which SPE criterion or criteria
   were not met — for traceability.

5. For PS assemblies, record the category of each sub-item alongside the
   PS category of the assembly. The composite result is the PS label at
   the top level with the constituent item results nested beneath it.

6. Confirm that every pressure item in scope has received a category
   assignment; flag any item whose input data was incomplete (missing MEOP,
   volume, or structural-load status) as an unresolved item requiring
   further data before the assessment can close.

## Pitfalls

- Applying the SPE check to an item that also carries structural loads —
  the PC branch must be resolved before the SPE gate is reached; an item
  that carries structural loads is PC regardless of whether it meets the
  simplicity criteria.

- Treating an assembly as a single PV because the assembly as a whole is
  not simple — the PS category exists specifically to capture assemblies;
  do not collapse a multi-component pressure circuit into a single PV
  assessment.

- Using proof or burst pressure rather than MEOP for the SPE threshold
  check — the SPE criteria reference the expected operating pressure, not
  the test or failure pressure; applying burst pressure will incorrectly
  exclude items that legitimately qualify as SPE.

- Omitting the structural-load question for items that are geometrically
  simple and low-pressure — a spherical titanium tank that is also a
  primary spacecraft structural node is PC, not SPE or PV, regardless of
  its pressure and volume values.

- Leaving a sub-item's category blank and rolling the whole assembly up to
  PS without individual records — figure 4-3 requires that each
  constituent item be categorized; the PS label at the assembly level does
  not replace the per-item category records needed for subsequent fracture
  control and factors-of-safety application.

## Behavior contract (gate 3)

The category-determination logic for PV, PS, PC, SPE, the SPE five-
condition gate, composite assembly resolution, and input validation are
exercised by the gate 3 contract test: scripts/test_ph_classification.py
against scripts/ph_classification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ph_classification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
