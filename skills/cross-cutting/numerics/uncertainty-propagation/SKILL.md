---
name: uncertainty-propagation
description: "Use when you must propagate measurement uncertainties through a calculation with the GUM first order law: combine the sensitivity coefficients and standard uncertainties of the independent inputs into the combined standard uncertainty, expand it with a coverage factor, and identify the dominant contribution. Produces the combined standard uncertainty, the expanded uncertainty, and the per input variance shares that gate the measurement uncertainty budget. Trigger: uncertainty propagation, combined standard uncertainty, expanded uncertainty, coverage factor, sensitivity coefficient, GUM, variance contribution, dominant uncertainty."
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
  tags: [uncertainty-propagation, combined-standard-uncertainty, expanded-uncertainty, coverage-factor, sensitivity-coefficient, gum, variance-contribution, dominant-contribution, uncertainty-budget]
  version: 0.1.0
  author: AeroSkills
---
# Uncertainty Propagation (cross-cutting/numerics/uncertainty-propagation)

Use when the task is propagating measurement uncertainties through a
calculation with the GUM first order law: combined standard
uncertainty, expanded uncertainty, and the dominant variance
contribution.

## Domain quick reference

- Input i has sensitivity coefficient s_i = df/dx_i at the operating
  point and standard uncertainty u_i (one sigma).
- The GUM first order law for independent inputs gives the combined
  standard uncertainty u_c = sqrt(sum_i (s_i * u_i)**2); the term
  (s_i * u_i)**2 is the variance contribution of input i.
- The expanded uncertainty is U = k * u_c with coverage factor k,
  2.0 by convention (roughly 95 percent coverage for a normal
  distribution).
- The percent share of input i is 100 * (s_i * u_i)**2 / u_c**2;
  shares sum to 100.
- The first order law assumes independent inputs; correlated inputs
  need the full covariance form, which this logic does not implement.

## Workflow

1. Collect the sensitivity coefficients and standard uncertainties
   for each independent input.
2. Combine them with combined_standard_uncertainty(sensitivities,
   uncertainties).
3. Expand with expanded_uncertainty(combined, k=2.0).
4. Rank the contributors with uncertainty_contributions(...) and
   report the dominant one with dominant_contribution(...) before
   gating the uncertainty budget.

## Pitfalls

- Applying the first order law to correlated inputs: the independent
  sum underestimates or overestimates the combined uncertainty; the
  covariance form is required.
- Negative uncertainties: physically meaningless; the logic raises
  ValueError.
- Mixing unit systems: sensitivities and uncertainties must share a
  consistent unit system; no conversion is performed.
- Using a non-positive coverage factor: the logic raises ValueError.
- Reporting the largest sensitivity instead of the largest variance
  contribution: the contribution weights the sensitivity by the
  uncertainty, so ranking by contribution is the correct ordering.

## Behavior contract (gate 3)

The propagation, expansion, and contribution logic is exercised by
the gate 3 contract test: scripts/test_uncertainty_propagation.py
against scripts/uncertainty_propagation_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_uncertainty_propagation.py

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. The GUM (JCGM 100) first order law
  is generic measurement methodology, not RTCA or SAE content;
  summary and formulas only.
- compliance: STANDARDS-REF, gated: false.
