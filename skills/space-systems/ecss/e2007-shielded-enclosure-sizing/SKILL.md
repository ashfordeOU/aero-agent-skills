---
name: e2007-shielded-enclosure-sizing
description: "Use when size an EMC shielded-enclosure against ECSS-E-ST-20-07C clause 5.2.2.2: strip the absorber-lined thickness off each internal dimension to obtain the usable envelope, place the unit-under-test on its ground-plane bench with the declared edge-clearance, add the measurement-antenna standoff, the antenna-body depth and the antenna-to-absorber-tip clearance along the measurement axis, then verify the enclosure clears the required length, width and height with positive margin while the quiet-zone diameter still covers the bench footprint. Use it to reject an enclosure too small for the declared layout before a facility slot is booked. Trigger: ecss, e-st-20-07c, shielded-enclosure-sizing, anechoic-chamber-envelope, absorber-lined-wall, measurement-antenna-placement, quiet-zone-diameter, ground-plane-bench-layout, emc-facility-adequacy."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-shielded-enclosure-sizing, shielded-enclosure, anechoic-chamber-envelope, absorber-lined-wall, measurement-antenna-placement, quiet-zone-diameter, ground-plane-bench-layout]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC Facility — Shielded-Enclosure Sizing (space-systems/ecss/e2007-shielded-enclosure-sizing)

Use when the task is the facility-adequacy check of ECSS-E-ST-20-07C
clause 5.2.2.2 -- deciding whether a shielded-enclosure or
absorber-lined anechoic room is physically large enough to hold the
declared unit-under-test layout and the measurement-antenna placement
that the emission and susceptibility runs require.

## Domain quick reference

- Clause 5.2.2.2 is a geometry requirement, not a shielding-performance
  requirement. The enclosure's shielding-effectiveness and its
  absorber-lined reflectivity are graded elsewhere; here the only
  question is whether the declared layout fits inside the enclosure
  with the clearances the measurement method demands.
- The internal dimensions of a shielded-enclosure are not the usable
  dimensions. Absorber on the two opposing walls of each axis consumes
  twice the absorber depth, and a ceiling-lined or floor-lined
  enclosure loses that depth again on the vertical axis. Sizing always
  works on the usable envelope, never on the raw internal envelope.
- Along the measurement axis the required length is the sum of four
  terms: the depth of the unit-under-test on its bench, the declared
  antenna standoff (the calibrated separation between the front face
  of the unit and the antenna reference point, typically 1 m, 3 m or
  10 m), the physical depth of the antenna body, and the clearance
  that must remain between the antenna and the absorber tips behind
  it. Dropping any one term silently shrinks the requirement.
- Across the lateral axis the required width is the bench width, which
  is the unit width plus the side edge-clearance on both sides, plus
  any support-equipment rack standing beside the bench and its own
  separation.
- On the vertical axis the required height is the ground-plane bench
  height plus the unit height plus headroom to the ceiling absorber;
  the antenna also scans over a height range, so the antenna's top
  scan position plus half its aperture must clear the same ceiling.
  The governing vertical requirement is the larger of the two.
- The quiet zone is the region within which the absorber-lined
  performance is qualified. The bench footprint diagonal must sit
  inside the declared quiet-zone diameter, otherwise part of the unit
  radiates from or is illuminated in an unqualified region even though
  the enclosure is dimensionally large enough.

## Workflow

1. Validate the enclosure record: internal length, width and height
   all positive, absorber depth non-negative, and twice the absorber
   depth strictly smaller than every internal dimension it is applied
   to. Reject the enclosure outright rather than returning a negative
   usable dimension.
2. Reduce the internal envelope to the usable envelope by removing the
   absorber depth from both ends of each lined axis.
3. Validate the layout record: unit footprint and height positive,
   bench height positive, edge-clearance and support-equipment
   separation non-negative, antenna standoff one of the calibrated
   separations, antenna type one of the recognized designations.
4. Build the requirement on each axis independently -- measurement
   axis, lateral axis, vertical axis -- from the terms above.
5. Compare each requirement against the matching usable dimension and
   record the signed margin. Treat a margin that is zero to within the
   dimensional tolerance as satisfied; the layout terms are a sum of
   floating-point lengths, so an exactly-fitting layout can otherwise
   read a few units in the last place short.
6. Check the bench footprint diagonal against the declared quiet-zone
   diameter under the same tolerance.
7. Aggregate the findings. The enclosure is adequate only when every
   axis margin is non-negative and the quiet-zone check passes; report
   the governing axis (smallest margin) so the facility search has a
   number to work against.

## Pitfalls

- Sizing against the raw internal dimensions and discovering on the
  day that the absorber wedges consume half a metre per wall. The
  usable envelope is the only envelope that counts.
- Omitting the antenna-body depth or the antenna-to-absorber-tip
  clearance because the antenna standoff sounds like the whole
  requirement -- the standoff is measured to the antenna reference
  point, and the hardware continues behind it.
- Taking the vertical requirement from the bench stack alone and
  forgetting that the antenna scans upward; the scan ceiling often
  governs a low-profile unit.
- Reading a dimensional pass as a quiet-zone pass. A large enclosure
  with a small qualified quiet zone still fails clause 5.2.2.2 for a
  wide bench footprint.
- Widening the engineering clearance to make an exactly-fitting layout
  pass. The fix for a boundary case is a dimensional tolerance on the
  comparison, never a smaller clearance.

## Behavior contract (gate 3)

The envelope-reduction, per-axis requirement, margin and quiet-zone
logic is exercised by the gate 3 contract test:
scripts/test_e2007_shielded_enclosure_sizing.py against
scripts/e2007_shielded_enclosure_sizing_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_shielded_enclosure_sizing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
