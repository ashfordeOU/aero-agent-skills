---
name: drd-fatigue-analysis
description: "Use when determine the content and completeness of a fatigue analysis report deliverable under ECSS-E-ST-32C Annex D (DRD-FA): verify the report defines all required load spectra, applies Miner's rule damage summation over rainflow-counted cycle blocks, adjusts predicted fatigue life by the required scatter factor, and confirms a positive life margin at each fatigue-critical location. Categorize each load event by spectrum type, sum fractional damage across stress amplitudes, and flag any location where the scatter-factor-adjusted life falls below the required design life. Trigger: ecss, e-st-32-structures-scope, fatigue-analysis, load-spectra, miner-rule, scatter-factor, s-n-curve, fatigue-life, damage-summation."
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
  tags: [ecss, e-st-32-structures-scope, fatigue-analysis, load-spectra, miner-rule, scatter-factor, s-n-curve, fatigue-life, damage-summation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fatigue Analysis Report (space-systems/ecss/drd-fatigue-analysis)

Use when the task is to determine whether a fatigue analysis report
satisfies the document requirement definition (DRD-FA) of
ECSS-E-ST-32C Annex D — covering load spectra definition, fatigue life
prediction via Miner's rule, scatter factor application, and life margin
verification for every fatigue-critical structural location.

## Domain quick reference

- ECSS-E-ST-32C Annex D defines the minimum content a fatigue analysis
  report must contain: the load spectrum for each critical location,
  the material S-N data and its source, the cycle-counting method, the
  damage summation approach, the scatter factor applied, and the
  resulting life margin.
- A load spectrum is the set of stress-amplitude / cycle-count pairs
  that represent the complete fatigue loading history for a location
  over the design life. Spectra are categorized as constant amplitude
  (single stress level throughout life), variable amplitude (multiple
  distinct levels), or combined (variable amplitude with rest blocks at
  zero stress). Each spectrum must be fully defined before damage is
  computed.
- Fatigue damage is accumulated by Miner's linear rule: for each
  amplitude block, the fractional damage is the applied cycle count
  divided by the allowable cycles from the S-N curve at that amplitude.
  The total damage D is the sum of all fractional contributions. D >= 1
  indicates predicted failure before the end of the design life.
- The scatter factor is a divisor applied to the predicted failure life
  to account for material variability, manufacturing scatter, and load
  uncertainty. ECSS-E-ST-32C requires a scatter factor of at least 4
  for metallic structures (higher values for composites and bonded
  joints) applied before comparing to the required design life.
- The life margin is (scatter-factor-adjusted life / required design
  life) - 1. A margin >= 0 indicates fatigue compliance; a negative
  margin must be resolved before the location is cleared.

## Workflow

1. Identify every fatigue-critical location in the structural model
   (stress concentrations, joints, interfaces, attachment holes).
   Confirm that a load spectrum has been defined for each location;
   flag any location lacking a spectrum as an open finding.
2. For each spectrum, categorize the loading type (constant amplitude,
   variable amplitude, or combined) and verify the cycle-count method
   is documented. Rainflow counting is required for variable-amplitude
   and combined spectra; range-mean counting or direct block extraction
   are acceptable for constant-amplitude histories.
3. Obtain the material S-N data applicable to each location — source,
   surface condition, stress ratio (R-value), and environment. Verify
   the data covers the stress range of the applied spectrum; extrapolation
   beyond the tested range must be flagged and justified.
4. Apply Miner's rule: for each amplitude block in the spectrum, look
   up the allowable cycle count N from the S-N curve (log-log
   interpolation), compute the fractional damage n/N, and sum across
   all blocks to obtain total damage D.
5. Invert the damage to obtain the predicted failure life in cycles
   (life = total applied cycles / D). Apply the required scatter factor
   by dividing the predicted life by the scatter factor to get the
   adjusted life.
6. Compute the life margin for each location. A positive margin clears
   the location. A negative margin, a missing spectrum, missing S-N
   data, or an undocumented scatter factor must each be raised as a
   finding in the report.
7. Aggregate findings across all fatigue-critical locations. The report
   is compliant only when every location has a non-negative margin, a
   fully documented spectrum, and a traceable scatter factor.

## Pitfalls

- Omitting rest blocks from variable-amplitude spectra — zero-amplitude
  blocks carry no damage but must be present to preserve the correct
  applied-cycle total when inverting damage to life.
- Using the same scatter factor for all material families — composites
  and bonded joints require higher scatter factors than metallic
  structures; applying the metallic value to a composite location
  understates uncertainty.
- Reporting D < 1 as "passing" without applying the scatter factor —
  the scatter factor must be applied to the predicted life, not just
  checked that D is below 1.0 at the nominal cycle count.
- Extrapolating S-N data to stress amplitudes below the fatigue limit
  without flagging the extrapolation — many metallic alloys exhibit a
  fatigue limit below which infinite life is predicted; applying the
  slope beyond that threshold overstates allowable cycles and is
  non-conservative.
- Treating a missing S-N dataset as a conservative "infinite life"
  assumption — a missing dataset is an open finding, not a
  conservative pass.

## Behavior contract (gate 3)

The spectrum categorization, S-N interpolation, Miner's rule damage
summation, scatter factor application, life margin computation, and
full-assessment workflow logic are exercised by the gate 3 contract
test: scripts/test_drd_fatigue_analysis.py against
scripts/drd_fatigue_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_fatigue_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
