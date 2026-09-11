---
name: e1009-mech-frames
description: "Use when define mechanical body frames for a spacecraft under ECSS-E-ST-10-09C §5.4.5: determine each frame's type (spacecraft body, equipment, or sensor mounting), verify the direction cosine matrix (DCM) satisfies orthogonality and proper-rotation constraints, confirm every equipment and sensor frame names a valid parent frame traceable to the spacecraft body frame, and validate that each equipment and sensor frame carries a tied alignment data record with a declared measurement status (measured, nominal, or estimated). Trigger: ecss, e-st-10-system-scope, mechanical-frames, body-frame, alignment-data, dcm, coordinate-frame, spacecraft-frame, sensor-mounting-frame."
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
  tags: [ecss, e-st-10-system-scope, mechanical-frames, body-frame, alignment-data, dcm, coordinate-frame, spacecraft-frame, sensor-mounting-frame]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling — Mechanical Body Frames (space-systems/ecss/e1009-mech-frames)

Use when the task is to define and validate mechanical body frames under
ECSS-E-ST-10-09C §5.4.5 — establishing the spacecraft body frame as the
root, attaching equipment and sensor mounting frames to it, verifying the
direction cosine matrix of each frame, and confirming that every
equipment and sensor frame carries a tied alignment data record.

## Domain quick reference

- ECSS-E-ST-10-09C §5.4.5 recognises three frame categories: the
  **spacecraft body frame** (root frame, origin at a designated structural
  reference point, parent = none), **equipment frames** (one per unit,
  origin at a defined mounting interface, parent must resolve to the
  spacecraft body frame), and **sensor mounting frames** (one per sensing
  element, parent must also resolve through the hierarchy to the spacecraft
  body frame). Each frame is described by a name, a 3-element origin
  vector, and a 3×3 direction cosine matrix (DCM) that rotates vectors
  expressed in that frame into the parent frame.
- A DCM is valid when it is orthogonal (R · Rᵀ = I within tolerance) and
  its determinant equals +1. A determinant of −1 indicates a reflection,
  not a physical rotation, and must be rejected. The tolerance for
  numerical orthogonality is 1 × 10⁻⁶ on the max element of |R·Rᵀ − I|.
- Alignment data ties a frame to the physical hardware. Each equipment
  and sensor frame must carry: the nominal DCM (as-designed rotation from
  the frame to its parent), a declared measurement status (measured,
  nominal, or estimated), and optionally a measured DCM obtained from
  post-integration theodolite or photogrammetry data. A frame whose
  measurement status is declared "measured" but whose measured DCM is
  absent warrants a warning.
- The parent chain of every non-spacecraft frame must be finite and
  acyclic: following parent links from any frame must eventually reach
  the spacecraft body frame without repeating a node.

## Workflow

1. Identify the spacecraft body frame and confirm it is defined with
   `parent = None`, a named origin, and a valid DCM (typically the
   identity matrix). Register it as the root of the frame hierarchy.
2. For each equipment frame, confirm the required fields are present
   (name, type, parent, origin, DCM), resolve the parent to an already
   registered frame, verify DCM orthogonality and determinant, and add
   the frame to the registry only if all checks pass.
3. For each sensor mounting frame, apply the same field, parent, and
   DCM checks as for equipment frames. Sensor frames may be parented to
   an equipment frame (which must itself already be registered) rather
   than directly to the spacecraft body frame.
4. For every equipment and sensor frame that has been accepted into the
   registry, confirm that an alignment data record exists naming that
   frame. Each alignment record must carry: `frame_name` (matching a
   registered frame), `nominal_dcm` (a valid 3×3 rotation matrix), and
   `measurement_status` (one of: measured, nominal, estimated). Flag
   any equipment or sensor frame with no alignment record as an
   incomplete alignment data package.
5. For each alignment record whose status is "measured", confirm a
   `measured_dcm` is present; if it is absent, raise a warning rather
   than a hard error, as the measurement may be planned but not yet
   delivered. If a `measured_dcm` is present, validate its orthogonality
   and determinant independently.
6. Walk the parent chain of every registered frame to confirm no cycle
   exists. A cycle indicates a data entry error and must be raised as a
   hard error.
7. Aggregate all hard errors and warnings per frame and per alignment
   record; the overall frame-set passes only when every frame and every
   alignment record is free of hard errors.

## Pitfalls

- Accepting a DCM with determinant −1 as a rotation: a pure sign error
  on one axis produces a reflection matrix that satisfies orthogonality
  but is physically invalid as a frame definition.
- Omitting the alignment record for sensor frames on the grounds that
  the sensor's position "is obvious from the drawing": the alignment data
  record is a contractual deliverable under §5.4.5 and its absence is a
  finding regardless of how well the geometry is understood informally.
- Nesting frames more than two levels deep without checking the full
  parent chain: a three-level chain (spacecraft → equipment → sensor) is
  valid, but a mis-typed parent name can silently truncate the chain or
  introduce a cycle that is invisible when checking only the immediate
  parent.
- Treating a "nominal" measurement status as equivalent to "measured":
  nominal indicates the as-designed value has not been verified by
  physical measurement; it is acceptable at early programme phases but
  must be replaced by "measured" before the alignment data package is
  closed for flight.

## Behavior contract (gate 3)

The frame-type, DCM orthogonality, parent-chain, and alignment-record
logic is exercised by the gate 3 contract test:
scripts/test_e1009_mech_frames.py against
scripts/e1009_mech_frames_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_mech_frames.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
