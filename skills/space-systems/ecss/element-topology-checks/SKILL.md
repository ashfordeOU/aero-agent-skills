---
name: element-topology-checks
description: "Use when verify finite element model topology against ECSS-E-ST-32C
  clause 5.3: categorize each element by its distortion metrics (aspect ratio,
  warping angle for four-node quadrilaterals, skewness for three-node triangles),
  check every node reference in the element connectivity table for validity, flag
  orphan nodes unreferenced by any element, and detect element pairs sharing
  identical node sets. The skill enforces threshold-based pass/warn/fail severity
  for each metric and aggregates findings into a single topology report. Trigger:
  ecss, e-st-32-structures-scope, element-topology, distortion-check, connectivity,
  duplicate-elements, fem-quality."
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
  tags: [ecss, e-st-32-structures-scope, element-topology, distortion-check, connectivity, duplicate-elements, fem-quality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Element Topology Checks (space-systems/ecss/element-topology-checks)

Use when the task is verifying the topological quality of a finite element
model per ECSS-E-ST-32C clause 5.3 — checking element distortions,
node connectivity integrity, and the presence of duplicate elements before
any structural analysis is run.

## Domain quick reference

- Clause 5.3 groups topology quality into three families. **Distortion**
  measures how far an element's shape deviates from its ideal form; a
  severely distorted element degrades stiffness matrix conditioning and
  introduces integration errors. **Connectivity** covers broken node
  references (an element references a node ID absent from the node table)
  and orphan nodes (a node defined in the table but unreferenced by any
  element). **Duplicate elements** are two or more elements whose node
  sets, when sorted, are identical; they superpose stiffness contributions
  and produce incorrect results.

- Distortion metrics depend on element type. For three-node triangles
  (TRIA3): **aspect ratio** (longest edge / shortest edge) and **skewness**
  (maximum deviation of any interior angle from the ideal 60°). For
  four-node quadrilaterals (QUAD4): aspect ratio and **warping angle**
  (dihedral angle between the two triangles formed by the diagonal split,
  measuring out-of-plane twist). Severity is two-tiered: WARN (usable but
  flag for review) and FAIL (element must be remeshed before analysis).

- Threshold guidance paraphrased from ECSS-E-ST-32C §5.3: aspect ratio
  WARN ≥ 5, FAIL ≥ 20; QUAD4 warping WARN ≥ 5°, FAIL ≥ 15°; TRIA3
  skewness WARN ≥ 45°, FAIL ≥ 60°.

## Workflow

1. Parse the node table into a mapping of node-ID → coordinates and the
   element table into a list of (element-ID, type, node-ID tuple) records.
   Reject any element type not in the supported set before it enters
   the distortion checks; log it as unsupported rather than silently
   skipping.

2. **Connectivity check** — for every element, verify that each referenced
   node ID exists in the node table; record a broken-reference finding with
   the element ID and missing node ID for any that do not. After iterating
   all elements, collect every node ID that was not referenced by any
   element and record an orphan-node finding for each.

3. **Duplicate-element check** — for every element, sort its node IDs to
   produce an order-independent key and insert the key into a dictionary
   mapping key → first-seen element ID. A collision on insert is a
   duplicate; record the pair of element IDs and the shared node set.

4. **Distortion check** — for each element whose type has a registered
   metric set, retrieve the node coordinates (skip if any node is missing;
   the connectivity check already reported the break), compute each metric,
   and compare against warn and fail thresholds. Record a finding with
   metric name, computed value, threshold, and severity for any breach.

5. Aggregate all findings into a topology report. The report passes only
   when it contains no FAIL-severity distortion findings, no connectivity
   findings, and no duplicate findings. WARN-level distortions are recorded
   but do not block the pass verdict.

6. Present the report grouped by finding family (distortion, connectivity,
   duplicate), sorted by severity (FAIL before WARN) within each family.
   For each distortion FAIL, recommend remeshing the flagged element before
   resubmitting.

## Pitfalls

- Applying distortion thresholds to element types for which they are not
  defined (e.g., using TRIA3 skewness on a TET4). Each metric is valid only
  for its target element topology; applying it elsewhere gives meaningless
  values.

- Treating a WARN verdict as equivalent to a clean pass when a downstream
  process expects strict compliance. WARN means the element is marginal but
  not necessarily illegal; project-specific analysis requirements may impose
  tighter limits than the clause 5.3 defaults.

- Reading "no connectivity findings" as proof that the mesh is fully
  connected. The connectivity check flags broken references and orphan
  nodes, not topological disconnection between sub-meshes (e.g., two
  independent groups of correctly referenced nodes with no shared boundary).
  Free-edge and free-face detection is a separate check outside the scope
  of this leaf.

- Confusing duplicate detection with coincident-node detection. Two
  elements are duplicates when their node-ID sets match; two physically
  overlapping elements whose node IDs differ are not caught by this check
  and require a geometric proximity search.

## Behavior contract (gate 3)

The connectivity, duplicate, and distortion logic is exercised by the gate
3 contract test: scripts/test_element_topology_checks.py against
scripts/element_topology_checks_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_element_topology_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
