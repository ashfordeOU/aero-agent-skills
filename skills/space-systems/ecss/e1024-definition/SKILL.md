---
name: e1024-definition
description: "Use when define interfaces for a space system element by establishing the geometry, signals, protocols, and allocated budgets at each interface end in the IDD or single-end ICD, following ECSS-E-ST-10-24C §5.4: identify every interface end, assign the required geometric envelope and mounting constraints, document signal types and electrical characteristics or communication protocols, allocate per-end resource budgets and verify margin against capacity, and confirm the interface-definition record is complete before it is submitted to the interface control baseline. Trigger: ecss, e-st-10-system-scope, interface-definition, idd, icd, geometry, signals, protocols, budget, interface-end."
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
  tags: [ecss, e-st-10-system-scope, interface-definition, idd, icd, geometry, signals, protocols, budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Interface Definition (space-systems/ecss/e1024-definition)

Use when the task is to define the interfaces of a space system element per
ECSS-E-ST-10-24C §5.4 — establishing the IDD or single-end ICD content for
geometry, signals, protocols, and per-end resource budgets.

## Domain quick reference

- ECSS-E-ST-10-24C §5.4 requires every interface end to carry four attribute
  groups before the interface can be submitted to the controlled baseline:
  *geometry* (mounting point, envelope dimensions, mass), *signals or
  protocols* (signal type, voltage, impedance, or protocol name, data rate,
  message format), and *budget* (allocated resource vs. capacity with margin).
  An interface end without all applicable groups is incomplete and must not
  be baselined.
- Interface types recognised by this leaf: **mechanical** (geometry only),
  **electrical** and **optical** (geometry + signals), **data** (geometry +
  protocols + budget), **fluid** and **thermal** (geometry + budget). Each
  type maps to a fixed set of required attribute groups; supplying groups
  beyond those required is permitted but does not satisfy missing ones.
- Budget compliance requires allocated ≤ capacity and capacity > 0. The
  margin percentage is (capacity − allocated) / capacity × 100. A surface
  with an unset budget on a budget-bearing interface type is a finding, not
  a pass.
- For electrical and optical interfaces, both ends of a two-end pair must
  carry the same signal type and compatible voltage levels (within 0.5 V
  tolerance). A mismatch is a compatibility finding that blocks the IDD from
  being complete.

## Workflow

1. Collect every interface end from the IDD or single-end ICD record. Reject
   any end whose `end_id` is absent or blank, and any end whose
   `interface_type` is not one of the recognised types listed above.
2. For each end, determine which attribute groups are required by its
   interface type. Check that each required group (geometry, signals,
   protocols, budget) is present as a structured block with all mandatory
   fields populated.
3. For every budget block, evaluate compliance: confirm `allocated` and
   `capacity` are numeric, `capacity` > 0, `allocated` ≥ 0, and
   `allocated` ≤ `capacity`. Record the margin percentage. Flag any
   exceedance or missing field.
4. For electrical and optical end pairs, verify signal type identity and
   voltage compatibility across the two ends. Record any mismatch as a
   compatibility finding.
5. Aggregate per-end findings and cross-end compatibility findings. The IDD
   is complete only when both lists are empty for every end.
6. Emit a structured result: `complete` flag, per-end finding lists,
   compatibility findings, and a one-line summary. An incomplete IDD must
   not be submitted to the interface control baseline.

## Pitfalls

- Treating budget absence as a non-issue for data, fluid, or thermal
  interfaces — an interface end of those types with no budget block is
  incomplete, not implicitly compliant.
- Collapsing electrical and mechanical geometry requirements — mechanical
  ends do not require a signals block; electrical ends do. Applying the
  same attribute set to all types produces false findings on mechanical ends
  and false passes on electrical ends.
- Accepting a voltage difference below 0.5 V as always safe — the tolerance
  is an engineering default; project-specific requirements may be tighter.
  Flag such pairs and defer to the project's electrical interface budget.
- Baselined IDD records with unresolved findings — the §5.4 check must be
  clean before the record enters configuration control, not after.

## Behavior contract (gate 3)

The geometry, signals, protocols, budget, signal-compatibility, and full-IDD
logic is exercised by the gate 3 contract test:
scripts/test_e1024_definition.py against scripts/e1024_definition_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1024_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
