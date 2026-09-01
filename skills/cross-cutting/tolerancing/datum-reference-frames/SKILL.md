---
name: datum-reference-frames
description: "Use when you must establish the datum reference frame for a part per ASME Y14.5: parse the primary, secondary, and tertiary datum precedence from the drawing callout, compute the datum feature simulators (plane, axis, point), determine the degrees of freedom each datum constrains (translation and rotation), apply the material condition modifiers (MMB, LMB, RMB) to the datum feature references, and build the feature control frame string. Produces the datum reference frame definition, the constrained degrees of freedom table, the datum shift from the material condition modifier, and the feature control frame string that gates the GD&T scheme. Trigger: datum reference frame, datum precedence, primary secondary tertiary, degrees of freedom, datum shift, MMB LMB RMB, feature control frame."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: asme-y14-5
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: tolerancing
  tags: [datum-reference-frames, gdt, datum-precedence, primary-secondary-tertiary, feature-control-frame, material-condition, mmb-lmb-rmb, degrees-of-freedom, datum-simulators, asme-y14-5]
  version: 0.1.0
  author: AeroSkills
---
# Datum Reference Frames (cross-cutting/tolerancing/datum-reference-frames)

Use when the task is the datum system of a GD&T scheme: establishing
the datum reference frame from the datum precedence, the degrees of
freedom each datum constrains, the datum feature simulators, the
material condition modifiers on datum feature references, and the
feature control frame callout. This leaf defines the reference frame;
position tolerance zone math lives in position-tolerance-calc and
worst-case stackup lives in tolerance-stackup.

## Domain quick reference

- A datum reference frame is the coordinate system established from
  the datum features of a part, taken in precedence order: the
  primary datum establishes the frame first, the secondary datum
  locates the frame in the next direction, and the tertiary datum
  finishes the location. The 3-2-1 rule is the common pattern: the
  primary datum constrains three degrees of freedom, the secondary
  two, the tertiary one.
- Six degrees of freedom exist: three translations (tx, ty, tz) and
  three rotations (rx, ry, rz).
- Datum feature simulators: a planar surface is simulated by a plane
  (three point contact), a cylindrical surface (hole, pin, shaft) by
  its axis, a spherical surface by a point.
- A plane constrains one translation (along its normal) and two
  rotations (tilting about the in-plane axes). An axis constrains two
  translations (perpendicular to the axis) and two rotations. A point
  constrains three translations.
- In a frame, each datum constrains only the degrees of freedom not
  already constrained by the earlier datums, so swapping the primary
  and secondary datums changes the constraint table.
- Material condition modifiers on datum feature references set the
  simulator boundary: RMB (regardless of material boundary) fixes the
  simulator with zero datum shift; MMB (maximum material boundary)
  allows datum shift equal to the departure of the actual mating size
  from the MMB size; LMB (least material boundary) allows datum shift
  equal to the departure from the LMB size. For a hole the MMB size is
  the smallest hole and the LMB size the largest; for a pin the MMB
  size is the largest pin and the LMB size the smallest.
- The feature control frame is the drawing callout: the geometric
  characteristic symbol, the tolerance value with an optional diameter
  symbol and material condition modifier, then the datum feature
  references with their modifiers, e.g. position symbol, diameter 0.5
  at MMC, datums A, B at MMB, C.

## Workflow

1. Collect the datum feature references from the drawing callout in
   precedence order: primary, secondary, tertiary. For each, record
   the feature type (plane, axis, point), the orientation (x, y, z)
   and any material condition modifier.
2. Parse and validate the precedence with parse_datum_precedence.
3. Build the reference frame with datum_reference_frame: read the
   simulators and the constrained degrees of freedom table from the
   result.
4. Read the unconstrained degrees of freedom: a fully located frame
   leaves none; a free rotation about a primary axis is a normal
   result, not an error.
5. Apply the material condition modifier with datum_shift to get the
   datum shift available from each datum feature reference.
6. Build the callout with feature_control_frame and report the frame
   definition, the constraint table, the datum shifts, and the frame
   string.

## Datum system model

### Degrees of freedom by simulator

| Feature type | Simulator | Constrains (orientation z shown) |
|---|---|---|
| plane | plane | tz, rx, ry (1 translation + 2 rotations) |
| axis | axis (centerline) | tx, ty, rx, ry (2 translations + 2 rotations) |
| point | point | tx, ty, tz (3 translations) |

### Precedence arithmetic

Each datum contributes its own degree of freedom set minus everything
already constrained. Example, the 3-2-1 block:

1. Primary plane with normal z: {tz, rx, ry}, three constrained.
2. Secondary plane with normal x: own set {tx, ry, rz} minus the
   primary leaves {tx, rz}, two constrained.
3. Tertiary plane with normal y: own set {ty, rx, rz} minus both
   leaves {ty}, one constrained.

Total six constrained, the frame is fully located. An axis primary
along z with two perpendicular planes leaves the rotation about the
axis free: that degree of freedom is reported unconstrained.

### Material condition model

The modifier on a datum feature reference sets the simulator boundary
and the datum shift available:

| Modifier | Boundary | Datum shift |
|---|---|---|
| RMB | fixed simulator | 0 |
| MMB (hole) | MMB size = smallest hole | actual mating size minus MMB size |
| MMB (pin) | MMB size = largest pin | MMB size minus actual mating size |
| LMB (hole) | LMB size = largest hole | LMB size minus actual mating size |
| LMB (pin) | LMB size = smallest pin | actual mating size minus LMB size |

### Feature control frame string

Format: symbol | tolerance segment | datum references. The tolerance
segment is the optional diameter symbol, the tolerance value, and the
optional material condition modifier (M, L, S). Datum references are
uppercase letters with an optional MMB or LMB suffix. Example:
position symbol, diameter 0.5 at MMC, datum A, datum B at MMB, datum
C renders as the symbol, the segment diameter-0.5-M, then A, B-M, C.

## Worked example

Mounting bracket: datum A is the base face (plane, normal z), datum B
is the side face (plane, normal x), datum C is the locating hole
(axis, z, referenced at MMB). The hole pattern uses a position
tolerance of 0.5 diameter at MMC.

1. parse_datum_precedence returns A (plane, z, rmb), B (plane, x,
   rmb), C (axis, z, mmb).
2. datum_reference_frame: A constrains tz, rx, ry (3); B constrains
   tx, rz (2); C constrains ty (1). Total six, nothing unconstrained.
3. The locating hole measures 10.2 actual mating size against the
   10.0 MMB size: datum_shift("mmb", "hole", 10.0, 10.2) gives 0.2
   datum shift for datum C.
4. feature_control_frame("position", 0.5, ("A", "B", {"letter": "C",
   "modifier": "mmb"}), "mmc") renders the frame string: position
   symbol, diameter 0.5 at MMC, datums A, B, C at MMB.

## Pitfalls

- Confusing the datum system with the tolerance zone: the reference
  frame defines where the coordinate system is and what each datum
  locks; the position zone diameter and the stackup are separate
  leaves (position-tolerance-calc, tolerance-stackup).
- Ignoring precedence: the secondary datum constrains only what the
  primary left free; reporting its full own set double counts
  degrees of freedom.
- Treating an unconstrained rotation as an error: an axis primary
  legitimately leaves the rotation about the axis free until a
  tertiary feature locks it.
- Reversing the MMB direction: a hole gains datum shift as it grows
  past the MMB size, a pin as it shrinks below it.
- Forgetting the material condition modifier on the datum feature
  reference: RMB is the default, MMB and LMB change both the boundary
  and the available shift.
- Writing the callout without the diameter symbol for cylindrical
  zones: position, concentricity, symmetry, and cylindricity zones
  are diameters.

## Behavior contract (gate 3)

The precedence parsing, simulator mapping, degree of freedom table,
material condition shift, and feature control frame string logic is
exercised by the gate 3 contract test:
scripts/test_datum_reference_frames.py against
scripts/datum_reference_frames_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_datum_reference_frames.py

## Compliance

- Standards referenced, not reproduced: ASME Y14.5 is proprietary and
  sold (ASME); the datum precedence method, the degree of freedom
  model, the material condition boundary rules, and the feature
  control frame format are common GD&T methodology, name and
  paraphrase only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false (reference-only listing).
