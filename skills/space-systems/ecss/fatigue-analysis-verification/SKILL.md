---
name: fatigue-analysis-verification
description: "Use when verify fatigue life compliance of a structural component under ECSS-E-ST-32C clause 4.6.2.8: validate the applied load spectrum (stress range and cycle count per block), select the S-N curve for the material, compute Miner's cumulative damage sum across all spectrum blocks, apply the required scatter factor, and determine whether design damage remains below unity. Covers load spectra definition, S-N curve parameters, damage summation under the Palmgren-Miner rule, scatter factor margins, and endurance limit handling. Trigger: ecss, e-st-32-structures-scope, fatigue, s-n-curve, miner-rule, load-spectrum, scatter-factor, damage-summation."
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
  tags: [ecss, e-st-32-structures-scope, fatigue, s-n-curve, miner-rule, load-spectrum, scatter-factor, damage-summation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fatigue Analysis Verification (space-systems/ecss/fatigue-analysis-verification)

Use when the task is to verify fatigue life compliance of a structural
component per ECSS-E-ST-32C clause 4.6.2.8 — building and validating
the load spectrum, applying the S-N curve and Palmgren-Miner damage
summation, imposing the required scatter factor, and confirming that
the resulting design damage is below the acceptance threshold.

## Domain quick reference

- ECSS-E-ST-32C clause 4.6.2.8 requires that fatigue life be assessed
  against a defined load spectrum representing the full mission load
  history. The spectrum is expressed as a set of stress-range/cycle-count
  blocks covering all load events (launch, deployment, on-orbit, re-entry
  where applicable).
- The S-N curve (stress versus cycles to failure) for the chosen material
  is the damage model. The power-law form `N_f = N_ref × (S_ref / S)^(1/b)`
  relates an applied stress range S to the number of cycles to failure N_f,
  anchored at a reference point (S_ref, N_ref) with exponent b. Some
  materials exhibit an endurance limit below which no fatigue damage
  accumulates; stress blocks at or below that limit contribute zero damage.
- Miner's rule (Palmgren-Miner linear damage accumulation) sums partial
  damage over every spectrum block: `D = Σ (n_i / N_f_i)`. A value D = 1
  corresponds to fatigue failure at the raw (unscattered) level.
- ECSS mandates a scatter factor k_s applied to raw Miner damage to account
  for material scatter, surface condition, and load uncertainty. The
  factored design damage is `D_design = k_s × D`. A component passes
  fatigue verification when `D_design < 1.0`; the margin on life is
  `MoL = 1 / D_design − 1` (positive = passing).
- Typical ECSS scatter factors for space primary structure range from 4
  (metallic, well-characterized) to 8 or higher (composite, limited coupon
  data). The governing value is set by the project structural margin
  philosophy, not by this leaf.

## Workflow

1. Assemble and validate the load spectrum: list every stress-range/
   cycle-count block covering the complete mission load history. Reject any
   block with a non-positive stress range or a non-positive cycle count
   before proceeding.
2. Identify the material and retrieve its S-N curve parameters (S_ref,
   N_ref, exponent b). If the material has an endurance limit, record it.
   Reject an unrecognized material identifier before computing damage.
3. For each spectrum block, compute cycles to failure N_f_i using the
   power-law S-N model. If the block stress range is at or below the
   endurance limit, set N_f_i = ∞ (zero contribution to damage).
4. Accumulate Miner's rule damage: sum `n_i / N_f_i` over all blocks that
   have finite N_f_i. Record the raw damage D.
5. Apply the scatter factor: compute `D_design = k_s × D`. Verify that
   k_s is positive (a zero or negative scatter factor is a data error).
6. Evaluate the pass/fail criterion: the component passes fatigue
   verification when `D_design < 1.0`. Compute the margin on life
   `MoL = 1 / D_design − 1`; a positive margin confirms compliance, a
   negative margin indicates the design life budget is exceeded.
7. Report raw damage, design damage, scatter factor, pass/fail status,
   and margin on life for each component analysed.

## Pitfalls

- Omitting spectrum blocks from the load history: every load event that
  contributes stress cycles must be included. Missing blocks understate
  raw damage and produce unconservative results.
- Treating endurance limit as a hard cutoff without confirming the
  material database: some materials (aluminium alloys) have no true
  endurance limit; applying an endurance limit where none exists removes
  real damage contributions.
- Confusing the scatter factor direction: the scatter factor multiplies
  the damage (reduces allowable life), not the S-N curve stress; applying
  it in the wrong direction overstates life by k_s^2 or more.
- Using raw damage D = 1.0 as the acceptance criterion without the scatter
  factor: ECSS requires the factored design damage to remain below unity,
  not the unfactored Miner sum.
- Applying a single scatter factor across materials with fundamentally
  different scatter bands: composites and welded joints require higher
  scatter factors than base-metal metallic coupons; mixing them
  underestimates risk for the higher-scatter items.

## Behavior contract (gate 3)

The load spectrum validation, S-N curve lookup, Miner damage accumulation,
scatter factor application, and pass/fail logic are exercised by the gate 3
contract test: scripts/test_fatigue_analysis_verification.py against
scripts/fatigue_analysis_verification_logic.py (stdlib unittest, offline).
Run:

    python3 scripts/test_fatigue_analysis_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS-E-ST-32C §4.6.2.8 (Fatigue analysis).
