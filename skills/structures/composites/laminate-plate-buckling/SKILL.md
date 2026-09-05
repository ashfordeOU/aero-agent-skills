---
name: laminate-plate-buckling
description: "Use when you must compute the elastic buckling load of an orthotropic or laminated flat plate: evaluate the energy-method critical load N_x_cr(m, n) per unit width for integer half-wave counts m and n from the classical lamination theory bending stiffnesses D11, D22, D12 and D66, minimize over the mode counts, and return the critical load, the governing buckling mode and the stability margin against the applied in-plane compression load. Produces the critical load, the buckling mode and the margin that gate composite panel stability checks. Trigger: laminate-plate-buckling, laminate-buckling, orthotropic-plate-buckling, d-matrix, buckling-mode-minimization, composite-panel-stability, compression-buckling."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [laminate-plate-buckling, laminate-buckling, orthotropic-plate-buckling, d-matrix, buckling-mode-minimization, composite-panel-stability, compression-buckling]
  version: 0.1.0
  author: AeroSkills
---

# Laminate Plate Buckling (structures/composites/laminate-plate-buckling)

Use when you must compute the elastic buckling load of an orthotropic or
laminated flat plate under uniaxial in-plane compression from the
classical lamination theory bending stiffnesses. This leaf implements the
energy-method critical load for a simply supported orthotropic plate,
minimizes it over the integer half-wave mode counts, and returns the
critical load per unit width, the governing mode and the stability margin
against the applied in-plane load, in pure Python, stdlib only. It pairs
with structures/fem/plate-buckling for isotropic plates, with
structures/composites/laminate-stiffness for the laminate stiffness
synthesis that feeds the D terms, and with structures/composites/
sandwich-panels and structures/composites/failure-criteria for the
other composite panel limit checks.

## Domain quick reference

- Energy-method critical load for mode (m, n), a simply supported
  orthotropic plate of length a (load direction) and width b with
  bending stiffnesses D11, D22, D12, D66 in N m:
  N_x_cr(m, n) = pi^2 * (D11 * (m/a)^2 + 2 * (D12 + 2*D66) * (n/b)^2 +
  D22 * n^4 * a^2 / (m^2 * b^4)), in N per unit width.
- The D12 + 2*D66 grouping is the torsional contribution and appears
  squared with the transverse half-wave count n.
- Mode minimization: the governing mode is the integer pair (m, n) in
  1..m_max by 1..n_max with the smallest critical load; ties resolve to
  the smallest (m, n) lexicographically.
- Margin: N_x_cr_min over the applied in-plane compression load per unit
  width. Below 1.0 the panel buckles under the applied load.
- Isotropic reduction: with D11 = D22 = D and D12 + 2*D66 = D the sweep
  over a plate long in the load direction reproduces the classic
  k = 4 result sigma_cr = 4 * pi^2 * D / (b^2 * t).
- Units are SI throughout: N m for the stiffnesses, m for the
  dimensions, N/m for the critical load, Pa for the stress.
- CMH-17 frames the composite materials context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the panel inputs: the load-direction length a, the width b, and
   the CLT bending stiffness terms D11, D22, D12 and D66 (N m) of the
   laminate.
2. Evaluate the energy-method critical load for one candidate half-wave
   mode (m, n) with critical_load.
3. Sweep the half-wave mode counts, m in 1..m_max and n in 1..n_max,
   with buckling_mode to minimize the critical load and recover the
   governing mode pair.
4. Compute the stability margin with buckling_margin, the minimized
   critical load over the applied in-plane compression load; a margin
   below 1.0 means the panel buckles.
5. Sanity-check the laminate result with the isotropic reduction: set
   D11 = D22 = D and D12 + 2*D66 = D and confirm the classic k = 4
   stress 4 * pi^2 * D / (b^2 * t) for a plate long in the load
   direction.
6. Confirm the deterministic contract test offline: python3
   scripts/test_laminate_plate_buckling.py.

## Worked example

A CFRP skin panel segment under uniaxial compression: a = 0.5 m (load
direction), b = 0.25 m, D11 = 200 N m, D22 = 120 N m, D12 = 25 N m,
D66 = 45 N m.

- Mode (2, 1): critical_load(200, 120, 25, 45, 0.5, 0.25, 2, 1) returns
  86852.5 N/m, that is 86.85 kN/m, matching the prep anchor within
  0.1 kN/m.
- Mode sweep: buckling_mode(200, 120, 25, 45, 0.5, 0.25) returns
  (86852.5, 2, 1): the governing half-wave mode is m = 2, n = 1, not the
  m = 1 fundamental, because the bending stiffness D11 is high along the
  load direction.
- Margin: buckling_margin(200, 120, 25, 45, 0.5, 0.25, 40000) returns
  2.171 against the applied 40 kN/m; the segment carries 2.17 times the
  applied load before buckling.
- Sweep truncation: with m_max = 1 the mode is forced to m = 1 and the
  load jumps to 120014.4 N/m at (1, 1), well above the minimized value,
  so the full mode sweep matters.
- Isotropic reduction: E = 70 GPa, nu = 0.3, t = 2 mm gives
  D = 51.28 N m; the sweep over a = 1.0 m, b = 0.25 m returns
  32392.5 N/m at mode (4, 1), and dividing by t = 0.002 m gives
  sigma_cr = 16.196 MPa against the classic 4 * pi^2 * D / (b^2 * t) =
  16.196 MPa, within the 16.20 MPa prep anchor.

## Verification

- Confirm critical_load(200, 120, 25, 45, 0.5, 0.25, 2, 1) returns
  86852.5 N/m and buckling_mode returns (86852.5, 2, 1).
- Confirm m_max = n_max = 2 still captures the (2, 1) mode and that
  m_max = 1 forces m = 1 with a higher load.
- Confirm the margin 2.171 at 40 kN/m applied and the isotropic
  reduction stress 16.196 MPa from the minimized N/m divided by
  t = 0.002 m.
- Confirm monotonicity: the critical load rises with D11 and with a
  narrower width b.
- Confirm determinism and tie resolution: repeated runs return the same
  pair, ties resolve to the smallest (m, n).
- Confirm every non-positive D11, D22, D12, D66, a, b, m, n and every
  non-positive applied load raises ValueError.
- Run the contract test offline: python3
  scripts/test_laminate_plate_buckling.py.

## Related leaves

- structures/fem/plate-buckling: isotropic plates buckled with a single
  coefficient k from the edge support and width, no D-matrix path.
- structures/composites/laminate-stiffness: the in-plane laminate
  stiffness synthesis that precedes the bending terms used here.
- structures/composites/sandwich-panels: face wrinkling into the core,
  a different composite panel failure mode.
- structures/composites/failure-criteria: lamina failure indices under
  the in-plane loads.

## Pitfalls

- Applying a single isotropic coefficient k to an orthotropic laminate:
  the mode energy carries the four D terms, and the minimized load over
  the half-wave sweep differs from any fixed-mode estimate (the m = 1
  estimate runs 120.0 kN/m against the 86.85 kN/m minimum here).
- Reporting the fundamental m = 1 mode as the critical mode: high D11
  shifts the governing half-wave count above one, as the (2, 1) mode
  shows in the worked example.
- Dropping the torsional term: 2 * (D12 + 2*D66) * (n/b)^2 contributes
  3680 of the 8800 N/m inner sum at mode (2, 1), so neglecting D12 and
  D66 badly understates the load.
- Confusing load per unit width with stress: the module returns N/m;
  divide by the panel thickness t to compare with a stress allowables
  value in MPa.
- Inconsistent units: stiffnesses in N m with dimensions in mm silently
  scale the result by 10^6; keep SI throughout.
- Reading a margin at or above 1.0 as safe margin: the margin is the
  ratio, so 2.171 means 2.171 times the applied load, not 2.171 percent
  of reserve.
- Truncating the mode sweep on a long panel: the governing half-wave
  count in the load direction grows near a/b, so keep m_max at or above
  the aspect ratio of the panel.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_laminate_plate_buckling.py

The test covers the worked-example contract (mode (2, 1) at 86.85 kN/m
within 0.1 kN/m, minimized load 86852.5 N/m, margin 2.171 within 0.01),
the isotropic reduction anchor at 16.20 MPa within 0.05 MPa, the sweep
capture at reduced m_max and n_max, the forced m = 1 higher load,
monotonicity in D11 and width, determinism with tie resolution to the
smallest (m, n), and ValueError rejection of every non-positive
stiffness, dimension, mode count and applied load.

## Compliance

- Standards referenced, not reproduced: CMH-17 (SAE) is cited as the
  composite materials context; the buckling relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
