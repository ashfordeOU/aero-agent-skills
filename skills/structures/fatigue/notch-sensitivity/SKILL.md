---
name: notch-sensitivity
description: "Use when a hole, fillet, or other stress raiser must be accounted for in a fatigue assessment of a structure. Compute the stress concentration factor and fatigue notch factor for a notched aerospace part: determine Kt for an elliptical or circular hole from the geometry, estimate the Peterson material constant from the ultimate tensile strength, convert Kt into the fatigue notch factor Kf with the Peterson and Neuber corrections using the notch root radius, evaluate the notch sensitivity q, and apply the effective stress amplitude to the fatigue strength check. Trigger: stress concentration factor, fatigue notch factor, notch sensitivity, Neuber, Peterson, notch root radius, effective stress amplitude."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fatigue
  tags: [notch-sensitivity, stress-concentration-factor, fatigue-notch-factor, neuber-method, peterson-method, notch-root-radius, effective-stress-amplitude, elliptical-hole, circular-hole, finite-width-plate, material-constant, elastic-peak-stress]
  version: 0.1.0
  author: Aero Agent Skills
---

# Notch Sensitivity and Fatigue Notch Factor (structures/fatigue/notch-sensitivity)

Use when a notched detail (hole, fillet, cutout, lug) must be
accounted for in a fatigue assessment: compute the elastic stress
concentration factor Kt, reduce it to the fatigue notch factor Kf with
the Peterson or Neuber method, quantify the notch sensitivity q, and
amplify the nominal stress amplitude before the endurance check.

## Domain quick reference

- Stress concentration factor: the elastic peak stress at the notch
  root divided by the nominal section stress, sigma_peak = Kt *
  sigma_nominal. Kt is a geometry-only quantity, independent of the
  material.
- Elliptical hole in an infinite plate: Kt = 1 + 2a/b, with a the semi
  axis perpendicular to the load and b the semi axis parallel to it.
  A circular hole (a = b) gives the classical Kt = 3.
- Circular hole in a finite width plate: Kt = 3 - 3.14(d/w) +
  3.667(d/w)^2 - 1.527(d/w)^3, a curve fit of the Howland solution
  valid for d/w <= 0.5, with d the hole diameter and w the plate
  width. As the hole shrinks (d/w toward 0) the factor returns to 3.
- Fatigue notch factor: the reduction of the fatigue strength caused by
  the notch, Kf = S_smooth / S_notched. It lies between 1 (notch
  ignored) and Kt (full sensitivity), and it is what the endurance
  check multiplies the nominal amplitude by.
- Peterson method: Kf = 1 + (Kt - 1) / (1 + a / rho), with rho the
  notch root radius and a the Peterson material constant in the same
  length unit.
- Peterson material constant from strength: a = 0.0254 * (2070 / Sut)^1.8
  in mm with Sut in MPa (steel correlation). At Sut = 2070 MPa the
  constant is 0.0254 mm, and it grows as the strength falls.
- Neuber method: Kf = 1 + (Kt - 1) / (1 + sqrt(a' / rho)), with a' the
  Neuber material constant in the same length unit as rho. The square
  root form decays more slowly with root radius than the Peterson
  linear form, so for a/rho below 1 the Neuber Kf sits below the
  Peterson Kf at equal constants.
- Notch sensitivity: q = (Kf - 1) / (Kt - 1), the fraction of the
  elastic concentration that actually affects fatigue. q = 0 means
  Kf = 1 (no fatigue reduction), q = 1 means Kf = Kt (full
  sensitivity). Blunt notches and ductile materials give q near 1;
  sharp notches and high strength give lower q.
- Effective stress amplitude: sigma_eff = Kf * sigma_nominal. The
  endurance check compares sigma_eff with the endurance limit, not the
  nominal amplitude.
- FAR-25 and CS-25 frame the certification context for fatigue
  substantiation of transport airplane structure; the notch mechanics
  themselves are standard mechanical engineering methodology.

## Workflow

1. Resolve the geometry into Kt. For an elliptical or circular hole
   use kt_elliptical_hole (a perpendicular, b parallel to the load) or
   kt_circular_hole_finite_width (d and w in the same unit) when the
   plate width is known.
2. Estimate the Peterson material constant with
   peterson_material_constant from the ultimate tensile strength in
   MPa, or supply the Neuber constant a' directly from the material
   database (near 0.25 mm for steel).
3. Reduce Kt to Kf with peterson_fatigue_notch_factor or
   neuber_fatigue_notch_factor using the notch root radius rho.
4. Quantify the loss with notch_sensitivity: q = (Kf - 1) / (Kt - 1).
5. Amplify the nominal stress amplitude with
   effective_stress_amplitude and compare sigma_eff with the endurance
   limit for the verdict; max_stress_at_notch gives the elastic peak
   stress when the local elastic stress is what matters.
6. Record Kt, Kf, q, and sigma_eff in the fatigue substantiation
   report together with the endurance check result.

## Pitfalls

- Using Kt in the fatigue check instead of Kf: the endurance limit
  comparison must use sigma_eff = Kf * sigma_nominal, not Kt *
  sigma_nominal, or the margin is systematically too small.
- Reading Kt from the wrong hole formula: 1 + 2a/b assumes the load
  runs along b; swap a and b and Kt drops from 5 to 2 for a 2:1
  ellipse. Keep the perpendicular semi axis on top.
- Applying the finite width fit beyond its range: the d/w polynomial
  is a curve fit of the Howland solution valid for d/w <= 0.5, and the
  code rejects d >= w outright.
- Mixing length units in the material constants: Peterson a and Neuber
  a' must share the unit of rho (mm is the common choice); a factor of
  25.4 error in a changes Kf materially at small root radii.
- Forgetting the strength dependence: the Peterson constant is not a
  fixed 0.0254 mm; it scales with (2070/Sut)^1.8, and using the
  high-strength value on a soft alloy overstates the fatigue notch
  factor.
- Treating q as a material constant: q depends on the root radius and
  the material constant together through Kf; a blunt notch in a
  notched part can show q near 1 while a sharp notch in the same
  material shows q near 0.5.
- Confusing peak elastic stress with fatigue-relevant stress: Kt *
  sigma_nominal is the local elastic peak; Kf * sigma_nominal is what
  the endurance limit check consumes. Report both, apply Kf.
- Assuming Neuber and Peterson agree: at equal constants and a/rho
  below 1, Neuber gives the lower Kf; pick one method and state it in
  the substantiation instead of cherry-picking the convenient one.

## Behavior contract (gate 3)

The notch math is exercised by the gate 3 contract test:
scripts/test_notch_sensitivity.py against
scripts/notch_sensitivity_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_notch_sensitivity.py

## Compliance

- Standards referenced, not reproduced: FAR-25 (US government work,
  public domain) and CS-25 (free EASA download) frame the fatigue
  substantiation context; the stress concentration, Peterson, and
  Neuber formulas above are common mechanical engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
