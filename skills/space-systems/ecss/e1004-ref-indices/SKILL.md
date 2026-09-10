---
name: e1004-ref-indices
description: "Use when selecting solar-activity and albedo/IR reference data for a space-environment case under ECSS-E-ST-10-04C Annex F (informative): determine the solar-cycle activity level (minimum/mean/maximum) that a case should assume from its F10.7 solar-flux value, look up the reference index set (F10.7 flux, sunspot number) and the Earth albedo/IR flux references for that level, validate a proposed index value against the dataset's valid range, interpolate an index across the solar-cycle phase when a cycle-phase fraction is given, and produce the combined solar-index plus albedo/IR reference record that a thermal or radiation case must cite. Trigger: ecss, e-st-10-04c, annex f, solar index, f10.7, sunspot number, solar cycle, albedo, earth ir, reference data, activity level, thermal case."
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
  tags: [ecss, e-st-10-04c, annex-f, solar-index, f107, sunspot, solar-cycle, albedo-ir, reference-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Solar/Absolute-Index Reference Data (space-systems/ecss/e1004-ref-indices)

Use when the task is selecting solar-activity and albedo/IR reference data
under ECSS-E-ST-10-04C Annex F (informative) — deciding which solar-cycle
activity level a case must assume from its F10.7 value, retrieving the
reference index set for that level, retrieving the Earth albedo/IR reference
for a thermal case, validating a proposed index value against its valid range,
interpolating an index across the solar-cycle phase, and assembling the
reference record a thermal or radiation case must cite.

## Domain quick reference

- Solar activity is represented by reference levels — minimum, mean, and
  maximum — rather than by a single number, because a mission case must
  bound the environment over its lifetime. A worst-hot thermal case uses
  the maximum level; a worst-cold case uses the minimum; a nominal case
  uses the mean.
- F10.7 (the 10.7 cm solar radio flux, in solar flux units) is the primary
  activity proxy. The level boundaries partition the F10.7 range so a case's
  assumed flux maps deterministically onto one of the three reference levels.
- The activity level selects both the solar index reference (F10.7 flux and
  sunspot number) and the Earth albedo/IR reference (bond albedo and emitted
  infrared flux). These must be drawn from the same level so a thermal
  balance is self-consistent.
- Each reference dataset has a valid range. A proposed value outside its
  dataset range is a data-usage violation and must be reported, not silently
  clamped — the engineer either corrects the input or documents a deviation.
- When a case gives a solar-cycle phase fraction (0 = cycle minimum,
  1 = next cycle minimum), the index may be interpolated piecewise-linearly
  between the tabulated levels; extrapolation beyond the tabulated range is
  not permitted.

## Workflow

1. Read the case's assumed F10.7 solar flux (sfu) and classify it:
   `classify_f107_activity_level(f107_solar_flux_sfu)` returns
   `"minimum"`, `"mean"`, or `"maximum"`.
2. Retrieve the matching solar index reference:
   `get_solar_index(level)` returns the F10.7 flux and sunspot number for
   the level.
3. Retrieve the matching albedo/IR reference:
   `get_albedo_ir_reference(level)` returns Earth bond albedo and emitted
   infrared flux for the level.
4. Validate any proposed index value:
   `validate_index_value(dataset_id, value)` returns a violation list
   (empty when within the dataset's valid range).
5. If a solar-cycle phase fraction is given, interpolate:
   `interpolate_solar_cycle_index(dataset_id, cycle_phase_fraction)`.
6. Cite the source: `source_reference_for_parameter(parameter)` returns the
   canonical Annex F citation string for a reference parameter.
7. For a worst-hot or worst-cold case, assemble the combined record:
   `thermal_case_reference(case)`.
8. Run the full review for one lookup and check it is clean:
   `reference_data_review(request)` → `is_reference_data_valid(review)`.

## Pitfalls

- Mixing levels: pulling the F10.7 index from one activity level and the
  albedo/IR reference from another produces a physically inconsistent case.
  Always derive both from the same categorized activity level.
- Silently clamping an out-of-range value: `validate_index_value` reports
  violations; do not discard them. An out-of-range index is a finding to
  resolve, not a value to trim.
- Gerund descriptions and security-marking vocabulary: the content-policy
  gate flags the security-marking word beginning "classif-"; use
  "categorized" instead.
- Extrapolating the cycle-phase interpolation outside the tabulated range
  is not supported — treat it as a data gap, not a value to invent.

## Behavior contract (gate 3)

`scripts/test_e1004_ref_indices.py` (stdlib unittest, offline) verifies
activity-level classification boundaries, index and albedo/IR retrieval per
level, valid-range enforcement (in-range accepted, out-of-range reported),
cycle-phase interpolation endpoints, source-citation lookup, and the full
review validity check.

## Compliance

ECSS-E-ST-10-04C Annex F is informative reference data. This leaf implements
only common-knowledge procedure and reference-value structure; the standard
and clause are cited as the anchor. `license: Apache-2.0`,
`compliance: STANDARDS-REF`, `standards: ecss` (reference-only), `gated: false`.
