---
name: model-geometry-checks
description: "Use when verify a finite element model geometry against ECSS-E-ST-32C
  §5.2 requirements: confirm all node IDs are unique, no two nodes share coordinates
  within the mesh tolerance, no unreferenced free nodes exist, every element references
  valid node IDs, interface node sets from adjacent substructures coincide within
  the specified interface tolerance, and surface element normals are consistently
  oriented. Apply before any FEM analysis (structural static, modal, or thermoelastic)
  to confirm the mesh is geometrically sound. Flag each finding as a geometry defect
  category—duplicate node ID, coincident nodes, free node, broken connectivity,
  interface mismatch, or reversed normal—and report pass or fail per category.
  Trigger: ecss, e-st-32-structures-scope, fem-geometry, node-uniqueness,
  interface-consistency, surface-normals, mesh-quality, free-nodes."
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
  tags: [ecss, e-st-32-structures-scope, fem-geometry, node-uniqueness, interface-consistency, surface-normals, mesh-quality, free-nodes]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — FEM Model Geometry Checks (space-systems/ecss/model-geometry-checks)

Use when the task is verifying the geometric soundness of a finite element
model under ECSS-E-ST-32C §5.2 before any structural analysis run. The
checks cover node consistency, element connectivity, substructure interface
compatibility, and surface element normal orientation.

## Domain quick reference

- ECSS-E-ST-32C §5.2 requires geometry checks on the FEM before analysis.
  The intent is to detect mesh defects that would silently corrupt results
  rather than produce a solver error: coincident nodes, disconnected mesh
  regions, interface gaps, and flipped surface patches.
- **Node uniqueness and coordinate checks**: every node must carry a unique
  ID. Two nodes whose coordinates coincide within the mesh coordinate
  tolerance (typically 1 × 10⁻⁶ model units) are flagged as a coincident
  pair; most solvers merge or ignore one arbitrarily, producing an
  unintended shared degree of freedom.
- **Free-node check**: a node not referenced by any element carries no
  stiffness contribution but consumes a degree of freedom and can produce
  spurious zero-energy modes in modal analysis. Every node must appear in
  at least one element connectivity list.
- **Element connectivity validity**: an element referencing a node ID that
  does not exist in the node table is a broken connectivity entry. The
  solver cannot assemble the element stiffness matrix and will abort or
  silently omit the element.
- **Interface node matching**: at the boundary between two substructure
  meshes (component-to-component, submodel-to-global, or thermal-to-
  structural), the nodes on each side of the interface must coincide within
  the interface tolerance (typically 1 × 10⁻⁴ model units, coarser than
  the coordinate tolerance to accommodate mesh-generation rounding). A gap
  beyond the interface tolerance means the two meshes are not connected and
  loads will not transfer correctly.
- **Surface normal consistency**: adjacent surface elements sharing an edge
  must have compatible winding order so that their outward normals agree in
  direction. The check uses the shared-edge winding rule: if element A
  traverses the shared edge from node P to node Q, element B must traverse
  it from Q to P. Two adjacent elements traversing the same edge in the
  same direction have inconsistent (opposing) normals.

## Workflow

1. Collect the full node table. Check that all node IDs are unique; record
   each duplicate ID as a finding before proceeding.
2. For every pair of nodes, compute the Euclidean distance and compare it
   against the mesh coordinate tolerance. Record each pair whose distance
   falls below the tolerance as a coincident-node finding.
3. Build a set of all node IDs referenced by elements. Any node ID in the
   node table but absent from this set is a free node; record it.
4. For every element, verify that each of its connectivity node IDs exists
   in the node table. Record any reference to a non-existent node ID as a
   broken-connectivity finding under the element ID.
5. For each named interface, retrieve the node lists from both sides (A and
   B). For every node on side A, search side B for a node within the
   interface tolerance; record any unmatched node from either side.
6. For each connected surface patch, apply the shared-edge winding check:
   build a directed edge map (source node → destination node) as each
   element's edges are processed. If an incoming element's edge direction
   already exists in the map (same direction as a prior element), record an
   inconsistent-normal-orientation finding for that element and its
   conflicting neighbor.
7. Aggregate all findings per category. The model geometry passes only when
   every category returns an empty finding list.

## Pitfalls

- Applying a coordinate tolerance that is too tight (e.g., machine epsilon)
  causes floating-point noise from mesh generation to appear as coincident-
  node findings. Use a tolerance matched to the model's unit system and
  mesh density, typically 1 × 10⁻⁶ of the characteristic part dimension.
- Applying an interface tolerance that is too loose masks genuine mesh gaps
  where substructure meshes are physically separated. Interface tolerance
  should be at most one order of magnitude larger than the coordinate
  tolerance.
- A free node in the model interior is almost always a mesh stitching error
  at a component boundary or a leftover node from a geometry cleanup step.
  Do not suppress the finding — trace it to the originating geometry
  operation.
- Single isolated surface elements have no shared edges and therefore
  produce no winding findings. A disconnected patch of one element cannot
  be verified for orientation; check it against the global outward-normal
  direction manually.
- Coincident nodes across an interface are not the same as a matched
  interface: a coincident-node pair within the same substructure at an
  interface location is still a defect, even if the interface check passes.

## Behavior contract (gate 3)

The node-uniqueness, coincident-coordinate, free-node, element-
connectivity, interface-matching, and surface-winding logic is exercised by
the gate 3 contract test: scripts/test_model_geometry_checks.py against
scripts/model_geometry_checks_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_model_geometry_checks.py
```

Expected output: `OK` with 15 or more tests passing.

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Normative anchor: ECSS-E-ST-32C §5.2 (geometry checks).
