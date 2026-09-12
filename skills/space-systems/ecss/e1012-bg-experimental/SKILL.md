---
name: e1012-bg-experimental
description: "Use when assess background radiation using experimental irradiation
  data under ECSS-E-ST-10C §10.4.8: validate each experimental flux or dose-rate
  record for completeness and uncertainty bounds, compare measurements against the
  applicable reference environment model, determine whether experimental data
  supersede or supplement the standard model estimate, compute the combined
  background assessment value and its uncertainty envelope, and confirm that data
  provenance is recorded in the assessment record. Trigger: ecss,
  e-st-10-system-scope, experimental-irradiation, background-assessment,
  radiation-flux, dose-rate, environment-model, uncertainty-bounds."
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
  tags: [ecss, e-st-10-system-scope, experimental-irradiation, background-assessment, radiation-flux, dose-rate, environment-model, uncertainty-bounds]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Experimental Irradiation Data in Background Assessments (space-systems/ecss/e1012-bg-experimental)

Use when the task is to incorporate experimental irradiation measurements into a
background radiation assessment under ECSS-E-ST-10C §10.4.8 -- validating
the experimental records, comparing them against the applicable reference
environment model, deciding whether they supersede or supplement that model,
and computing a combined background value with a propagated uncertainty envelope.

## Domain quick reference

- ECSS-E-ST-10C §10.4.8 permits experimental irradiation data (in-orbit
  measurements, ground-based irradiation campaign results, or dedicated
  flight-instrument datasets) to replace or supplement a standard environment
  model (e.g. AP8, AE8, CREME96) in the background dose or flux assessment,
  provided the data meet quality and provenance requirements.
- An experimental record must specify: the originating source and instrument,
  the particle type (proton, electron, heavy ion, or gamma), the radiometric
  quantity (flux, fluence, dose rate, or dose), the measured value with a
  relative uncertainty in percent, the measurement duration, a quality flag
  (valid, suspect, or invalid), and a provenance description linking the data
  to a documented dataset or campaign report.
- Supersedure of the reference model is granted only when all three criteria
  hold: quality flag is "valid", relative uncertainty does not exceed
  MAX_SUPERSEDE_UNCERTAINTY_PCT (20 %), and the signed offset from the reference
  model stays within ±MAX_OFFSET_FOR_SUPERSEDE_PCT (50 %). Data that pass
  quality but fail an uncertainty or offset criterion supplement the model
  through an inverse-variance weighted combination rather than replacing it.
- The combined background value is derived by inverse-variance weighting of
  the experimental and model estimates on their absolute uncertainties; the
  reference model carries a default assumed uncertainty of
  DEFAULT_MODEL_UNCERTAINTY_PCT (30 %) when no instrument-specific value is
  on record.
- Every experimental record must carry a non-empty source identifier, a
  non-empty provenance description, and a positive measurement duration.
  A record with incomplete provenance is flagged in the assessment output
  even when its numerical values are otherwise compliant.

## Workflow

1. Collect all experimental irradiation records to be incorporated and validate
   each one: check that all required fields are present, that particle type and
   radiometric quantity are drawn from the permitted vocabularies, that the
   measured value is non-negative, that relative uncertainty is in (0, 100] %,
   that measurement duration is positive, that the quality flag is one of
   {"valid", "suspect", "invalid"}, and that source and provenance are
   non-empty strings. Reject any record that fails validation before it
   enters the assessment.
2. Collect reference environment model records for the same particle-type and
   quantity combinations. Validate each reference record: positive value,
   non-empty model name, and compatible particle type and quantity vocabulary.
   Flag any experimental record whose (particle_type, quantity) pair has no
   matching reference entry -- it will be carried forward with its own value
   as the combined result and an explicit "no reference model" issue flag.
3. For each matched (particle_type, quantity) pair, compute the signed
   percentage offset of the experimental value from the reference model value:
   (experimental − reference) / reference × 100. This offset quantifies
   systematic agreement and is a prerequisite for the supersedure decision.
4. Apply the supersedure criteria to each pair: the experimental data supersede
   the model only when quality_flag is "valid", uncertainty_pct ≤ 20 %, and
   |offset_pct| ≤ 50 %. Record the boolean outcome and the rationale string
   for the assessment report.
5. Compute the combined background assessment value and uncertainty:
   - If supersedure holds, the combined value and uncertainty equal the
     experimental value and uncertainty directly.
   - Otherwise, apply inverse-variance weighting using absolute uncertainties
     (sigma_i = relative_unc_i × value_i); the combined value is the
     weighted mean and the combined uncertainty is propagated from the total
     inverse variance. The reference model uncertainty defaults to 30 % when
     not otherwise specified.
6. For each record, confirm provenance completeness: source, provenance
   description, and positive measurement duration must all be present. A
   record that passes numerical validation but has incomplete provenance
   receives an explicit provenance issue flag in the output; it is not silently
   treated as compliant.
7. Aggregate the results per (particle_type, quantity) pair into the
   assessment report: experimental and reference values, model name, offset,
   supersedure flag and rationale, combined value and uncertainty, provenance
   status, and any open issues. The pair is fully compliant only when the
   issues list is empty.

## Pitfalls

- Using experimental data that carry a "suspect" or "invalid" quality flag
  directly in the assessment without applying the supersedure gate -- only
  "valid" data may supersede a reference model; suspect or invalid data
  must never replace the model estimate unchecked.
- Treating an offset within ±50 % of the reference model as automatically
  acceptable without also checking uncertainty -- a high-uncertainty dataset
  with a plausible offset does not supersede the model; it supplements it
  through the weighted combination.
- Applying the reference model value as zero uncertainty when computing the
  weighted average -- environment models carry inherent uncertainty (typically
  30 % or more); collapsing that to zero would artificially bias the combined
  result toward the experimental value even when the experimental uncertainty
  is large.
- Accepting a record as provenance-complete because it passes numerical
  validation without separately confirming that a non-empty provenance
  description and source identifier are on record -- incomplete provenance
  is itself a finding under §10.4.8, not a silent pass.
- Comparing experimental and reference records across different particle types
  or radiometric quantities -- offset computation requires an identical
  (particle_type, quantity) pair; mismatched pairs must be rejected before
  any numerical comparison is attempted.

## Behavior contract (gate 3)

The validation, offset computation, supersedure decision, combined assessment,
provenance check, and full-run orchestration logic are exercised by the gate 3
contract test:
scripts/test_e1012_bg_experimental.py against
scripts/e1012_bg_experimental_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bg_experimental.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
