---
name: q7053-property-degradation-assessment
description: "Assess the property degradation a sterilization-compatibility exposure leaves behind, in the evaluation clauses of ECSS-Q-ST-70-53C. Use when pre-exposure and post-exposure measurements exist and someone has to say whether the material still meets its mechanical, physical and functional requirements. Forms each property's relative change against its own baseline, applies that property's limit in its own direction (loss-limited, gain-limited or two-sided), absorbs the measurement resolution at the limit instead of widening the limit, rolls the per-property verdicts up per category, names the governing property by utilisation, and flags a category left unmeasured. Trigger: ecss, q-st-70-53-sterilization-compatibility-scope, sterilization-property-degradation, allowable-property-change-limit, degradation-category-rollup, governing-degraded-property, unmeasured-property-category."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-property-degradation-assessment, sterilization-property-degradation, allowable-property-change-limit, degradation-category-rollup, governing-degraded-property, unmeasured-property-category]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Property Degradation Assessment (space-systems/ecss/q7053-property-degradation-assessment)

Use when the task is the evaluation step of an ECSS-Q-ST-70-53C
materials-and-hardware compatibility test — turning a table of
pre-exposure and post-exposure property values into a per-property,
per-category and overall statement of how much the sterilization
process degraded the item.

## Domain quick reference

- Degradation is a change relative to the item's own baseline, not an
  absolute value read against a datasheet. Two batches of the same
  polymer can start at different tensile strengths; the compatibility
  question is what the exposure did to each of them, so every property
  is normalised by its own pre-exposure measurement.
- The allowable change has a direction. Tensile strength and elongation
  are loss-limited: a gain is not a failure. Mass and hardness are
  usually gain-limited or two-sided, because an uptake of sterilant or a
  post-cure embrittlement both show as an increase. Applying a symmetric
  band to a loss-limited property fails items that improved.
- Properties fall into three evaluation categories — mechanical,
  physical and functional — and a compatibility statement covers all
  three. A category with no property measured is a coverage gap in the
  evaluation, not an implicit pass.
- A change smaller than the measurement resolution of the method is not
  evidence of degradation. It is absorbed by recording the property as
  resolution-limited, which is different from widening the allowable
  change: the limit stays where the specification put it.
- The property that governs is the one with the highest utilisation of
  its own allowable change, not the one with the largest raw percentage.
  A 4 % loss against a 5 % limit governs over a 20 % loss against a
  50 % limit.

## Workflow

1. Validate each property record: a positive finite baseline, a finite
   exposed value, a known category, a known direction, a positive
   allowable change and a non-negative resolution.
2. Form the relative change (exposed minus baseline, over baseline). If
   the absolute difference is within the declared resolution, record the
   change as zero and mark the property resolution-limited.
3. Convert the signed change into an adverse fraction according to the
   direction: the loss for a loss-limited property, the gain for a
   gain-limited one, the magnitude for a two-sided one. A favourable
   change has an adverse fraction of zero.
4. Compare the adverse fraction with the allowable change, absorbing
   floating-point representation error at the boundary with a named
   tolerance rather than by relaxing the allowable value.
5. Roll the records up per category: the worst utilisation in the
   category, and whether every property in it stayed within its limit.
6. Name the governing property as the highest utilisation across all
   categories, breaking an exact tie on the property name so the result
   is reproducible.
7. Report findings: each property over its limit, and each of the three
   categories that carries no measured property at all.

## Pitfalls

- Applying one blanket percentage to every property. The allowable
  change belongs to the property, and a single number across a mixed
  mechanical and functional set either passes a critical loss or fails a
  harmless one.
- Treating a favourable change as degradation. A two-sided band is a
  deliberate choice for properties where an increase is also harmful; it
  is not the safe default for a loss-limited property.
- Ranking on the raw percentage change. Utilisation against each
  property's own limit is what decides which property governs the
  compatibility statement.
- Widening the limit to swallow measurement noise. Noise is handled by
  the declared resolution of the method, applied to the measured
  difference; the limit stays as specified.
- Reading silence as a pass. A category with nothing measured leaves the
  compatibility statement incomplete and is reported as a finding in its
  own right.

## Behavior contract (gate 3)

The record validation, relative-change and resolution handling,
direction-aware adverse fraction, limit comparison, category rollup and
governing-property selection are exercised by the gate 3 contract test:
scripts/test_q7053_property_degradation_assessment.py against
scripts/q7053_property_degradation_assessment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7053_property_degradation_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
