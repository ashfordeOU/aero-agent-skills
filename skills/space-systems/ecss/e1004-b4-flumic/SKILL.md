---
name: e1004-b4-flumic
description: "Use when implementing the FLUMIC outer/inner radiation belt worst-case trapped electron model under ECSS-E-ST-10-04C Annex B.4: select the belt region (inner belt, outer belt, or both for a belt-crossing orbit), apply the confidence (percentile) level and the worst-case exposure-duration class the analysis purpose requires, evaluate the resulting electron energy spectrum, and integrate the flux above a shielding-relevant threshold energy for internal (deep-dielectric) charging design. Trigger: FLUMIC, worst-case electron spectrum, outer belt, inner belt, internal charging, deep dielectric charging, trapped electrons, Annex B.4, e-st-10-04, ecss, space environment, radiation belt model."
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
  tags: [ecss, e-st-10-04c, flumic, trapped-electrons, internal-charging, radiation-belt, annex-b4]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS FLUMIC Worst-Case Trapped Electron Model (space-systems/ecss/e1004-b4-flumic)

Use when the task is implementing the FLUMIC worst-case trapped
electron model under ECSS-E-ST-10-04C Annex B.4, to bound the electron
energy spectrum in the outer radiation belt (including geostationary
altitudes) and the inner belt for internal (deep-dielectric) charging
design.

## Domain quick reference

- FLUMIC characterizes the trapped electron environment as a
  worst-case energy spectrum rather than a long-term average: it
  answers "how bad can the electron flux get" for a stated confidence
  level and exposure duration, which is the input internal-charging
  analyses need, not the mission-average flux the long-term belt
  models (sibling e1004-trapped-leo, e1004-geo-ige, e1004-meo-meov2
  leaves) provide.
- The model spans two distinct belt regions with different reference
  spectra: the outer belt (harder spectrum, extending to higher
  electron energies, dominant driver of GEO and outer-belt internal
  charging risk) and the inner belt (softer spectrum). An orbit that
  crosses both regions needs the combined contribution of both.
- "Worst case" is only meaningful relative to a confidence (percentile)
  level and an exposure-duration class: a short duration class
  (a single worst day) bounds transient peak flux for peak-risk
  assessments, while a long duration class (the mission life) gives
  the appropriate cumulative-fluence bound -- these are not
  interchangeable, and picking the wrong one for the analysis purpose
  gives a spectrum that does not answer the question being asked.
- Internal (deep-dielectric) charging risk depends on the flux of
  electrons energetic enough to penetrate typical shielding and
  deposit charge in dielectric materials, so the assessment needs the
  integral flux above a shielding-relevant threshold energy, not the
  full differential spectrum.
- This leaf scopes the FLUMIC spectral evaluation and threshold
  integration only. Rolling FLUMIC together with the NASA worst-case
  GEO electron spectrum into an internal-charging assessment is the
  sibling e1004-internal-charging leaf (clause 9.2.1.3); the NASA
  worst-case GEO spectrum itself is the sibling e1004-b5-geo-wc leaf
  (Annex B.5).

## Workflow

1. For each internal-charging case, record its belt region(s)
   (inner belt, outer belt, or both, from the orbit's belt crossings),
   its analysis purpose (peak transient risk or cumulative fluence),
   the confidence (percentile) level required, the duration class
   assumed, and the shielding-relevant threshold energy.
2. Determine the duration class the analysis purpose requires (a
   worst-day duration for peak-risk assessments; a mission-life
   duration for cumulative-fluence assessments) and verify the case's
   assumed duration class matches it; flag a mismatch rather than
   evaluating a spectrum that does not answer the analysis question.
3. Evaluate the FLUMIC differential electron energy spectrum for each
   of the case's belt regions at the case's confidence level and
   duration class.
4. Integrate each region's spectrum above the case's threshold energy
   to obtain the region's contribution to the shielding-relevant
   electron flux.
5. Sum the per-region contributions to obtain the case's total
   flux above threshold; a belt-crossing orbit must include every
   region it crosses, not just the one with the higher reference flux.
6. Mark the case compliant only when its duration class matches what
   its analysis purpose requires, and roll every case's compliance
   into the internal-charging input record; do not hand a
   duration-mismatched spectrum to the internal-charging assessment.

## Pitfalls

- Using a mission-life duration class for a peak transient-risk
  assessment (or a worst-day duration class for a cumulative-fluence
  assessment), which understates peak risk or overstates cumulative
  fluence because the two exposure-duration classes answer different
  questions.
- Evaluating only the outer-belt spectrum for an orbit that also
  dwells in the inner belt, dropping a real contribution to the
  shielding-relevant flux.
- Using the full differential spectrum (or the flux at a single
  energy) in place of the integral flux above the shielding-relevant
  threshold energy, which does not represent the electrons actually
  capable of causing deep-dielectric charging.
- Treating FLUMIC and the NASA worst-case GEO spectrum as
  interchangeable rather than complementary worst-case bounds that the
  internal-charging assessment (sibling e1004-internal-charging leaf)
  must consider together.

## Behavior contract (gate 3)

The region selection, confidence/duration scaling, spectrum
evaluation, threshold integration, and duration-class compliance logic
is exercised by the gate 3 contract test:
scripts/test_e1004_b4_flumic.py against scripts/e1004_b4_flumic_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1004_b4_flumic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
