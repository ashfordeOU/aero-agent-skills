---
name: convergence-verification
description: "Use when you must verify that a CFD or structural mesh sequence has converged: compute the observed order of accuracy from the finest, medium, and coarse solutions, apply Richardson extrapolation to estimate the exact solution, and report the grid convergence index (GCI) with the 1.25 safety factor. Produces the observed order, the extrapolated value, the GCI, and a monotone converged, oscillatory, or diverging verdict that gate whether the discretization error is acceptable for the assessment. Trigger: richardson extrapolation, grid convergence index, gci, observed order, refinement ratio, discretization error, mesh refinement study."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [convergence-verification, richardson-extrapolation, grid-convergence-index, gci, observed-order, discretization-error, refinement-ratio, richardson, extrapolation, oscillatory]
  version: 0.1.0
  author: Aero Agent Skills
---
# Convergence Verification (cross-cutting/numerics/convergence-verification)

Use when the task is verifying that a CFD or structural mesh
sequence has converged: computing the observed order of accuracy,
Richardson extrapolation of the exact solution, and the grid
convergence index (GCI) with its safety factor.

## Domain quick reference

- Three solutions from a systematic refinement family: f1 finest,
  f2 medium, f3 coarse, refinement ratio r = h_coarse / h_fine > 1.
- Observed order p = ln((f3-f2)/(f2-f1)) / ln(r); valid only for a
  monotone sequence, ratio (f3-f2)/(f2-f1) > 0.
- Richardson extrapolation f_exact = f1 + (f1 - f2) / (r**p - 1).
- Grid convergence index gci = Fs * abs((f1 - f2) / f1) / (r**p - 1),
  safety factor Fs = 1.25 for three-grid studies.
- Verdict from ratio (f3-f2)/(f2-f1): monotone converged when ratio
  > 0, oscillatory when ratio < 0, diverging when abs(ratio) > 1
  (diverging takes precedence on the negative branch).
- f1, f2, f3 in any consistent solution units; r, p, and gci are
  dimensionless; gci is a fraction, not a percentage.

## Workflow

1. Collect f1, f2, f3 from the three refinement levels and the
   constant refinement ratio r.
2. Compute the observed order with observed_order(f1, f2, f3, r).
3. Estimate the exact solution with richardson_extrapolation(f1, f2, r, p).
4. Bound the discretization error with grid_convergence_index(f1, f2, r, p, fs=1.25).
5. Classify the study with convergence_verdict(f1, f2, f3, r) and
   decide whether the finest mesh is adequate for the assessment.

## Pitfalls

- Calling the study converged on a non-monotone sequence:
  observed_order raises ValueError when the ratio (f3-f2)/(f2-f1)
  is not positive.
- Using a refinement ratio r <= 1: the observed order is undefined;
  r must exceed 1.
- Reporting the GCI as a percentage when the function returns a
  fraction.
- Trusting the extrapolated value when the observed order is near
  zero: r**p - 1 collapses and the estimate is garbage.
- Treating an oscillatory or diverging sequence as quantifiable:
  order, extrapolated value, and GCI are None when the sequence is
  not monotone.

## Behavior contract (gate 3)

The grid convergence logic is exercised by the gate 3 contract test:
scripts/test_convergence_verification.py against
scripts/convergence_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_convergence_verification.py

## Compliance

- NACA Report 824 is US government work (public domain); summary
  and physics values only, per standards-map.yaml. Convergence
  verification is generic numerical methodology: Richardson
  extrapolation and the GCI are standard discretization error
  estimation, not RTCA or SAE content.
- compliance: STANDARDS-REF, gated: false.
