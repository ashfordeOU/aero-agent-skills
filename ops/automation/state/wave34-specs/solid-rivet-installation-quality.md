# Wave-34 leaf spec: solid-rivet-installation-quality (manufacturing-quality, assembly pack)

- Path: skills/manufacturing-quality/assembly/solid-rivet-installation-quality/
- Pack: assembly. Closest sibling: fastener-installation-quality
  (threaded and lock-bolt fasteners by torque, clamp load, grip, thread
  protrusion, swage collar: F = T/(k D) mechanics). This leaf owns
  DEFORMATION-driven permanent fasteners: rivet length selection by
  head-style allowance, driven shop-head geometry bands, squeeze force
  to upset, and hole-fill clearance. No function overlap.
- Standards id: as9100 (reference-only; sibling convention). Ledger
  Standard: as9100.
- Family: manufacturing-quality

## Claim

Verify solid rivet installation quality: select the rivet length from
the stack thickness and a head-style allowance (typical protruding
1.5 d, countersunk 0.8 d), judge the driven shop-head geometry against
typical workmanship bands (driven diameter 1.4-1.5 d, driven height
0.4-0.5 d), compute the squeeze force required to upset the rivet, and
check the hole-fill clearance against the limit. Produces the selected
rivet length, the shop-head geometry verdict, the squeeze force and
the hole-fill verdict, the deformation-fastener complement to the
torque-based fastener leaf.

Does NOT do: threaded fasteners, torque-tension, clamp load, swage
collars (fastener-installation-quality owns threaded/lock-bolt
mechanics); hole drilling process control; rivet fatigue allowables.

## Model (implement exactly)

Module constants (leaf-local typical factors, same epistemic class as
the sibling's k = 0.2 torque coefficient; state them as workmanship
practice, not standard data):
- PROTRUDING_ALLOWANCE_D = 1.5; COUNTERSUNK_ALLOWANCE_D = 0.8.
- SHOP_D_MIN_D = 1.4; SHOP_D_MAX_D = 1.5 (driven head diameter band).
- SHOP_H_MIN_D = 0.4; SHOP_H_MAX_D = 0.5 (driven head height band).
- SQUEEZE_FACTOR_DEFAULT = 1.5.
- MAX_HOLE_CLEARANCE_MM = 0.1.

Conventions: dimensions in mm, force in N, flow stress in MPa
(N/mm2). Head style is a string "protruding" or "countersunk".

Functions (pure stdlib):
- select_rivet_length(stack_mm, diameter_mm, head_style) -> dict
  {allowance_mm, length_mm} = stack + allowance * diameter.
  ValueErrors: stack <= 0, diameter <= 0, head_style not in
  {"protruding", "countersunk"}.
- shop_head_verdict(driven_diameter_mm, driven_height_mm,
  rivet_diameter_mm) -> dict {d_over_d, h_over_d, ok} with ok True
  when d_over_d in [1.4, 1.5] AND h_over_d in [0.4, 0.5]. ValueErrors:
  any dimension <= 0.
- squeeze_force(diameter_mm, flow_stress_mpa, factor =
  SQUEEZE_FACTOR_DEFAULT) -> dict {area_mm2, force_n} = factor *
  flow_stress * (pi d^2 / 4) (force to upset against the flow
  stress over the shank area with an allowance factor).
  ValueErrors: diameter <= 0, flow_stress <= 0, factor <= 0.
- hole_fill_check(hole_diameter_mm, rivet_diameter_mm,
  max_clearance_mm = MAX_HOLE_CLEARANCE_MM) -> dict
  {clearance_mm, ok} = hole - rivet <= max. ValueErrors: hole <= 0,
  rivet <= 0, rivet > hole (interference is out of scope: ValueError),
  max_clearance < 0.
- installation_verdict(stack_mm, rivet_diameter_mm, head_style,
  driven_diameter_mm, driven_height_mm, squeeze_force_n,
  flow_stress_mpa, hole_diameter_mm, factor = SQUEEZE_FACTOR_DEFAULT,
  max_clearance_mm = MAX_HOLE_CLEARANCE_MM) -> dict combining
  selected length, shop-head verdict, squeeze force and hole-fill
  verdict plus overall ok (all sub-checks ok).

Geometry identity to test: the driven head band is symmetric around
1.45 d and 0.45 d; a rivet driven to exactly 1.45 d and 0.45 d passes
with zero margin on both ratios at the band edges.

## Worked example

Reference: 4.0 mm protruding rivet over a 6.0 mm stack; driven head
5.8 mm diameter x 1.8 mm height (good) then 5.0 x 1.2 mm
(under-driven); flow stress 275 MPa; hole 4.08 mm.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- select_rivet_length(6.0, 4.0, "protruding"): allowance 6.0 mm,
  length 12.0 mm.
- select_rivet_length(6.0, 4.0, "countersunk"): allowance 3.2 mm,
  length 9.2 mm.
- shop_head_verdict(5.8, 1.8, 4.0): d_over_d 1.45, h_over_d 0.45,
  ok True.
- shop_head_verdict(5.0, 1.2, 4.0): d_over_d 1.25, h_over_d 0.30,
  ok False (under-driven).
- squeeze_force(4.0, 275): area = 12.566 mm2; force = 1.5 * 275 *
  12.566 = 5183.6 N.
- hole_fill_check(4.08, 4.0): clearance 0.08 mm <= 0.1, ok True.
- A hole of 4.15 mm gives clearance 0.15 mm, ok False.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: stack <= 0; diameter <= 0; bad head_style; non-positive
  driven dimensions; flow_stress <= 0; factor <= 0; hole <= 0;
  rivet > hole (interference); max_clearance < 0.
- Length selection: protruding 6.0 stack 4.0 d -> 12.0 mm;
  countersunk -> 9.2 mm; doubling stack adds exactly the stack
  increment.
- Shop head: (1.45, 0.45) ratios pass; (1.25, 0.30) fail;
  (1.6, 0.45) fail (diameter too large); (1.45, 0.55) fail (height
  too large).
- Squeeze force: 5183.6 N for the worked case to 0.1 N; force scales
  with d^2 and linearly with flow stress and factor.
- Hole fill: 0.08 mm clearance passes; 0.15 mm fails; exact 0.1 mm
  boundary passes (<=).
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-solid-rivet-installation-quality.yaml)

Query 1 (copy verbatim):
  "select the solid rivet length from the stack thickness and head style allowance and judge the driven shop head diameter and height against the workmanship bands"
  intent: "manufacturing-quality; solid rivet length selection and driven shop head geometry verdict"
  expected_skill: "manufacturing-quality/assembly/solid-rivet-installation-quality"
Query 2 (copy verbatim):
  "compute the squeeze force required to upset a solid rivet and check the hole fill clearance against the installation limit"
  intent: "manufacturing-quality; rivet squeeze force and hole fill clearance check"
  expected_skill: "manufacturing-quality/assembly/solid-rivet-installation-quality"
Task ids: w34-solid-rivet-installation-quality-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must verify the installation
quality of solid rivets:" and include the outputs in the Claim. First
tag: solid-rivet-installation-quality. Additional tags ONLY:
solid-rivet-installation, driven-head-formation, shop-head-dimension-
check, rivet-squeeze-force, hole-fill-verification. NEVER single
generic words (rivet, installation, head, squeeze, hole, fastener,
quality). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): torque, clamp load, grip,
thread, lock-bolt, swage collar, nut (fastener-installation-quality
owns threaded fastener mechanics); EWIS, wiring (ewis-installation-
quality). The words "solid rivet", "shop head", "driven head",
"squeeze force", "hole fill" are this leaf's own.

Tags: [solid-rivet-installation-quality, solid-rivet-installation,
driven-head-formation, shop-head-dimension-check, rivet-squeeze-force,
hole-fill-verification]

Sibling-citation lines for Related leaves:
manufacturing-quality/assembly/fastener-installation-quality (the
threaded/lock-bolt sibling; boundary: torque mechanics vs deformation
fasteners),
manufacturing-quality/assembly/ewis-installation-quality (wiring
sibling).

Ledger Standard: as9100.
