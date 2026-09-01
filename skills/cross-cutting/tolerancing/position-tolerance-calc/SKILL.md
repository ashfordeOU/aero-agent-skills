---
name: position-tolerance-calc
description: "Use when you must compute the position tolerance verification for a hole or pin feature controlled by a true position callout per ASME Y14.5: calculate the radial deviation of the actual feature center from the true position, convert the deviation into the cylindrical zone diameter that contains the actual center, apply the maximum material condition bonus tolerance from the actual feature size, derive the virtual condition boundary for the mating part, and decide whether the feature is acceptable. Produces the deviation, the required zone diameter, the bonus tolerance, the total tolerance, the virtual condition, and the acceptance verdict that gate the GD&T verification. Trigger: position tolerance, true position, MMC, bonus tolerance, virtual condition, feature control frame."
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
  tags: [position-tolerance-calc, position-tolerance, true-position, mmc-bonus, virtual-condition, feature-control-frame, maximum-material-condition]
  version: 0.1.0
  author: AeroSkills
---
# Position Tolerance Calculation (cross-cutting/tolerancing/position-tolerance-calc)

Use when the task is the GD&T position tolerance check for a hole or
pin feature: radial deviation from the true position, required zone
diameter, MMC bonus tolerance, virtual condition boundary, and the
acceptance verdict.

## Domain quick reference

- A position tolerance callout defines a cylindrical zone, expressed
  as a diameter, around the true position of the feature; the actual
  feature center must lie inside the zone.
- Radial deviation of the actual center from the true position:
  d = sqrt((x_a - x_t)^2 + (y_a - y_t)^2), any consistent length
  unit (mm, inch).
- Required zone diameter: D_zone = 2 * d, the smallest cylinder
  centered on the true position that contains the actual center.
- MMC bonus tolerance for a hole: the MMC size is the smallest hole
  (most material); bonus = actual_size - mmc_size, zero at MMC and
  growing as the hole grows.
- Total tolerance: T_total = stated_tolerance + bonus.
- Virtual condition, the fixed worst-case boundary for the mating
  part: hole VC = mmc_size - stated_tolerance; pin VC = mmc_size +
  stated_tolerance. The stated tolerance only, never the bonus.
- Acceptance verdict: 2 * d <= stated_tolerance + bonus. The maximum
  allowed center offset is (stated_tolerance + bonus) / 2.

## Workflow

1. Collect the true position coordinates, the measured actual center,
   the stated tolerance diameter, the actual feature size, the MMC
   size, and the part type (hole or pin).
2. Compute the deviation with positional_deviation.
3. Compute the required zone diameter with position_zone_diameter.
4. Apply the MMC modifier with mmc_bonus (zero when the actual size
   equals MMC).
5. Sum the stated tolerance and the bonus with
   total_position_tolerance.
6. Derive the mating boundary with virtual_condition.
7. Decide with position_verdict and report the allowed offset with
   max_center_offset before gating the verification.

## Pitfalls

- Forgetting that the position tolerance is a diameter: the deviation
  is a radius, so compare 2 * d, not d, against the stated tolerance.
- Applying the bonus to the wrong feature: the hole gains bonus as it
  grows (material removed), while a pin gains bonus as it shrinks;
  the size direction differs by part type.
- Using an actual size below MMC: a hole smaller than its MMC size
  violates the size limits, the bonus would be negative, and the
  logic raises ValueError.
- Confusing the virtual condition with the bonus boundary: the VC
  uses the stated tolerance only, so it is a fixed boundary for the
  mating part, not the growing acceptance zone.
- Checking only one boundary: the tolerance zone and the virtual
  condition are separate limits and both must be satisfied.

## Behavior contract (gate 3)

The deviation, zone diameter, bonus, total tolerance, virtual
condition, and verdict logic is exercised by the gate 3 contract test:
scripts/test_position_tolerance_calc.py against
scripts/position_tolerance_calc_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_position_tolerance_calc.py

## Compliance

- Standards referenced, not reproduced: ASME Y14.5 is proprietary
  (ASME); the position tolerance method, the MMC bonus rule, and the
  virtual condition formulas are common GD&T methodology, name and
  paraphrase only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false (reference-only listing).
