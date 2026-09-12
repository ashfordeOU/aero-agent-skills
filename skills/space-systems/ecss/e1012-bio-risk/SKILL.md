---
name: e1012-bio-risk
description: "Use when run a radiobiological risk assessment for a crewed or uncrewed space mission under ECSS-E-ST-10C §11.5: estimate excess cancer risk from accumulated effective dose, categorize each uncertainty source (dosimetry, biological, model, epidemiological, transport) per the §11.5 uncertainty taxonomy, derive risk bounds using the compound uncertainty factor, and determine whether the risk estimate meets mission-acceptable limits. Trigger: ecss, e-st-10-system-scope, radiobiology, space-radiation-risk, effective-dose, cancer-risk, uncertainty-analysis, dose-response."
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
  tags: [ecss, e-st-10-system-scope, radiobiology, space-radiation-risk, effective-dose, cancer-risk, uncertainty-analysis, dose-response]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Radiobiological Risk Assessment (space-systems/ecss/e1012-bio-risk)

Use when the task is the radiobiological risk assessment of ECSS-E-ST-10C §11.5 —
estimating excess cancer risk from mission radiation exposure, categorizing each
uncertainty source by type, deriving risk bounds from the compound uncertainty
factor, and checking the estimate against mission acceptance criteria.

## Domain quick reference

- §11.5 structures the risk estimate around three quantities: the accumulated
  effective dose (weighted sum of organ equivalent doses using ICRP Publication 103
  tissue weighting factors), the risk coefficient that converts effective dose to
  excess lifetime cancer probability, and the uncertainty envelope applied to the
  point estimate.
- Uncertainty sources are grouped into five categories per the §11.5 taxonomy:
  DOSIMETRY (detector calibration, flux measurement), BIOLOGY (radiation biological
  effectiveness, DNA repair), MODEL (dose-response extrapolation, risk projection),
  EPIDEMIOLOGY (population transfer, baseline cancer rate), and TRANSPORT (shielding
  transport, geomagnetic cutoff). Each category carries a multiplicative uncertainty
  factor; the compound factor is the product of all applicable category factors.
- The risk bounds are derived symmetrically in log space: upper bound = point
  estimate × compound factor, lower bound = point estimate ÷ compound factor. The
  assessment is compliant when the upper bound lies at or below the mission
  acceptable risk limit; the upper bound drives the determination, not the point
  estimate alone.
- Standard ICRP Publication 103 tissue weighting factors sum to 1.0 across the
  reference organ set. An effective dose computed from a partial organ set
  underestimates true effective dose and must be flagged as incomplete if significant
  doses to unrecorded organs are expected.

## Workflow

1. Collect equivalent doses for each irradiated organ or tissue from the mission
   dose assessment and verify that every dose value is non-negative and that the
   tissue name appears in the ICRP reference organ set.
2. Compute effective dose by multiplying each organ's equivalent dose by the
   corresponding ICRP tissue weighting factor and summing over all organs in the
   input set; note whether the input covers the full reference organ set.
3. Apply the risk coefficient (default: nominal BEIR VII-aligned value for a
   mixed-sex reference population, 5.0 × 10⁻⁴ per mSv) to the effective dose to
   obtain the point excess cancer risk estimate.
4. Identify every applicable uncertainty source for the mission and map each one to
   its category (DOSIMETRY, BIOLOGY, MODEL, EPIDEMIOLOGY, or TRANSPORT); reject any
   source label not in the recognised taxonomy.
5. Compute the compound uncertainty factor as the product of the individual category
   factors for all categories represented in the source list.
6. Derive the lower and upper risk bounds using the compound factor:
   upper = point × factor, lower = point ÷ factor.
7. Compare the upper bound against the mission acceptable risk limit; record
   compliant when upper bound ≤ limit and the point estimate ≤ limit;
   record non-compliant otherwise.
8. Report all intermediate quantities (effective dose, point risk, lower bound,
   upper bound, compound factor, compliance status) for traceability.

## Pitfalls

- Using the point risk estimate directly against the limit without applying the
  uncertainty envelope understates the assessed risk; the upper bound of the
  uncertainty range is the controlling quantity.
- Treating a partial organ-dose set as a complete effective-dose computation —
  organs absent from the input are treated as zero dose, which silently
  underestimates effective dose when significant exposure to unrecorded organs is
  expected.
- Conflating different uncertainty categories into a single aggregate factor without
  tracking which source drove the spread; this prevents identification of which
  category dominates risk bound width for shielding or mission-duration trade studies.
- Using a population-specific risk coefficient (for example a single-sex value) on a
  crew with a different demographic profile — the nominal mixed-sex coefficient is
  conservative for male-only crews but non-conservative for female-heavy crews
  relative to female-specific values.

## Behavior contract (gate 3)

The effective-dose computation, risk estimation, uncertainty categorization,
risk-bounds derivation, and mission-limit compliance check are exercised by the
gate 3 contract test: scripts/test_e1012_bio_risk.py against
scripts/e1012_bio_risk_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bio_risk.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
