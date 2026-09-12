---
name: buckling-analysis-verification
description: "Use when verify buckling onset margins for space structure panels,
  plates, shells, and columns under ECSS-E-ST-32C clause 4.6.2.10: categorize the
  structural geometry into a buckling mode (plate, shell, column, or crippling),
  select and bound a knockdown factor per HB-32-24 empirical guidance, apply the
  knockdown factor to the classical theoretical buckling load to obtain the critical
  load, compute the reserve factor against the design applied load and factor of
  safety, and flag every component with a deficient margin or an out-of-bounds
  knockdown factor. Trigger: ecss, e-st-32-structures-scope, buckling,
  knockdown-factor, plate-buckling, shell-buckling, crippling, hb-32-24,
  reserve-factor, column-buckling."
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
  tags: [ecss, e-st-32-structures-scope, buckling, knockdown-factor, plate-buckling, shell-buckling, crippling, hb-32-24, reserve-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Buckling Onset Analysis Verification (space-systems/ecss/buckling-analysis-verification)

Use when the task is the buckling onset analysis verification for a structural
component under ECSS-E-ST-32C clause 4.6.2.10 -- categorizing the geometry
into a buckling mode, bounding and validating the knockdown factor per HB-32-24
empirical guidance, computing the critical buckling load, and checking the
reserve factor against the applied load and factor of safety.

## Domain quick reference

- Clause 4.6.2.10 requires that classical theoretical buckling loads be reduced
  by empirically derived knockdown factors before being compared to applied
  loads. Knockdown factors account for geometric imperfections, boundary-
  condition uncertainties, and load-introduction effects that cause real
  structures to buckle below the classical prediction. The HB-32-24 handbook
  provides empirical data and certified correlations for selecting knockdown
  factors by structural form.
- Structural geometry maps to one of four buckling modes: plate (flat panels and
  stiffened panels), shell (cylindrical or conical shells, most imperfection-
  sensitive), column (slender members under axial compression), and crippling
  (local flange or web buckling in thin-walled open sections such as angles,
  channels, Z-sections, and hat sections). Each mode carries a distinct
  knockdown factor range; shells carry the widest range and the lowest lower
  bound because of their acute sensitivity to imperfections.
- The critical buckling load is the product of the classical theoretical
  buckling load and the knockdown factor. The reserve factor is the ratio of
  the critical load to the applied load multiplied by the factor of safety. A
  reserve factor below 1.0 indicates a deficient margin; clause 4.6.2.10
  compliance requires the reserve factor to be at least 1.0 for every
  buckling-critical load case.
- HB-32-24 common-knowledge knockdown factor bounds by mode: plate [0.5, 1.0],
  shell [0.1, 1.0], column [0.5, 1.0], crippling [0.3, 1.0]. A selected
  knockdown factor below the mode's lower bound is outside the range covered
  by the HB-32-24 empirical dataset and must be flagged for additional
  justification.

## Workflow

1. Identify every buckling-critical structural component and record its geometry
   type, classical theoretical buckling load, analyst-selected knockdown factor,
   design applied load, and factor of safety.
2. For each component, map its geometry type to a buckling mode: flat_plate and
   stiffened_panel → plate; cylindrical_shell and conical_shell → shell; column
   and beam_column → column; angle_section, channel_section, z_section, and
   hat_section → crippling. Reject an unrecognized geometry type before the
   assessment proceeds.
3. Retrieve the HB-32-24 knockdown factor bounds for the identified mode and
   confirm the selected knockdown factor falls within those bounds. Flag any
   factor below the lower bound as requiring additional justification; a factor
   above 1.0 is physically inadmissible.
4. Compute the critical buckling load: classical theoretical buckling load
   multiplied by the knockdown factor.
5. Compute the reserve factor: critical buckling load divided by the product of
   the applied load and the factor of safety.
6. Evaluate the buckling status: reserve factor ≥ 1.0 is adequate; below 1.0
   is margin-deficient. Record a violation for any deficient component.
7. Aggregate all violations (knockdown-factor out of bounds, margin deficient)
   per component. A component is buckling-compliant only when its violation
   list is empty.

## Pitfalls

- Applying the classical theoretical buckling load directly as the critical
  load without a knockdown factor -- this can overestimate the true onset load
  by factors of 2 to 10 for thin-walled shells and leads to unconservative
  margins that are not compliant with clause 4.6.2.10.
- Using a single knockdown factor range across all buckling modes -- the lower
  bound for shells (0.1) is far below that for plates (0.5) and columns (0.5),
  and applying the plate range to a shell geometry understates the allowable
  knockdown and artificially constrains the design margin.
- Reading a reserve factor of exactly 1.0 as a strong positive result -- it is
  the minimum acceptable value; any load uncertainty, load redistribution, or
  analysis approximation that erodes this margin by any amount produces a
  non-compliant result.
- Omitting the knockdown factor validation step because the selected value
  appears conservative -- a value outside the HB-32-24 empirical dataset (even
  one lower than the lower bound) lacks certified test correlation and must be
  flagged regardless of whether it makes the reserve factor larger.

## Behavior contract (gate 3)

The geometry categorization, knockdown factor bounding and validation, critical
load computation, reserve factor calculation, and component review logic is
exercised by the gate 3 contract test:
scripts/test_buckling_analysis_verification.py against
scripts/buckling_analysis_verification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_buckling_analysis_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
