---
name: welded-joint-analysis
description: "Use when assess welded joints under ECSS-E-ST-32C clause 4.6.2.14: categorize each weld by quality class (WQ1, WQ2, WQ3) to derive the joint efficiency factor, compute the allowable normal and shear stresses from the parent material ultimate strength reduced by that efficiency and the applicable safety factor, calculate the effective weld throat area from the joint geometry (butt or fillet weld), determine the applied normal and shear stress components from the design load case, evaluate the margin of safety for the normal mode, shear mode, and combined von Mises criterion, and flag any negative margin as a finding requiring redesign or re-categorization at a higher quality class. Trigger: ecss, e-st-32-structures-scope, welded-joint, weld-quality-class, joint-efficiency, allowable-stress, margin-of-safety, fillet-weld, butt-weld."
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
  tags: [ecss, e-st-32-structures-scope, welded-joint, weld-quality-class, joint-efficiency, allowable-stress, fillet-weld, butt-weld]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Welded-Joint Analysis (space-systems/ecss/welded-joint-analysis)

Use when the task is the structural assessment of a welded joint under
ECSS-E-ST-32C clause 4.6.2.14 — categorizing the weld by quality class,
deriving allowable stresses from the parent material and joint efficiency,
computing the effective weld area from geometry, and evaluating margins of
safety in the normal, shear, and combined stress modes.

## Domain quick reference

- ECSS-E-ST-32C clause 4.6.2.14 defines three weld quality classes that
  drive the joint efficiency factor applied to the parent material's
  ultimate tensile strength:
  - **WQ1** — premium quality; full volumetric inspection (radiography or
    ultrasonic) on every weld; joint efficiency η = 1.00.
  - **WQ2** — standard quality; spot volumetric inspection (sampled);
    joint efficiency η = 0.85.
  - **WQ3** — basic quality; visual and surface examination only;
    joint efficiency η = 0.70.
- Two weld geometry types are addressed:
  - **Butt weld** (full penetration): effective throat equals the plate
    thickness; weld area = throat × weld length.
  - **Fillet weld**: effective throat = 0.707 × leg size; weld area =
    0.707 × leg size × weld length.
- Allowable normal stress: σ_allow = (F_tu × η) / SF, where F_tu is the
  parent material ultimate tensile strength and SF is the applicable
  structural safety factor.
- Allowable shear stress: τ_allow = 0.577 × σ_allow (von Mises shear
  yield criterion).
- Applied stresses from load case: σ = N / A_weld (normal), τ = V / A_weld
  (shear), where N and V are the normal and shear resultant loads.
- Margin of safety for each mode: MoS = (allowable / applied) − 1.
- Combined criterion uses the von Mises interaction ratio
  R = √[(σ/σ_allow)² + (τ/τ_allow)²]; compliant when R ≤ 1.0;
  MoS_combined = (1/R) − 1.

## Workflow

1. Receive the joint definition: weld type (butt or fillet), weld quality
   class (WQ1/WQ2/WQ3), weld length, throat dimension (butt) or leg size
   (fillet), parent material ultimate tensile strength, structural safety
   factor, and design load case (normal force N and shear force V).
   Reject any input outside these options before proceeding.
2. Categorize the weld by quality class and retrieve the associated joint
   efficiency factor η. A quality class not in {WQ1, WQ2, WQ3} is an
   invalid input — raise an error and stop.
3. Compute the effective weld throat area: for a butt weld, A = length ×
   throat; for a fillet weld, A = length × 0.707 × leg. Reject zero or
   negative geometry.
4. Derive allowable stresses: σ_allow = (F_tu × η) / SF and
   τ_allow = 0.577 × σ_allow. Reject a safety factor ≤ 0.
5. Compute applied stresses: σ = N / A_weld and τ = V / A_weld. When
   both components are zero, the joint trivially passes; record MoS = ∞.
6. Evaluate margins of safety for:
   - Normal mode: MoS_n = (σ_allow / σ) − 1 (skip if σ = 0).
   - Shear mode: MoS_s = (τ_allow / τ) − 1 (skip if τ = 0).
   - Combined mode: R = √[(σ/σ_allow)² + (τ/τ_allow)²];
     MoS_c = (1/R) − 1.
7. Flag any MoS < 0 as a failure finding. A joint is compliant only when
   all applicable margins are ≥ 0.
8. Return the full result: quality class, η, A_weld, σ_allow, τ_allow,
   σ_applied, τ_applied, MoS_n, MoS_s, MoS_c, and overall compliance.

## Pitfalls

- Applying the parent material allowable directly without the quality class
  efficiency reduction overstates the weld capacity and produces
  non-conservative margins.
- Using the leg size as the fillet weld throat instead of 0.707 × leg
  overstates the effective area by ~41 % and produces non-conservative
  results for fillet welds.
- Treating a zero shear or zero normal component as a passing margin
  rather than an inapplicable check — only the combined criterion is
  always applicable when at least one component is non-zero.
- Confusing the safety factor role: SF divides the allowable (entering
  after efficiency), not the applied load — applying it twice or to the
  wrong side of the inequality flips the sign of the error.
- Selecting WQ3 for structural primary joints without verifying that the
  inspection plan actually specifies only visual examination — a mismatch
  between the declared quality class and the actual inspection regime
  invalidates the efficiency factor.

## Behavior contract (gate 3)

The quality-class categorization, throat-area, allowable-stress,
applied-stress, margin-of-safety, and combined-criterion logic is
exercised by the gate 3 contract test:
scripts/test_welded_joint_analysis.py against
scripts/welded_joint_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_welded_joint_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
