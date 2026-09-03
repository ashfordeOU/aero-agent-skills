---
name: winglet-design
description: "Use when you must size a winglet as a wingtip device for induced-drag reduction on a fixed-wing aircraft: compute the effective span extension and the effective aspect ratio from the winglet height fraction and the cant angle, estimate the improved span efficiency, the induced-drag factor and the induced-drag coefficient at a reference lift coefficient, the percent drag reduction, and the root bending moment penalty at the wing root, then size the winglet height by bisection to hit a target drag reduction. Produces the winglet height, the effective aspect ratio, the drag reduction and the bending penalty that gate the wingtip device trade. Trigger: winglet design, wingtip device, induced drag reduction, effective aspect ratio, span efficiency, cant angle, winglet height, root bending moment penalty."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: aerodynamics
pack: wing-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: wing-design
  tags: [winglet-design, wingtip-device, induced-drag-reduction, effective-aspect-ratio, span-efficiency, cant-angle, winglet-height, root-bending-moment-penalty]
  version: 0.1.0
  author: AeroSkills
---

# Winglet Design (aerodynamics/wing-design/winglet-design)

Use when the task is the wingtip device trade for induced-drag reduction:
sizing the winglet height and cant from the reference wing geometry and
a target drag reduction, and weighing the drag gain against the root
bending moment penalty. This leaf implements the effective-span
extension model in pure Python, stdlib only. It pairs with
aerodynamics/wing-design/wing-planform-design for the reference
planform, and with vehicle-design/sizing/wing-planform-sizing and the
drag-polar leaves for the system context. The improved span efficiency
and bending penalty models are documented conceptual approximations for
a preliminary trade; a real winglet design needs a VLM/CFD pass and a
structural FEM pass.

## Domain quick reference

- Effective span extension: extension = K_HEIGHT * height_frac, with
  K_HEIGHT = 0.8 the documented fraction of the winglet height that acts
  as span extension. height_frac is the winglet height over the local
  semi-span.
- Cant weighting: cant_factor = cos(cant_deg). A vertical winglet
  (cant 0) keeps the full effect; a flat tip (cant 90) loses it.
- Extended span and effective aspect ratio: b_eff = b * (1 + 2 *
  cant_factor * K_HEIGHT * height_frac) adds both tips, and
  AR_eff = b_eff^2 / area.
- Improved span efficiency: e_eff = 1 - (1 - e_base) / (AR_eff / AR)
  with AR = span^2 / area. Documented approximation: the drag factor
  k = 1 / (pi * e * AR) shrinks with the effective-AR gain.
- Induced drag: k = 1 / (pi * e * AR) and cd_i = cl^2 * k at the
  reference lift coefficient.
- Drag reduction: reduction_pct = 100 * (1 - cd_i_wl / cd_i_base).
- Root bending penalty: penalty_pct = cant_factor * K_HEIGHT *
  height_frac * 100 * (1 + 0.5 * height_frac). Approximate scaling, the
  winglet load acts near the tip so the added root moment grows roughly
  with the height fraction.
- Sizing: size_winglet bisects height_frac in [0.01, 0.5] to a 0.1 pct
  reduction tolerance and returns the physical height
  height_m = height_frac * span / 2 (semi-span local reference).
- Units are SI: m, m^2, degrees.

## Workflow

1. Take the reference wing geometry from the planform design: span,
   area, base span efficiency e_base, and the lift coefficient cl_ref
   for the drag check.
2. Read off the winglet height fraction and cant, or the target
   reduction percent when sizing.
3. Compute the span extension with effective_span_extension and the
   cant weighting with cant_factor.
4. Get the effective aspect ratio with ar_eff and the improved span
   efficiency with e_winglet.
5. Get the induced-drag factors with induced_drag_factor, then the
   drag coefficients with cd_i, and the gain with
   drag_reduction_pct.
6. Check the structural side with root_bending_penalty_pct.
7. To size the device, run size_winglet with the target reduction and
   inspect the returned height fraction, height, ar_eff, e_eff, cd_i,
   reduction_pct and bending_penalty_pct.
8. Confirm the deterministic checks with the contract test
   scripts/test_winglet_design.py.

## Worked example

Wing: span 30 m, area 100 m^2 (AR 9), e_base 0.80, cl_ref 0.5. Direct
case height_frac 0.12, cant 0 deg, taper 0.35.

- Extension: 0.8 * 0.12 = 0.096; cant factor 1.0.
- Extended span: 30 * (1 + 2 * 1.0 * 0.096) = 35.76 m; AR_eff =
  35.76^2 / 100 = 12.788.
- Span efficiency: e_eff = 1 - 0.2 / (12.788 / 9) = 0.85924.
- Drag factors: k_base = 1 / (pi * 0.8 * 9) = 0.044210; k_wl = 1 / (pi *
  0.85924 * 12.788) = 0.028969.
- Drag coefficients: cd_i base = 0.25 * 0.044210 = 0.011052; cd_i wl =
  0.25 * 0.028969 = 0.007242.
- Reduction: 100 * (1 - 0.007242 / 0.011052) = 34.47 pct.
- Bending penalty: 1.0 * 0.8 * 0.12 * 100 * (1 + 0.06) = 10.18 pct.
- Sizing case: size_winglet(30, 100, 0.8, 25, 0.5) returns height_frac
  0.0784, height_m 1.176 m, ar_eff 11.40, e_eff 0.8421, reduction_pct
  25.00 within the 0.1 pct tolerance, bending_penalty_pct 6.52.

## Verification

- Confirm ar_eff(30, 100, 0.12, 0.0) returns 12.788 within 0.01.
- Confirm e_winglet(0.8, 0.12, 0.0) returns 0.85924 within 1e-4.
- Confirm induced_drag_factor(0.8, 9.0) returns 0.044210 within 1e-6
  and the winglet factor matches 1 / (pi * e_eff * AR_eff).
- Confirm cd_i base 0.011052 and the drag reduction 34.47 pct against
  the worked example band (34.43 within 0.05).
- Confirm root_bending_penalty_pct(0.12, 0.0) returns 10.18 within
  0.05 and drops to zero for a flat tip at 90 deg cant.
- Confirm size_winglet with target 25 pct returns a height fraction in
  [0.05, 0.12] and a reduction within 0.1 pct of the target.
- Confirm every non-positive span, area, lift coefficient, span
  efficiency outside (0, 1], height fraction outside [0, 0.6], cant
  outside [-90, 90] degrees, taper outside (0, 1] and target reduction
  outside (0, 100) raises ValueError.
- Run the contract test offline: python3
  scripts/test_winglet_design.py (31 tests, deterministic).

## Related leaves

- aerodynamics/wing-design/wing-planform-design: the reference planform
  geometry and spanwise loading the winglet sizing starts from.
- vehicle-design/sizing/wing-planform-sizing: vehicle-level wing area
  sizing context.
- aerodynamics/drag-polars/drag-polar and
  aerodynamics/drag-polars/parasite-drag: the full polar the induced
  term feeds into.
- aerodynamics/cfd/vortex-lattice-method: the higher-fidelity follow-on
  for the spanwise loading with the winglet fitted.
- structures/fem/calculix-linear: the structural follow-on for the root
  bending check.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_winglet_design.py

The test covers the worked example contract (AR_eff 12.788, e_eff
0.85924, k_base 0.044210, drag reduction 34.47 pct, bending penalty
10.18 pct), the cant weighting bounds, the effective-aspect-ratio
identity, the sizing bisection contract and its monotonicity, the
height from the semi-span reference, and ValueError rejection of every
non-physical input.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the classic
  induced-drag and airfoil-data basis and FAR 25 the structural and
  airworthiness context; both are cited by name only with the model
  relations stated as standard engineering methodology, summary-only
  per standards-map.yaml.
- The e_eff improvement and bending-penalty models are documented
  conceptual approximations for a preliminary trade.
- compliance: STANDARDS-REF, gated: false.
