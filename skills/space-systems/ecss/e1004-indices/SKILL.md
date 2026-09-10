---
name: e1004-indices
description: "Use when you must determine which solar and geomagnetic activity indices (F10.7, Ap/Kp) apply to a space environment analysis epoch under ECSS-E-ST-10-04C clause 6.2.2 and Annex A: identify the index set an analysis purpose requires (atmospheric drag/lifetime, electromagnetic radiation reference, geomagnetic field epoch), classify the solar-cycle epoch from the F10.7 81-day-average index into solar minimum/mean/maximum, select the reference index values for that epoch, and verify a case's provided indices are complete and match the worst-case solar condition its purpose requires before the epoch is handed to the leaf that consumes it. Trigger: F10.7, solar radio flux, Ap index, Kp index, geomagnetic activity index, solar activity index, solar-cycle epoch, environment epoch selection, e-st-10-04c 6.2.2, annex a, ecss, space environment indices."
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
  tags: [ecss, e-st-10-04c, indices, f10.7, ap-index, kp-index, solar-activity, geomagnetic-activity, space-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar/Geomagnetic Activity Indices (space-systems/ecss/e1004-indices)

Use when the task is selecting which solar and geomagnetic activity
indices, and which reference values for them, apply to a space
environment analysis epoch under ECSS-E-ST-10-04C clause 6.2.2 and
Annex A.

## Domain quick reference

- F10.7 is the 10.7 cm solar radio flux, the standard proxy for solar
  EUV/UV output that drives upper-atmosphere heating (feeding
  atmosphere density models) and the EM radiation environment; it is
  reported both as a daily value and as an 81-day-centered running
  average (F10.7bar) that smooths out the roughly 27-day solar-rotation
  variation for models that need a slowly varying driver.
- Ap is the daily, linear-scale geomagnetic activity index derived from
  the 3-hourly, quasi-logarithmic Kp index; both track geomagnetic
  disturbance level (driven by solar wind and coronal mass ejections)
  and feed atmosphere density models (geomagnetic heating term) and
  external geomagnetic field model epochs.
- Solar activity varies over an approximately 11-year solar cycle
  between a solar-minimum epoch (low F10.7, low Ap) and a
  solar-maximum epoch (high F10.7, higher Ap); different analysis
  purposes need different worst-case points on this cycle, not simply
  "high" or "low" activity taken in isolation.
- Atmospheric-drag and thermal analyses need the solar-maximum epoch as
  their worst case, since high F10.7/Ap heats and expands the
  thermosphere, raising density and drag at a given altitude.
- Deorbit/orbital-lifetime compliance analyses need the opposite worst
  case: solar minimum, since low density gives the slowest decay and
  therefore the longest predicted lifetime -- the case least likely to
  meet a maximum-lifetime requirement.
- EM radiation reference terms (consumed by the sibling
  e1004-em-radiation leaf) typically use the solar-mean epoch rather
  than either extreme.
- Reference values for each epoch come from the Annex A solar-cycle
  data tables; this leaf provides the selection logic and
  characteristic reference magnitudes, while the full tabulated Annex A
  history is the sibling e1004-annex-a-data reference leaf.
- This leaf scopes index-requirement identification, solar-cycle epoch
  determination, reference-value selection, and
  completeness/condition verification only. Applying the selected
  indices inside a specific model (atmosphere density, EM radiation,
  external geomagnetic field) is the job of the consuming sibling leaf
  (e1004-atmosphere, e1004-em-radiation, e1004-geomag).

## Workflow

1. For each environment analysis case, record its id, its purpose
   (drag_worst_case, deorbit_lifetime_worst_case, em_radiation_reference,
   or geomagnetic_field_epoch), and the indices dict it has been given
   (any of f107_daily, f107_81day_avg, ap_daily, kp_3hourly).
2. Determine the index set the case's purpose requires (drag_worst_case
   and deorbit_lifetime_worst_case both require f107_daily,
   f107_81day_avg and ap_daily; em_radiation_reference requires
   f107_81day_avg; geomagnetic_field_epoch requires kp_3hourly) and
   check the case's indices dict for completeness against it, noting
   any missing index by name.
3. When f107_81day_avg is present, determine the solar-cycle epoch it
   represents -- solar_minimum, solar_mean, or solar_maximum -- against
   the reference thresholds.
4. Determine the worst-case solar condition the case's purpose requires
   (solar_maximum for drag_worst_case, solar_minimum for
   deorbit_lifetime_worst_case, no fixed requirement for
   em_radiation_reference or geomagnetic_field_epoch) and compare the
   case's solar-cycle epoch determination against it.
5. When a case needs standard reference index values rather than
   mission-specific measurements, select them from the reference table
   for the required epoch (or the solar-mean epoch when the purpose has
   no fixed worst-case requirement).
6. Mark a case compliant only when its indices are complete and, where
   the purpose fixes a required solar condition, its solar-cycle epoch
   matches it; roll every case's result into an assessment record and
   do not hand an epoch to a consuming leaf while its case remains
   non-compliant.

## Pitfalls

- Using the daily (instantaneous) F10.7 value where a model needs the
  81-day-centered average, or vice versa -- the daily value carries
  short-term solar-rotation noise the averaged driver is meant to
  smooth out.
- Selecting solar-maximum indices for a deorbit/lifetime compliance
  case: that direction understates decay time and hides a
  lifetime-requirement violation that only shows up at solar minimum.
- Treating Ap and F10.7 as independently chosen for a reference epoch
  -- Annex A pairs them by solar-cycle position, so combining, say,
  solar-minimum F10.7 with solar-maximum Ap is not a self-consistent
  reference epoch.
- Confusing the 3-hourly, quasi-logarithmic Kp index with its daily,
  linear-scale Ap counterpart when a model specifically calls for one
  or the other.

## Behavior contract (gate 3)

The index-requirement identification, solar-cycle epoch determination,
reference-value selection, and completeness/condition verification
logic is exercised by the gate 3 contract test:
scripts/test_e1004_indices.py against scripts/e1004_indices_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1004_indices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
