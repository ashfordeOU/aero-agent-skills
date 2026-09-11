---
name: e1009-csd-drd
description: "Use when generate or validate a Coordinate Systems Document
  (CSD) for a spacecraft project under ECSS-E-ST-10-09C Annex A DRD
  requirements: define each coordinate frame with a unique identifier,
  origin, axis directions, frame type, and attachment body; record every
  frame-to-frame transformation with its rotation sequence and translation
  vector; populate the parameter tables with numeric values and units
  referencing the correct frame; and verify the document satisfies the DRD
  completeness checklist. Apply at any project phase that produces or
  updates a formal CSD deliverable. Trigger: ecss, e-st-10-system-scope,
  coordinate-systems, csd, frames, transformations, parameter-tables, drd,
  annex-a, rotation-sequence."
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
  tags: [ecss, e-st-10-system-scope, coordinate-systems, csd, parameter-tables, drd, annex-a]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coordinate Systems — CSD DRD (space-systems/ecss/e1009-csd-drd)

Use when the task is to generate or validate a Coordinate Systems Document
(CSD) per the ECSS-E-ST-10-09C Annex A DRD -- defining coordinate frames,
recording frame-to-frame transformations, populating parameter tables, and
verifying the document meets the DRD completeness checklist.

## Domain quick reference

- A CSD per ECSS-E-ST-10-09C Annex A must define every coordinate frame
  used in the spacecraft design. Each frame requires a unique identifier,
  a frame type drawn from the recognised set (inertial, body-fixed, orbital,
  sensor, antenna, solar-array, instrument, launch, topocentric), a stated
  origin, three orthogonally directed axes, and a body-attachment reference
  where applicable.
- Frame-to-frame transformations connect the coordinate tree. Each
  transformation entry specifies the source and target frame by identifier,
  the rotation sequence (an Euler-angle convention from the recognised set
  such as ZYX or ZXZ), three rotation angles in degrees, and a three-
  component translation vector in metres. Because transformations are
  invertible, the graph of defined transformations is treated as undirected
  when searching for a path between two frames.
- The parameter table records numeric geometric values that characterise
  the spacecraft geometry (offsets, alignment angles, mass properties). Each
  entry carries a name, a value, a unit, and a reference frame identifier
  that must resolve to a frame defined in the same document.
- The Annex A DRD completeness checklist requires: a document title and
  issue number; at least one inertial frame (e.g. J2000, GCRF); at least
  one body-fixed frame; at least one defined transformation; and a non-empty
  parameter table. A document is not compliant until all four validation
  passes (frame, transformation, parameter, DRD checklist) return no findings.

## Workflow

1. Assemble the inventory of all coordinate frames needed for the mission:
   identify the reference inertial frame, the spacecraft body-fixed frame,
   any orbital frame, and all instrument, sensor, and antenna frames. Assign
   a unique identifier and a frame type to each. Reject any frame whose type
   is not in the recognised set before it enters the document.
2. For each frame, specify the origin (a physical point or mass-centre),
   the three axis directions in plain text or by cross-product rule, and
   the body-attachment reference. Flag any frame missing an origin or axis
   definition before continuing.
3. For each pair of frames that must be directly linked, define a
   transformation entry: choose a valid Euler rotation sequence, specify
   three rotation angles (degrees), and a translation vector (metres).
   Verify that both frame identifiers resolve and that no self-transformation
   exists (source == target is invalid).
4. Build the parameter table: for each geometric parameter (mounting offset,
   alignment angle, focal length, etc.) record the name, numeric value, unit,
   and the frame in which the value is expressed. Reject any entry with an
   empty name, a missing unit, or a frame reference that does not resolve.
5. Run the DRD completeness check: confirm the title and issue number are
   present, that the frame set contains at least one inertial and one
   body-fixed frame, that at least one transformation is defined, and that
   the parameter table is non-empty.
6. Aggregate all findings from the four passes; the document is compliant
   only when every finding list is empty. For each rotation matrix entry,
   optionally verify orthonormality (R^T R = I and det(R) = +1) as an
   independent check on the numeric angles supplied.

## Pitfalls

- Defining two frames with the same identifier -- the second silently
  overwrites the first in some tools; the validation pass must flag
  duplicate frame IDs before any downstream calculation uses them.
- Providing a transformation whose rotation sequence is not in the
  recognised set -- a freeform sequence string such as "ABC" will produce
  a matrix that is numerically wrong; the sequence must be validated before
  the matrix is computed.
- Adding a parameter that references a frame defined in a different
  document -- the parameter table is self-contained; every frame_id in the
  table must resolve within the same CSD.
- Reading an empty findings list as a pass when the DRD completeness check
  was never run -- a document with no inertial frame and no transformations
  can reach the parameter-validation step without triggering an error there;
  the completeness step must always run last and is never optional.
- Treating transformation direction as one-way -- by convention, each
  defined transformation is invertible, so path-search must treat the
  transformation graph as undirected.

## Behavior contract (gate 3)

The frame-definition validation, transformation validation,
parameter-table validation, DRD completeness check, rotation-matrix
computation, orthonormality test, frame grouping by type, and
transformation-path search logic are exercised by the gate 3 contract
test: scripts/test_e1009_csd_drd.py against
scripts/e1009_csd_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_csd_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
