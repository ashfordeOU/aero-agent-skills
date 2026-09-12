---
name: e1012-dd-degradation
description: "Use when determine the end-of-life parametric degradation of a
  component exposed to displacement damage dose under ECSS-E-ST-10-12C §8.6:
  select the degradation curve model (power-law, exponential, or tabular) for
  the part, compute the normalized EOL parameter value from the displacement
  damage dose and curve coefficients, apply the design margin, and verify the
  margin-adjusted EOL value meets the circuit minimum requirement. Flag any
  component whose degradation curve is not on record or whose dose falls outside
  the characterized range. Trigger: ecss, e-st-10-12c, displacement-damage,
  dd-degradation, parametric-degradation, non-ionizing, eol-parameter,
  ddd-curve, bipolar-degradation."
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
  tags: [ecss, e-st-10-12c, displacement-damage, dd-degradation, parametric-degradation, non-ionizing, eol-parameter, ddd-curve, bipolar-degradation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Effects — Displacement Damage Parametric Degradation (space-systems/ecss/e1012-dd-degradation)

Use when the task is predicting how a component's key electrical or optical
parameter degrades over mission life due to displacement damage, following
the procedure in ECSS-E-ST-10-12C §8.6. The workflow covers: selecting a
degradation curve model for the part, computing the end-of-life (EOL)
normalized parameter value, applying the required design margin, and checking
that the margin-adjusted value still satisfies the circuit minimum requirement.

## Domain quick reference

- Displacement damage (DD) is caused by non-ionizing radiation (primarily
  protons, neutrons, and heavy ions) displacing lattice atoms, degrading
  carrier lifetime, mobility, and quantum efficiency in sensitive device types
  such as solar cells, bipolar transistors, CCDs, and optocouplers.
- The severity is quantified by the displacement damage dose (DDD), typically
  expressed in MeV/g (silicon equivalent) or as equivalent fluence. DDD is
  accumulated over the mission duration at the shielded device location and
  is the primary driver for selecting points along the parametric degradation
  curve.
- Three model forms cover the range of available data: power-law
  (P_eol/P_0 = 1 − α·DDD^β), exponential (P_eol/P_0 = exp(−k·DDD)), and
  tabular (linear interpolation through manufacturer- or test-derived
  data points). The power-law and exponential forms require at least two
  curve-fit coefficients traceable to a characterized lot or irradiation
  dataset; the tabular form requires a minimum of two (DDD, fraction) pairs
  spanning the expected dose range.
- Design margin is applied multiplicatively: the margin-adjusted EOL fraction
  equals the computed degraded fraction divided by the margin factor (factor
  > 1 is conservative). ECSS-E-ST-10-12C §8.6 mandates a specific radiation
  design margin (RDM); the required value depends on the component category
  and lot characterization status — use the applicable RDM table entry rather
  than a default.
- The minimum acceptable fraction (min_fraction) is the ratio of the
  circuit-required parameter floor to the begin-of-life (BOL) nominal value;
  it must be derived from the functional requirement, not assumed.

## Workflow

1. For each component subject to a DD degradation requirement, retrieve the
   accumulated DDD at its shielded location from the environment analysis
   (ECSS-E-ST-10-12C §6 or the mission radiation environment specification).
   Record the DDD value and its units; mismatched units (e.g. MeV/g vs. p/cm²)
   are a common source of error and must be resolved before proceeding.
2. Identify the degradation curve model type (power-law, exponential, or
   tabular) that is on record for the part lot. If no characterized curve
   exists, raise a finding before continuing — applying an uncharacterized
   model produces unreliable results.
3. Compute the normalized EOL parameter value P_eol/P_0 using the selected
   model and the DDD:
   - Power-law: P_eol/P_0 = 1 − α·DDD^β (coefficients α, β from the curve fit)
   - Exponential: P_eol/P_0 = exp(−k·DDD) (coefficient k from the curve fit)
   - Tabular: linear interpolation between the two bracketing (DDD, fraction)
     data points; reject a DDD that falls outside the characterized range.
4. Apply the radiation design margin: margin-adjusted fraction =
   (P_eol/P_0) / RDM_factor. Use the margin factor from the applicable
   ECSS-E-ST-10-12C §8 RDM table entry for the component category.
5. Compare the margin-adjusted fraction to the circuit minimum fraction
   (min_fraction). If margin-adjusted fraction < min_fraction, record a
   non-compliance finding identifying the component, its DDD, the computed
   fraction, and the shortfall.
6. Aggregate findings across all components; a component with no finding on
   record passes the DD degradation gate. Components with findings require
   a design response (increased shielding, part substitution, derating
   reanalysis, or waiver).

## Pitfalls

- Omitting the margin step and comparing the raw degraded fraction to
  min_fraction — this appears to pass cases that the RDM requirement would
  reject; the margin-adjusted value must be used for the compliance check.
- Using a tabular curve's first or last data point as a default when the DDD
  falls outside the table range — extrapolation is not valid; the out-of-range
  condition must be flagged and the curve extended with additional test data
  before the assessment can proceed.
- Applying generic lot-average coefficients to a part procured from a
  different lot or process split — each lot should have its own characterized
  curve; mixing lots without explicit justification introduces unquantified
  uncertainty.
- Deriving min_fraction from the BOL measured value rather than the BOL
  nominal (or worst-case) specification — using a high measured value makes
  min_fraction appear easier to meet and conceals a potential shortfall on
  units with lower BOL values.
- Treating P_eol/P_0 < 0 (power-law with large DDD) as a negligible numerical
  artefact — a negative computed fraction signals that the dose exceeds the
  model's valid range; flag and stop rather than saturating at zero.

## Behavior contract (gate 3)

The degradation model selection, EOL fraction computation, margin application,
and compliance check logic is exercised by the gate 3 contract test:
scripts/test_e1012_dd_degradation.py against
scripts/e1012_dd_degradation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_dd_degradation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
