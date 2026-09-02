---
name: windtunnel-wall-corrections
description: "Use when you must apply closed-wall wind tunnel corrections to measured lift and drag coefficients: compute solid blockage from model volume over the test-section volume scale with K1 = 0.52, wake blockage from the uncorrected drag coefficient, total blockage, buoyancy drag increment from the streamwise pressure gradient, lift interference and streamline curvature alpha increment, sigma factor from span over section height, and first-order corrected lift and drag coefficients with corrected q and velocity. Produces corrected coefficients, alpha, q and V for free-air comparison. Trigger: wall corrections, solid blockage, wake blockage, wind tunnel boundary interference, lift interference, buoyancy drag, test section constraint, corrected drag coefficient."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: wind-tunnel
  tags: [windtunnel-wall-corrections, solid-blockage, wake-blockage, wall-interference, lift-interference, streamline-curvature, buoyancy-drag, test-section-constraint, corrected-drag-coefficient, closed-wall-tunnel]
  version: 0.1.0
  author: Aero Agent Skills
---

# Wind Tunnel Wall Corrections (aerodynamics/wind-tunnel/windtunnel-wall-corrections)

Use when the task is correcting measured aerodynamic coefficients for the
presence of the walls of a closed solid-wall (slotted or solid) test
section, the classical low-speed correction set of Barlow, Rae and Pope
(Low-Speed Wind Tunnel Testing, boundary corrections chapter, method set
paraphrased here): solid blockage, wake blockage, horizontal buoyancy
drag, and the lift interference and streamline curvature corrections.
The input is a set of coefficients already reduced from raw balance
readings at the measured dynamic pressure; the output is the
wall-corrected polar an operator would compare with free-air or CFD
data. Raw-run data reduction, tare subtraction, Reynolds and Mach
corrections and uncertainty estimation belong to
aerodynamics/wind-tunnel/windtunnel-data-reduction, not to this leaf.

## Domain quick reference

Closed rectangular test section of cross-sectional area C (m^2) and
height h, model of planform area S_model, volume V_model and span b.
All corrections below are first order in the small blockage factors.

- Solid blockage: eps_sb = K1 * V_model / C^1.5, with C^1.5 the cubic
  scale of the section (volume units) and K1 = 0.52 for a closed
  rectangular section (classical Barlow value, allow override with the
  tunnel-specific calibration).
- Wake blockage: eps_wb = (S_model / (4 * C)) * CDu, with CDu the
  uncorrected drag coefficient at the uncorrected dynamic pressure.
- Total blockage: eps = eps_sb + eps_wb.
- Dynamic pressure and speed: q_c = q_u * (1 + eps)^2 and
  V_c = V_u * (1 + eps). Blockage always raises q and V.
- Buoyancy drag: dCD_buoy = -(dP/dx) * V_model / (q * S_ref), with dP/dx
  the streamwise static pressure gradient of the empty section in Pa/m.
  Sign convention: in a closed solid-wall section the core flow
  accelerates downstream, dP/dx is negative and the increment is
  positive, drag added; a positive gradient subtracts drag. The
  buoyancy increment is added to the corrected drag coefficient.
- Lift interference: delta_alpha = delta * (S_model / C) * CLu in
  radians, delta = pi / 48 for the closed wall (classical value, allow
  override); corrected alpha = alpha_u + delta_alpha.
- Lift factor: sigma = (pi^2 / 48) * (b / h)^2 for the closed wall
  (classical value, allow override), valid while b < h.
- Corrected coefficients (first-order form, re-referencing is already
  inside the factors):
  CLc = CLu * (1 - sigma - 2 * eps_sb)
  CDc = CDu * (1 - 3 * eps_sb - 2 * eps_wb) + dCD_buoy
- K1, delta and the sigma coefficient are classical approximations for a
  closed rectangular section; replace them with the tunnel-specific
  calibration when one is available (see Compliance).

## Workflow

1. Gather the uncorrected measured coefficients CLu, CDu and alpha_u per
   point, the model planform area S_ref, model volume and span, and the
   test section area C, height h and uncorrected dynamic pressure q_u.
2. Optionally record the empty-section streamwise pressure gradient
   dP/dx for the buoyancy term.
3. Compute eps_sb with solid_blockage, eps_wb with wake_blockage and
   eps with total_blockage (module
   scripts/windtunnel_wall_corrections_logic.py).
4. Compute sigma with sigma_lift_factor and the angle increment with
   lift_interference_delta_alpha to get alpha_corrected.
5. Compute CLc with corrected_lift_coefficient and CDc with
   corrected_drag_coefficient, adding the buoyancy increment from
   buoyancy_drag_increment when dP/dx is available.
6. Correct the dynamic pressure and speed with
   corrected_dynamic_pressure and corrected_velocity.
7. For a single point call apply_wall_corrections once; for a whole
   polar call correct_measured_polar, which returns every corrected
   point with its correction ledger.
8. Sanity check the fit constraints: model volume below C^1.5, planform
   area below C, span below h; violations raise ValueError.

## Worked example

Model with S_model = 0.16 m^2, volume 0.004 m^3, CDu = 0.03, CLu = 0.5
at alpha_u = 4 deg, span 0.9 m, in a closed test section 1.4 m by 1.0 m
(C = 1.4 m^2, h = 1.0 m), q_u = 500 Pa.

- Solid blockage: eps_sb = 0.52 * 0.004 / 1.4^1.5 = 0.0012557.
- Wake blockage: eps_wb = (0.16 / (4 * 1.4)) * 0.03 = 0.0008571.
- Total blockage: eps = 0.0021128.
- Dynamic pressure: q_c = 500 * 1.0021128^2 = 502.12 Pa; velocity ratio
  V_c / V_u = 1.00211.
- Lift factor: sigma = (pi^2 / 48) * (0.9 / 1.0)^2 = 0.166550.
- Angle increment: delta_alpha = (pi / 48) * (0.16 / 1.4) * 0.5 rad =
  0.003740 rad = 0.2143 deg, so alpha_c = 4.2143 deg.
- Corrected lift: CLc = 0.5 * (1 - 0.166550 - 2 * 0.0012557) = 0.41547,
  below the uncorrected 0.5 as expected for positive blockage.
- Corrected drag: CDc = 0.03 * (1 - 3 * 0.0012557 - 2 * 0.0008571) =
  0.0298356, below the uncorrected 0.03.
- Buoyancy with dP/dx = -0.25 Pa/m: dCD_buoy = 0.25 * 0.004 / (500 *
  0.16) = 1.25e-5, so CDc = 0.0298356 + 0.0000125 = 0.0298481.

## Verification

- eps_sb, eps_wb and eps are non-negative for physical inputs, and every
  correction shrinks as the model-to-tunnel size ratio shrinks (smaller
  model volume, planform area or span).
- q_c and V_c exceed their uncorrected values for eps above zero, and
  collapse to the identity at eps = 0.
- Corrected CL stays below the uncorrected value at positive lift with
  positive blockage; corrected CD stays below CDu when no buoyancy
  gradient is applied, and the negative streamwise gradient of a closed
  section adds drag on top.
- The worked example above reproduces the reference values within 1%
  (asserted in the contract test).
- ValueError is raised on non-positive inputs and on any model larger
  than the test section: model volume at or above C^1.5, planform area
  at or above C, or span at or above the section height.

## Related leaves

- aerodynamics/wind-tunnel/windtunnel-data-reduction: reduces raw
  balance runs (tare, tare shift, Reynolds, Mach, uncertainty) into the
  uncorrected coefficients this leaf takes as input.
- aerodynamics/drag-polars/drag-polar: the parabolic polar model to
  compare the corrected points against.
- aerodynamics/drag-polars/lift-curve-slope: the predicted lift slope to
  check corrected CL against corrected alpha.
- aerodynamics/cfd/cfd-validation: validation culture; wall-corrected
  wind tunnel data is the experimental anchor for CFD validation, so
  this correction chain and its constants belong in the validation
  report next to the error metrics.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/aerodynamics/wind-tunnel/windtunnel-wall-corrections/scripts/test_windtunnel_wall_corrections.py

The test covers the worked example within 1%, internal consistency
(monotone shrinkage with model-to-tunnel size, eps non-negative,
corrected CL below uncorrected), the q and V identity at zero blockage,
the buoyancy sign convention, zero-correction round trips, the full
single-point pipeline against the individual calls, a three-point polar
against per-point corrections, and ValueError rejection of non-positive
inputs and models larger than the test section.

## Pitfalls

- Feed uncorrected coefficients: applying this set to coefficients that
  already carry corrections double-counts the wall effects.
- Do not re-divide the forces by the corrected q: the first-order
  coefficient factors already contain the dynamic pressure
  re-referencing.
- Compute the wake blockage from the uncorrected CDu at the uncorrected
  dynamic pressure, not from an iterated value.
- Take dP/dx from the empty test section, not from a pressure field
  measured with the model installed.
- Watch the units: dP/dx in Pa/m, q in Pa, volumes in m^3.
- Treat K1 = 0.52, delta = pi/48 and the sigma coefficient pi^2/48 as
  classical closed-rectangular approximations, not as universal
  constants; prefer the tunnel-specific calibration when available, and
  never trust the first-order forms when the model nearly fills the
  section (span approaching the height, or blockage above a few
  percent).

## Compliance

- STANDARDS-REF, gated: false. NACA Report 824 (public domain) is named
  as the reference-only anchor for the measured data culture; standard
  engineering methodology is summarized, not reproduced.
- Honesty note: K1 = 0.52, delta = pi/48 and the sigma coefficient
  pi^2/48 are classical approximations for a closed rectangular test
  section as documented in the Barlow, Rae and Pope method set. The
  operator should replace them with the tunnel-specific calibration when
  available; the logic functions accept k1, delta and sigma_coefficient
  overrides for exactly that purpose.
