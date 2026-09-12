---
name: margin-of-safety-calculation
description: "Use when compute the margin of safety for a structural element per ECSS-E-ST-32C clause 4.5.16: identify the applied load at each design load level (limit, yield, ultimate), retrieve the allowable strength or stability load for each active failure mode (yield stress, ultimate stress, buckling), divide the allowable by the applied load and subtract one to obtain the margin, verify every margin is non-negative at each load level, and flag any negative margin as a structural exceedance. Trigger: ecss, e-st-32-structures-scope, margin-of-safety, structural-margin, yield-margin, ultimate-margin, buckling-margin, failure-mode, load-level."
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
  tags: [ecss, e-st-32-structures-scope, margin-of-safety, structural-margin, yield-margin, ultimate-margin, buckling-margin, failure-mode, load-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Analysis — Margin of Safety Computation (space-systems/ecss/margin-of-safety-calculation)

Use when the task is to compute the margin of safety for a structural
element across all applicable load levels and failure modes, per
ECSS-E-ST-32C clause 4.5.16.

## Domain quick reference

- MOS formula: MOS = (Allowable / Applied Load) − 1. A value of zero
  means the allowable is exactly met; positive means reserve remains;
  negative means the applied load exceeds the allowable and structural
  failure is predicted at that load level and failure mode.
- Load levels to check:
  - Design Yield Load (DYL) = Limit Load × yield safety factor
  - Design Ultimate Load (DUL) = Limit Load × ultimate safety factor
  Typical ECSS-E-ST-32C values are 1.0–1.1 for yield and 1.25 for
  ultimate, but project-specific factors from the structural
  requirements apply.
- Failure modes to assess in each analysis: yield (applied stress vs.
  yield strength allowable), ultimate (applied stress vs. ultimate
  strength allowable), and buckling (applied compressive or shear load
  vs. stability allowable derived with applicable knockdown factors).
  Fatigue is added when the element is in a cyclic load environment.
- The governing margin is the smallest MOS across all (failure mode,
  load level) combinations; it determines the critical sizing case and
  the remaining structural reserve.
- Allowables must already incorporate material-scatter factors,
  environmental knockdowns, and test-basis corrections before entering
  the MOS computation; do not apply corrections inside the formula.

## Workflow

1. Identify every active failure mode for the element (yield, ultimate,
   buckling; add fatigue for cyclic load environments). An element with
   no active failure modes cannot have a margin computed — flag it for
   analyst review before continuing.
2. Derive design loads from the limit load: multiply by the applicable
   yield safety factor to obtain DYL, and by the ultimate safety factor
   to obtain DUL. Reject a limit load that is zero or negative as an
   invalid input.
3. Retrieve the allowable for each (failure mode, load level) pair from
   the verified materials database or structural test report. Verify
   that each allowable is positive; a zero or negative allowable
   indicates a data-entry error and must not enter the computation.
4. Compute MOS for every (failure mode, load level) pair:
   MOS = allowable ÷ applied load − 1. Record each result with its
   pair label for traceability.
5. Check MOS ≥ 0 at every pair. Flag each negative margin, identifying
   the failure mode and load level responsible. A single negative margin
   at any pair constitutes a structural exceedance requiring design
   action before verification can close.
6. Identify the governing pair — the (failure mode, load level)
   combination with the smallest MOS. Report the governing margin and
   all other margins together; suppressing non-governing results hides
   latent exceedances that become critical under margin-eroding
   conditions.
7. Document the full margin set (all modes, all load levels), the
   governing case, and a structural-adequacy conclusion (all margins
   non-negative = adequate; any margin negative = inadequate) in the
   structural analysis report.

## Pitfalls

- Checking only the ultimate load level and skipping yield — yield MOS
  can be the governing case for ductile materials in stiffness-driven
  designs where the yield allowable is relatively low.
- Applying the same safety factor to the buckling allowable as to the
  strength allowable — buckling safety factors are distinct from
  strength safety factors and must follow the structural analysis
  procedure, not the strength sizing rule.
- Using nominal (unfactored) allowables when a material-scatter or
  test-basis knockdown applies — the MOS formula assumes pre-adjusted
  allowables; applying corrections inside the formula double-counts
  them.
- Reading a zero or near-zero positive MOS as fully compliant without
  flagging it for engineering review — a margin near zero has no
  practical reserve against model uncertainty and load variability;
  it should be scrutinized even when it formally passes.
- Reporting only the governing (minimum) MOS and omitting other pairs —
  non-governing negative margins can emerge as governing when load
  cases or allowables are updated; the full set must be on record.

## Behavior contract (gate 3)

The MOS computation, design-load derivation, failure-mode assessment,
and element-level aggregation logic is exercised by the gate 3 contract
test: scripts/test_margin_of_safety_calculation.py against
scripts/margin_of_safety_calculation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_margin_of_safety_calculation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
