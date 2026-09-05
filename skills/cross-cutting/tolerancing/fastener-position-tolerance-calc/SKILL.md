---
name: fastener-position-tolerance-calc
description: "Use when you must size positional tolerances or clearance holes for mating fastener patterns: compute the total positional tolerance budget as the clearance hole MMC diameter minus the fastener maximum diameter, split the budget between the two mating members with the floating fastener formula, apply the fixed fastener formula when the threaded member share acts through a projected tolerance zone, and invert the formula to find the minimum clearance hole MMC diameter for a given fastener and tolerance split. Produces the tolerance split, the minimum hole diameter and the projected zone height that gate the hole pattern callout. Trigger: fastener position tolerance, fixed fastener, floating fastener, clearance hole MMC, projected tolerance zone, mating hole pattern, hole pattern callout, maximum material condition."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: asme-y14-5
    reference-only: true
gated: false
domain: cross-cutting
pack: tolerancing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: tolerancing
  tags: [fastener-position-tolerance-calc, fixed-fastener-formula, floating-fastener-formula, projected-tolerance-zone, mating-hole-clearance]
  version: 0.1.0
  author: AeroSkills
---

# Fastener Position Tolerance Calculation (cross-cutting/tolerancing/fastener-position-tolerance-calc)

Use when the task is the design-side sizing of positional tolerances and
clearance holes for bolted and screwed joints with the ASME Y14.5 fixed
and floating fastener formulas: total positional tolerance budget from
the clearance hole MMC diameter and the fastener maximum diameter, the
budget split between two mating members, the projected tolerance zone
variant for the threaded or stud side, and the inverse sizing of the
minimum clearance hole MMC diameter. The leaf implements the Y14.5
fastener design method in pure Python, stdlib only. It pairs with
cross-cutting/tolerancing/position-tolerance-calc for the verification
side (checking a drawn callout from measured coordinates) and
cross-cutting/tolerancing/gdandt-basics for frame interpretation context.

## Domain quick reference

- Total positional tolerance budget: T_total = H - F, where H is the
  clearance hole MMC diameter and F is the fastener maximum diameter at
  MMC. The hole is smallest and the fastener is largest at MMC, so the
  difference is the worst-case clearance available to absorb both member
  tolerances.
- Floating fastener case: both members carry clearance holes, so each
  member takes a share of the budget as its own positional tolerance,
  H = F + T1 + T2, with T1 the clearance member tolerance and T2 the
  other member tolerance. The total budget is independent of the split.
- Fixed fastener case: one member is threaded or carries a stud, so the
  same budget H - F applies and the other member share acts through a
  projected tolerance zone whose height defaults to the full mating part
  thickness (projected_zone_height), keeping the engaged threads inside
  the zone.
- Minimum clearance hole MMC: invert the formula, H_min = F + T1 + T2,
  to size the hole for a given fastener and member tolerance split.
- Equal split is the default: split_tolerance divides the total with T1 =
  total * first_share and T2 = total - T1, so the pair sums back to the
  total; any first_share strictly between 0 and 1 is allowed.
- All diameters and tolerances are millimeters, reported at 0.01 mm.
- ASME Y14.5 is referenced, not reproduced; the relations above are the
  standard engineering method, summary only.

## Workflow

1. Record the joint inputs: the case (floating fastener for two clearance
   members, fixed fastener for a clearance member against a threaded or
   stud member), the fastener maximum diameter F at MMC, and the
   clearance hole MMC diameter H where one is already set.
2. Budget traverse: compute the total positional tolerance budget with
   floating_fastener_total_tolerance (floating case) or
   fixed_fastener_total_tolerance (fixed case): the clearance H minus F
   available to the two member tolerances.
3. Split traverse: divide the total budget between the two mating members
   with split_tolerance, default equal shares (0.20 and 0.20 in the
   worked example) or any first_share between 0 and 1 for an unequal
   allocation.
4. Projected zone traverse: in the fixed case, assign the threaded member
   share to a projected tolerance zone with projected_zone_height, whose
   default height is the full mating part thickness; the multiplier
   variant gives a shorter zone where the drawing calls one out.
5. Minimum hole traverse: when the hole must be sized instead of checked,
   invert the formula with minimum_clearance_hole_mmc: F plus the two
   member tolerances gives the minimum clearance hole MMC diameter.
6. Report bookkeeping: assemble the sizing record with fastener_report:
   case, total tolerance, clearance member tolerance, other member
   tolerance, hole diameter, minimum hole when solving, and the projected
   zone height for the fixed case.
7. Confirm the callout values with the deterministic contract test
   scripts/test_fastener_position_tolerance_calc.py.

## Worked example

Fastener F = 6.35 mm with a clearance hole MMC H = 6.75 mm.

- Floating case, total positional tolerance budget:
  floating_fastener_total_tolerance(6.75, 6.35) = 0.40 mm.
- Equal split: split_tolerance(0.40) = (0.20, 0.20), and the pair sums
  back to 0.40 mm; an unequal split such as split_tolerance(0.40, 0.75)
  = (0.30, 0.10) keeps the same 0.40 mm total.
- Fixed case, same F and H: fixed_fastener_total_tolerance(6.75, 6.35) =
  0.40 mm, the same budget as the floating case; with the hole tolerance
  0.25 mm and the stud side tolerance 0.15 mm, the minimum hole is
  minimum_clearance_hole_mmc(6.35, 0.25, 0.15) = 6.75 mm.
- Projected zone: projected_zone_height(12.0) = 12.0 mm for the full
  12 mm mating part thickness, and projected_zone_height(12.0, 0.75) =
  9.0 mm for a 0.75 multiplier zone.
- Full record for the fixed joint on a 12 mm stack:
  fastener_report("fixed", fastener_max=6.35, tol_clearance_member=0.25,
  tol_other_member=0.15, mating_thickness=12.0) returns the case, total
  tolerance 0.40 mm, clearance member tolerance 0.25 mm, other member
  tolerance 0.15 mm, hole MMC 6.75 mm, minimum hole 6.75 mm and
  projected zone height 12.0 mm.

## Verification

- Confirm floating_fastener_total_tolerance(6.75, 6.35) returns 0.40 mm
  and fixed_fastener_total_tolerance(6.75, 6.35) returns the same budget.
- Confirm split_tolerance(0.40) returns (0.20, 0.20) and that the pair
  sums back to the total within 0.01 mm.
- Confirm the split independence identity: split_tolerance(0.40, 0.75)
  and split_tolerance(0.40, 0.25) give (0.30, 0.10) and (0.10, 0.30),
  both summing to the same 0.40 mm total.
- Confirm minimum_clearance_hole_mmc inverts the budget:
  minimum_clearance_hole_mmc(6.35, 0.20, 0.20) = 6.75 mm, and feeding
  that hole back to floating_fastener_total_tolerance recovers 0.40 mm;
  a larger fastener at a fixed hole leaves a smaller budget.
- Confirm projected_zone_height(12.0) = 12.0 mm and the multiplier
  variant projected_zone_height(12.0, 0.75) = 9.0 mm.
- Confirm the fastener_report key contract: base keys in every record,
  minimum_hole_mmc only when solving, projected_zone_height only for the
  fixed case with a mating thickness, matching the documented key sets.
- Confirm every non-physical input raises ValueError: hole MMC not larger
  than the fastener maximum, zero or negative fastener, zero or negative
  total tolerance, first share 0 or 1, negative member tolerance, and
  zero mating thickness.
- Run the contract test offline: python3
  scripts/test_fastener_position_tolerance_calc.py.

## Related leaves

- cross-cutting/tolerancing/position-tolerance-calc: the verification
  side, checking a drawn positional callout from measured coordinates
  instead of sizing the hole pattern.
- cross-cutting/tolerancing/gdandt-basics: frame interpretation and
  modifier context for the callouts this leaf sizes.
- cross-cutting/tolerancing/tolerance-stackup: assembly-level fit
  assessment that consumes the sized hole and tolerance values.

## Pitfalls

- Sizing on nominal instead of MMC diameters: the budget H - F uses the
  clearance hole at MMC (smallest hole) and the fastener at MMC (largest
  fastener), the worst-case clearance, so nominal-minus-nominal
  understates the required hole or overstates the budget.
- Splitting the budget without the sum property: report T2 = total - T1
  at two decimals so the pair always sums back to the total instead of
  rounding each share independently and losing 0.01 mm.
- Dropping the projected zone in the fixed case: the threaded or stud
  member share must act through a projected tolerance zone whose height
  is the full mating part thickness by default, or the engaged thread
  length is not controlled.
- Sizing the hole from one member tolerance alone: H_min = F + T1 + T2
  needs both shares, so a joint that only assigns the clearance member
  tolerance leaves the other member uncontrolled.
- Using this leaf to verify a drawn callout from measured coordinates:
  that is the position-tolerance-calc role; this leaf sizes the callout
  before the drawing exists.
- Feeding a hole equal to the fastener maximum diameter: H must exceed F
  for any clearance, and the module raises ValueError rather than
  returning a zero budget.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fastener_position_tolerance_calc.py

The test covers the worked-example sizing contract (total budget 0.40 mm
within bounds, equal split 0.20 and 0.20, fixed budget equal to the
floating budget at the same diameters, minimum hole 6.75 mm, projected
zone 12.0 mm), the split independence identity, the inverse round trip
between minimum_clearance_hole_mmc and floating_fastener_total_tolerance,
larger-fastener budget scaling, the documented fastener_report key sets,
determinism across repeated calls, and ValueError rejection of every
non-physical input listed in Verification.

## Compliance

- Standards referenced, not reproduced: ASME Y14.5 is proprietary; the
  fixed and floating fastener relations above are standard engineering
  methodology, name and paraphrase only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
