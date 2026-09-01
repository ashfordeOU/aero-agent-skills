---
name: gdandt-basics
description: "Interpret geometric dimensioning and tolerancing callouts per ASME Y14.5: parse a feature control frame into its symbol, tolerance, and datum references, identify the tolerance zone type and whether the callout is a form, orientation, position, profile, or runout tolerance, apply the material condition modifiers MMC, LMC, and RFS, and compute the bonus tolerance and the total tolerance when the feature departs from its maximum material condition size. Produce the callout summary with zone, category, modifier meaning, and any bonus. Use when the task is GD&T fundamentals: feature control frames, datum reference frames, form tolerances such as flatness, straightness, circularity, and cylindricity, orientation tolerances such as perpendicularity, parallelism, and angularity, position tolerance, profile, runout, or material condition and bonus tolerance on drawings. Trigger: feature control frame, GD&T, MMC, LMC, RFS, bonus tolerance, datum reference frame, flatness, perpendicularity, position tolerance."
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
  tags: [gdandt-basics, gdandt, feature-control-frame, datum-reference-frame, form-tolerances, orientation-tolerances, position-tolerance, profile-tolerance, runout, mmc, lmc, rfs, bonus-tolerance]
  version: 0.1.0
  author: AeroSkills
---
# GDandT Basics (cross-cutting/tolerancing/gdandt-basics)

Use when the task is the geometric dimensioning and tolerancing
fundamentals behind an ASME Y14.5 drawing: reading a feature control
frame, establishing the datum reference frame, telling a form,
orientation, position, profile, or runout tolerance apart, applying
the material condition modifiers (MMC, LMC, RFS), and computing the
bonus tolerance that becomes available when a feature departs from its
maximum material condition size. This leaf is the foundation for the
tolerancing pack; it is distinct from
cross-cutting/tolerancing/position-tolerance-calc (which runs the full
position verification with virtual condition), from
cross-cutting/tolerancing/tolerance-stackup (which sums tolerance
contributions across an assembly), and from
cross-cutting/tolerancing/datum-reference-frames (which builds and
evaluates datum reference frames in detail).

## Domain quick reference

- Feature control frame: the drawing symbol that carries the
  tolerance. It reads, in order: geometric characteristic symbol,
  tolerance value (diameter symbol when the zone is cylindrical),
  optional material condition modifier, then up to three datum
  references. Example: position | diameter 0.5 (M) | A | B (M) | C.
- Geometric characteristic categories: form tolerances (flatness,
  straightness, circularity, cylindricity) control shape alone and
  carry no datum; orientation tolerances (perpendicularity,
  parallelism, angularity) control orientation relative to a datum
  reference frame; position controls location relative to the true
  position; profile controls a boundary offset from the true profile;
  runout controls coaxiality relative to a datum axis.
- Tolerance zone types: flatness is two parallel planes; circularity
  is an annulus between two concentric circles; cylindricity is the
  annular space between two coaxial cylinders; position is a
  cylindrical zone, expressed as a diameter, about the true position;
  perpendicularity, parallelism, and angularity are planes or
  cylinders oriented to the datum frame.
- Datum reference frame: the ordered set of datum features (primary,
  secondary, tertiary) that locates and orients the tolerance zones.
  The frame is read left to right in the feature control frame.
- Material condition modifiers, applied to the tolerance in the frame:
  M means maximum material condition (MMC), the most material the
  feature can have (smallest hole, largest pin); L means least
  material condition (LMC), the least material (largest hole,
  smallest pin); S, or no modifier at all, means regardless of feature
  size (RFS).
- Bonus tolerance at MMC: the stated tolerance applies at the MMC
  size; any departure of the actual feature size from the MMC size
  adds bonus. For a hole (MMC = smallest size) the bonus is
  actual - mmc; for a pin (MMC = largest size) the bonus is
  mmc - actual. Total tolerance = stated tolerance + bonus.
- LMC bonus works in the opposite direction: for a hole the bonus is
  lmc - actual, for a pin it is actual - lmc.
- Zero tolerance at MMC is legitimate: a position callout of
  diameter 0 (M) means the feature must sit exactly at true position
  when at MMC, and every unit of departure from MMC becomes the
  available tolerance.

## Workflow

1. Read the feature control frame off the drawing and parse it with
   parse_feature_control_frame; the result carries the symbol, the
   tolerance value, the diameter flag, the modifier, and the datum
   list.
2. Identify the tolerance category with tolerance_category (form,
   orientation, location, profile, or runout) and the zone shape with
   tolerance_zone_type.
3. Read the material condition modifier with
   material_condition_modifier and explain it with
   modifier_meaning (MMC, LMC, or RFS default).
4. From the size limits and the part type, derive the boundary sizes
   with mmc_size and lmc_size.
5. When the modifier is M, compute the bonus tolerance with
   bonus_tolerance_at_mmc from the actual feature size, and the total
   budget with total_tolerance_at_mmc.
6. For an LMC callout, use bonus_tolerance_at_lmc instead.
7. Assemble the full interpretation with
   interpret_feature_control_frame, which includes the bonus and total
   tolerance whenever the modifier is M and the sizes are supplied.
8. Confirm the deterministic checks with the contract test
   scripts/test_gdandt_basics.py.

## Worked example

Interpret the feature control frame "position | diameter 0.5 (M) | A |
B | C" for a hole with size limits 10.0 to 10.3 mm:

- parse_feature_control_frame returns symbol "position", tolerance
  0.5, diameter True, modifier "M", and datums A, B, C in order.
- tolerance_category is "location"; tolerance_zone_type is the
  cylindrical zone of diameter 0.5 about the true position.
- modifier_meaning("M") is "maximum material condition (MMC): the
  stated tolerance applies at the MMC size and grows with departure
  from MMC".
- mmc_size((10.0, 10.3), "hole") is 10.0; the bonus is zero when the
  hole measures 10.0 and grows as the hole grows.
- If the actual hole measures 10.3, bonus_tolerance_at_mmc gives
  10.3 - 10.0 = 0.3 and total_tolerance_at_mmc gives
  0.5 + 0.3 = 0.8; the acceptance zone diameter is 0.8 at that size.
- A hole measuring 9.9 is below MMC, violates the size limits, and
  the logic raises ValueError rather than returning a negative bonus.

A second example: "flatness | 0.2" is a form tolerance, so
tolerance_category returns "form", the zone is two parallel planes
0.2 apart, and parse_feature_control_frame raises if a datum is added,
because form tolerances reference no datum.

## Related leaves

- cross-cutting/tolerancing/position-tolerance-calc: full position
  verification, deviation from true position, virtual condition, and
  the acceptance verdict.
- cross-cutting/tolerancing/tolerance-stackup: summing tolerance
  contributions across an assembly.
- cross-cutting/tolerancing/datum-reference-frames: datum reference
  frame construction and evaluation in detail.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gdandt_basics.py

The test covers feature control frame parsing (symbol, tolerance,
diameter flag, modifier, datums), category and zone classification,
modifier meanings, MMC and LMC bonus tolerance including size-limit
violations, boundary sizes, total tolerance at MMC, zero tolerance at
MMC, the full frame interpreter, and invalid-input edge cases.

## Compliance

- Standards referenced, not reproduced: ASME Y14.5 is proprietary
  (ASME); the feature control frame structure, the tolerance
  categories, the MMC/LMC/RFS modifiers, and the bonus tolerance rule
  are common GD&T methodology, name and paraphrase only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false (reference-only listing).
