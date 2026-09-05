# Wave-39 leaf spec: fastener-position-tolerance-calc (cross-cutting, tolerancing pack)

- Path: skills/cross-cutting/tolerancing/fastener-position-tolerance-calc/
- Pack: tolerancing. Closest siblings: position-tolerance-calc (verifies a
  DRAWN callout from measured coordinates: positional_deviation,
  position_zone_diameter, mmc_bonus, total_position_tolerance,
  virtual_condition, max_center_offset, position_verdict - the verification
  side; no design-side sizing of clearance holes and fastener patterns),
  gdandt-basics (interprets feature control frames and modifiers), gage-
  rr-anova (not GD&T), tolerance-stackup. Whole-tree greps at prep:
  "fixed fastener", "floating fastener", "fastener fit", "projected
  tolerance zone" = 0 hits in skills/. GENUINE CC gap (fresh probe): the
  ASME Y14.5 fixed and floating fastener design formulas are the missing
  deterministic GD&T function.
- Standards id: asme-y14-5 (reference-only). Ledger Standard: asme-y14-5.
- Family: cross-cutting

## Claim

Size positional tolerances and clearance holes for bolted and screwed
joints with the ASME Y14.5 fastener formulas: compute the total positional
tolerance budget as the difference between the clearance-hole MMC diameter
and the fastener maximum diameter, split the budget between two mating
members in the floating fastener case (each member carries a positional
tolerance), apply the fixed fastener case where the threaded member's
tolerance acts through a projected tolerance zone, and invert the formula
to find the minimum clearance-hole MMC diameter for a given fastener and
tolerance split. Produces the tolerance split, the minimum hole diameter
and the projected-zone variant that gate mating-hole pattern design. Does
NOT do: verification of an existing positional callout from measured
coordinates (position-tolerance-calc); feature control frame interpretation
(gdandt-basics); tolerance stackup (tolerance-stackup).

## Model (implement exactly)

Conventions: fastener maximum diameter F (at MMC), clearance hole MMC
diameter H, positional tolerance split T1 (clearance member) and T2
(other member). All diameters in millimeters.

Functions (pure stdlib):
- floating_fastener_total_tolerance(hole_mmc, fastener_max) -> float
  H - F; ValueError if hole_mmc <= fastener_max (no clearance) or
  fastener_max <= 0.
- split_tolerance(total_tolerance, first_share=0.5) -> tuple
  (round(T1, 2), round(T2, 2)) with T1 + T2 = total (within 0.01) and T2 =
  total - T1; ValueError if total_tolerance <= 0 or first_share outside
  (0, 1).
- fixed_fastener_total_tolerance(hole_mmc, fastener_max) -> float H - F
  (the same budget; the threaded member's share is applied through a
  projected tolerance zone whose height equals the mating part thickness,
  documented); ValueErrors as above.
- minimum_clearance_hole_mmc(fastener_max, tol_clearance_member,
  tol_other_member) -> float F + T1 + T2; ValueError if fastener_max <= 0
  or either tolerance < 0.
- projected_zone_height(mating_thickness, multiplier=1.0) -> float
  mating_thickness * multiplier, the documented default projected zone
  height (full mating thickness); ValueError if mating_thickness <= 0.
- fastener_report(...) -> dict with keys case ("floating" or "fixed"),
  total_tolerance, tol_clearance_member, tol_other_member, hole_mmc,
  minimum_hole_mmc (when solving), projected_zone_height (fixed case).

Identity to test: minimum_clearance_hole_mmc inverts
floating_fastener_total_tolerance: for F = 6.35 with a split of 0.20 and
0.20 the minimum hole is 6.75; the total budget is independent of the
split; a larger fastener at fixed hole leaves a smaller budget.

## Worked example

Floating fastener: fastener F = 6.35 mm, clearance hole MMC H = 6.75 mm:
- total tolerance = 0.40 mm; equal split (0.20, 0.20) at two decimals.
Fixed fastener: same F and H with the stud-side tolerance projected over
the full mating thickness:
- total budget 0.40 mm; hole tolerance 0.25, stud (projected) tolerance
  0.15.
- minimum_clearance_hole_mmc(6.35, 0.25, 0.15) = 6.75 mm.
- projected_zone_height(12.0) = 12.0 mm.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (direct arithmetic on the Y14.5 formula).

## Validation list (contract test must include)

- floating_fastener_total_tolerance(6.75, 6.35) = 0.40.
- split_tolerance(0.40) = (0.20, 0.20) with the sum back to 0.40.
- minimum_clearance_hole_mmc(6.35, 0.25, 0.15) = 6.75.
- fixed case total equals the floating total at the same F and H.
- projected_zone_height default and multiplier variants.
- Budget independence of the split (0.30/0.10 and 0.10/0.30 both sum to
  the total).
- ValueErrors: hole_mmc <= fastener_max, fastener_max 0, negative
  tolerance, first_share 0 or 1, mating thickness 0.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-fastener-position-tolerance-calc.yaml)

Query 1 (copy verbatim):
  "apply the fixed fastener formula to assign the positional tolerance between the two mating hole patterns at maximum material condition"
  intent: "cross-cutting; Y14.5 fixed fastener positional tolerance budget"
  expected_skill: "cross-cutting/tolerancing/fastener-position-tolerance-calc"
Query 2 (copy verbatim):
  "floating fastener minimum clearance hole diameter for the given fastener size and the positional tolerance split"
  intent: "cross-cutting; floating fastener clearance hole sizing"
  expected_skill: "cross-cutting/tolerancing/fastener-position-tolerance-calc"
Task ids: w39-fastener-position-tolerance-calc-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size positional tolerances or
clearance holes for mating fastener patterns:" and include the outputs in
the Claim. First tag: fastener-position-tolerance-calc. Additional tags
ONLY: fixed-fastener-formula, floating-fastener-formula, projected-
tolerance-zone, mating-hole-clearance. NEVER single generic words
(fastener, position, tolerance, hole, bolt, screw, clearance, zone).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): positional-deviation,
virtual-condition, mmc-bonus, bonus-tolerance, position-verdict
(position-tolerance-calc); feature-control-frame, datum (gdandt-basics);
worst-case-stackup, rss (tolerance-stackup).
