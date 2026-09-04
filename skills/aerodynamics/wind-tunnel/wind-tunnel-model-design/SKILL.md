---
name: wind-tunnel-model-design
description: "Use when you must design the wind tunnel model and the test setup for a wind tunnel campaign on an aircraft configuration: select the model scale as the smaller of the test section blockage limit and the span clearance, compute the model wing area, span and mean aerodynamic chord from the scale, check the model Reynolds number at the maximum tunnel speed against the full scale flight Reynolds number and report the Reynolds mismatch, estimate the maximum dynamic pressure and the model load at the maximum test lift coefficient, rate the force balance capacity against that load, and size the model support sting for the bending moment. Produces the chosen scale, model reference dimensions, blockage ratio, Reynolds ratio, balance verdict and sting diameter that gate the model build. Trigger: wind tunnel model design, model scale selection, blockage ratio, reynolds mismatch, force balance rating, sting sizing, test section."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: wind-tunnel
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: wind-tunnel
  tags: [wind-tunnel-model-design, model-scale-selection, blockage-ratio, reynolds-mismatch, force-balance-rating, sting-sizing, test-section]
  version: 0.1.0
  author: Aero Agent Skills
---

# Wind Tunnel Model Design (aerodynamics/wind-tunnel/wind-tunnel-model-design)

Use when the task is designing the scale model and the test setup for a
wind tunnel campaign on an aircraft configuration, the pre-test design
step that fixes the model geometry and the loads the installation must
carry before any runs. The model scale is driven by the smaller of two
geometric constraints, the test section blockage limit and the span
clearance to the walls; the model reference dimensions follow from the
scale; the model Reynolds number at the maximum tunnel speed is compared
with the full-scale flight Reynolds number; and the maximum test
dynamic pressure and the resulting model load are used to rate the force
balance and to size the model support sting. The leaf pairs with the
post-test siblings: aerodynamics/wind-tunnel/windtunnel-data-reduction
reduces the raw balance readings into coefficients after the runs, and
aerodynamics/wind-tunnel/windtunnel-wall-corrections corrects measured
coefficients for the test section boundaries; this leaf stops at the
pre-test design and reports a Reynolds mismatch flag rather than a
corrected result.

The module constants BLOCKAGE_MAX (0.05), SPAN_CLEARANCE (0.8) and
STING_ALLOWABLE_STRESS_PA (800 MPa) are documented typical values only:
they are program and test specific inputs, and every function and the
analyze pass accept explicit overrides. NACA TR-824 frames the
compressible-flow context the tunnel operates in; the relations below
are standard low-speed model sizing and load estimation methodology,
summary-only. Pure Python stdlib, deterministic, offline.

## Domain quick reference

- Test section area: A_test = w * h (test_section_area).
- Blockage-limited scale: lambda_blockage = sqrt(blockage_max *
  A_test / S_full), the scale at which the model wing area equals
  blockage_max times the test section area (scale_from_blockage).
- Span-limited scale: lambda_span = (w * clearance) / b_full, the
  largest model that keeps the span inside the available fraction of
  the section width (scale_from_span).
- Chosen scale: lambda = min(lambda_blockage, lambda_span)
  (choose_scale). The dict also carries model_wing_area = S_full *
  lambda^2, model_mac = c_full * lambda, model_span = b_full * lambda,
  blockage_ratio = S_model / A_test and blocked_ok (the blockage limit
  is inclusive). choose_scale takes the full-scale MAC as its fifth
  argument so the model chord is reported; the scale selection itself
  depends only on the areas and the span.
- Model Reynolds number: Re_model = rho * V * c_model / mu, rho and mu
  at sea level by default (reynolds_model).
- Reynolds ratio: Re_model / Re_full (reynolds_ratio). The analyze
  pass reports "reynolds-matched" when the ratio is at least 0.5 and
  "reynolds-mismatch" below; this is an engineering flag about the
  tunnel capability, not a pass/fail gate on the campaign.
- Maximum dynamic pressure: q = 0.5 * rho * Vmax^2.
- Model load at the maximum test lift coefficient: L = q * S_model *
  CL_max_test (model_load_N), the load the balance must carry.
- Balance rating: "balance-ok" when L <= balance_capacity_N, else
  "balance-overload" (balance_verdict).
- Sting sizing: M = L * sting_arm, then d = (32 * M / (pi *
  sigma_allow))^(1/3) for the solid circular sting section
  (sting_diameter_m).
- One-call pass: analyze(inputs) returns the scale selection, model
  dimensions, blockage ratio, model Reynolds number and ratio, dynamic
  pressure, load, balance verdict, sting bending moment and diameter in
  a single dict.
- Units are SI throughout: m, m2, m/s, Pa, N, N m, kg/(m s).

## Workflow

1. Gather the test section geometry (test_section_width_m,
   test_section_height_m, or the area directly), the full-scale
   reference data (full_span_m, full_wing_area_m2, full_mac_m,
   full_reynolds), the tunnel maximum speed, and the program specific
   inputs: max_test_cl (default 1.4), balance_capacity_N, sting_arm_m,
   sting_allowable_stress_pa, blockage_max and clearance when they
   differ from the documented typicals.
2. Confirm the test section area with test_section_area, or pass
   test_section_area_m2 to skip the product.
3. Select the scale with choose_scale and read lambda, the model wing
   area, MAC and span, the blockage_ratio and blocked_ok from the
   returned dict; when the span limit binds the model is smaller than
   the blockage limit allows.
4. Check the tunnel Reynolds capability: reynolds_model at the maximum
   tunnel speed, then reynolds_ratio against the full-scale flight
   condition. A ratio below 0.5 flags reynolds-mismatch, the usual
   low-speed outcome for a large transport, and is reported as a
   limitation of the campaign, not an error.
5. Compute q = 0.5 * rho * Vmax^2 and the model load at the maximum
   test lift coefficient with model_load_N, then rate the balance with
   balance_verdict.
6. Size the sting: the bending moment is the model load times the sting
   arm (model quarter chord to the sting mount); sting_diameter_m gives
   the solid circular section diameter at the allowable stress.
7. For the complete setup in one call, run analyze(inputs) and read the
   whole dict; it applies the same sequence and validates every input.
8. Confirm the deterministic checks with the contract test
   scripts/test_wind_tunnel_model_design.py.

## Worked example

A 2.44 m square test section (area 5.9536 m2) for a full-scale
transport: span 34.0 m, wing area 122.6 m2, MAC 4.2 m, full-scale
Reynolds number 3.0e7. Tunnel maximum speed 80 m/s, max_test_cl 1.4,
balance capacity 5000 N, sting arm 0.35 m, sting allowable stress
800 MPa, default blockage_max 0.05 and clearance 0.8.

- scale_from_blockage: sqrt(0.05 * 5.9536 / 122.6) = 0.04927, the
  blockage-limited scale.
- scale_from_span: (2.44 * 0.8) / 34.0 = 0.05741. The chosen scale is
  the smaller, lambda = 0.04927.
- Model dimensions: wing area 122.6 * 0.04927^2 = 0.29761 m2, MAC
  4.2 * 0.04927 = 0.20693 m, span 34.0 * 0.04927 = 1.6752 m.
- Blockage ratio: 0.29761 / 5.9536 = 0.04999, within the 0.05 limit,
  so blocked_ok. The module carries full precision (scale 0.049275,
  model area 0.29768 m2), which lands the ratio on the limit and the
  reported anchors within their contract tolerances.
- Model Reynolds at 80 m/s: 1.225 * 80 * 0.20693 / 1.789e-5 = 1.1337e6.
  Ratio to the full-scale condition: 1.1337e6 / 3.0e7 = 0.03779, far
  below 0.5, so reynolds_limitation is "reynolds-mismatch": the
  low-speed model runs at 3.8% of the flight Reynolds number.
- Dynamic pressure: q = 0.5 * 1.225 * 80^2 = 3920 Pa. Model load at
  max_test_cl 1.4: 3920 * 0.29761 * 1.4 = 1633.3 N, against a 5000 N
  balance, so the verdict is balance-ok (a 1000 N balance would read
  balance-overload).
- Sting: bending moment 1633.3 * 0.35 = 571.7 N m; diameter
  (32 * 571.7 / (pi * 800e6))^(1/3) = 0.01938 m = 19.38 mm at 800 MPa.

## Verification

- Confirm choose_scale on the worked example returns scale 0.04927
  within 1e-4, model area 0.29761 m2 within 1e-4, model MAC 0.20693 m
  within 1e-4 and model span 1.6752 m within 2e-4 (the published span
  anchor is computed from the scale truncated to five decimals).
- Confirm reynolds_model returns 1.1337e6 within 1e3, the ratio 0.03779
  within 1e-4, and analyze reports "reynolds-mismatch".
- Confirm model_load_N returns 1633.3 N within 1 N and
  balance_verdict gives "balance-ok" at 5000 N capacity and
  "balance-overload" at 1000 N.
- Confirm sting_diameter_m returns 0.01938 m within 0.01 mm.
- Confirm every non-positive width, height, area, span, MAC, Reynolds
  number, tunnel speed, lift coefficient, balance capacity, sting arm
  and allowable stress raises ValueError, in the individual functions
  and in analyze.
- Run the contract test offline: python3
  scripts/test_wind_tunnel_model_design.py (35 tests, deterministic,
  exit 0).

## Related leaves

- aerodynamics/wind-tunnel/windtunnel-data-reduction: reduces the raw
  balance and pressure measurements into coefficients after the runs,
  with the tare and uncertainty steps this pre-test leaf does not do.
- aerodynamics/wind-tunnel/windtunnel-wall-corrections: applies the
  closed-wall corrections to the measured coefficients, the post-test
  counterpart of the pre-test blockage budget fixed here.

## Pitfalls

- Taking the blockage limit as the scale without checking the span
  clearance: choose_scale returns the smaller of lambda_blockage and
  lambda_span, and in the worked example the span limit would allow
  0.05741 while blockage binds at 0.04927 — the reverse case binds on
  span, so report which constraint drove the choice.
- Treating a reynolds-mismatch flag as a campaign error: a ratio below
  0.5 (0.03779 in the worked example) is the usual low-speed outcome
  for a large transport and is reported as a tunnel-capability
  limitation, not a pass/fail gate on the model.
- Overriding the documented typical constants without checking the
  program: BLOCKAGE_MAX, SPAN_CLEARANCE and STING_ALLOWABLE_STRESS_PA
  are test-specific inputs with defaults; each function and analyze
  accept explicit overrides, so pass program values rather than
  assuming the defaults hold.
- Rating the balance on the cruise load: the load that must be carried
  is q * S_model * CL_max_test at the maximum test lift coefficient
  (1633 N in the example), and a 1000 N balance reads balance-overload
  even though the 5000 N rating passes.
- Sizing the sting on force alone: the bending moment is the model load
  times the sting arm (quarter chord to mount), and the diameter comes
  from that moment at the allowable stress — an arm change alters the
  diameter even at fixed load.
- Quoting the rounded scale anchors: the module carries full precision
  (scale 0.049275 vs the published 0.04927) so the round-trip dimension
  checks land within tolerance; do not truncate inputs to the published
  anchors before calling.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_wind_tunnel_model_design.py

The test covers the worked example anchors (scale 0.04927, model wing
area 0.29761 m2, MAC 0.20693 m, span 1.6752 m, blockage ratio 0.04999,
model Reynolds 1.1337e6, Reynolds ratio 0.03779, load 1633.3 N, sting
diameter 19.38 mm), scale selection as the minimum of the blockage and
span limits with exact dimension round trips, the span-limited case,
the balance overload verdict, the reynolds-matched flag above a 0.5
ratio, the default max_test_cl, the direct test section area input,
determinism of the analyze pass, and ValueError rejection of every
non-positive input class.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named for the
  compressible-flow context only; the sizing relations above are
  standard low-speed wind tunnel methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
