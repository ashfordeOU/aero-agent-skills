---
name: lpbf-parameter-development
description: "Develop the laser powder bed fusion (LPBF) parameter window: compute the volumetric energy density from laser power, scan speed, hatch spacing, and layer thickness, check hatch overlap between melt tracks, classify the process window as conduction mode, transition, or keyhole mode with porosity expectations, and build the parameter development matrix across power, speed, and hatch grids plus the qualification test matrix of coupon builds, density, and mechanical testing per the additive manufacturing qualification framework. Use when developing LPBF process parameters, mapping energy density to melt pool regime, screening keyhole mode risk, or sizing the parameter development matrix for a powder bed fusion build. Trigger: LPBF, laser powder bed fusion, volumetric energy density, process window, keyhole mode, conduction mode, melt pool, parameter development matrix."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: additive
  tags: [lpbf, laser-powder-bed-fusion, volumetric-energy-density, scan-speed, hatch-spacing, layer-thickness, melt-pool, keyhole-mode, conduction-mode, process-window, laser, power, scan, speed, hatch, spacing, layer, volumetric, energy, density, powder, bed, fusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# LPBF Parameter Development (manufacturing-quality/additive/lpbf-parameter-development)

Use when developing the laser powder bed fusion (LPBF) process
parameter window for a metal powder build: computing the volumetric
energy density from the four build parameters, checking hatch overlap,
classifying the process window as conduction mode, transition, or
keyhole mode, and building the parameter development matrix plus the
qualification test matrix.

## Domain quick reference

- LPBF parameter set: laser power (W), scan speed (mm/s), hatch
  spacing (mm), and layer thickness (mm). These four values pin the
  energy input to the melt pool of a powder bed fusion build.
- Volumetric energy density: VED = laser power / (scan speed x hatch
  spacing x layer thickness), in J/mm^3. High VED means a hot, deep
  melt pool; low VED means a shallow, cool pool.
- Melt pool regimes: conduction mode (shallow, wide, stable pool),
  transition (mixed, intermittent keyholing), and keyhole mode (deep,
  narrow pool with a vapor depression). Keyhole mode carries porosity
  risk from trapped vapor and keyhole collapse.
- Hatch overlap: overlap = (melt pool width - hatch spacing) / melt
  pool width. Positive overlap means adjacent melt tracks merge;
  negative overlap means un-melted gaps between tracks, which flags
  incomplete fusion risk.
- Melt pool penetration: melt pool depth / layer thickness. A ratio
  well above 1 is the deep penetration signature of keyhole mode.
- Qualification test matrix: each candidate parameter set is proven by
  coupon builds: density coupons (Archimedes density), tensile,
  fatigue, and hardness coupons, per the additive manufacturing
  qualification framework.
- AS9100 link: parameter development feeds the additive manufacturing
  qualification program under production control and quality
  management; AS9100 is referenced, not reproduced.

## Workflow

1. Compute the volumetric energy density from the four build
   parameters: volumetric_energy_density(laser_power, scan_speed,
   hatch_spacing, layer_thickness) returns VED in J/mm^3.
2. Check hatch overlap between melt tracks:
   hatch_overlap_fraction(melt_pool_width, hatch_spacing) returns the
   overlap fraction, negative when the hatch spacing leaves gaps.
3. Check melt pool penetration: melt_pool_penetration(melt_pool_depth,
   layer_thickness) returns the depth to layer ratio, a keyhole
   signature when well above 1.
4. Classify the process window: classify_process_window(ved) maps the
   energy density to conduction, transition, or keyhole mode with the
   porosity expectation. The window bounds (conduction_ved, keyhole_ved)
   are material dependent and may be passed explicitly; the defaults
   are 60 and 100 J/mm^3.
5. Build the parameter development matrix:
   build_parameter_matrix(power_values, speed_values, hatch_values,
   layer_thickness) builds every power x speed x hatch combination at
   the fixed layer thickness, with the VED and regime per row, sorted
   deterministically by power, scan speed, then hatch spacing.
6. Apply the process window to the matrix:
   process_window_verdict(matrix) counts conduction, transition, and
   keyhole rows, flags any keyhole exposure, and returns a one-line
   verdict for the screen.
7. Derive the qualification test matrix:
   build_qualification_test_matrix(parameter_sets) assigns density,
   tensile, fatigue, and hardness coupons to each candidate parameter
   set per the additive manufacturing qualification framework.
8. Validate inputs first: non-numeric or non-positive parameters, empty
   grids, unknown regimes, and malformed parameter sets raise
   ValueError instead of returning a silent result.

## Worked example

A powder bed fusion parameter screen on a 0.03 mm layer thickness:

- Power grid: 200 W and 350 W. Speed grid: 800 and 1200 mm/s. Hatch
  grid: 0.08 and 0.12 mm.
- build_parameter_matrix([200, 350], [800, 1200], [0.08, 0.12], 0.03)
  returns 2 x 2 x 2 = 8 rows. The corner points:

  - 200 W, 800 mm/s, 0.08 mm: VED = 200 / (800 x 0.08 x 0.03) =
    104.2 J/mm^3, keyhole mode.
  - 200 W, 1200 mm/s, 0.12 mm: VED = 200 / (1200 x 0.12 x 0.03) =
    46.3 J/mm^3, conduction mode.
  - 350 W, 800 mm/s, 0.08 mm: VED = 350 / (800 x 0.08 x 0.03) =
    182.3 J/mm^3, keyhole mode, highest porosity risk.

- Hatch overlap check: a 0.12 mm melt pool at 0.10 mm hatch gives
  (0.12 - 0.10) / 0.12 = 0.167, a 17% track overlap. At 0.15 mm hatch
  the same pool gives -0.25, un-melted gaps between tracks.
- Melt pool penetration: a 0.12 mm deep pool over a 0.03 mm layer
  gives a ratio of 4.0, deep penetration consistent with keyhole mode.
- process_window_verdict() over the 8 rows reports the keyhole count;
  the 350 W, 800 mm/s corners are screened out and the 200 W, 1200
  mm/s corners move to coupon builds.
- build_qualification_test_matrix() then assigns the density, tensile,
  fatigue, and hardness coupon builds to the surviving parameter sets.

## Pitfalls

- Confusion with additive-manufacturing-qualification: the
  qualification leaf owns the qualification record, witness coupon
  sample planning, material property verification, and first article
  checks. This leaf owns the parameter window development itself: VED,
  hatch overlap, melt pool regime, and the parameter development
  matrix. Develop the window here, then feed the survivors into the
  qualification program.
- Unit mixing: VED in J/mm^3 needs W, mm/s, mm, mm. Converting the
  scan speed to m/s or the hatch spacing to cm changes the result by
  orders of magnitude.
- Treating the window bounds as material independent: the conduction
  and keyhole thresholds are alloy specific. Use per-alloy bounds
  instead of the defaults for production screening.
- Hatch overlap as a single number: overlap needs the melt pool width,
  which itself changes with power and speed. Re-check overlap per
  matrix row, not once for the whole build.
- Keyhole mode at the corners: high power with low scan speed and
  tight hatch spacing is exactly where keyhole porosity appears; the
  verdict count exists to catch corner combinations, not just the
  center of the grid.
- Qualification test matrix vs production part: coupon builds prove
  the parameter set; they do not replace the production first article
  checks owned by the qualification framework.

## Behavior contract (gate 3)

The parameter development logic is exercised by the gate 3 contract
test: scripts/test_lpbf_parameter_development.py against
scripts/lpbf_parameter_development_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_lpbf_parameter_development.py

## Compliance

- Standards referenced, not reproduced: AS9100 frames additive
  manufacturing parameter development within production control and
  quality management; summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
