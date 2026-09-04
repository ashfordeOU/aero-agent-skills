---
name: windtunnel-data-reduction
description: "Correct wind tunnel balance and pressure measurements into standard aerodynamic coefficients: subtract support tare and tareshift, apply solid and wake blockage corrections, correct wall interference and streamline curvature, apply Reynolds number and Mach corrections, estimate repeat-run uncertainty of the measured coefficients, and reduce raw runs to lift, drag, and pitching moment coefficients plus pressure distributions referenced to planform area and reference length, with a full correction ledger. Use when the task is experimental wind tunnel data reduction, tare or blockage correction, wall interference, dynamic pressure correction, coefficient reduction, or uncertainty from repeated runs. Trigger: windtunnel data reduction, tare correction, blockage correction, wall interference, reynolds correction, aerodynamic coefficients, pressure distribution, uncertainty estimation, balance data, experimental aerodynamics."
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
  tags: [windtunnel-data-reduction, tare-correction, blockage-correction, wall-interference, reynolds-correction, aerodynamic-coefficients, pressure-distribution, balance-data, uncertainty-estimation, experimental-aerodynamics]
  version: 0.1.0
  author: Aero Agent Skills
---

# Wind Tunnel Data Reduction (aerodynamics/wind-tunnel/windtunnel-data-reduction)

Use when the task is experimental wind tunnel test data reduction:
converting raw balance forces and pressure tap readings into corrected
aerodynamic coefficients. The leaf covers tare and tareshift
subtraction, solid and wake blockage, wall interference, streamline
curvature, Reynolds number and Mach corrections, coefficient reduction
referenced to planform area and reference length, and uncertainty
estimation from repeated runs. It is the experimental counterpart to
the computational leaves (cfd/panel-method, airfoil/xfoil-analysis):
those compute aerodynamics, this one reduces measured data.

## Domain quick reference

- Tare: the support system (sting, strut, brackets) carries load even
  with the model unloaded. Record a tare run with the model removed or
  at zero lift and subtract it from every balance reading. A model at
  zero angle of attack whose raw drag equals its tare reads zero net
  drag after subtraction.
- Tareshift: the tare itself changes with angle of attack because the
  support loads the balance differently as the model pitches. Bracket
  the polar with tare runs at a low and a high angle and interpolate
  the tare linearly at each measurement angle.
- Solid blockage: the model volume displaces air in the closed test
  section, accelerating the flow around the model. The solid blockage
  increment is eps_sb = K1 * (model volume / test section volume), with
  K1 = 0.96 for a closed rectangular section (0.34 for an open one).
- Wake blockage: the model wake fills the test section and slows the
  flow, raising the effective dynamic pressure. The wake blockage
  increment is eps_wb = 0.25 * (S / C) * CDu, with S the planform area,
  C the test section area, CDu the uncorrected drag coefficient.
- Blockage correction: the corrected dynamic pressure is
  q_corr = q_u * (1 + eps)^2 and the corrected speed is
  V_corr = V_u * (1 + eps), with eps = eps_sb + eps_wb. Blockage always
  raises the dynamic pressure.
- Wall interference: the tunnel walls constrain the streamlines around
  a lifting model like an image vortex system, adding an angle of
  attack increment delta_alpha = delta * (S / C) * CL, with delta = 0.82
  for a closed section and 0.125 for an open one.
- Streamline curvature: the curved streamlines act like added camber,
  shifting the angle of attack and the pitching moment. The increments
  scale with (S / C) * CL * (chord / height) and reduce the moment
  magnitude for a positive CL.
- Reynolds number: measured coefficients are only valid at the test
  Reynolds number. Scale a reference drag with the flat plate skin
  friction law CD(Re) = CD_ref * (Re_ref / Re)^n, n = 0.2 turbulent,
  n = 0.5 laminar.
- Mach corrections: above M = 0.3 use the compressible dynamic pressure
  q = 0.5 * gamma * p * M^2 and correct pressure coefficients with the
  Prandtl Glauert factor Cp = Cp_inc / sqrt(1 - M^2).
- Coefficient reduction: CL = L / (q S), CD = D / (q S),
  Cm = M / (q S c_ref) referenced to planform area S and reference
  length c_ref; local Cp = (p_local - p_ref) / q.
- Uncertainty: repeated runs of the same condition give a sample mean,
  a sample standard deviation (n - 1 denominator), a standard error of
  the mean std / sqrt(n), and an expanded uncertainty at a coverage
  factor (typically 2 for about 95% confidence).
- Correction ledger: record every applied correction with its numeric
  value so the final coefficients are auditable and reproducible.

## Workflow

1. Record the tare runs: balance readings with the model removed or
   unloaded at the low and high angles of the polar.
2. For each measurement point, interpolate the tare at the measurement
   angle and subtract it from the raw lift, drag, and moment.
3. Compute the uncorrected coefficients at the measured dynamic
   pressure (use the compressible form when M >= 0.3).
4. Compute the solid and wake blockage increments, sum them, and
   correct the dynamic pressure and speed.
5. Apply the wall interference and streamline curvature corrections to
   the angle of attack and the pitching moment.
6. Re-reduce the forces at the corrected dynamic pressure to get the
   final CL, CD, and Cm; compute Cp distributions from the pressure
   taps with the corrected q.
7. Apply Reynolds number scaling if the reference data come from a
   different Reynolds number.
8. Repeat the measurement condition several times and report the mean
   coefficients with the expanded uncertainty from the repeat runs.
9. Write the correction ledger alongside the coefficients.

## Correction formulas

Tare at angle alpha between two tare runs (tareshift):

    tare(alpha) = tare_low + (tare_high - tare_low)
                   * (alpha - alpha_low) / (alpha_high - alpha_low)

Blockage:

    eps_sb = K1 * V_model / V_test_section
    eps_wb = 0.25 * (S / C) * CDu
    eps = eps_sb + eps_wb
    q_corr = q_u * (1 + eps)^2
    V_corr = V_u * (1 + eps)

Wall interference and streamline curvature:

    delta_alpha_wall = delta * (S / C) * CL          (radians)
    delta_alpha_curv = (S / C) * CL * (chord / (4 h)) (radians)
    delta_cm = -(S / C) * CL * (chord / (8 h))

Reynolds and Mach:

    CD(Re_test) = CD_ref * (Re_ref / Re_test)^n
    q = 0.5 * gamma * p * M^2
    Cp = Cp_inc / sqrt(1 - M^2)

Coefficients:

    CL = L / (q S)          CD = D / (q S)
    Cm = M / (q S c_ref)    Cp = (p_local - p_ref) / q

Uncertainty from n repeat runs:

    mean = sum(x_i) / n
    s = sqrt(sum((x_i - mean)^2) / (n - 1))
    SE = s / sqrt(n)        U = k * SE    (k = 2 default)

## Worked example

Model: wing with planform area S = 0.4 m^2, reference chord
c_ref = 0.25 m in a closed rectangular test section of area 8.0 m^2,
height 1.5 m, volume 6.0 m^3. Model volume 0.004 m^3.

Raw readings at alpha = 4 deg: L = 510.0 N, D = 32.0 N, M = 12.5 N m.
Tare runs bracket the polar: at 0 deg tare drag 2.0 N, at 10 deg
2.2 N (lift and moment tare zero). Measured dynamic pressure
q = 980 Pa.

1. Tare at 4 deg: 2.0 + 0.2 * (4 / 10) = 2.08 N of drag. Corrected
   forces: L = 510 N, D = 29.92 N, M = 12.5 N m.
2. Uncorrected coefficients at q = 980 Pa:
   CL = 510 / 392 = 1.30102, CD = 29.92 / 392 = 0.07633,
   Cm = 12.5 / 98 = 0.12755.
3. Blockage: eps_sb = 0.96 * 0.004 / 6 = 0.00064,
   eps_wb = 0.25 * (0.4 / 8) * 0.07633 = 0.000954,
   eps = 0.001594, q_corr = 980 * 1.001594^2 = 983.13 Pa.
4. Wall interference: delta_alpha = 0.82 * 0.05 * 1.30102 rad =
   3.056 deg. Streamline curvature: 0.155 deg, delta_cm = -0.001355.
   Corrected angle alpha = 4 + 3.056 + 0.155 = 7.21 deg.
5. Final coefficients on q_corr:
   CL = 510 / (983.13 * 0.4) = 1.29688,
   CD = 29.92 / (983.13 * 0.4) = 0.07608,
   Cm = 12.5 / (983.13 * 0.4 * 0.25) - 0.001355 = 0.12579.

Repeated runs of the same condition gave drag coefficient values
0.0300, 0.0305, 0.0298, 0.0302, 0.0301: mean 0.03012, sample std
0.000259, standard error 0.000116, expanded uncertainty at coverage 2
U = 0.000232, so the reported CD is 0.03012 +/- 0.00023.

## Behavior contract (gate 3)

    python3 skills/aerodynamics/wind-tunnel/windtunnel-data-reduction/scripts/test_windtunnel_data_reduction.py

Stdlib unittest only, offline, deterministic. Covers tare subtraction
removing the drag offset, tareshift interpolation, blockage raising the
dynamic pressure, wall interference and streamline curvature values,
Reynolds and Mach corrections, the coefficient formulas on the known
case above, the full pipeline with ledger, and the uncertainty bounds.

## Pitfalls

- Keep the reference area and length consistent everywhere: CL, CD,
  and Cm all use the same planform area and reference chord.
- Apply the tare before computing any coefficient; a forgotten tare
  leaves a drag offset that inflates CD at every angle.
- Compute the wake blockage from the uncorrected drag coefficient;
  iterating with the corrected value changes nothing of consequence.
- Do not apply the Prandtl Glauert factor at or above M = 1; it is a
  subsonic correction only.
- Report the standard error of the mean, not the per-run scatter, as
  the uncertainty of the reported mean; the expanded uncertainty is the
  coverage factor times the standard error.
- Use at least three repeat runs for a meaningful sample standard
  deviation.
