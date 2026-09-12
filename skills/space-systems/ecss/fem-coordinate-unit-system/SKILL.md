---
name: fem-coordinate-unit-system
description: "Use when verify that a finite element model (FEM) exchange package
  conforms to ECSS-E-ST-32C clause 4.2 coordinate-system and unit-system conventions:
  confirm every coordinate frame is right-handed Cartesian with an identified label
  and reference-frame linkage; confirm the declared unit system is an approved ECSS
  combination (SI: N, kg, m, Pa or engineering: N, t, mm, MPa); verify mass, force,
  length, and pressure units are internally consistent; flag coordinate frames whose
  axes fail the right-hand rule or lack a reference-frame linkage; and flag any exchange
  package whose declared unit system conflicts with its numeric content. Trigger:
  ecss, e-st-32-structures-scope, fem, coordinate-system, unit-system, right-hand-rule,
  si-units, structural-fem, exchange-package."
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
  tags: [ecss, e-st-32-structures-scope, fem, coordinate-system, unit-system, right-hand-rule, si-units, structural-fem, exchange-package]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — FEM Coordinate and Unit System (space-systems/ecss/fem-coordinate-unit-system)

Use when the task is verifying that a finite element model exchange package
satisfies the coordinate-system and unit-system conventions of
ECSS-E-ST-32C clause 4.2 before handover between organisations or tools.

## Domain quick reference

- ECSS-E-ST-32C clause 4.2 requires every FEM exchange package to declare
  its unit system and coordinate frames explicitly so that any receiving
  analyst can reconstruct the model geometry and load magnitudes without
  ambiguity.
- Two unit-system families are recognised. The SI family uses Newton for
  force, kilogram for mass, metre for length, and Pascal for pressure
  (N, kg, m, Pa). The engineering millimetre family uses Newton for force,
  tonne for mass, millimetre for length, and megapascal for pressure
  (N, t, mm, MPa). Within each family the force, mass, length, and pressure
  units are physically consistent — any mix across families (e.g. kg with mm
  or Pa with mm) is flagged as an error.
- Every coordinate frame in the exchange package must be right-handed
  Cartesian: the Z axis must equal the cross product of X and Y (to within
  numerical tolerance), and all three axes must be mutually orthogonal.
  Each frame must carry a non-empty label and a reference to the frame that
  defines its origin, so the frame tree can be reconstructed.
- One frame in the package must be designated as the global reference frame.
  All other frames trace their origin back through the frame tree to this
  global frame. A package that declares no global frame, or that names a
  global frame absent from the frame list, is non-compliant.

## Workflow

1. Retrieve the exchange package header: locate the declared unit-system
   block (force, mass, length, pressure fields) and the list of coordinate
   frame definitions. Reject any package missing either block before
   proceeding.
2. Validate the unit system: confirm the four unit fields are present, check
   that the pressure unit is derivable from force divided by length squared
   for the declared combination, and check that the mass unit satisfies
   force equals mass times acceleration for the declared force and length.
   Flag each inconsistency as a unit error. A consistent combination that
   matches neither approved family is flagged as requiring explicit project
   approval rather than automatic acceptance.
3. Validate each coordinate frame: confirm the label and origin-reference
   fields are non-empty strings; confirm each axis is a three-component
   vector; check mutual orthogonality of the three axes; verify the
   right-hand rule by computing the cross product of X and Y and comparing
   it to Z within tolerance. Record every failure as a frame error.
4. Resolve the global frame: confirm the package declares a global-frame
   label and that this label matches one of the validated frames. Flag a
   missing declaration or a label that is absent from the frame list.
5. Aggregate results: the exchange package is compliant only when all three
   error lists (unit errors, frame errors, global-frame errors) are empty.
   Report each finding with the specific field or frame label that triggered
   it so the originating analyst can locate and correct the source.

## Pitfalls

- Assuming that a unit system labelled "mm-based" is automatically
  consistent — the tonne (not kilogram) is the mass unit consistent with
  Newton and millimetre, because one newton equals one tonne times one
  millimetre per second squared. Using kilogram with millimetre and newton
  introduces a factor-of-1000 error in every inertial load.
- Accepting a coordinate frame whose axes look roughly orthogonal without
  computing the cross product — small angular errors accumulated across
  frame chains can place nodes millimetres out of position at model extremes,
  producing spurious stress concentrations in static analysis.
- Treating the absence of a global-frame declaration as a minor omission —
  without a named global frame the receiving tool cannot resolve absolute
  node positions, and any two analysts will reconstruct the geometry
  differently depending on which frame their pre-processor treats as global.
- Checking only the header unit declaration and not comparing it against the
  numeric values in the node or element data — a package exported with one
  unit system and whose header was manually edited to another will pass the
  header check while silently corrupting every load and stiffness magnitude.

## Behavior contract (gate 3)

The unit-system consistency, right-hand-rule, frame-field completeness, and
global-frame resolution logic is exercised by the gate 3 contract test:
scripts/test_fem_coordinate_unit_system.py against
scripts/fem_coordinate_unit_system_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fem_coordinate_unit_system.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
