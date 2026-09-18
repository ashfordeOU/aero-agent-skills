---
name: q7002-cvcm-measurement
description: "Compute the collected volatile condensable material of a thermal-vacuum outgassing screening run under ECSS-Q-ST-70-02C. Use when replicate specimens have been baked and each collector plate carries a pre-bake and a post-bake weighing, and the run needs a defensible CVCM per specimen plus its replicate mean. Normalises every plate gain by the mass the specimen started with, holds a gain under the balance quantification floor to a bounded sub-floor statement instead of a small positive number, rejects a plate that lost mass past the weighing noise, and reports a replicate spread outside the reproducibility band. Trigger: ecss, q-st-70-02, collected-volatile-condensable-material, micro-vcm-collector-plate, collector-plate-mass-gain, outgassing-replicate-spread, balance-quantification-floor, cvcm-percent-of-initial-specimen-mass."
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
  tags: [ecss, q-st-70-materials-outgassing-scope, q7002-cvcm-measurement, collected-volatile-condensable-material, micro-vcm-collector-plate, collector-plate-mass-gain, outgassing-replicate-spread, balance-quantification-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — CVCM Measurement (space-systems/ecss/q7002-cvcm-measurement)

Use when the task is the CVCM measurement step of the ECSS-Q-ST-70-02C
thermal-vacuum outgassing screening test — turning a set of collector
plate weighings into the condensable figure a material is screened on,
and saying whether that figure is defensible.

## Domain quick reference

- The specimen undergoes a pre-bake weighing, a vacuum bake at the
  screening temperature, and condensation of whatever leaves it onto a
  collector plate held much colder. The plate goes onto a microbalance either side of
  the bake; the difference is the condensed mass. That difference,
  not the specimen's own mass loss, is what CVCM is built from — a
  material can lose a great deal of water and condense almost nothing.
- CVCM is the condensed mass as a percentage of the mass the specimen
  started the run with. Normalising by the lost mass, or by the mass
  remaining, moves the number by the entire volatile fraction and
  produces a figure no data set will match.
- A plate difference is a quantified number only once it is several
  readability steps of the balance. Below that the difference is
  weighing scatter, and the honest report is a bounded sub-floor
  statement — a number reported to a microgram on a balance that cannot
  resolve one invites a contamination budget to be built on noise.
- A plate that is lighter once the bake finishes has lost mass of its own.
  Inside a narrow noise band that is scatter around a zero deposit;
  beyond it the plate was disturbed, contaminated before the tare or
  exchanged, and the specimen owes a re-run rather than a negative
  entry.
- The run is replicated because a single specimen cannot separate the
  material from its preparation. The reported figure is the mean, and a
  spread wider than the reproducibility band of the method says the
  replicates were not the same material state — a finding against the
  run, not something the mean absorbs.

## Workflow

1. Validate each specimen record: identifier, initial specimen mass
   inside the holder window, and non-negative before and after collector
   masses. A missing mass, a boolean, or a specimen outside the mass
   window is an input error, not a value to clamp.
2. Form the plate gain as the post-bake weighing minus the pre-bake
   weighing, keeping the sign.
3. Categorize the gain: a loss past the noise band is a plate defect, a
   gain under the quantification floor is sub-floor, anything above it
   is quantified.
4. Compute CVCM as the gain over the initial specimen mass, scaled to a
   percentage, and alongside it the quantification floor expressed in
   the same percentage units so a sub-floor result carries its own
   bound.
5. Report a value only for a quantified gain; a sub-floor specimen is
   usable but reports no figure, and a defective plate is neither.
6. Aggregate the replicates: mean and spread over the usable specimens,
   a finding when there are fewer replicates than the method requires,
   and a finding when the spread exceeds the reproducibility band by
   more than its representation tolerance.
7. Report per-specimen gains, statuses and values, the run mean, the
   spread, and every finding.

## Pitfalls

- Dividing the plate gain by the specimen's mass loss instead of its
  initial mass. That is a different quantity with a similar magnitude,
  and it silently inflates CVCM for exactly the hygroscopic materials
  the screening cares about.
- Carrying a sub-floor plate difference into a budget as a small
  positive number. The balance cannot tell it from zero, so it is a
  bound, and treating it as a measurement gives a contamination budget
  false precision in its most sensitive region.
- Averaging a negative plate value into the mean. A plate that lost
  mass measured its own damage, and letting it pull the mean down
  reports a cleaner material overall.
- Reporting the mean of a wide replicate set without the spread. Three
  specimens at 0.02, 0.02 and 0.26 percent average to a comfortable
  figure describing none of them.
- Relaxing the reproducibility band so a marginal run passes. An
  equality at the band edge is a representation question, handled by the
  named tolerance inside the comparison; the band itself stays as
  specified.

## Behavior contract (gate 3)

The specimen validation, plate-gain categorization, percentage
normalization, quantification floor, and replicate mean and spread logic
are exercised by the gate 3 contract test:
scripts/test_q7002_cvcm_measurement.py against
scripts/q7002_cvcm_measurement_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_cvcm_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
