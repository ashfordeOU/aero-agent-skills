---
name: fem-modelling-requirements
description: "Use when define and validate the finite element modelling requirements for a spacecraft structural FEM under ECSS-E-ST-32C section 4.3: select the idealization strategy for each structural component (stick, shell, or solid element region), choose element types matched to the load path and geometry, verify mesh density satisfies the spatial resolution criterion for the highest relevant mode or stress gradient, and confirm each material model maps to the correct constitutive law for the thermal and load regime. Verify coordinate and unit system consistency across the full model and confirm all boundary conditions carry a mechanical justification. Trigger: ecss, e-st-32-structures-scope, fem, mesh-density, element-types, idealization, material-models, calculix-linear."
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
  tags: [ecss, e-st-32-structures-scope, fem, mesh-density, element-types, idealization, material-models, calculix-linear]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — FEM Modelling Requirements (space-systems/ecss/fem-modelling-requirements)

Use when the task is to define or audit the modelling requirements for a
finite element model of a spacecraft structure under ECSS-E-ST-32C
section 4.3 -- choosing the idealization for each component, selecting
element types, setting mesh density criteria, assigning material models,
and confirming coordinate/unit system consistency and boundary-condition
justifications throughout the model.

## Domain quick reference

- Section 4.3 governs how a structural FEM is set up before analysis.
  Every component in the model must be assigned one of three
  idealization levels: STICK (beam/truss, aspect ratio ≥ 10),
  SHELL (thin-walled plate or shell element region), or SOLID
  (volumetric brick/tet, aspect ratio ≤ 5). The idealization must
  match the dominant structural behaviour of the component.
- Element types must be consistent with the chosen idealization:
  beam and truss elements for STICK regions, shell and membrane
  elements for SHELL regions, hexahedral/tetrahedral/wedge elements
  for SOLID regions. Mixing incompatible element families across an
  idealization boundary is a modelling error.
- Mesh density is governed by a spatial resolution criterion. For a
  stress analysis, the element size must not exceed one quarter of
  the characteristic stress-gradient length (e.g. the fillet radius,
  hole diameter, or wall thickness at the location of interest).
  For a modal analysis, at least six elements must span one
  half-wavelength of the highest target mode shape.
- Every material region must use a constitutive law appropriate to
  its material class and thermal loading: LINEAR_ELASTIC or ISOTROPIC
  for metallic materials with temperature excursions below 200 K,
  ORTHOTROPIC for unidirectional composites, and LAMINATE for
  multi-ply composite stacking sequences. A temperature excursion
  above 200 K on a metal with a LINEAR_ELASTIC model must be flagged
  for verification of property variation.
- The entire model must use a single, internally consistent coordinate
  and unit system. ECSS-E-ST-32C permits SI_N_M or SI_N_MM; mixing
  the two in the same model is a non-conformance.
- Every boundary condition must carry a written mechanical
  justification (symmetry plane, rigid interface, pin joint, etc.).
  An unjustified boundary condition is a modelling assumption that
  has not been substantiated and must be flagged.

## Workflow

1. List every structural component that will appear in the FEM.
   Assign an idealization (STICK, SHELL, or SOLID) to each, based
   on the dominant structural behaviour and geometry. Reject any
   component for which the idealization cannot be justified by the
   aspect ratio or load-path argument.
2. For each component, select an element type consistent with its
   idealization (beam/truss/bar for STICK; shell/membrane/plate for
   SHELL; hex/tet/wedge for SOLID). Flag any element type that
   crosses an idealization boundary without an explicit compatibility
   check.
3. Apply the mesh density criterion to each component: compute the
   limiting element size from the characteristic geometric feature
   (stress gradient length or modal wavelength), and verify the
   proposed element size does not exceed that limit.
4. Map each material region to a constitutive model. Check that
   composite materials use ORTHOTROPIC or LAMINATE models. Check
   that metals with temperature excursions above 200 K are flagged
   for property-variation verification.
5. Confirm that the entire model uses a single coordinate system
   (CARTESIAN, CYLINDRICAL, or SPHERICAL) and a single unit system
   (SI_N_M or SI_N_MM).
6. Review every boundary condition. Confirm each carries a written
   mechanical justification. Flag unjustified constraints.
7. Collect all findings. The model is not compliant until all
   findings are resolved.

## Pitfalls

- Applying SOLID elements to a component with a high aspect ratio
  and assuming it will still capture bending correctly -- slender
  members modelled as solid bricks exhibit shear locking and
  over-stiffness unless high-order elements and fine meshes are used;
  the correct remedy is to switch to a STICK or SHELL idealization.
- Setting the element size to the characteristic geometric feature
  size rather than a fraction of it -- the mesh density criterion
  requires multiple elements across the gradient, not one element
  per feature.
- Using a LINEAR_ELASTIC model for a large temperature excursion and
  treating the result as conservative -- material stiffness and
  strength often vary non-monotonically with temperature; the model
  may be non-conservative in one direction.
- Mixing coordinate systems or unit systems between sub-models and
  relying on the solver to reconcile them -- inconsistency is
  silent in many solvers and produces wrong interface loads.
- Leaving boundary conditions unjustified and treating the absence
  of a constraint violation as confirmation that the model is correct
  -- a spurious constraint can mask rigid-body modes and
  artificially stiffen the structure.

## Behavior contract (gate 3)

The idealization, element-type, mesh-density, material-model,
unit-system, and boundary-condition logic is exercised by the gate 3
contract test: scripts/test_fem_modelling_requirements.py against
scripts/fem_modelling_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_fem_modelling_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
