---
name: q7029-toxicity-assessment
description: "Assess the offgassing load of a material or assembled article against the spacecraft maximum allowable concentrations under ECSS-Q-ST-70-29: scale each vessel concentration to the predicted cabin concentration for the flown quantity, form the ratio to its SMAC, add those ratios inside each toxicological group and take the governing group total as the T-value. Use when offgassing concentrations must become a crew-exposure verdict and a product with no published SMAC has to be surfaced rather than counted as harmless. Trigger: ecss, q-st-70-29, offgassing-toxicity-assessment, spacecraft-maximum-allowable-concentration, offgassing-t-value, offgassing-toxicological-group, offgassing-cabin-scaling, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-toxicity-assessment, offgassing-toxicity-assessment, spacecraft-maximum-allowable-concentration, offgassing-t-value, offgassing-toxicological-group, offgassing-cabin-scaling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Toxicity Assessment (space-systems/ecss/q7029-toxicity-assessment)

Use when the task is the crew-health assessment step of ECSS-Q-ST-70-29:
taking the concentrations measured on a test quantity of material and deciding
whether the quantity actually flown, offgassing into the actual cabin, keeps
the crew inside the spacecraft maximum allowable concentrations.

## Domain quick reference

- The measurement is made on a sample, the verdict is about the flight
  article. The predicted cabin concentration scales with the ratio of flown to
  tested mass and with the ratio of vessel to cabin volume, so a small test
  sample in a small vessel can stand in for a large flown mass in a large
  cabin only through that scaling, which is stated explicitly.
- The exposure limit is a duration-specific SMAC. The same compound has
  different allowable concentrations for a short contingency exposure and for
  a long mission, so the assessment names the exposure duration it is grading
  against and refuses a limit set that does not cover it.
- Individual compliance is not sufficiency. Compounds acting on the same
  target organ combine, so their concentration-to-SMAC ratios are added inside
  the toxicological group. The governing T-value is the largest group total,
  and the unit acceptance boundary sits on that governing total.
- A product with no published SMAC is not a zero contribution. It is a gap in
  the assessment and is reported as one, because reading an absent limit as an
  absent hazard is the failure mode this step exists to prevent.
- Atmospheric revitalisation changes the arithmetic. Where a scrubbing or
  trace-contaminant-control removal fraction is credited, it is applied
  transparently per compound so a reviewer can see which verdict depends on
  the removal system continuing to work.

## Workflow

1. Validate the cabin model: positive vessel volume, positive cabin volume,
   positive tested mass and positive flown mass, and an exposure duration that
   the SMAC table covers.
2. For each product, scale the measured vessel concentration to the predicted
   cabin concentration using the mass ratio and the volume ratio.
3. Apply any credited removal fraction, which must lie between zero and one
   and is recorded with the compound so the credit is visible.
4. Look up the SMAC for the compound at the stated exposure duration. A
   missing entry produces a gap record and a finding; it never produces a zero
   ratio.
5. Form the concentration-to-SMAC ratio for each product.
6. Add the ratios within each toxicological group, then take the governing
   T-value as the largest group total.
7. Compare the governing total with the unit boundary, absorbing
   representation error at the boundary with a named tolerance rather than by
   relaxing the boundary.
8. Report the governing group, the driving compounds inside it, every gap, and
   every removal credit relied on.

## Pitfalls

- Grading the vessel concentration directly against the SMAC. The vessel is
  neither the flown quantity nor the cabin volume; skipping the scaling can
  move the verdict either way and hides which assumption carried it.
- Adding every ratio into one global total regardless of target organ. That
  overstates unrelated compounds and understates nothing, but it also hides
  which group actually governs, so the driving compounds cannot be acted on.
- Treating an absent SMAC as a zero. The gap is a finding; the assessment is
  incomplete until a limit is obtained or the product is removed.
- Crediting a removal fraction without recording it. A verdict that depends on
  the trace-contaminant-control system has to say so, because the credit
  vanishes when that system is off.
- Comparing against a SMAC for a different exposure duration because it is the
  one to hand. A short-exposure limit is far higher than a long-exposure one;
  the duration is part of the limit, not a label on it.
- Rounding the governing total down onto the boundary to declare compliance.
  The comparison carries its own tolerance for representation error; the
  engineering limit is not the thing that moves.

## Behavior contract (gate 3)

The cabin-model validation, concentration scaling, removal credit, SMAC
lookup with gap reporting, ratio formation, group addition, governing-total
selection and boundary comparison are exercised by the gate 3 contract test:
scripts/test_q7029_toxicity_assessment.py against
scripts/q7029_toxicity_assessment_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7029_toxicity_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
