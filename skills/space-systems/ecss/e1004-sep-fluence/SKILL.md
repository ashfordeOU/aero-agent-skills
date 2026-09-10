---
name: e1004-sep-fluence
description: "Use when you must compute solar proton fluences for a mission's radiation environment using the ESP model per ECSS-E-ST-10-04C clause 9.2.2.2 and Annex B.6: select the confidence level and mission duration, compute the cumulative fluence spectrum across energy thresholds, and verify the fluence is monotonically consistent with duration, confidence level and energy threshold before it feeds the radiation environment specification. Trigger: solar proton fluence, ESP model, solar particle event fluence, confidence level, mission duration, sep fluence, e-st-10-04c 9.2.2.2, annex b.6."
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
  tags: [ecss, e-st-10-04c, sep, solar-proton, esp-model, fluence, radiation-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Proton Fluence — ESP Model (space-systems/ecss/e1004-sep-fluence)

Use when the task is ECSS-E-ST-10-04C clause 9.2.2.2 and Annex B.6:
computing the cumulative solar proton fluence a mission must design
against, using the ESP (Emission of Solar Protons) statistical model,
for a stated confidence level and mission duration.

## Domain quick reference

- Solar particle events (SPEs) are stochastic: how many events occur,
  and how large each one is, varies unpredictably from cycle to cycle.
  The ESP model does not predict individual events; it gives the
  cumulative proton fluence (integral flux above a stated energy
  threshold, accumulated over the whole mission duration) that is
  exceeded with a stated probability (1 minus the confidence level).
- Two independent inputs drive the result: the mission duration (in
  years of solar-particle-event exposure to be covered) and the
  confidence level (the probability that the true cumulative fluence
  stays at or below the computed value). Both must be fixed by the
  project's radiation requirement before the model is run — the model
  does not choose them.
- For a fixed confidence level, fluence increases with mission
  duration: a longer exposure window can accumulate more events. For a
  fixed duration, fluence increases with confidence level: demanding a
  smaller probability of exceedance costs a larger design value. A
  fluence result that violates either trend for otherwise-identical
  inputs indicates a model or input error, not a valid result.
- The fluence is threshold-specific: it is reported per proton energy
  threshold (for example >10 MeV, >30 MeV, >60 MeV, >100 MeV). Because
  integral flux above a higher energy threshold can only be less than
  or equal to the integral flux above a lower one (protons counted
  above the higher threshold are a subset of those above the lower
  one), the fluence spectrum across thresholds must be
  non-increasing with increasing threshold energy.
- The ESP model's historical database spans a limited number of solar
  cycles; confidence levels pushed very close to 100% extrapolate well
  beyond the observed event population and carry materially larger
  statistical uncertainty than mid-range confidence levels (for
  example 80-95%). This leaf treats the underlying ESP numeric
  coefficients as an external, pluggable model call (implemented by
  the sibling Annex B.6 leaf, e1004-b6-esp) and focuses on selecting
  valid inputs, invoking that model per threshold, and verifying the
  result is self-consistent before it is handed to the radiation
  environment specification (sibling e1004-rad-env-spec).
- This leaf covers cumulative fluence only. Worst-case single-event
  peak flux (for single-event-effect analyses) is a separate concern,
  covered by sibling leaf e1004-sep-peakflux; do not substitute one
  for the other.

## Workflow

1. Fix the two policy inputs from the project's radiation requirement:
   mission_duration_years (the exposure period to cover) and
   confidence_level_pct (the required probability of non-exceedance).
   Validate both with validate_mission_duration and
   validate_confidence_level before proceeding.
2. Fix the list of energy thresholds (MeV) the radiation environment
   specification needs (driven by the parts/shielding analyses that
   consume this data, for example total-dose or SEE thresholds).
3. For each threshold, call compute_threshold_fluence, which invokes
   the pluggable ESP model function (model_fn) for that threshold,
   duration, and confidence level, and checks the returned fluence is
   a finite, non-negative number.
4. Assemble the full spectrum with compute_fluence_spectrum, which
   also checks the non-increasing-with-energy invariant across
   thresholds and reports any violation instead of silently accepting
   an inconsistent spectrum.
5. Before accepting the spectrum for a given duration/confidence
   policy, spot-check the model's monotonic trends with
   check_confidence_monotonicity (fluence must not decrease as
   confidence level increases, duration held fixed) and
   check_duration_monotonicity (fluence must not decrease as duration
   increases, confidence level held fixed).
6. Combine steps 3-5 with sep_fluence_specification to produce the
   fluence entry for the mission's radiation environment
   specification; do not hand a spectrum to e1004-rad-env-spec unless
   every consistency check in the result passed.

## Pitfalls

- Running the ESP model with a duration or confidence level that was
  never actually approved in the project's radiation requirement,
  instead of ones fixed by that requirement.
- Accepting a fluence spectrum where a higher energy threshold reports
  a larger fluence than a lower one — a sign of a threshold mix-up or
  a broken model call, not a real result.
- Treating an extreme confidence level (for example 99.9%) as free of
  extra uncertainty; the ESP model's short historical baseline makes
  such values far less reliable than mid-range confidence levels.
- Confusing cumulative mission fluence (this leaf) with worst-case
  single-event peak flux (e1004-sep-peakflux) — they answer different
  design questions and are not interchangeable.
- Hardcoding the ESP model's numeric coefficients into this workflow
  leaf instead of delegating to the dedicated Annex B.6 implementation
  (e1004-b6-esp) via the model_fn hook.

## Behavior contract (gate 3)

The input-validation, spectrum-assembly, and monotonicity-check logic
is exercised by the gate 3 contract test:
scripts/test_e1004_sep_fluence.py against
scripts/e1004_sep_fluence_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_sep_fluence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
