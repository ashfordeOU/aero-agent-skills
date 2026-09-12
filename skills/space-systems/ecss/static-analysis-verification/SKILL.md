---
name: static-analysis-verification
description: "Use when verify stress, strain, and stability analysis results against Design Yield Load (DYL) and Design Ultimate Load (DUL) at all structural levels per ECSS-E-ST-32C clause 4.6.2.3: categorize each structural element into the applicable analysis tier, compute the margin of safety for every load-case and structural level, confirm stability reserve factors for buckling-critical elements, and flag any negative margin as a non-compliance finding. Apply to calculix-linear, calculix-nonlinear, and truss/beam hand-method models. Trigger: ecss, e-st-32-structures-scope, static-analysis, margin-of-safety, stress-verification, stability, buckling, calculix."
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
  tags: [ecss, e-st-32-structures-scope, static-analysis, margin-of-safety, stress-verification, stability, buckling, calculix]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Static Analysis Verification (space-systems/ecss/static-analysis-verification)

Use when the task is the static analysis verification of structural elements
per ECSS-E-ST-32C clause 4.6.2.3 — confirming that computed stress, strain,
and stability results carry non-negative margins of safety against the Design
Yield Load (DYL) and Design Ultimate Load (DUL) at every structural level,
using calculix-linear, calculix-nonlinear, or truss/beam hand methods.

## Domain quick reference

- ECSS-E-ST-32C §4.6.2.3 defines two design load levels for structural
  verification: DYL (Design Yield Load, the load level at which permanent
  deformation is the limit) and DUL (Design Ultimate Load, the load level at
  which fracture or collapse is the limit). Both levels must show positive
  margins; yield limits typically govern metallic ductile failure modes and
  ultimate limits govern brittle or stability-driven failure modes.
- Margin of Safety (MOS) is the single acceptance criterion:
  MOS = (Allowable / |Applied|) − 1. A value of 0.0 is the minimum
  acceptable; any negative value is a structural finding requiring design
  action. Allowable values come from material data sheets, design allowables
  documents, or test-derived knock-down factors.
- Stability (buckling) uses a reserve factor: RF = Critical Load / Applied
  Load; MOS = RF − 1. The critical load may come from an eigenvalue
  (linear buckling, calculix-linear), a nonlinear collapse analysis
  (calculix-nonlinear), or a closed-form buckling formula (hand method for
  columns, plates, shells). A separate MOS is required for each buckling
  mode of concern.
- Structural levels addressed by this leaf: material coupon, detail element
  (bolt, lug, weld), component (bracket, fitting, panel), sub-assembly, and
  system. Each level carries its own applied load and allowable, derived from
  the model appropriate to that level.
- Analysis methods: calculix-linear (linear FEA, stress/strain extraction per
  element), calculix-nonlinear (geometric and/or material nonlinearity for
  post-buckling or plasticity), truss hand method (axial-only members, direct
  force/area), beam hand method (bending, shear, torsion formulae per
  cross-section).

## Workflow

1. Inventory all structural elements that are in scope for the current load
   case set. Assign each element to exactly one analysis tier: FEA
   (calculix-linear or calculix-nonlinear) or hand method (truss or beam).
   Elements that span tiers (e.g. a fitting verified by both FEA and a hand
   check) receive a separate MOS record per method; the governing (lowest)
   MOS controls.
2. For each element, identify the applicable load-case pair: DYL for yield-
   critical failure modes (ductile metals under static load) and DUL for
   ultimate-critical failure modes (composites, castings, joints, any element
   with a scatter or knock-down factor applied). Both must be checked unless
   the design authority formally waives one with documented rationale.
3. Extract the applied stress or strain from the analysis output (peak
   element stress in FEA, computed section stress in hand methods) and
   retrieve the corresponding allowable from the materials/allowables database.
   The allowable must be appropriate for the load type (yield allowable for
   DYL, ultimate allowable for DUL) and must account for temperature, surface
   finish, and any applicable knock-down.
4. Compute MOS = (Allowable / |Applied|) − 1 for each element/load-type pair.
   Record the result with the element identifier, analysis method, and load
   type.
5. For buckling-critical elements (columns, thin-walled panels, shells), also
   compute the stability MOS: extract the critical load from the eigenvalue
   or hand formula, divide by the applied compressive or shear load, subtract
   one. Apply the required knock-down factor to the critical load before
   computing the reserve factor when the analysis method is linear FEA
   (eigenvalue methods overestimate critical load for imperfection-sensitive
   structures).
6. Flag every element/load-type pair where MOS < 0.0 as a structural finding.
   Flag every element that has a compressive load path but no stability check
   on record as an incomplete verification. Aggregate findings at each
   structural level; a level is not verified until all its element findings
   are resolved.

## Pitfalls

- Applying a yield allowable at DUL or an ultimate allowable at DYL — the
  allowable must match the load level; mixing them produces a non-conservative
  margin for one level and an over-conservative margin for the other.
- Omitting the knock-down factor on a linear-buckling eigenvalue — eigenvalue
  critical loads do not account for geometric imperfections and can overstate
  the true critical load by 30–50 % for thin shells; a knock-down factor
  (empirically or analytically derived) must be applied before computing the
  stability MOS.
- Recording MOS = 0.0 as a marginal pass without noting it — a zero margin
  means there is no reserve at all; the analysis authority should document it
  as a known-tight margin requiring change-control scrutiny.
- Verifying only at the system level and skipping element-level margins —
  a positive system-level load path does not guarantee every detail element
  is within allowable; each fastener, lug, and weld must carry its own MOS
  record.
- Conflating applied strain with applied stress — strain-based allowables
  (composites, coupons) require strain extraction, not stress extraction, from
  the FEA output; using one in place of the other invalidates the MOS
  arithmetic.

## Behavior contract (gate 3)

The load categorization, MOS computation, stress verification, stability
verification, and aggregated analysis-run logic are exercised by the gate 3
contract test: scripts/test_static_analysis_verification.py against
scripts/static_analysis_verification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_static_analysis_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
