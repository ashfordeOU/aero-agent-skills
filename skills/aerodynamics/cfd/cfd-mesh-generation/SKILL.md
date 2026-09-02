---
name: cfd-mesh-generation
description: "Generate a CFD mesh for an aerospace flow case: choose between structured, unstructured, and hybrid grids, size the near-wall first cell height from a y plus target and skin friction coefficient, build boundary-layer prism layers with a growth ratio, flag cell quality with skewness, orthogonality, and aspect ratio checks, size the far-field domain, and plan refinement levels. Use when the task is CFD mesh generation, grid type selection, prism layer setup, near-wall resolution, domain sizing, or cell quality checking for a solver run. Produces the grid type recommendation, first cell height, prism layer count, quality verdict, cell count estimate, and refinement plan. Trigger: mesh generation, grid types, prism layers, first cell height, skewness, orthogonality, aspect ratio, domain size, mesh refinement."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: cfd
  tags: [cfd, mesh-generation, grid-types, structured-grid, unstructured-grid, hybrid-grid, prism-layers, first-cell-height, y-plus, skewness, orthogonality, aspect-ratio, domain-sizing, mesh-refinement]
  version: 0.1.0
  author: Aero Agent Skills
---

# CFD Mesh Generation (aerodynamics/cfd/cfd-mesh-generation)

Use when the task is CFD mesh generation for an aerospace flow
case: choosing the grid type, sizing the near-wall spacing from a
y plus target, building boundary-layer prism layers, checking cell
quality, sizing the far-field domain, or planning refinement.

## Domain quick reference

- Grid types: a structured grid is hexahedral with implicit
  point ordering, efficient for simple geometries such as airfoil
  sections, cascades, and ducts; an unstructured grid of tetrahedra
  or polyhedra fits complex geometries such as a full aircraft;
  a hybrid grid stacks prism layers on the walls and fills the rest
  with unstructured cells, the standard for wall-bounded external
  aerodynamics.
- Near-wall resolution: the first cell height comes from the
  dimensionless wall distance y+ = y * u_tau / nu, so
  y = y+ * nu / u_tau; u_tau = v_inf * sqrt(cf / 2) follows from
  the skin friction coefficient. A target y+ near 1 resolves the
  viscous sublayer, values up to about 30 blend wall treatment,
  and wall functions tolerate y+ up to about 300.
- Boundary-layer prism layers grow the first cell outward with a
  geometric growth ratio, commonly 1.1 to 1.3, until the
  boundary-layer thickness is covered; the layer count follows the
  geometric series sum h1 * (r^n - 1) / (r - 1).
- Cell quality metrics: skewness near 0 is good and above about
  0.9 is bad, the orthogonality angle should stay above about 20
  degrees, and the aspect ratio should stay small for general cells
  while boundary-layer cells legitimately run high.
- Domain sizing: far-field boundaries sit tens of chord or body
  lengths away, commonly 20 to 50 chords for external aero, so the
  boundary condition effect stays small; the cell count scales with
  domain volume over spacing cubed.
- Mesh refinement: each refinement level halves the cell size, so
  level n gives size_n = base / 2^n; refine the wake, shock, and
  separation regions, and adapt where the error indicator is large.

## Workflow

1. Choose the grid type with grid_type_recommendation from the
   geometry complexity and the boundary-layer resolution need.
2. Estimate u_tau from cf and v_inf, then size the first cell
   height from the y+ target with first_cell_height_from_cf (or
   first_cell_height when u_tau is known).
3. Count the prism layers with prism_layer_count from the first
   cell height, boundary-layer thickness, and growth ratio.
4. Check cell quality with quality_flags on skewness, orthogonality
   angle, and aspect ratio; pass boundary_layer_cell=True for
   near-wall cells so their high aspect ratio is not flagged.
5. Size the far-field domain and estimate the cell count with
   estimate_cell_count; plan refinement levels with
   refinement_sizes.
6. Verify the achieved y plus of the produced first cell with
   achieved_y_plus before generating the mesh.

## Pitfalls

- Sizing the first cell from the wrong y+ band: a y+ near 1 cell
  paired with a wall-function treatment wastes cells; the y+ target
  must match the wall treatment.
- Confusing the first cell height with twice it: y+ uses the cell
  center distance from the wall, not the cell width.
- Growth ratios near 1 explode the prism layer count; ratios above
  about 1.5 degrade the boundary-layer profile resolution.
- Ignoring quality metrics: skewed or low-orthogonality cells stall
  the solver even when the near-wall spacing is correct.
- A domain too small contaminates the solution from the far-field
  boundary; a domain too large wastes cells.
- Treating boundary-layer aspect ratio like general-cell aspect
  ratio: high aspect ratio is expected in prisms, not in the free
  stream.

## Behavior contract (gate 3)

The grid type, y plus, prism layer, quality, domain sizing, and
refinement logic is exercised by the gate 3 contract test:
scripts/test_cfd_mesh_generation.py against
scripts/cfd_mesh_generation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_cfd_mesh_generation.py

## Compliance

- NACA Report 824 is US government work (public domain); summary
  and reference data only, per standards-map.yaml. The mesh
  generation methodology here is common CFD practice, not
  reproduced text.
- compliance: STANDARDS-REF, gated: false.
