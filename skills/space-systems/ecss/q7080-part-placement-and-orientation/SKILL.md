---
name: q7080-part-placement-and-orientation
description: "Determine the build orientation and plate placement of an additively manufactured part. Use when candidate orientations have to be compared before a job is nested and the choice has to be defended on properties rather than on packing: rotate each candidate's surface normals into the machine frame, measure the down-facing area left below the self-supporting angle, separate support that lands on a surface the design marked critical, measure build height and the bonded span presented to the plate as a residual-stress proxy, check the loaded axis is not aligned with the weak build direction, then score the survivors. Trigger: ecss, q-st-70-80-additive-manufacturing, am-build-orientation-selection, am-part-placement-on-platform, am-overhang-self-supporting-angle, am-residual-stress-orientation, am-build-direction-anisotropy."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-part-placement-and-orientation, am-build-orientation-selection, am-part-placement-on-platform, am-overhang-self-supporting-angle, am-residual-stress-orientation, am-build-direction-anisotropy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Part Placement and Orientation (space-systems/ecss/q7080-part-placement-and-orientation)

Use when the task is the part clause of ECSS-Q-ST-70-80 that places and
orients a part on the platform: choosing the orientation the part is built
at, with the resulting material properties, support burden and residual
stress all following from that one decision.

## Domain quick reference

- Orientation is a design decision, not a nesting convenience. It sets
  the anisotropy of the material in the part, which surfaces carry
  support witness, how tall the build is and how much stress the part
  accumulates, so packing more parts on a plate cannot pay for it.
- The build direction is the weak direction. Layer interfaces run
  perpendicular to it, so a loading axis aligned with the build is the
  orientation that puts every interface across the load path.
- A down-facing surface is self-supporting above an inclination to the
  plate, and not below it. The quantity is the angle between the facet
  and the plate, which is the complement of the angle between its normal
  and the build direction, and it moves with every candidate rotation.
- Support on a critical surface is a different failure from support
  area. Ordinary down-facing area costs time and finish; support fused
  to a sealing face or a fatigue-critical fillet leaves witness where
  the design cannot accept it.
- Residual stress grows with the bonded span and the build height. A
  long section anchored to the plate restrains contraction along its
  whole length, and every added layer adds another contraction cycle to
  restrain, which is why a lying-down part and a standing part with the
  same volume behave differently.
- The recoater blade meets a full-length edge all at once when that edge
  runs parallel to the blade. Skewing the part in plane turns the
  contact into a progressive one, which is why orientation includes an
  in-plane angle even for a part that only lies flat.
- Angles come out of trigonometry, so a facet exactly on the
  self-supporting angle can read a few units in the last place below it.
  The comparison absorbs that; the angle requirement is never relaxed.

## Workflow

1. Validate the bounding box, the facet set and every candidate
   orientation. A tilt outside a half turn, a zero-length normal or a
   non-positive facet area is an input error.
2. For each candidate, rotate the facet normals into the machine frame
   in-plane first and then by the tilt, and keep the down-facing facets
   whose inclination falls below the self-supporting angle.
3. Total that area, and total separately the part of it that lands on a
   facet the design marked critical.
4. Compute the oriented extents: the build height in the build direction
   and the longest in-plane extent as the bonded span.
5. Form the residual-stress index from the bonded span and the height
   against their reference values, so candidates are comparable.
6. Measure the angle between the declared loading axis and the build
   direction, and the skew of the part's long in-plane axis against the
   recoater blade line.
7. Reject candidates breaking a hard constraint: over the vertical
   envelope, loading axis closer to the build direction than allowed, or
   any support on a critical surface. Score the survivors on support
   area, height and stress, breaking an exact tie on the smaller support
   area and then on the identifier.
8. Report the selected orientation with its support burden and any blade
   skew finding, or report that nothing was feasible.

## Pitfalls

- Choosing the orientation that packs the plate best. Every property of
  the delivered part follows from the orientation, and the nest can be
  rebuilt around a decision that the part's properties cannot.
- Grading overhangs from the part frame. The facet angles that matter
  are the ones after the candidate rotation, and a surface that is
  self-supporting lying flat can be an overhang once the part is tilted.
- Treating support area as a single number. The same square millimetres
  are cheap on a rough non-functional underside and unacceptable on a
  sealing face, which is why the critical part of the area is separated.
- Standing a long part up to save plate area without checking the load
  path. That is precisely the orientation that lays every layer
  interface across the loading axis.
- Ignoring in-plane rotation because the part lies flat either way. The
  blade meets a long unskewed edge along its whole length, and a
  recoater strike loses the build the layout was optimising.

## Behavior contract (gate 3)

The bounding-box and candidate validation, normal rotation, overhang and
critical-surface area, oriented extents, residual-stress index, loading
axis and blade-skew angles, hard-constraint rejection and the scored
selection are exercised by the gate 3 contract test:
scripts/test_q7080_part_placement_and_orientation.py against
scripts/q7080_part_placement_and_orientation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_part_placement_and_orientation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
