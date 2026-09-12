---
name: bonded-joint-analysis
description: "Use when assess the structural integrity of adhesive-bonded joints per ECSS-E-ST-32C clause 4.6.2.12: apply the Volkersen shear-lag model to determine peak shear stress at overlap ends, compute peel stress from load eccentricity at the adhesive-adherend interface, derive margins of safety against adhesive shear and peel allowables, and flag any joint whose margin falls below zero for both failure modes. Trigger: ecss, e-st-32-structures-scope, adhesive-bonded-joints, peel-stress-bonded-joints, shear-lag, bonded-joint, joint-analysis, adhesive-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, adhesive-bonded-joints, peel-stress-bonded-joints, shear-lag, bonded-joint, joint-analysis, adhesive-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Bonded-Joint Analysis (space-systems/ecss/bonded-joint-analysis)

Use when the task is the adhesive-bonded-joint assessment per ECSS-E-ST-32C clause
4.6.2.12 — determining the shear stress concentration from the Volkersen shear-lag
model, computing the peel stress at the overlap ends, and comparing both against
adhesive allowables to derive margins of safety.

## Domain quick reference

- The Volkersen shear-lag model captures the non-uniform shear stress distribution
  along the bond overlap. Shear stress concentrates at both ends of the overlap and
  reaches a peak that exceeds the nominal (average) value by a factor determined by
  the shear-lag parameter ω and the overlap length l.
- For identical adherends: ω = sqrt(G_a/t_a × 2/(E × t_s)), where G_a is the
  adhesive shear modulus, t_a the adhesive thickness, E the adherend Young's
  modulus, and t_s the adherend thickness. For dissimilar adherends:
  ω = sqrt(G_a/t_a × (1/(E1 t1) + 1/(E2 t2))).
- Peak shear stress (identical adherends): τ_max = P·ω / (2·b) · coth(ω·l/2),
  where P is the applied axial load and b the bond width.
- Peel stress arises from load eccentricity in a single-lap joint. A simplified
  estimate: σ_peel = 6·P·e / (b·l²), where e = (t1+t2)/2 + t_a.
- Margin of safety for each mode: MS = allowable / applied − 1. A margin ≥ 0
  is required for compliance.
- For a symmetric double-lap joint the load eccentricity cancels and peel stress
  is zero; for scarf joints the single-lap estimate is applied conservatively.

## Workflow

1. Collect joint inputs: adherend elastic moduli and thicknesses for both adherends,
   adhesive shear modulus and tensile modulus, adhesive thickness, overlap length,
   bond width, applied axial load, joint type (single_lap / double_lap / scarf),
   and adhesive allowable shear and peel stresses. Reject any positive-definite
   parameter that is ≤ 0 or an unrecognized joint type before proceeding.
2. Compute the shear-lag parameter ω from the adherend and adhesive properties.
   Note whether the adherends are identical or dissimilar; dissimilar adherends
   shift the shear-stress peak toward the stiffer overlap end and may require a
   more refined asymmetric Volkersen treatment at project level.
3. Apply the Volkersen formula to determine τ_max at the overlap end. Record
   τ_avg = P/(b·l) and the stress concentration factor SCF = τ_max / τ_avg.
   An SCF near 1.0 indicates a very long or very stiff overlap where shear is
   nearly uniform; an SCF > 3 flags a short, compliant bond that warrants
   overlap-length optimisation.
4. Compute σ_peel from the eccentric-load model for single_lap and scarf joints.
   For double_lap, record σ_peel = 0 (symmetric geometry cancels eccentricity)
   and set the peel margin to positive infinity.
5. Derive margins of safety: MS_shear = allowable_shear / τ_max − 1 and
   MS_peel = allowable_peel / σ_peel − 1.
6. Report status PASS when both margins ≥ 0, FAIL otherwise. List every violated
   failure mode with the applied stress, allowable, and margin value.

## Pitfalls

- Using average shear stress τ_avg as the design shear stress and ignoring the
  Volkersen stress concentration: the peak shear at the overlap end can be 2–4×
  the average for short, compliant overlaps, and comparing the allowable only
  against the average produces a non-conservative margin.
- Treating double-lap joints identically to single-lap joints for peel: the load
  eccentricity cancels in a symmetric double-lap configuration and peel stress is
  markedly lower than the single-lap estimate. Using the single-lap formula for
  a double-lap joint is conservative but can reject a compliant design.
- Omitting the peel check for nominally axial loading: secondary bending from the
  overlap offset always generates peel stress in single-lap configurations even
  when the applied load is purely axial.
- Applying the adhesive bulk tensile strength as the peel allowable without
  knockdowns for surface preparation, environmental exposure, and long-duration
  creep effects. Adhesive allowables for space joints must be qualified against
  the actual substrate finish and thermal cycle regime.

## Behavior contract (gate 3)

The shear-lag parameter, peak shear stress, peel stress, margin-of-safety, and
joint pass/fail logic are exercised by the gate 3 contract test:
scripts/test_bonded_joint_analysis.py against scripts/bonded_joint_analysis_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_bonded_joint_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
