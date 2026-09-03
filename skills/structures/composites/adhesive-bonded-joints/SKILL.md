---
name: adhesive-bonded-joints
description: "Use when you must analyze a single-lap adhesive bonded joint between two identical adherends: compute the Volkersen shear-lag parameter from the adherend modulus and thickness and the adhesive shear modulus and thickness, the average adhesive shear stress from the load, bond width and overlap length, the peak shear stress at the bondline ends with the shear-lag correction, and the joint margin against the adhesive allowable shear stress. Produces the average and peak stresses, the peak to average concentration, the margin ratio with MS margin, and the pass or fail verdict. Trigger: adhesive bonded joint, single lap joint, shear lag parameter, adhesive shear stress, overlap length, Volkersen shear distribution, bondline peak stress, adhesive allowable."
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
  tags: [adhesive-bonded-joints, single-lap-joint, shear-lag-parameter, adhesive-shear-stress, overlap-length, volkersen-shear-distribution, bondline-peak-stress, adhesive-allowable]
  version: 0.1.0
  author: Aero Agent Skills
---

# Adhesive Bonded Joints (structures/composites/adhesive-bonded-joints)

Use when the task is analyzing a single-lap adhesive bonded joint
between two adherends of a composite or metallic structure: the
Volkersen-style shear-lag model for the bondline, the average and peak
adhesive shear stresses, and the joint margin against the adhesive
allowable. This leaf implements the shear-lag model in pure Python,
stdlib only, and reports the peak stress concentration that gates
bonded joint design in the CMH-17 composite context. It pairs with
structures/composites/composite-bolted-joints, the mechanical fastener
alternative in the same pack, and with failure-criteria and
laminate-stiffness for the adherend side of the joint.

## Domain quick reference

- Geometry: single-lap joint with overlap length L, bond width b and
  two identical adherends of thickness t and modulus E, bonded by an
  adhesive layer of thickness t_a and shear modulus G_a.
- Shear-lag parameter: beta = sqrt((G_a / t_a) * (2.0 / (E * t)))
  in 1/m. For identical adherends the 2.0/(E*t) term is the sum
  1/(E1*t1) + 1/(E2*t2) with E1 = E2 = E and t1 = t2 = t.
- Average adhesive shear stress: tau_avg = P / (b * L).
- Peak shear stress at the overlap ends (Volkersen style):
  tau_max = tau_avg * (beta*L/2) / tanh(beta*L/2). The factor
  (beta*L/2)/tanh(beta*L/2) tends to 1 as beta*L tends to 0 (uniform
  shear) and grows with beta*L, so long overlaps do not lower the peak
  below the load divided by the bond area without the concentration.
- Concentration factor: peak to average ratio
  (beta*L/2) / tanh(beta*L/2).
- Joint margin: margin_ratio = allowable / tau_max; the MS-style
  margin of safety is margin_ms = margin_ratio - 1.0. The joint passes
  when tau_max does not exceed the adhesive allowable shear stress.
- SI units throughout: N, m, Pa.
- The model is a Volkersen-style bondline shear analysis only; peel
  and adherend bending are out of scope. Peel-critical designs need a
  Goland-Reissner or FE analysis. CMH-17 frames the bonded joint data
  context; the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Fix the joint geometry and materials: load P (load_n), bond width b
   (width_m), overlap L (overlap_m), adherend E and t
   (adherend_E_pa, adherend_t_m), adhesive G_a and t_a
   (adhesive_G_pa, adhesive_t_m), and the adhesive allowable
   (allowable_shear_pa).
2. Compute the shear-lag parameter with shear_lag_beta; it measures
   how fast the shear stress peaks near the overlap ends.
3. Get the average bondline stress with avg_shear_stress = P/(b*L).
4. Apply the correction with peak_shear_stress (or scale the average
   by concentration_factor) to get the bondline peak stress.
5. Rate the joint with joint_margin against the adhesive allowable;
   the margin ratio is allowable/peak and the MS margin is that ratio
   minus one.
6. Run analyze to get the full dict {beta, tau_avg, tau_max,
   concentration, margin_ratio, margin_ms, pass} in one call.
7. Confirm the deterministic checks with the contract test
   scripts/test_adhesive_bonded_joints.py.

## Worked example

Aluminum adherends E = 70 GPa, t = 2 mm; adhesive G_a = 0.5 GPa,
t_a = 0.2 mm; bond width 25 mm; load 10 kN.

Case 1: overlap L = 25 mm, allowable 25 MPa.
- beta = sqrt((0.5e9/0.2e-3) * (2/(70e9*2e-3))) = 188.98 1/m,
  beta*L = 4.72.
- tau_avg = 10000 / (0.025 * 0.025) = 16 MPa.
- tau_max = 16 MPa * 2.3623 / tanh(2.3623) = 38.47 MPa, so the
  concentration factor is 2.40.
- margin_ratio = 25/38.47 = 0.650, margin_ms = -0.350: FAIL.

Case 2: overlap L = 10 mm, allowable 25 MPa.
- tau_avg = 10000 / (0.025 * 0.010) = 40 MPa.
- tau_max = 51.25 MPa (beta*L = 1.89, concentration 1.28): FAIL.
- The shorter overlap raises both the average and the peak stress;
  the peak exceeds the 25 mm case.

Case 3: allowable 45 MPa, L = 25 mm.
- margin_ratio = 45/38.47 = 1.170, margin_ms = +0.170: PASS.

## Verification

- Confirm shear_lag_beta(70e9, 2e-3, 0.5e9, 0.2e-3) returns 188.98 1/m
  within 0.5.
- Confirm avg_shear_stress(10000, 0.025, 0.025) returns 16 MPa and
  peak_shear_stress gives 38.47 MPa within 0.2 MPa of the 38.51 MPa
  spec anchor, with concentration 2.40 within 0.01 of 2.407.
- Confirm the 10 mm overlap peaks higher than the 25 mm overlap and
  that analyze reports pass False for the 25 MPa allowables and pass
  True for the 45 MPa allowable at L = 25 mm.
- Confirm negative load, zero or negative width and overlap, and
  non-positive modulus, thickness, adhesive shear modulus, adhesive
  thickness and allowable all raise ValueError.
- Run the contract test offline: python3
  scripts/test_adhesive_bonded_joints.py (34 tests, deterministic).

## Related leaves

- structures/composites/composite-bolted-joints: the mechanical
  fastener alternative for joining composite laminates.
- structures/composites/failure-criteria: ply-level failure checks of
  the adherends either side of the bondline.
- structures/composites/laminate-stiffness: adherend modulus and
  thickness inputs for laminate adherends.
- structures/composites/cmh17-allowables: composite material and joint
  data context behind the CMH-17 reference.
- structures/composites/sandwich-panels: skin to core bonds where the
  same adhesive allowables apply.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_adhesive_bonded_joints.py

The test covers the worked example anchors (beta 188.98, average 16
and 40 MPa, peak 38.47 and 51.25 MPa, concentration 2.40), the shorter
overlap penalty, the margin ratio and MS margin for the 25 MPa FAIL
and 45 MPa PASS cases, the uniform-shear limit for a small beta*L, the
peak over average round trip, load scaling, zero-load behaviour, the
finite concentration for long overlaps, and ValueError rejection of
negative load, zero overlap and width, zero modulus, thickness and
adhesive thickness, and non-positive allowables.

## Compliance

- Standards referenced, not reproduced: CMH-17 is a SAE-published
  composite materials handbook (sae.org/publications/cmh-17); the
  single-lap shear-lag relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
